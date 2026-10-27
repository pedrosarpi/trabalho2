import re

# Constantes de Cores
VERDE = '\033[92m'
VERMELHO = '\033[91m'
AMARELO = '\033[93m'
AZUL = '\033[94m'
RESET = '\033[0m'

def centralizar_texto(texto, largura=66):
    texto_limpo = re.sub(r'\x1b\[[0-9;]*m', '', texto)
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

def selecionar_ativo(ativos, mensagem):
    if not ativos:
        mensagem_aviso('Nenhum ativo cadastrado.')
        return None
    print(f'\n{mensagem}\n')
    ids = list(ativos)
    for indice, ativo_id in enumerate(ids, 1):
        print(f'{indice} - {ativos[ativo_id]["nome"]}')
    opcao = ler_inteiro('\nDigite o número do ativo: ')
    if not 1 <= opcao <= len(ids):
        mensagem_aviso('Opção de ativo inválida.')
        return None
    return ids[opcao - 1]