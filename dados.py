import json
import os
from utilidades import mensagem_erro

ARQUIVO_DADOS = 'vulnerabilidades.json'

def carregar_dados():
    if not os.path.exists(ARQUIVO_DADOS):
        return {'ativos': {}, 'vulnerabilidades': {}}
    try:
        with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        mensagem_erro('Não foi possível ler o arquivo de dados.')
        return {'ativos': {}, 'vulnerabilidades': {}}
    
    if isinstance(dados, dict) and 'ativos' in dados and 'vulnerabilidades' in dados:
        return dados
    return {'ativos': {}, 'vulnerabilidades': dados if isinstance(dados, dict) else {}}

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)