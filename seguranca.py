"""Validação de CVE e cálculo de CVSS Base, sem acesso à rede ou terminal."""
from dataclasses import dataclass
import math
import re

from cvss import CVSS3, CVSS4
from cvss.exceptions import CVSSError


BASE3 = ('AV', 'AC', 'PR', 'UI', 'S', 'C', 'I', 'A')
BASE4 = ('AV', 'AC', 'AT', 'PR', 'UI', 'VC', 'VI', 'VA', 'SC', 'SI', 'SA')


def validar_cve(valor):
    if valor is None or valor == '':
        return None
    if not isinstance(valor, str):
        raise ValueError('CVE deve ser texto.')
    valor = valor.strip().upper()
    if not re.fullmatch(r'CVE-[0-9]{4}-[0-9]{4,}', valor):
        raise ValueError('Use CVE-AAAA-NNNN (quatro ou mais dígitos finais).')
    return valor


def classificar(nota):
    if isinstance(nota, bool) or not isinstance(nota, (int, float)):
        raise ValueError('A nota CVSS deve ser numérica.')
    if not math.isfinite(nota) or not 0 <= nota <= 10:
        raise ValueError('A nota CVSS deve estar entre 0 e 10.')
    if nota == 0:
        return 'NENHUMA'
    if nota < 4:
        return 'BAIXA'
    if nota < 7:
        return 'MEDIA'
    if nota < 9:
        return 'ALTA'
    return 'CRITICA'


@dataclass(frozen=True)
class AvaliacaoCVSS:
    versao: str
    vetor: str
    nota: float
    fonte: str = 'Cálculo local'

    @property
    def severidade(self):
        return classificar(self.nota)

    def to_dict(self):
        return dict(versao=self.versao, vetor=self.vetor, nota=self.nota, fonte=self.fonte)

    @classmethod
    def from_dict(cls, dados):
        if not isinstance(dados, dict):
            raise ValueError('CVSS deve ser um objeto JSON.')
        avaliacao = calcular_cvss(dados.get('vetor'), dados.get('fonte', 'Cálculo local'))
        classificar(dados.get('nota'))
        if dados.get('versao') != avaliacao.versao or dados['nota'] != avaliacao.nota:
            raise ValueError('Nota ou versão CVSS não corresponde ao vetor.')
        return avaliacao


def calcular_cvss(vetor, fonte='Cálculo local'):
    if not isinstance(vetor, str) or not vetor.strip():
        raise ValueError('Informe um vetor CVSS.')
    if not isinstance(fonte, str) or not fonte.strip():
        raise ValueError('Informe a fonte da avaliação CVSS.')
    vetor = vetor.strip()
    prefixo = vetor.split('/')[0]
    if prefixo not in ('CVSS:3.0', 'CVSS:3.1', 'CVSS:4.0'):
        raise ValueError('Versões aceitas: CVSS:3.0, CVSS:3.1 e CVSS:4.0.')
    chaves = [parte.split(':')[0] for parte in vetor.split('/')[1:]]
    esperadas = BASE4 if prefixo == 'CVSS:4.0' else BASE3
    # Não confundir CVSS Base com notas temporais, ambientais ou de ameaça.
    if len(chaves) != len(set(chaves)):
        raise ValueError('O vetor possui métricas duplicadas.')
    if set(chaves) != set(esperadas):
        raise ValueError('Informe somente as métricas Base: ' + ', '.join(esperadas))
    try:
        calculadora = (CVSS4 if prefixo == 'CVSS:4.0' else CVSS3)(vetor)
        nota = float(calculadora.scores()[0])
        normalizado = calculadora.clean_vector()
    except CVSSError as erro:
        raise ValueError(f'Vetor CVSS inválido: {erro}') from erro
    return AvaliacaoCVSS(prefixo.split(':')[1], normalizado, nota, fonte.strip())
