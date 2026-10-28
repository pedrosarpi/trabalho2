import json
import os
from utilidades import mensagem_erro
from modelos import Equipamentos # Importar a classe para criar os objetos

ARQUIVO_DADOS = 'vulnerabilidades.json'

def carregar_dados():
    dados_memoria = {'ativos': {}, 'vulnerabilidades': {}}
    
    if not os.path.exists(ARQUIVO_DADOS):
        return dados_memoria
        
    try:
        with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as arquivo:
            dados_lidos = json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        mensagem_erro('Não foi possível ler o arquivo de dados.')
        return dados_memoria
    
    # Se for uma lista (novo formato exigido), reconstrói a estrutura de dicionários
    if isinstance(dados_lidos, list):
        for ativo in dados_lidos:
            ativo_id = ativo['id_ativo']
            dados_memoria['ativos'][ativo_id] = {
                'nome': ativo['nome'],
                'responsavel': ativo['responsavel'],
                'setor_localizacao': ativo['setor_localizacao'],
                'tipo': ativo['tipo'],
                'status': ativo['status'],
                'descricao': ativo['descricao']
            }
            dados_memoria['vulnerabilidades'][ativo_id] = ativo.get('vulnerabilidades', [])
            
    # Fallback para caso você ainda esteja usando a estrutura de dicionários no arquivo JSON antigo
    elif isinstance(dados_lidos, dict) and 'ativos' in dados_lidos:
        return dados_lidos
        
    return dados_memoria

def salvar_dados(dados):
    array_objetos_json = []
    
    # Derivar os objetos que representam os equipamentos e adicioná-los à lista
    for ativo_id, info in dados['ativos'].items():
        vulns = dados['vulnerabilidades'].get(ativo_id, [])
        
        # Instanciar o objeto individual da classe Equipamentos
        equipamento_obj = Equipamentos(
            id_ativo=ativo_id,
            nome=info['nome'],
            responsavel=info['responsavel'],
            setor_localizacao=info['setor_localizacao'],
            tipo=info['tipo'],
            status=info['status'],
            descricao=info['descricao'],
            vulnerabilidades=vulns
        )
        
        array_objetos_json.append(equipamento_obj.to_dict())

    # O arquivo gerado é constituído por um array (lista) de objetos JSON
    with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as arquivo:
        json.dump(array_objetos_json, arquivo, ensure_ascii=False, indent=4)