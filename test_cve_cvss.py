"""Testes determinísticos: o serviço externo é simulado, o cálculo é real."""
from copy import deepcopy
import io
import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from consulta_cve import ClienteNVD, ErroConsultaCVE, interpretar_resposta
from dados import ArmazenamentoJSON
from interface_cvss import ler_avaliacao
from inventario import Inventario
from menus import MenuVulnerabilidades
from modelos import SeveridadeVulnerabilidade, Vulnerabilidade
from seguranca import AvaliacaoCVSS, calcular_cvss, classificar, validar_cve
from test_sistema import novo_equipamento


V3 = 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'
V4 = 'CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:N'
CVE = 'CVE-2021-44228'


def resposta(vetor=V3):
    avaliacao = calcular_cvss(vetor)
    return {'vulnerabilities': [{'cve': {
        'id': CVE, 'vulnStatus': 'Analyzed',
        'descriptions': [{'lang': 'en', 'value': 'Descrição simulada para teste.'}],
        'metrics': {'cvssMetricV40' if avaliacao.versao == '4.0' else 'cvssMetricV31': [{
            'source': 'fonte@example.org', 'type': 'Primary',
            'cvssData': {'version': avaliacao.versao, 'vectorString': vetor, 'baseScore': avaliacao.nota}}]}}}]}


@pytest.mark.parametrize('vetor,nota', [(V3, 9.8), (V3.replace('3.1', '3.0'), 9.8),
                                      (V4, 9.9), (V3.replace('C:H/I:H/A:H', 'C:N/I:N/A:N'), 0.0),
                                      ('CVSS:3.0/AV:P/AC:H/PR:H/UI:R/S:C/C:H/I:H/A:N', 6.5)])
def test_calculo_referencia(vetor, nota):
    assert calcular_cvss(vetor).nota == nota


@pytest.mark.parametrize('nota,esperada', [(0, 'NENHUMA'), (0.1, 'BAIXA'), (3.9, 'BAIXA'),
                                         (4, 'MEDIA'), (6.9, 'MEDIA'), (7, 'ALTA'), (8.9, 'ALTA'),
                                         (9, 'CRITICA'), (10, 'CRITICA')])
def test_faixas(nota, esperada):
    assert classificar(nota) == esperada


@pytest.mark.parametrize('nota', [-1, 11, float('nan'), float('inf'), True, '9.8', None])
def test_nota_invalida(nota):
    with pytest.raises(ValueError):
        classificar(nota)


@pytest.mark.parametrize('vetor', ['', None, 'CVSS:2.0/AV:N', V3 + '/AV:N', V3 + '/E:F',
                                   V4 + '/E:P', V3.replace('/A:H', ''), V3.replace('AV:N', 'AV:Z'),
                                   V4.replace('AV:N', 'AV:Z')])
def test_vetor_invalido(vetor):
    with pytest.raises(ValueError):
        calcular_cvss(vetor)


def test_cve_formato_nao_confirma_existencia():
    assert validar_cve(' cve-2021-44228 ') == CVE
    assert validar_cve('CVE-2026-1234567') == 'CVE-2026-1234567'
    assert validar_cve('') is None
    for valor in ['CVE-2021-123', 'CVE-21-1234', CVE + '?x=1', 1]:
        with pytest.raises(ValueError):
            validar_cve(valor)


def test_persistencia_e_compatibilidade(tmp_path):
    antigo = {'descricao': 'Problema', 'categoria': 'Software', 'severidade': 'ALTA', 'status': 'ABERTA'}
    v = Vulnerabilidade.from_dict(antigo)
    assert v.cvss is None and v.severidade == SeveridadeVulnerabilidade.ALTA
    v.cvss = calcular_cvss(V3)
    v.cve_id = CVE
    ativo = novo_equipamento()
    ativo.adicionar_vulnerabilidade(v)
    armazenamento = ArmazenamentoJSON(str(tmp_path / 'dados.json'))
    armazenamento.salvar([ativo])
    restaurado = armazenamento.carregar()[0].vulnerabilidades[0]
    assert restaurado.to_dict() == v.to_dict()
    assert restaurado.severidade == SeveridadeVulnerabilidade.CRITICA
    dados = v.cvss.to_dict()
    dados['nota'] = 1
    with pytest.raises(ValueError):
        AvaliacaoCVSS.from_dict(dados)


def test_nvd_multiplas_fontes_versoes():
    dados = resposta()
    dados['vulnerabilities'][0]['cve']['metrics'].update(resposta(V4)['vulnerabilities'][0]['cve']['metrics'])
    resultado = interpretar_resposta(dados, CVE)
    assert [v.versao for v in resultado.avaliacoes] == ['4.0', '3.1']
    assert resultado.avaliacoes[0].fonte == 'fonte@example.org'
    assert resultado.consultado_em


def test_nvd_sem_nota_e_divergencia():
    dados = resposta()
    dados['vulnerabilities'][0]['cve']['metrics']['cvssMetricV31'][0]['cvssData']['baseScore'] = 1
    resultado = interpretar_resposta(dados, CVE)
    assert resultado.avaliacoes == () and len(resultado.avisos) == 2
    dados['vulnerabilities'][0]['cve'].pop('metrics')
    assert interpretar_resposta(dados, CVE).avaliacoes == ()


