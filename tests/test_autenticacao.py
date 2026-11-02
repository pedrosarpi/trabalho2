import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.autenticacao import RepositorioUsuarios
from app.dados import ErroArmazenamento


@pytest.fixture
def repo(tmp_path):
    return RepositorioUsuarios(tmp_path / 'usuarios.json')


def test_migracao_sha256_login_sem_perder_identidade(repo):
    repo.caminho.write_text(json.dumps({'legado': hashlib.sha256(b'senha-teste').hexdigest()}))
    identidade = repo.listar()[0]['id']
    assert repo.autenticar('legado', 'errada') is None
    assert repo.autenticar('legado', 'senha-teste')['id'] == identidade
    registro = json.loads(repo.caminho.read_text())['legado']
    assert registro['senha'].startswith('scrypt:')
    assert repo.autenticar('legado', 'senha-teste')['id'] == identidade


@pytest.mark.parametrize('nome,senha', [('', 'senha-teste'), ('a', 'senha-teste'), ('ana teste', 'senha-teste'),
                                      ('ana', 'curta'), ('ana', 'x'*257)])
def test_validacoes(repo, nome, senha):
    with pytest.raises(ValueError):
        repo.registrar(nome, senha)
    assert not repo.caminho.exists()


def test_crud_e_sem_vazamento_de_hash(repo):
    assert repo.registrar('ana', 'senha-teste')
    assert not repo.registrar('ANA', 'senha-teste')
    assert 'senha' not in repo.listar()[0]
    assert repo.renomear('ana', 'ANA')
    assert repo.autenticar('ana', 'senha-teste') is None
    assert repo.autenticar('ANA', 'senha-teste')
    repo.alterar_senha('ANA', 'nova-senha')
    assert repo.autenticar('ANA', 'senha-teste') is None
    assert repo.autenticar('ANA', 'nova-senha')['versao'] == 2
    repo.deletar('ANA')
    assert not repo.listar()


@pytest.mark.parametrize('texto', ['[]', '{quebrado', '{"ana":123}', '{"ana":"hash-invalido"}'])
def test_contas_corrompidas_nao_sao_sobrescritas(repo, texto):
    repo.caminho.write_text(texto)
    with pytest.raises(ErroArmazenamento):
        repo.registrar('bruno', 'senha-teste')
    assert repo.caminho.read_text() == texto


def test_cadastros_simultaneos_nao_perdem_dados(repo):
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(pool.map(lambda nome: repo.registrar(nome, 'senha-teste'), ['ana', 'bruno']))
    assert len(repo.listar()) == 2


@pytest.mark.parametrize('nome', ['p', 'Pedro Henrique'])
def test_conta_legada_com_nome_anterior_continua_entrando(repo, nome):
    repo.caminho.write_text(json.dumps({nome: hashlib.sha256(b'senha-teste').hexdigest()}))
    assert repo.autenticar(nome, 'senha-teste')
    assert repo.autenticar(nome, 'senha-teste')  # Também após a migração para scrypt.
