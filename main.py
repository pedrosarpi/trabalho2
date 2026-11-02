import os

from dados import ArmazenamentoJSON, ErroArmazenamento
from inventario import Inventario
from menus import MenuPrincipal, exibir_tela_login
from utilidades import mensagem_aviso, mensagem_erro

NOME_ARQUIVO = 'vulnerabilidades.json'

def caminho_do_arquivo() -> str:
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
                           'Corrija ou restaure a base antes de iniciar novamente.')
        else:
            mensagem_aviso('Corrija ou restaure a base antes de iniciar novamente.')

        return

    try:
        usuario_logado = exibir_tela_login()
        if usuario_logado is not None:
            # Instancia passando o usuário agora
            MenuPrincipal(inventario, usuario_logado).executar()
    except (ErroArmazenamento, ValueError) as erro:
        mensagem_erro(str(erro))
    except (KeyboardInterrupt, EOFError):
        print()
        mensagem_aviso('Programa encerrado.')

if __name__ == '__main__':
    main()