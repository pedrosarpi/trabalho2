"""Contas em JSON, hash scrypt com salt e migração do SHA-256 legado no login.

O ID é permanente. Trocar o login não troca a identidade nem reescreve autoria.
A versão da sessão invalida cookies anteriores quando a senha muda.
"""
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
from uuid import uuid4, uuid5, NAMESPACE_URL

from filelock import FileLock
from werkzeug.security import check_password_hash, generate_password_hash

from dados import ErroArmazenamento
from persistencia import gravar_json

ARQUIVO_USUARIOS = str(Path(__file__).with_name('usuarios.json'))


def validar_login(usuario):
    if not isinstance(usuario, str) or not re.fullmatch(r'[\w.@-]{2,64}', usuario, flags=re.UNICODE):
        raise ValueError('O login deve ter 2 a 64 letras, números, ponto, @, hífen ou sublinhado.')
    return usuario


def validar_senha(senha):
    if not isinstance(senha, str) or not 6 <= len(senha) <= 256:
        raise ValueError('A senha deve ter entre 6 e 256 caracteres.')


def hash_senha(senha: str) -> str:
    validar_senha(senha)
    return generate_password_hash(senha, method='scrypt')


class RepositorioUsuarios:
    def __init__(self, caminho):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.caminho) + '.lock', timeout=10)

    def carregar(self):
        if not self.caminho.exists():
            return {}
        try:
            dados = json.loads(self.caminho.read_text(encoding='utf-8'))
            if not isinstance(dados, dict):
                raise ValueError('esperado um objeto de contas')
            ids = set()
            for nome, registro in list(dados.items()):
                # Cadastros antigos aceitavam espaços e logins de um caractere.
                # A regra nova vale para criação/renomeação, não bloqueia contas existentes.
                if not isinstance(nome, str) or not nome.strip() or any(ord(c) < 32 for c in nome):
                    raise ValueError('login persistido inválido')
                if isinstance(registro, str) and re.fullmatch(r'[0-9a-f]{64}', registro):
                    registro = {'id': str(uuid5(NAMESPACE_URL, 'inventario-legado:' + nome)),
                                'senha': registro, 'versao': 1}
                    dados[nome] = registro
                if not isinstance(registro, dict) or not isinstance(registro.get('id'), str) or not registro['id']:
                    raise ValueError('conta sem identidade válida')
                if registro['id'] in ids:
                    raise ValueError('identidade de conta duplicada')
                ids.add(registro['id'])
                if not isinstance(registro.get('senha'), str) or not (
                    registro['senha'].startswith('scrypt:') or re.fullmatch(r'[0-9a-f]{64}', registro['senha'])
                ):
                    raise ValueError('hash de senha inválido')
                if type(registro.get('versao')) is not int or registro['versao'] < 1:
                    raise ValueError('versão de sessão inválida')
            return dados
        except (OSError, UnicodeError, ValueError) as erro:
            raise ErroArmazenamento(f'Não foi possível ler as contas: {erro}') from erro

    def salvar(self, usuarios):
        try:
            gravar_json(self.caminho, usuarios)
        except (OSError, ValueError) as erro:
            raise ErroArmazenamento(f'Não foi possível salvar as contas: {erro}') from erro

    @contextmanager
    def transacao(self):
        with self.lock:
            usuarios = self.carregar()
            yield usuarios
            self.salvar(usuarios)

    def listar(self):
        # Hashes nunca saem na API de listagem.
        with self.lock:
            return [dict(id=r['id'], login=n, versao=r['versao']) for n, r in self.carregar().items()]

    def obter(self, identificador):
        return next((u for u in self.listar() if u['id'] == identificador), None)

    def registrar(self, usuario, senha):
        validar_login(usuario)
        senha_hash = hash_senha(senha)
        with self.lock:
            usuarios = self.carregar()
            if any(n.casefold() == usuario.casefold() for n in usuarios):
                return False
            usuarios[usuario] = dict(id=str(uuid4()), senha=senha_hash, versao=1)
            self.salvar(usuarios)
        return True

    def autenticar(self, usuario, senha):
        if not isinstance(senha, str) or len(senha) > 256:
            return None
        with self.lock:
            usuarios = self.carregar()
            registro = usuarios.get(usuario)
            if registro is None:
                return None
            armazenada = registro['senha']
            legado = bool(re.fullmatch(r'[0-9a-f]{64}', armazenada))
            try:
                valido = (hmac.compare_digest(armazenada, hashlib.sha256(senha.encode()).hexdigest())
                          if legado else check_password_hash(armazenada, senha))
            except (ValueError, TypeError):
                valido = False
            if not valido:
                return None
            if legado:
                # Mesmo uma senha antiga curta pode entrar; mudança usa a política atual.
                registro['senha'] = generate_password_hash(senha, method='scrypt')
                self.salvar(usuarios)
            return dict(id=registro['id'], login=usuario, versao=registro['versao'])

    def renomear(self, antigo, novo):
        validar_login(novo)
        with self.lock:
            usuarios = self.carregar()
            if antigo not in usuarios or any(n.casefold() == novo.casefold() and n != antigo for n in usuarios):
                return False
            usuarios[novo] = usuarios.pop(antigo)
            self.salvar(usuarios)
        return True

    def alterar_senha(self, usuario, senha):
        senha_hash = hash_senha(senha)
        with self.transacao() as usuarios:
            if usuario not in usuarios:
                raise ValueError('Usuário inexistente.')
            usuarios[usuario]['senha'] = senha_hash
            usuarios[usuario]['versao'] += 1

    def deletar(self, usuario):
        with self.transacao() as usuarios:
            usuarios.pop(usuario, None)


def repositorio():
    return RepositorioUsuarios(os.environ.get('USUARIOS_ARQUIVO') or ARQUIVO_USUARIOS)


def carregar_usuarios():
    return repositorio().carregar()


def salvar_usuarios(usuarios):
    repositorio().salvar(usuarios)


def registrar_usuario(usuario, senha):
    return repositorio().registrar(usuario, senha)


def autenticar_usuario(usuario, senha):
    return repositorio().autenticar(usuario, senha) is not None


def alterar_login(login_antigo, login_novo):
    return repositorio().renomear(login_antigo, login_novo)


def alterar_senha_usuario(usuario, nova_senha):
    repositorio().alterar_senha(usuario, nova_senha)


def deletar_usuario(usuario):
    repositorio().deletar(usuario)
