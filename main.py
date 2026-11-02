"""Ponto de entrada: monta as peças (armazenamento, inventário, menu) e inicia."""
import os

from dados import ArmazenamentoJSON, ErroArmazenamento
from inventario import Inventario
from menus import MenuPrincipal, exibir_tela_login
from utilidades import mensagem_aviso, mensagem_erro

NOME_ARQUIVO = 'vulnerabilidades.json'

def main() -> None:
    armazenamento = ArmazenamentoJSON(caminho_do_arquivo())
    inventario = Inventario(armazenamento)
    # ... (bloco try-except de carregamento do inventário mantido) ...

    try:
        # Só executa o MenuPrincipal se o login retornar True
        if exibir_tela_login():
            MenuPrincipal(inventario).executar()
    except (KeyboardInterrupt, EOFError):
        print()
        mensagem_aviso('Programa encerrado.')


def caminho_do_arquivo() -> str:
    """O arquivo fica ao lado do código (e não na pasta de onde o programa foi chamado).

    A variável de ambiente INVENTARIO_ARQUIVO permite trocar o local, por exemplo
    para apontar para um volume quando o programa rodar em um container.
    """
    padrao = os.path.join(os.path.dirname(os.path.abspath(__file__)), NOME_ARQUIVO)
    return os.environ.get('INVENTARIO_ARQUIVO') or padrao


def main() -> None:
    armazenamento = ArmazenamentoJSON(caminho_do_arquivo())
    inventario = Inventario(armazenamento)
    try:
        inventario.carregar()
    except ErroArmazenamento as erro:
        mensagem_erro(str(erro))
        copia = armazenamento.guardar_copia()
        if copia:
            mensagem_aviso(f'Uma cópia do arquivo original foi guardada em:\n{copia}\n'
                           'O programa vai iniciar com a base vazia.')
        else:
            mensagem_aviso('O programa vai iniciar com a base vazia.')

    try:
        # Chama a tela de login e só entra no menu principal se retornar True
        if exibir_tela_login():
            MenuPrincipal(inventario).executar()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C / Ctrl+D: os dados já foram gravados a cada operação.
        print()
        mensagem_aviso('Programa encerrado.')


if __name__ == '__main__':
    main()
