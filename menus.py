"""Menus da aplicação (camada de interface com o usuário).

`Menu` é a classe base: ela sabe mostrar as opções, ler a escolha e chamar a
ação certa. Cada menu concreto só diz QUAIS são as suas opções.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from dados import ErroArmazenamento
from equipamentos import ID_MAXIMO, Equipamento
from modelos import SeveridadeVulnerabilidade, StatusAtivo, StatusTratamento, TipoAtivo, Vulnerabilidade
from utilidades import (AZUL, RESET, cabecalho, confirmar, escolher_enum, ler_inteiro, ler_texto,
                        mensagem_aviso, mensagem_erro, mensagem_sucesso)


class Menu(ABC):
    titulo = ''

    def __init__(self, inventario):
        self.inventario = inventario

    @abstractmethod
    def opcoes(self) -> dict:
        """Devolve {número: (rótulo, ação)}. Ação None significa sair do menu."""

    def exibir_titulo(self) -> None:
        cabecalho(f'{AZUL}{self.titulo}{RESET}')

    def ao_sair(self) -> None:
        """Gancho: as subclasses podem sobrescrever para mostrar algo ao sair."""

    def executar(self) -> None:
        while True:
            opcoes = self.opcoes()
            self.exibir_titulo()
            for numero, (rotulo, _) in opcoes.items():
                print(f'{numero} - {rotulo}')
            escolha = ler_inteiro('\nDigite uma opção: ')
            if escolha not in opcoes:
                mensagem_aviso('Digite uma opção válida!')
                continue
            acao = opcoes[escolha][1]
            if acao is None:
                self.ao_sair()
                return
            acao()

    # --- Auxiliares usados pelos menus concretos ---------------------------

    def _salvar(self) -> bool:
        try:
            self.inventario.salvar()
        except ErroArmazenamento as erro:
            mensagem_erro(f'{erro}\nA alteração vale apenas até fechar o programa.')
            return False
        return True

    def _selecionar_ativo(self, mensagem: str) -> Equipamento | None:
        ativos = self.inventario.listar()
        if not ativos:
            mensagem_aviso('Nenhum ativo cadastrado.')
            return None
        print(f'\n{mensagem}\n')
        for indice, ativo in enumerate(ativos, 1):
            print(f'{indice} - {ativo.nome} ({ativo.id_formatado})')
        opcao = ler_inteiro('\nDigite o número do ativo: ')
        if not 1 <= opcao <= len(ativos):
            mensagem_aviso('Opção de ativo inválida.')
            return None
        return ativos[opcao - 1]

    def _selecionar_vulnerabilidade(self, ativo: Equipamento, mensagem: str) -> Vulnerabilidade | None:
        vulnerabilidades = ativo.vulnerabilidades
        if not vulnerabilidades:
            mensagem_aviso('Esse ativo não possui vulnerabilidades cadastradas.')
            return None
        for indice, vulnerabilidade in enumerate(vulnerabilidades, 1):
            print(f'{indice} - {vulnerabilidade.descricao}')
        opcao = ler_inteiro(mensagem)
        if not 1 <= opcao <= len(vulnerabilidades):
            mensagem_aviso('Vulnerabilidade inválida.')
            return None
        return vulnerabilidades[opcao - 1]

    def _ler_vulnerabilidade(self, ativo: Equipamento) -> Vulnerabilidade:
        # Polimorfismo em ação: cada tipo de ativo sugere categorias diferentes.
        print(f'\nSugestões de categoria para {ativo.tipo.name}: {", ".join(ativo.categorias_sugeridas)}')
        descricao = ler_texto('Digite a descrição da vulnerabilidade: ')
        categoria = ler_texto('Digite a categoria ou tipo da vulnerabilidade: ')
        severidade = escolher_enum('Selecione a severidade:', SeveridadeVulnerabilidade)
        status = escolher_enum('Selecione o status do tratamento:', StatusTratamento)
        return Vulnerabilidade(descricao, categoria, severidade, status)


class MenuPrincipal(Menu):
    titulo = 'Sistema de Gerenciamento de Ativos e Vulnerabilidades'

    def opcoes(self) -> dict:
        return {
            1: ('Cadastrar ativo', self.cadastrar_ativo),
            2: ('Listar ativos', self.listar_ativos),
            3: ('Pesquisar ativo por ID ou nome', self.pesquisar_ativo),
            4: ('Atualizar ativo', self.atualizar_ativo),
            5: ('Remover ativo', self.remover_ativo),
            6: ('Gerenciar vulnerabilidades', self.gerenciar_vulnerabilidades),
            7: ('Sair', None),
        }

    def ao_sair(self) -> None:
        mensagem_sucesso('Espero te ver novamente!')

    def cadastrar_ativo(self) -> None:
        id_ativo = ler_inteiro(
            f'Digite o identificador do ativo (número inteiro de 0 a {ID_MAXIMO}): ',
            minimo=0, maximo=ID_MAXIMO,
            erro=f'O identificador deve ser um número inteiro entre 0 e {ID_MAXIMO}.')
        if self.inventario.existe(id_ativo):
            mensagem_erro('Já existe um ativo com esse identificador.')
            return
        nome = ler_texto('Digite o nome ou hostname do ativo: ')
        if self.inventario.nome_em_uso(nome):
            mensagem_erro('Já existe um ativo com esse nome ou hostname.')
            return
        responsavel = ler_texto('Digite o responsável: ')
        setor = ler_texto('Digite o setor ou localização: ')
        tipo = escolher_enum('Selecione o tipo geral do ativo:', TipoAtivo)
        status = escolher_enum('Selecione o status do ativo:', StatusAtivo)
        descricao = ler_texto('Digite a descrição do ativo (opcional): ', obrigatorio=False)

        # A fábrica devolve um objeto da subclasse correspondente ao tipo escolhido.
        ativo = Equipamento.criar(
            tipo, id_ativo=id_ativo, nome=nome, responsavel=responsavel,
            setor_localizacao=setor, status=status, descricao=descricao)

        pergunta = 'Deseja cadastrar uma vulnerabilidade para este ativo agora?'
        while confirmar(pergunta):
            ativo.adicionar_vulnerabilidade(self._ler_vulnerabilidade(ativo))
            pergunta = 'Deseja cadastrar outra vulnerabilidade?'

        self.inventario.adicionar(ativo)
        if self._salvar():
            mensagem_sucesso(f'Ativo {nome} cadastrado com sucesso.')

    def listar_ativos(self) -> None:
        ativos = self.inventario.listar()
        if not ativos:
            mensagem_aviso('Nenhum ativo cadastrado.')
            return
        print('\nAtivos cadastrados:\n')
        for ativo in ativos:
            print(ativo)

    def pesquisar_ativo(self) -> None:
        termo = ler_texto('Digite o ID ou nome/hostname do ativo: ')
        encontrados = self.inventario.buscar(termo)
        if not encontrados:
            mensagem_aviso('Ativo não encontrado.')
        elif len(encontrados) > 1:
            print('\nMais de um ativo corresponde à busca:\n')
            for ativo in encontrados:
                print(f'{ativo.id_formatado} - {ativo.nome}')
        else:
            print(f'\n{encontrados[0].detalhes()}\n')

    def atualizar_ativo(self) -> None:
        ativo = self._selecionar_ativo('Selecione o ativo para atualizar:')
        if ativo is None:
            return
        print('\nPressione Enter para manter o valor atual.\n')
        novo_nome = self._ler_novo_nome(ativo)
        novo_responsavel = input(f'Responsável [{ativo.responsavel}]: ').strip()
        novo_setor = input(f'Setor/localização [{ativo.setor_localizacao}]: ').strip()
        nova_descricao = input(f'Descrição [{ativo.descricao}]: ').strip()
        novo_tipo = None
        if confirmar(f'Alterar tipo ({ativo.tipo.name})?'):
            novo_tipo = escolher_enum('Selecione o novo tipo:', TipoAtivo)
        novo_status = None
        if confirmar(f'Alterar status ({ativo.status.name})?'):
            novo_status = escolher_enum('Selecione o novo status:', StatusAtivo)

        ativo.atualizar(nome=novo_nome, responsavel=novo_responsavel, setor_localizacao=novo_setor,
                        descricao=nova_descricao, status=novo_status)
        if novo_tipo is not None and novo_tipo != ativo.tipo:
            # Trocar o tipo = criar um objeto da outra subclasse e colocá-lo no lugar do antigo.
            self.inventario.substituir(ativo.converter_para(novo_tipo))
        if self._salvar():
            mensagem_sucesso('Ativo atualizado com sucesso.')

    def _ler_novo_nome(self, ativo: Equipamento) -> str | None:
        while True:
            nome = input(f'Nome/hostname [{ativo.nome}]: ').strip()
            if not nome:
                return None
            if self.inventario.nome_em_uso(nome, ignorar_id=ativo.id_ativo):
                mensagem_erro('Já existe outro ativo com esse nome ou hostname.')
                continue
            return nome

    def remover_ativo(self) -> None:
        ativo = self._selecionar_ativo('Selecione o ativo para remover:')
        if ativo is None:
            return
        if not confirmar(f'Remover {ativo.nome} e suas vulnerabilidades?'):
            mensagem_aviso('Remoção cancelada.')
            return
        self.inventario.remover(ativo.id_ativo)
        if self._salvar():
            mensagem_sucesso(f'Ativo {ativo.nome} e suas vulnerabilidades foram removidos.')

    def gerenciar_vulnerabilidades(self) -> None:
        MenuVulnerabilidades(self.inventario).executar()


class MenuVulnerabilidades(Menu):
    titulo = 'Gerenciamento de Vulnerabilidades'

    def exibir_titulo(self) -> None:
        # Sobrescreve o método da classe base: o submenu usa um título mais discreto.
        print(f'\n{self.titulo}')

    def opcoes(self) -> dict:
        return {
            1: ('Cadastrar vulnerabilidade', self.cadastrar_vulnerabilidade),
            2: ('Listar vulnerabilidades', self.listar_vulnerabilidades),
            3: ('Visualizar vulnerabilidades de um ativo', self.visualizar_vulnerabilidades),
            4: ('Alterar status', self.alterar_status),
            5: ('Remover vulnerabilidade', self.remover_vulnerabilidade),
            6: ('Voltar', None),
        }

    def cadastrar_vulnerabilidade(self) -> None:
        ativo = self._selecionar_ativo('Selecione o ativo para cadastrar a vulnerabilidade:')
        if ativo is None:
            return
        ativo.adicionar_vulnerabilidade(self._ler_vulnerabilidade(ativo))
        if self._salvar():
            mensagem_sucesso('Vulnerabilidade cadastrada com sucesso.')

    def listar_vulnerabilidades(self) -> None:
        com_vulnerabilidades = [a for a in self.inventario.listar() if a.vulnerabilidades]
        if not com_vulnerabilidades:
            mensagem_aviso('Nenhuma vulnerabilidade cadastrada.')
            return
        print('\nVulnerabilidades cadastradas:\n')
        for ativo in com_vulnerabilidades:
            print(f'Ativo {ativo.id_formatado} - {ativo.nome}')
            for indice, vulnerabilidade in enumerate(ativo.vulnerabilidades, 1):
                print(f'  {indice} - {vulnerabilidade}')

    def visualizar_vulnerabilidades(self) -> None:
        ativo = self._selecionar_ativo('Selecione o ativo:')
        if ativo is None:
            return
        if not ativo.vulnerabilidades:
            mensagem_aviso('O ativo está sem vulnerabilidades registradas.')
            return
        print(f'\nVulnerabilidades de {ativo.nome}:\n')
        for indice, vulnerabilidade in enumerate(ativo.vulnerabilidades, 1):
            print(f'{indice} - {vulnerabilidade}')

    def alterar_status(self) -> None:
        ativo = self._selecionar_ativo('Selecione o ativo da vulnerabilidade:')
        if ativo is None:
            return
        vulnerabilidade = self._selecionar_vulnerabilidade(ativo, 'Digite o número da vulnerabilidade: ')
        if vulnerabilidade is None:
            return
        vulnerabilidade.alterar_status(escolher_enum('Selecione o novo status:', StatusTratamento))
        if self._salvar():
            mensagem_sucesso('Status atualizado com sucesso.')

    def remover_vulnerabilidade(self) -> None:
        ativo = self._selecionar_ativo('Selecione o ativo da vulnerabilidade:')
        if ativo is None:
            return
        vulnerabilidade = self._selecionar_vulnerabilidade(
            ativo, 'Digite o número da vulnerabilidade para remover: ')
        if vulnerabilidade is None:
            return
        ativo.remover_vulnerabilidade(vulnerabilidade)
        if self._salvar():
            mensagem_sucesso('Vulnerabilidade removida com sucesso.')
