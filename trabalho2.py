# Início do trabalho 2, mesclando com o trabalho 1
    
import json
import os
import re
from enum import Enum


class TipoAtivo(Enum):
    EQUIPAMENTO = 1
    SISTEMA = 2
    SERVICO = 3
    DISPOSITIVO_DE_REDE = 4
    BANCO_DE_DADOS = 5

VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
AZUL = '\033[94m'
RESET = '\033[0m'


class StatusAtivo(Enum):
    ATIVO = 1
    INATIVO = 2
    EM_MANUTENCAO = 3


class SeveridadeVulnerabilidade(Enum):
    BAIXA = 1
    MEDIA = 2
    ALTA = 3
    CRITICA = 4


class StatusTratamento(Enum):
    ABERTA = 1
    EM_TRATAMENTO = 2
    CORRIGIDA = 3
    ACEITA_COMO_RISCO = 4


ARQUIVO_DADOS = 'vulnerabilidades1.json'

# Enum: usado para criar categorias fixas e legíveis, como tipos e status.


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
    # json.dump: grava o dicionário em arquivo JSON, preservando o conteúdo do sistema.
    with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)


def ler_texto(mensagem, obrigatorio=True):
    while True:
        valor = input(mensagem).strip()
        if valor or not obrigatorio:
            return valor
        mensagem_aviso('Este campo não pode ficar vazio.')


def ler_inteiro(mensagem, minimo=None):
    while True:
        try:
            valor = int(input(mensagem))
            if minimo is None or valor >= minimo:
                return valor
        except ValueError:
            pass
        mensagem_aviso('Digite um número inteiro válido.')


def ler_id_ativo():
    while True:
        valor = input('Digite o identificador do ativo (6 algarismos, por exemplo 000000): ').strip()
        if len(valor) == 6 and all('0' <= caractere <= '9' for caractere in valor):
            return valor
        mensagem_aviso('O identificador deve conter exatamente 6 algarismos numéricos.')


def escolher_enum(mensagem, enum_classe):
    print(f'\n{mensagem}')
    for item in enum_classe:
        print(f'{item.value} - {item.name}')
    valores = [item.value for item in enum_classe]
    while True:
        escolha = ler_inteiro('\nDigite o número correspondente: ')
        if escolha in valores:
            return enum_classe(escolha).name
        mensagem_aviso('Opção inválida.')


