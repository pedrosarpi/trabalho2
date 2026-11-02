"""Regressões dos caminhos após mover o código para o pacote app."""
from app import caminhos
from app.main import caminho_do_arquivo
from app.web import criar_app


def test_dados_fora_do_codigo_e_fallback_legado(tmp_path, monkeypatch):
    monkeypatch.setattr(caminhos, 'RAIZ', tmp_path)
    assert caminhos.arquivo_dados('usuarios.json') == str(tmp_path / 'dados/usuarios.json')
    legado = tmp_path / 'usuarios.json'
    legado.write_text('{}')
    assert caminhos.arquivo_dados('usuarios.json') == str(legado)


def test_caminho_cli_respeita_variavel(tmp_path, monkeypatch):
    alvo = str(tmp_path / 'externo.json')
    monkeypatch.setenv('INVENTARIO_ARQUIVO', alvo)
    assert caminho_do_arquivo() == alvo


def test_templates_e_estaticos_no_pacote(tmp_path):
    app = criar_app(dict(TESTING=True, SECRET_KEY='teste-de-organizacao-' * 3,
                        INVENTARIO_ARQUIVO=str(tmp_path / 'i.json'),
                        USUARIOS_ARQUIVO=str(tmp_path / 'u.json')))
    cliente = app.test_client()
    assert cliente.get('/login').status_code == 200
    assert cliente.get('/static/estilo.css').status_code == 200
    assert cliente.get('/static/app.js').status_code == 200
    assert cliente.get('/static/icones.svg').status_code == 200
