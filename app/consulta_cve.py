"""Consulta explícita à API NVD 2.0. Nenhum equipamento é enviado ao serviço."""
from dataclasses import dataclass
from datetime import datetime, timezone
from http.client import HTTPException
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.seguranca import AvaliacaoCVSS, calcular_cvss, validar_cve


class ErroConsultaCVE(Exception):
    pass


@dataclass(frozen=True)
class ResultadoCVE:
    cve_id: str
    descricao: str
    status: str
    avaliacoes: tuple[AvaliacaoCVSS, ...]
    consultado_em: str
    avisos: tuple[str, ...] = ()

    @property
    def url(self):
        return f'https://nvd.nist.gov/vuln/detail/{self.cve_id}'


class ClienteNVD:
    URL = 'https://services.nvd.nist.gov/rest/json/cves/2.0'

    def __init__(self, api_key=None, timeout=15):
        self.api_key = api_key or os.environ.get('NVD_API_KEY', '')
        self.timeout = timeout
        self._ultima_consulta = None

    def consultar(self, cve_id):
        cve_id = validar_cve(cve_id)
        if cve_id is None:
            raise ValueError('Informe um CVE para consultar.')
        # Intervalo conservador, inclusive após falhas; sem repetição automática.
        intervalo = 0.6 if self.api_key else 6.0
        if self._ultima_consulta is not None:
            restante = intervalo - (time.monotonic() - self._ultima_consulta)
            if restante > 0:
                time.sleep(restante)
        headers = {'Accept': 'application/json', 'User-Agent': 'InventarioAcademico/1.0'}
        if self.api_key:
            headers['apiKey'] = self.api_key
        requisicao = Request(self.URL + '?' + urlencode({'cveId': cve_id}), headers=headers)
        self._ultima_consulta = time.monotonic()
        try:
            with urlopen(requisicao, timeout=self.timeout) as resposta:
                corpo = resposta.read(2_000_001)
            if len(corpo) > 2_000_000:
                raise ErroConsultaCVE('Resposta da NVD excedeu o tamanho esperado.')
            dados = json.loads(corpo)
        except HTTPError as erro:
            if erro.code in (403, 429):
                raise ErroConsultaCVE('A NVD limitou ou recusou a consulta. Tente mais tarde; confira NVD_API_KEY.') from erro
            raise ErroConsultaCVE(f'A NVD respondeu com erro HTTP {erro.code}.') from erro
        except (URLError, TimeoutError, OSError, HTTPException) as erro:
            raise ErroConsultaCVE('Não foi possível acessar a NVD. Confira a conexão e tente novamente.') from erro
        except (ValueError, UnicodeError) as erro:
            raise ErroConsultaCVE('A NVD retornou conteúdo inválido.') from erro
        return interpretar_resposta(dados, cve_id)


def interpretar_resposta(dados, cve_id):
    try:
        registros = dados['vulnerabilities']
        if not isinstance(registros, list):
            raise ValueError()
        if not registros:
            raise ErroConsultaCVE('CVE não encontrado na NVD. Isso não comprova que o identificador não existe.')
        registro = next(item['cve'] for item in registros if item['cve']['id'] == cve_id)
        status = registro.get('vulnStatus', 'Não informado')
        if status == 'Rejected':
            raise ErroConsultaCVE('Este CVE foi rejeitado. Ele não será importado como vulnerabilidade válida.')
        descricoes = registro.get('descriptions', [])
        descricao = next((d['value'] for d in descricoes if d.get('lang') == 'pt'), None)
        if not descricao:
            descricao = next((d['value'] for d in descricoes if d.get('lang') == 'en'), cve_id)
        if not isinstance(descricao, str) or not isinstance(status, str):
            raise ValueError()
        metricas = registro.get('metrics', {})
        avaliacoes, avisos = [], []
        # Exibe todas; o usuário escolhe, sem misturar versões/fontes.
        for campo in ('cvssMetricV40', 'cvssMetricV31', 'cvssMetricV30'):
            for item in metricas.get(campo, []):
                try:
                    cvss = item['cvssData']
                    fonte = item['source']
                    avaliacao = calcular_cvss(cvss['vectorString'], fonte)
                    if cvss['version'] != avaliacao.versao or cvss['baseScore'] != avaliacao.nota:
                        raise ValueError('A nota publicada diverge do vetor.')
                    avaliacoes.append(avaliacao)
                except (KeyError, TypeError, ValueError) as erro:
                    avisos.append(f'Avaliação {campo} ignorada: dados ausentes, inválidos ou divergentes ({erro}).')
        if not avaliacoes:
            avisos.append('Sem avaliação Base compatível (3.0/3.1/4.0). Ausência de nota não significa nota zero.')
        return ResultadoCVE(cve_id, descricao, status, tuple(avaliacoes),
                            datetime.now(timezone.utc).isoformat(), tuple(avisos))
    except (KeyError, TypeError, ValueError, AttributeError, StopIteration) as erro:
        raise ErroConsultaCVE('Resposta da NVD em formato inesperado.') from erro
