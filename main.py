from dados import carregar_dados
from utilidades import cabecalho, ler_inteiro, mensagem_sucesso, mensagem_aviso, AZUL, RESET
from ativos import cadastrar_ativo, listar_ativos, pesquisar_ativo, atualizar_ativo, remover_ativo
from vulnerabilidades import gerenciar_vulnerabilidades

def main():
    dados = carregar_dados()
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
    main()