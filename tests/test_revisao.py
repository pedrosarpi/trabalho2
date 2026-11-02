"""Regressões encontradas na revisão da versão recebida."""
import json
from unittest.mock import patch

import pytest

from app import autenticacao as auth
from tests.test_cve_cvss import CVE, preparar_menu, resposta
from app.consulta_cve import interpretar_resposta


@pytest.fixture
def contas(tmp_path, monkeypatch):
    caminho = tmp_path / 'usuarios.json'
    monkeypatch.setenv('USUARIOS_ARQUIVO', str(caminho))
    monkeypatch.setattr(auth, 'ARQUIVO_USUARIOS', str(caminho))
    return caminho


def test_senhas_iguais_recebem_salts_distintos(contas):
    assert auth.hash_senha('senha-teste') != auth.hash_senha('senha-teste')


def test_senha_curta_recusada_no_dominio(contas):
    with pytest.raises(ValueError):
        auth.registrar_usuario('ana', 'a')


def test_trocar_senha_nao_cria_usuario_fantasma(contas):
    with pytest.raises(ValueError):
        auth.alterar_senha_usuario('inexistente', 'nova-senha')
    assert not contas.exists() or not json.loads(contas.read_text())


def test_renomear_inexistente_nao_quebra_com_keyerror(contas):
    assert auth.alterar_login('inexistente', 'novo') is False


def test_cve_importado_preserva_autoria(contas, tmp_path):
    menu, inventario = preparar_menu(tmp_path)
    with patch('app.consulta_cve.ClienteNVD.consultar', return_value=interpretar_resposta(resposta(), CVE)), \
         patch('builtins.input', side_effect=[CVE, 's', '1', 'Software', '1']):
        menu.consultar_cve()
    inventario.carregar()
    v = inventario.listar()[0].vulnerabilidades[0]
    assert v.adicionado_por == v.ultima_modificacao_por == 'teste'


def test_ctrl_c_login_em_base_valida_nao_quebra(tmp_path, monkeypatch, capsys):
    from app import main
    monkeypatch.setenv('INVENTARIO_ARQUIVO', str(tmp_path / 'ativos.json'))
    with patch('app.main.exibir_tela_login', side_effect=KeyboardInterrupt):
        main.main()
    assert 'Programa encerrado.' in capsys.readouterr().out
