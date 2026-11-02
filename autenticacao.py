import json
import hashlib
import os

ARQUIVO_USUARIOS = 'usuarios.json'

def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

def carregar_usuarios() -> dict:
    if not os.path.exists(ARQUIVO_USUARIOS):
        return {}
    with open(ARQUIVO_USUARIOS, 'r') as f:
        return json.load(f)

def salvar_usuarios(usuarios: dict) -> None:
    with open(ARQUIVO_USUARIOS, 'w') as f:
        json.dump(usuarios, f)

def registrar_usuario(usuario: str, senha: str) -> bool:
    usuarios = carregar_usuarios()
    if usuario in usuarios:
        return False
    usuarios[usuario] = hash_senha(senha)
    salvar_usuarios(usuarios)
    return True

def autenticar_usuario(usuario: str, senha: str) -> bool:
    usuarios = carregar_usuarios()
    return usuarios.get(usuario) == hash_senha(senha)

# --- NOVAS FUNÇÕES ---
def alterar_login(login_antigo: str, login_novo: str) -> bool:
    usuarios = carregar_usuarios()
    if login_novo in usuarios:
        return False 
    usuarios[login_novo] = usuarios.pop(login_antigo)
    salvar_usuarios(usuarios)
    return True

def alterar_senha_usuario(usuario: str, nova_senha: str) -> None:
    usuarios = carregar_usuarios()
    usuarios[usuario] = hash_senha(nova_senha)
    salvar_usuarios(usuarios)

def deletar_usuario(usuario: str) -> None:
    usuarios = carregar_usuarios()
    if usuario in usuarios:
        del usuarios[usuario]
        salvar_usuarios(usuarios)