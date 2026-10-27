from modelos import TipoAtivo, StatusAtivo
from utilidades import ler_texto, ler_id_ativo, escolher_enum, selecionar_ativo, mensagem_sucesso, mensagem_erro, mensagem_aviso
from dados import salvar_dados

def cadastrar_ativo(dados):
    ativo_id = ler_id_ativo()
    if ativo_id in dados['ativos']:
        mensagem_erro('Já existe um ativo com esse identificador.')
        return
    nome = ler_texto('Digite o nome ou hostname do ativo: ')
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