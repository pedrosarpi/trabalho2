from modelos import SeveridadeVulnerabilidade, StatusTratamento
from utilidades import ler_texto, ler_inteiro, escolher_enum, selecionar_ativo, mensagem_sucesso, mensagem_aviso
from dados import salvar_dados

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