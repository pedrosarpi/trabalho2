"""Funções de entrada e saída no terminal. Não contêm regras do domínio."""
import re

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


def ler_inteiro(mensagem, minimo=None, maximo=None, erro='Digite um número inteiro válido.'):
    while True:
        texto = input(mensagem).strip()
        if re.fullmatch(r'[+-]?[0-9]+', texto):
            valor = int(texto)
            if (minimo is None or valor >= minimo) and (maximo is None or valor <= maximo):
                return valor
        mensagem_aviso(erro)


def confirmar(mensagem):
    return input(f'{mensagem} [s/N]: ').strip().casefold() == 's'


def escolher_enum(mensagem, enum_classe):
    """Mostra as opções numeradas de um Enum e devolve o MEMBRO escolhido."""
    print(f'\n{mensagem}')
    for item in enum_classe:
        print(f'{item.value} - {item.name}')
    while True:
        escolha = ler_inteiro('\nDigite o número correspondente: ')
        try:
            return enum_classe(escolha)
        except ValueError:
            mensagem_aviso('Opção inválida.')