@pytest.mark.parametrize('dados', [{}, None, {'vulnerabilities': {}}, {'vulnerabilities': []},
                                  {'vulnerabilities': [{'cve': {'id': 'CVE-2020-1234'}}]}])
def test_nvd_resposta_invalida_ou_ausente(dados):
    with pytest.raises(ErroConsultaCVE):
        interpretar_resposta(dados, CVE)


def test_nvd_rejeitado():
    dados = resposta()
    dados['vulnerabilities'][0]['cve']['vulnStatus'] = 'Rejected'
    with pytest.raises(ErroConsultaCVE, match='rejeitado'):
        interpretar_resposta(dados, CVE)


def test_requisicao_e_intervalo():
    with patch('consulta_cve.urlopen', side_effect=lambda *a, **k: io.BytesIO(json.dumps(resposta()).encode())) as abrir, \
         patch('consulta_cve.time.monotonic', side_effect=[100, 101, 106]), \
         patch('consulta_cve.time.sleep') as esperar:
        cliente = ClienteNVD(api_key='')
        cliente.api_key = ''
        assert cliente.consultar(CVE).cve_id == CVE
        cliente.consultar(CVE)
        esperar.assert_called_once_with(5.0)
        assert abrir.call_args.args[0].full_url.endswith('?cveId=' + CVE)
        assert abrir.call_args.kwargs['timeout'] == 15


@pytest.mark.parametrize('erro', [HTTPError('url', 429, 'limit', {}, None),
                                HTTPError('url', 403, 'blocked', {}, None),
                                HTTPError('url', 500, 'server', {}, None),
                                URLError('offline'), TimeoutError()])
def test_rede_falha_controlada(erro):
    with patch('consulta_cve.urlopen', side_effect=erro), pytest.raises(ErroConsultaCVE):
        ClienteNVD().consultar(CVE)


def test_rede_json_invalido():
    with patch('consulta_cve.urlopen', return_value=io.BytesIO(b'<!doctype html>')), pytest.raises(ErroConsultaCVE):
        ClienteNVD().consultar(CVE)


def test_questionario():
    with patch('builtins.input', side_effect=['1', '1', '1', '1', '1', '1', '3', '3', '3']):
        assert ler_avaliacao().vetor == V3


def preparar_menu(tmp_path):
    inventario = Inventario(ArmazenamentoJSON(str(tmp_path / 'dados.json')))
    inventario.adicionar(novo_equipamento())
    return MenuVulnerabilidades(inventario), inventario


def test_menu_importacao_com_recarga(tmp_path):
    menu, inventario = preparar_menu(tmp_path)
    resultado = interpretar_resposta(resposta(), CVE)
    with patch('consulta_cve.ClienteNVD.consultar', return_value=resultado), \
         patch('builtins.input', side_effect=[CVE, 's', '1', 'Software', '1']):
        menu.consultar_cve()
    inventario.carregar()
    v = inventario.listar()[0].vulnerabilidades[0]
    assert v.cve_id == CVE and v.cvss.nota == 9.8
    # Uma nova consulta não duplica a ocorrência no mesmo ativo.
    with patch('consulta_cve.ClienteNVD.consultar', return_value=resultado), \
         patch('builtins.input', side_effect=[CVE, 's', '1']):
        menu.consultar_cve()
    assert len(inventario.listar()[0].vulnerabilidades) == 1


def test_menu_sem_nota(tmp_path):
    menu, inventario = preparar_menu(tmp_path)
    dados = deepcopy(resposta())
    dados['vulnerabilities'][0]['cve']['metrics'] = {}
    with patch('consulta_cve.ClienteNVD.consultar', return_value=interpretar_resposta(dados, CVE)), \
         patch('builtins.input', side_effect=[CVE, 's', '1', 'Software', '1']):
        menu.consultar_cve()
    v = inventario.listar()[0].vulnerabilidades[0]
    assert v.cvss is None and v.severidade == SeveridadeVulnerabilidade.NAO_AVALIADA


def test_menu_calculo_aplicado_e_cancelamento(tmp_path):
    menu, inventario = preparar_menu(tmp_path)
    v = Vulnerabilidade('Falha', 'Software', SeveridadeVulnerabilidade.BAIXA)
    inventario.listar()[0].adicionar_vulnerabilidade(v)
    with patch('builtins.input', side_effect=['2', V3, 's', '1', '1', CVE]):
        menu.calcular_cvss()
    assert v.cvss.nota == 9.8 and v.cve_id == CVE
    with patch('builtins.input', side_effect=['2', V4, 's', '1', '1', 'n']):
        menu.calcular_cvss()
    assert v.cvss.nota == 9.8


def test_menu_offline_nao_modifica_dados(tmp_path):
    menu, inventario = preparar_menu(tmp_path)
    with patch('consulta_cve.ClienteNVD.consultar', side_effect=ErroConsultaCVE('offline')), \
         patch('builtins.input', return_value=CVE):
        menu.consultar_cve()
    assert not inventario.listar()[0].vulnerabilidades
