"""Integração real: HTTP Flask, JSON temporário, sessões, CSRF, domínio e risco."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import re
from unittest.mock import patch

import pytest

from consulta_cve import ErroConsultaCVE, interpretar_resposta
from servicos import ConflitoEdicao
from test_cve_cvss import CVE, V3, resposta
from test_sistema import novo_equipamento
from web import criar_app


@pytest.fixture
def app(tmp_path):
    return criar_app({'TESTING': True, 'SECRET_KEY': 'segredo-exclusivo-dos-testes-' * 2,
                      'USUARIOS_ARQUIVO': str(tmp_path / 'usuarios.json'),
                      'INVENTARIO_ARQUIVO': str(tmp_path / 'inventario.json')})


def token(client):
    client.get('/login', follow_redirects=True)
    with client.session_transaction() as s:
        return s['csrf']


def post(client, url, data=None, **kwargs):
    payload = {'csrf': token(client), **(data or {})}
    return client.post(url, data=payload, **kwargs)


@pytest.fixture
def client(app):
    app.extensions['usuarios'].registrar('ana', 'senha-teste')
    c = app.test_client()
    assert post(c, '/login', {'login': 'ana', 'senha': 'senha-teste'}).status_code == 302
    return c


def rev(app):
    return app.extensions['inventario'].ler()[1]


def ativo(client, app, ident=1, nome='Servidor-Web', **extra):
    return post(client, '/ativos/novo', dict(revisao=rev(app), id_ativo=str(ident), nome=nome,
                responsavel='Equipe TI', setor_localizacao='Laboratório', tipo='SERVICO', status='ATIVO', **extra))


def vuln(client, app, ident=1, **extra):
    dados = dict(revisao=rev(app), descricao='Configuração insegura', categoria='Configuração',
                 severidade='ALTA', status='ABERTA', vetor='', cve_id='')
    dados.update(extra)
    return post(client, f'/ativos/{ident}/vulnerabilidades/nova', dados)


@pytest.mark.parametrize('url', ['/', '/ativos', '/ativos/novo', '/vulnerabilidades', '/riscos',
                                '/dependencias', '/cve', '/cvss', '/usuarios', '/exportar'])
def test_rotas_exigem_login(app, url):
    r = app.test_client().get(url)
    assert r.status_code == 302 and r.location.endswith('/login')


@pytest.mark.parametrize('url', ['/', '/ativos', '/ativos/novo', '/vulnerabilidades', '/riscos',
                                '/dependencias', '/cve', '/cvss', '/usuarios', '/healthz'])
def test_telas_vazias_renderizam(client, url):
    assert client.get(url).status_code == 200


def test_cadastro_autenticacao_csrf_e_logout(app):
    c = app.test_client()
    assert c.post('/cadastro', data={'login': 'intruso', 'senha': 'senha-teste'}).status_code == 400
    assert not app.extensions['usuarios'].listar()
    assert post(c, '/cadastro', {'login': 'pedro', 'senha': 'senha-teste', 'confirmacao': 'diferente'}).status_code == 400
    assert post(c, '/cadastro', {'login': 'pedro', 'senha': 'senha-teste', 'confirmacao': 'senha-teste'}).status_code == 302
    assert post(c, '/login', {'login': 'pedro', 'senha': 'errada'}).status_code == 200
    assert post(c, '/login', {'login': 'pedro', 'senha': 'senha-teste'}).status_code == 302
    assert post(c, '/sair').status_code == 302
    assert c.get('/').status_code == 302


def test_cadastro_fechado(app):
    app.config['PERMITIR_CADASTRO'] = False
    assert app.test_client().get('/cadastro').status_code == 404


def test_cookie_seguro_e_cabecalhos(client):
    r = client.get('/')
    assert "script-src 'self'" in r.headers['Content-Security-Policy']
    assert r.headers['X-Frame-Options'] == 'DENY'
    assert r.headers['Cache-Control'] == 'no-store'


def test_limite_de_tentativas_de_login(app):
    c = app.test_client()
    for _ in range(10):
        assert post(c, '/login', {'login': 'ausente', 'senha': 'senha'}).status_code == 200
    assert post(c, '/login', {'login': 'ausente', 'senha': 'senha'}).status_code == 429


def test_secret_key_obrigatoria(tmp_path):
    with pytest.raises(RuntimeError):
        criar_app({'SECRET_KEY': 'curta'})


def test_crud_ativos_vinculos_exportacao_e_reinicio(client, app):
    u = app.extensions['usuarios'].listar()[0]
    assert ativo(client, app, responsavel_id=u['id']).status_code == 302
    assert client.get('/ativos/1').status_code == 200
    assert 'Servidor-Web' in client.get('/ativos?q=Servidor').text
    assert 'Servidor-Web' not in client.get('/ativos?q=Ausente').text
    assert 'Servidor-Web' not in client.get('/ativos?tipo=BANCO_DE_DADOS').text
    assert ativo(client, app).status_code == 400
    assert ativo(client, app, 2, 'servidor-web').status_code == 400
    assert client.get('/ativos/1/editar').status_code == 200
    dados = dict(revisao=rev(app), nome='Web novo', responsavel='Manual', setor_localizacao='Sala 2',
                 tipo='SISTEMA', status='EM_MANUTENCAO', descricao='')
    assert post(client, '/ativos/1/editar', dados).status_code == 302
    base = client.get('/exportar').json
    assert isinstance(base, list) and base[0]['tipo'] == 'SISTEMA'
    assert base[0]['adicionado_por_id'] == u['id']
    outro_app = criar_app(dict(app.config))
    assert outro_app.extensions['inventario'].ler()[0].obter(1).nome == 'Web novo'
    assert post(client, '/ativos/1/excluir', {'revisao': rev(app)}).status_code == 302
    assert client.get('/exportar').json == []


@pytest.mark.parametrize('campo,valor', [('id_ativo', '-1'), ('id_ativo', '1.5'), ('id_ativo', 'nan'),
                                      ('nome', ''), ('status', 'NAO_EXISTE'), ('tipo', 'ABC'),
                                      ('responsavel_id', 'nao-existe')])
def test_ativo_invalido_nao_grava(client, app, campo, valor):
    dados = dict(revisao=rev(app), id_ativo='1', nome='Web', responsavel='Ana', setor_localizacao='TI',
                 tipo='SERVICO', status='ATIVO')
    dados[campo] = valor
    assert post(client, '/ativos/novo', dados).status_code == 400
    assert len(app.extensions['inventario'].ler()[0]) == 0


def test_xss_escapado(client, app):
    nome = '<script>alert(1)</script>'
    assert ativo(client, app, nome=nome).status_code == 302
    html = client.get('/ativos').text
    assert nome not in html and '&lt;script&gt;' in html


def test_csrf_em_exclusao_e_metodo_get(client, app):
    ativo(client, app)
    assert client.get('/ativos/1/excluir').status_code == 405
    assert client.post('/ativos/1/excluir', data={'revisao': rev(app)}).status_code == 400
    assert app.extensions['inventario'].ler()[0].obter(1)


def test_formulario_antigo_nao_sobrescreve_nem_exclui_outro_indice(client, app):
    ativo(client, app)
    vuln(client, app, descricao='Primeira')
    vuln(client, app, descricao='Segunda')
    antiga = rev(app)
    assert post(client, '/ativos/1/vulnerabilidades/0/excluir', {'revisao': antiga}).status_code == 302
    assert post(client, '/ativos/1/vulnerabilidades/0/excluir', {'revisao': antiga}).status_code == 409
    assert app.extensions['inventario'].ler()[0].obter(1).vulnerabilidades[0].descricao == 'Segunda'


def test_crud_vulnerabilidade_e_cvss(client, app):
    ativo(client, app)
    assert vuln(client, app).status_code == 302
    assert client.get('/ativos/1/vulnerabilidades/0/editar').status_code == 200
    dados = dict(revisao=rev(app), descricao='Editada', categoria='Software', severidade='BAIXA',
                 status='CORRIGIDA', vetor=V3, cve_id=CVE)
    assert post(client, '/ativos/1/vulnerabilidades/0/editar', dados).status_code == 302
    a = app.extensions['inventario'].ler()[0].obter(1)
    assert a.vulnerabilidades[0].cvss.nota == 9.8
    assert a.vulnerabilidades[0].adicionado_por == 'ana'
    assert a.vulnerabilidades[0].ultima_modificacao_por_id
    assert 'Editada' in client.get('/vulnerabilidades?status=CORRIGIDA').text
    assert 'Editada' not in client.get('/vulnerabilidades?status=ABERTA').text
    assert '9,80' in client.get('/riscos').text  # Corrigida ainda entra no modelo.
    assert post(client, '/ativos/1/vulnerabilidades/0/excluir', {'revisao': rev(app)}).status_code == 302
    assert app.extensions['inventario'].ler()[0].obter(1).vulnerabilidades == ()


def test_cvss_questionario_calculo_e_aplicacao(client, app):
    ativo(client, app)
    vuln(client, app)
    metricas = dict(AV='N', AC='L', PR='N', UI='N', S='U', C='H', I='H', A='H')
    r = post(client, '/cvss', {'modo': 'questionario', **metricas})
    assert r.status_code == 200 and '9,80' in r.text
    dados = dict(acao='aplicar', vetor=V3, alvo='1:0', cve_id=CVE, revisao=rev(app))
    assert post(client, '/cvss', dados).status_code == 302
    dados['revisao'] = rev(app)
    assert post(client, '/cvss', dados).status_code == 400
    dados['confirmar_substituicao'] = 'sim'
    assert post(client, '/cvss', dados).status_code == 302
    assert post(client, '/cvss', {'vetor': 'invalido'}).status_code == 400


def test_cve_importacao_fonte_autoria_e_duplicidade(client, app):
    ativo(client, app)
    resultado = interpretar_resposta(resposta(), CVE)
    with patch('web.ClienteNVD.consultar', return_value=resultado):
        r = post(client, '/cve', {'cve_id': CVE})
    assert r.status_code == 200 and '9,80' in r.text
    consulta = re.search(r'name="consulta" value="([^"]+)"', r.text).group(1)
    dados = dict(acao='importar', consulta=consulta, avaliacao='0', ativo='1', categoria='Software',
                 status='ABERTA', revisao=rev(app), nota='0', descricao='forjada')
    assert post(client, '/cve', dados).status_code == 302
    v = app.extensions['inventario'].ler()[0].obter(1).vulnerabilidades[0]
    assert v.cvss.nota == 9.8 and v.cvss.fonte == 'fonte@example.org'
    assert v.descricao != 'forjada' and v.adicionado_por == 'ana' and v.consultado_em
    dados['revisao'] = rev(app)
    assert post(client, '/cve', dados).status_code == 400


def test_cve_sem_avaliacao_e_offline(client, app):
    ativo(client, app)
    dados = resposta()
    dados['vulnerabilities'][0]['cve']['metrics'] = {}
    with patch('web.ClienteNVD.consultar', return_value=interpretar_resposta(dados, CVE)):
        r = post(client, '/cve', {'cve_id': CVE})
    consulta = re.search(r'name="consulta" value="([^"]+)"', r.text).group(1)
    assert post(client, '/cve', dict(acao='importar', consulta=consulta, ativo='1', categoria='Software',
                status='ABERTA', revisao=rev(app))).status_code == 302
    assert 'NÃO AVALIADAS' in client.get('/riscos').text
    with patch('web.ClienteNVD.consultar', side_effect=ErroConsultaCVE('offline')):
        assert 'offline' in post(client, '/cve', {'cve_id': CVE}).text
    assert post(client, '/cve', {'acao': 'importar', 'consulta': 'forjada'}).status_code == 400


def test_risco_completo_matrizes_e_cascata(client, app):
    for ident, nome, severidade in [(1, 'Servidor-Web', 'ALTA'), (2, 'Banco-Dados', 'MEDIA'), (3, 'Roteador', 'BAIXA')]:
        ativo(client, app, ident, nome)
        vuln(client, app, ident, severidade=severidade)
    for destino, origem, peso in [(1, 2, '0,25'), (1, 3, '0.10'), (2, 3, '0.50')]:
        assert post(client, '/dependencias', dict(revisao=rev(app), destino=destino, origem=origem, peso=peso)).status_code == 302
    r = app.extensions['inventario'].ler()[0].calcular_riscos()
    assert list(r.x) == [9.7, 6, 2]
    html = client.get('/riscos').text
    for esperado in ['9,70', '6,00', '2,00', 'Incidência', 'Equações de cada ativo', 'Sistema resolvido']:
        assert esperado in html
    assert '9,70' in client.get('/').text
    assert '25,00%' in client.get('/dependencias').text
    assert post(client, '/ativos/3/excluir', {'revisao': rev(app)}).status_code == 302
    inv = app.extensions['inventario'].ler()[0]
    assert list(inv.calcular_riscos().x) == [9.25, 5]
    assert post(client, '/dependencias', dict(acao='excluir', revisao=rev(app), destino=1, origem=2)).status_code == 302


@pytest.mark.parametrize('destino,origem,peso', [(1, 1, '.2'), (1, 99, '.2'), (1, 2, 'nan'),
                                               (1, 2, 'inf'), (1, 2, '-.2'), (1, 2, '1'), (1, 2, 'abc')])
def test_dependencias_invalidas(client, app, destino, origem, peso):
    ativo(client, app)
    ativo(client, app, 2, 'Banco')
    assert post(client, '/dependencias', dict(revisao=rev(app), destino=destino, origem=origem, peso=peso)).status_code == 400
    assert not app.extensions['inventario'].ler()[0].obter(1).dependencias


def test_singular_na_web_nao_exibe_solucao(client, app):
    Path(app.config['INVENTARIO_ARQUIVO']).write_text(Path('exemplos/risco_singular.json').read_text())
    r = client.get('/riscos')
    assert r.status_code == 200 and 'não é invertível' in r.text and 'Indisponível' in r.text


def test_renomear_senha_excluir_vinculo_preservado(client, app):
    u = app.extensions['usuarios'].listar()[0]
    ativo(client, app, responsavel_id=u['id'])
    vuln(client, app)
    assert post(client, '/usuarios', dict(acao='renomear', novo_login='ana-nova', senha_atual='errada')).status_code == 400
    assert post(client, '/usuarios', dict(acao='renomear', novo_login='ana-nova', senha_atual='senha-teste')).status_code == 302
    assert app.extensions['usuarios'].listar()[0]['id'] == u['id']
    assert 'ana-nova' in client.get('/ativos/1').text
    segundo = app.test_client()
    post(segundo, '/login', {'login': 'ana-nova', 'senha': 'senha-teste'})
    assert post(client, '/usuarios', dict(acao='senha', senha_atual='senha-teste', nova_senha='nova-senha',
                                        confirmacao='nova-senha')).status_code == 302
    assert segundo.get('/').status_code == 302
    assert post(client, '/login', {'login': 'ana-nova', 'senha': 'nova-senha'}).status_code == 302
    assert post(client, '/usuarios', dict(acao='excluir', senha_atual='nova-senha', confirmacao_exclusao='ana-nova')).status_code == 302
    assert app.extensions['usuarios'].listar() == []
    inv = app.extensions['inventario'].ler()[0]
    assert inv.obter(1).responsavel_id == u['id'] and len(inv.obter(1).vulnerabilidades) == 1
    app.extensions['usuarios'].registrar('ana', 'outra-senha')
    assert app.extensions['usuarios'].listar()[0]['id'] != u['id']


def test_base_corrompida_nao_e_substituida(client, app):
    p = Path(app.config['INVENTARIO_ARQUIVO'])
    p.write_text('{ quebrado')
    assert client.get('/healthz').status_code == 503
    assert client.get('/ativos').status_code == 503
    assert p.read_text() == '{ quebrado'


def test_edicoes_concorrentes_uma_conflita(app):
    servico = app.extensions['inventario']
    revisao = rev(app)
    def editar(i):
        try:
            with servico.editar(revisao) as inv:
                inv.adicionar(novo_equipamento(i, f'Ativo-{i}'))
            return 'salvo'
        except ConflitoEdicao:
            return 'conflito'
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(editar, [1, 2]))
    assert sorted(resultados) == ['conflito', 'salvo']
    assert len(servico.ler()[0]) == 1


def test_csrf_unicode_invalido_responde_400(client):
    assert client.post('/sair', data={'csrf': 'não-válido'}).status_code == 400


def test_trocar_cve_nao_reutiliza_data_de_consulta_antiga(client, app):
    ativo(client, app)
    vuln(client, app, cve_id=CVE, vetor=V3)
    with app.extensions['inventario'].editar(rev(app)) as inv:
        inv.obter(1).vulnerabilidades[0].consultado_em = '2026-01-01T00:00:00Z'
    dados = dict(revisao=rev(app), descricao='Outra falha', categoria='Software', severidade='ALTA',
                 status='ABERTA', vetor=V3, cve_id='CVE-2020-1234')
    assert post(client, '/ativos/1/vulnerabilidades/0/editar', dados).status_code == 302
    assert app.extensions['inventario'].ler()[0].obter(1).vulnerabilidades[0].consultado_em is None