def centralizar_texto(texto, largura=66):
    # regex: remove as sequências ANSI da cor para calcular o tamanho real do texto.
    texto_limpo = re.sub(r'\x1b\[[0-9;]*m', '', texto)
    # Cálculo de espaçamento para centralizar o título visualmente.
    espacos = max((largura - len(texto_limpo)) // 2, 0)
    return ' ' * espacos + texto


def cabecalho(titulo):
    borda = f'{AZUL}{"@" * 66}{RESET}'
    print(f'\n{borda}\n\n{centralizar_texto(titulo)}\n\n{borda}\n')


def mensagem_sucesso(mensagem):
    print(f'\n{VERDE}{mensagem}{RESET}\n')


def mensagem_erro(mensagem):
    print(f'\n{VERMELHO}{mensagem}{RESET}\n')


def mensagem_aviso(mensagem):
    print(f'\n{AMARELO}{mensagem}{RESET}\n')


def selecionar_ativo(ativos, mensagem):
    if not ativos:
        mensagem_aviso('Nenhum ativo cadastrado.')
        return None
    print(f'\n{mensagem}\n')
    # list() e enumerate(): transformam chaves do dicionário em lista e numeram as opções.
    ids = list(ativos)
    for indice, ativo_id in enumerate(ids, 1):
        print(f'{indice} - {ativos[ativo_id]["nome"]}')
    opcao = ler_inteiro('\nDigite o número do ativo: ')
    if not 1 <= opcao <= len(ids):
        mensagem_aviso('Opção de ativo inválida.')
        return None
    return ids[opcao - 1]


def cadastrar_ativo(dados):
    ativo_id = ler_id_ativo()
    if ativo_id in dados['ativos']:
        mensagem_erro('Já existe um ativo com esse identificador.')
        return
    nome = ler_texto('Digite o nome ou hostname do ativo: ')
    # any() + casefold(): valida se já existe um ativo com nome igual ignorando maiúsculas/minúsculas.
    if any(a['nome'].casefold() == nome.casefold() for a in dados['ativos'].values()):
        mensagem_erro('Já existe um ativo com esse nome ou hostname.')
        return
    dados['ativos'][ativo_id] = {
        'nome': nome,
        'responsavel': ler_texto('Digite o responsável: '),
        'setor_localizacao': ler_texto('Digite o setor ou localização: '),
        'tipo': escolher_enum('Selecione o tipo geral do ativo:', TipoAtivo),
        'status': escolher_enum('Selecione o status do ativo:', StatusAtivo),
        'descricao': ler_texto('Digite a descrição do ativo (opcional): ', False),
    }
    # setdefault(): cria a lista de vulnerabilidades do ativo se ela ainda não existir.
    dados['vulnerabilidades'].setdefault(ativo_id, [])
    salvar_dados(dados)
    mensagem_sucesso(f'Ativo {nome} cadastrado com sucesso.')


def listar_ativos(dados):
    if not dados['ativos']:
        mensagem_aviso('Nenhum ativo cadastrado.')
        return
    print('\nAtivos cadastrados:\n')
    for ativo_id, ativo in dados['ativos'].items():
        tipo = ativo.get('tipo', 'NAO_INFORMADO')
        print(f'{ativo_id} - {ativo["nome"]} | Tipo: {tipo} | Status: {ativo["status"]}')


def exibir_ativo(ativo_id, ativo, vulnerabilidades):
    print(f'\nID: {ativo_id}')
    print(f'Nome/hostname: {ativo["nome"]}')
    print(f'Responsável: {ativo["responsavel"]}')
    print(f'Setor/localização: {ativo["setor_localizacao"]}')
    print(f'Tipo: {ativo.get("tipo", "NAO_INFORMADO")}')
    print(f'Status: {ativo["status"]}')
    print(f'Descrição: {ativo["descricao"] or "Não informada"}')
    print(f'Vulnerabilidades: {len(vulnerabilidades.get(str(ativo_id), []))}\n')


def pesquisar_ativo(dados):
    termo = ler_texto('Digite o ID ou nome/hostname do ativo: ')
    # List comprehension + items(): busca os ativos por ID ou parte do nome sem diferenciar maiúsculas/minúsculas.
    resultado = [(chave, ativo) for chave, ativo in dados['ativos'].items()
                 if chave == termo or termo.casefold() in ativo['nome'].casefold()]
    if not resultado:
        mensagem_aviso('Ativo não encontrado.')
    elif len(resultado) > 1:
        print('\nMais de um ativo corresponde à busca:\n')
        for chave, ativo in resultado:
            print(f'{chave} - {ativo["nome"]}')
    else:
        exibir_ativo(resultado[0][0], resultado[0][1], dados['vulnerabilidades'])


def atualizar_ativo(dados):
    ativo_id = selecionar_ativo(dados['ativos'], 'Selecione o ativo para atualizar:')
    if ativo_id is None:
        return
    ativo = dados['ativos'][ativo_id]
    print('\nPressione Enter para manter o valor atual.\n')
    for campo, rotulo in [('nome', 'Nome/hostname'), ('responsavel', 'Responsável'),
                          ('setor_localizacao', 'Setor/localização'), ('descricao', 'Descrição')]:
        novo = input(f'{rotulo} [{ativo[campo]}]: ').strip()
        if novo:
            ativo[campo] = novo
    for campo, classe in [('tipo', TipoAtivo), ('status', StatusAtivo)]:
        valor_atual = ativo.get(campo, 'NAO_INFORMADO')
        if input(f'Alterar {campo} ({valor_atual})? [s/N]: ').strip().casefold() == 's':
            ativo[campo] = escolher_enum(f'Selecione o novo {campo}:', classe)
    salvar_dados(dados)
    mensagem_sucesso('Ativo atualizado com sucesso.')


def remover_ativo(dados):
    ativo_id = selecionar_ativo(dados['ativos'], 'Selecione o ativo para remover:')
    if ativo_id is None:
        return
    nome = dados['ativos'][ativo_id]['nome']
    if input(f'Remover {nome} e suas vulnerabilidades? [s/N]: ').strip().casefold() != 's':
        mensagem_aviso('Remoção cancelada.')
        return
    del dados['ativos'][ativo_id]
    dados['vulnerabilidades'].pop(ativo_id, None)
    salvar_dados(dados)
    mensagem_sucesso(f'Ativo {nome} e suas vulnerabilidades foram removidos.')


def cadastrar_vulnerabilidade(dados):
    ativo_id = selecionar_ativo(dados['ativos'], 'Selecione o ativo para cadastrar a vulnerabilidade:')
    if ativo_id is None:
        return
    vulnerabilidade = {
        'descricao': ler_texto('Digite a descrição da vulnerabilidade: '),
        'categoria': ler_texto('Digite a categoria ou tipo da vulnerabilidade: '),
        'severidade': escolher_enum('Selecione a severidade:', SeveridadeVulnerabilidade),
        'status': escolher_enum('Selecione o status do tratamento:', StatusTratamento),
    }
    dados['vulnerabilidades'].setdefault(ativo_id, []).append(vulnerabilidade)
    salvar_dados(dados)
    mensagem_sucesso('Vulnerabilidade cadastrada com sucesso.')


def listar_vulnerabilidades(dados):
    encontradas = False
    print('\nVulnerabilidades cadastradas:\n')
    for ativo_id, lista in dados['vulnerabilidades'].items():
        if not lista:
            continue
        encontradas = True
        nome = dados['ativos'].get(str(ativo_id), {}).get('nome', 'Ativo removido')
        print(f'Ativo {ativo_id} - {nome}')
        for indice, vuln in enumerate(lista, 1):
            print(f'  {indice} - Descrição: {vuln["descricao"]} | Categoria: {vuln["categoria"]} | '
                  f'Severidade: {vuln["severidade"]} | Status: {vuln["status"]}')
    if not encontradas:
        mensagem_aviso('Nenhuma vulnerabilidade cadastrada.')


def visualizar_vulnerabilidades(dados):
    ativo_id = selecionar_ativo(dados['ativos'], 'Selecione o ativo:')
    if ativo_id is None:
        return
    lista = dados['vulnerabilidades'].get(ativo_id, [])
    if not lista:
        mensagem_aviso('O ativo está sem vulnerabilidades registradas.')
        return
    print(f'\nVulnerabilidades de {dados["ativos"][ativo_id]["nome"]}:\n')
    for indice, vuln in enumerate(lista, 1):
        print(f'{indice} - Descrição: {vuln["descricao"]} | Severidade: {vuln["severidade"]} | Status: {vuln["status"]}')


def alterar_status_vulnerabilidade(dados):
    ativo_id = selecionar_ativo(dados['ativos'], 'Selecione o ativo da vulnerabilidade:')
    if ativo_id is None:
        return
    lista = dados['vulnerabilidades'].get(ativo_id, [])
    if not lista:
        mensagem_aviso('Esse ativo não possui vulnerabilidades cadastradas.')
        return
    for indice, vuln in enumerate(lista, 1):
        print(f'{indice} - {vuln["descricao"]}')
    opcao = ler_inteiro('Digite o número da vulnerabilidade: ')
    if not 1 <= opcao <= len(lista):
        mensagem_aviso('Vulnerabilidade inválida.')
        return
    lista[opcao - 1]['status'] = escolher_enum('Selecione o novo status:', StatusTratamento)
    salvar_dados(dados)
    mensagem_sucesso('Status atualizado com sucesso.')


def remover_vulnerabilidade(dados):
    ativo_id = selecionar_ativo(dados['ativos'], 'Selecione o ativo da vulnerabilidade:')
    if ativo_id is None:
        return
    lista = dados['vulnerabilidades'].get(ativo_id, [])
    if not lista:
        mensagem_aviso('Esse ativo não possui vulnerabilidades cadastradas.')
        return
    for indice, vuln in enumerate(lista, 1):
        print(f'{indice} - {vuln["descricao"]}')
    opcao = ler_inteiro('Digite o número da vulnerabilidade para remover: ')
    if not 1 <= opcao <= len(lista):
        mensagem_aviso('Vulnerabilidade inválida.')
        return
    lista.pop(opcao - 1)
    salvar_dados(dados)
    mensagem_sucesso('Vulnerabilidade removida com sucesso.')


def gerenciar_vulnerabilidades(dados):
    # while True: mantém o submenu aberto até o usuário sair da opção.
    while True:
        print('\nGerenciamento de Vulnerabilidades\n1 - Cadastrar vulnerabilidade\n2 - Listar vulnerabilidades\n'
              '3 - Visualizar vulnerabilidades de um ativo\n4 - Alterar status\n5 - Remover vulnerabilidade\n6 - Voltar')
        opcao = ler_inteiro('\nDigite a opção: ')
        if opcao == 1:
            cadastrar_vulnerabilidade(dados)
        elif opcao == 2:
            listar_vulnerabilidades(dados)
        elif opcao == 3:
            visualizar_vulnerabilidades(dados)
        elif opcao == 4:
            alterar_status_vulnerabilidade(dados)
        elif opcao == 5:
            remover_vulnerabilidade(dados)
        elif opcao == 6:
            return
        else:
            mensagem_aviso('Opção inválida.')


def ativos():
    dados = carregar_dados()
    # Loop principal do menu: estrutura de repetição para manter o sistema em execução.
    while True:
        cabecalho(f'{AZUL}Sistema de Gerenciamento de Ativos e Vulnerabilidades{RESET}')
        print('1 - Cadastrar ativo\n2 - Listar ativos\n3 - Pesquisar ativo por ID ou nome\n'
              '4 - Atualizar ativo\n5 - Remover ativo\n6 - Gerenciar vulnerabilidades\n7 - Sair')
        opcao = ler_inteiro('\nDigite uma opção: ')
        if opcao == 1:
            cadastrar_ativo(dados)
        elif opcao == 2:
            listar_ativos(dados)
        elif opcao == 3:
            pesquisar_ativo(dados)
        elif opcao == 4:
            atualizar_ativo(dados)
        elif opcao == 5:
            remover_ativo(dados)
        elif opcao == 6:
            gerenciar_vulnerabilidades(dados)
        elif opcao == 7:
            mensagem_sucesso('Espero te ver novamente!')
            return
        else:
            mensagem_aviso('Digite uma opção válida!')


if __name__ == '__main__':
    ativos()