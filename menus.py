"""Menus da aplicação (camada de interface com o usuário).

`Menu` é a classe base: ela sabe mostrar as opções, ler a escolha e chamar a
ação certa. Cada menu concreto só diz QUAIS são as suas opções.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import math
import sys
from getpass import getpass

from consulta_cve import ClienteNVD, ErroConsultaCVE
from autenticacao import registrar_usuario, autenticar_usuario, alterar_login, alterar_senha_usuario, deletar_usuario, repositorio
from interface_cvss import ler_avaliacao, mostrar_avaliacao
from seguranca import validar_cve
from dados import ErroArmazenamento
from equipamentos import ID_MAXIMO, Equipamento
from modelos import SeveridadeVulnerabilidade, StatusAtivo, StatusTratamento, TipoAtivo, Vulnerabilidade
from riscos import ErroAnaliseRisco
from utilidades import (AZUL, RESET, cabecalho, confirmar, escolher_enum, ler_inteiro, ler_texto,
                        mensagem_aviso, mensagem_erro, mensagem_sucesso)

def exibir_tela_login() -> str | None:
    while True:
        cabecalho(f'{AZUL}TELA DE ACESSO{RESET}')
        print("1 - Fazer Login\n2 - Cadastrar Novo Usuário\n0 - Sair")
        opcao = ler_inteiro("\nOpção: ", minimo=0, maximo=2)

        if opcao == 0:
            print("Saindo do programa...")
            return None # Alterado para retornar None
        elif opcao == 1:
            usuario = ler_texto("Usuário: ")
            senha = getpass("Senha: ")
            if autenticar_usuario(usuario, senha):
                return usuario # Alterado para retornar o nome do usuário
            mensagem_erro("Usuário ou senha inválidos.")
        elif opcao == 2:
            usuario = ler_texto("Novo usuário: ")
            while True:
                senha = getpass("Nova senha (mínimo de 6 caracteres): ")
                if len(senha) < 6:
                    mensagem_aviso("A senha deve ter pelo menos 6 caracteres.")
                    continue
                confirmacao = getpass("Confirme a senha: ")
                if senha != confirmacao:
                    mensagem_erro("As senhas não coincidem. Tente novamente.")
                    continue
                break
            if registrar_usuario(usuario, senha):
                mensagem_sucesso("Usuário cadastrado com sucesso!")
            else:
                mensagem_erro("O usuário já existe.")


class Menu(ABC):
    titulo = ''

    def __init__(self, inventario, usuario_logado: str):
        self.inventario = inventario
        self.usuario_logado = usuario_logado
        conta = next((u for u in repositorio().listar() if u['login'] == usuario_logado), None)
        self.usuario_id = conta['id'] if conta else ''

    @abstractmethod
    def opcoes(self) -> dict:
        """Devolve {número: (rótulo, ação)}."""

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
            try:
                acao()
            except (ValueError, ErroArmazenamento) as erro:
                mensagem_erro(str(erro))

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
        print(f'\nSugestões de categoria para {ativo.tipo.name}: {", ".join(ativo.categorias_sugeridas)}')
        descricao = ler_texto('Digite a descrição da vulnerabilidade: ')
        categoria = ler_texto('Digite a categoria ou tipo da vulnerabilidade: ')
        severidade = escolher_enum('Selecione a severidade:', SeveridadeVulnerabilidade)
        status = escolher_enum('Selecione o status do tratamento:', StatusTratamento)
        return Vulnerabilidade(descricao, categoria, severidade, status, 
                               adicionado_por=self.usuario_logado, 
                               ultima_modificacao_por=self.usuario_logado,
                               adicionado_por_id=self.usuario_id, ultima_modificacao_por_id=self.usuario_id)


class MenuPrincipal(Menu):
    titulo = 'Sistema de Gerenciamento de Ativos e Vulnerabilidades'

    def exibir_titulo(self) -> None:
        cabecalho(f'{AZUL}{self.titulo} - Logado como: {self.usuario_logado}{RESET}')

    def opcoes(self) -> dict:
        return {
            1: ('Cadastrar ativo', self.cadastrar_ativo),
            2: ('Listar ativos', self.listar_ativos),
            3: ('Pesquisar ativo por ID ou nome', self.pesquisar_ativo),
            4: ('Atualizar ativo', self.atualizar_ativo),
            5: ('Remover ativo', self.remover_ativo),
            6: ('Gerenciar vulnerabilidades', self.gerenciar_vulnerabilidades),
            7: ('Análise de risco e dependências', self.gerenciar_riscos),
            8: ('Gerenciar usuário', self.gerenciar_usuario),
            9: ('Sair', None),
        }

    def ao_sair(self) -> None:
        mensagem_sucesso('Espero te ver novamente!')

    def gerenciar_usuario(self) -> None:
        print("\n--- GERENCIAR USUÁRIO ---")
        print("1 - Alterar Login\n2 - Alterar Senha\n3 - Excluir Conta\n0 - Voltar")
        opcao = ler_inteiro("\nOpção: ", minimo=0, maximo=3)

        if opcao != 0 and not autenticar_usuario(self.usuario_logado, getpass('Senha atual: ')):
            mensagem_erro('Senha atual incorreta.')
            return
        if opcao == 1:
            novo_login = ler_texto("Digite o novo nome de usuário: ")
            if confirmar(f"Deseja salvar o login como '{novo_login}'?"):
                if alterar_login(self.usuario_logado, novo_login):
                    self.usuario_logado = novo_login
                    mensagem_sucesso(f"Login atualizado para '{novo_login}'.")
                else:
                    mensagem_erro("Esse nome de usuário já está em uso.")
                    
        elif opcao == 2:
            nova_senha = getpass("Nova senha: ")
            if confirmar("Confirmar alteração de senha?"):
                alterar_senha_usuario(self.usuario_logado, nova_senha)
                mensagem_sucesso("Senha atualizada com sucesso.")
                
        elif opcao == 3:
            if confirmar("ATENÇÃO: Deseja realmente excluir sua conta?"):
                deletar_usuario(self.usuario_logado)
                mensagem_sucesso("Conta excluída. Encerrando o sistema...")
                sys.exit(0)

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

        ativo = Equipamento.criar(
            tipo, id_ativo=id_ativo, nome=nome, responsavel=responsavel,
            setor_localizacao=setor, status=status, descricao=descricao, 
            adicionado_por=self.usuario_logado, ultima_modificacao_por=self.usuario_logado,
            adicionado_por_id=self.usuario_id, ultima_modificacao_por_id=self.usuario_id)

        pergunta = 'Deseja cadastrar uma vulnerabilidade para este ativo agora?'
        while confirmar(pergunta):
            ativo.adicionar_vulnerabilidade(self._ler_vulnerabilidade(ativo))
            pergunta = 'Deseja cadastrar outra vulnerabilidade?'

        self.inventario.adicionar(ativo)
        if self._salvar():
            mensagem_sucesso(f'Ativo {nome} cadastrado com sucesso por {self.usuario_logado}.')

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
                        descricao=nova_descricao, status=novo_status, 
                        ultima_modificacao_por=self.usuario_logado)
        ativo.ultima_modificacao_por_id = self.usuario_id
        if novo_tipo is not None and novo_tipo != ativo.tipo:
            self.inventario.substituir(ativo.converter_para(novo_tipo))
        if self._salvar():
            mensagem_sucesso(f'Ativo atualizado com sucesso por {self.usuario_logado}.')

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
        if not confirmar(f'Remover {ativo.nome}, suas vulnerabilidades e as dependências ligadas a ele?'):
            mensagem_aviso('Remoção cancelada.')
            return
        self.inventario.remover(ativo.id_ativo)
        if self._salvar():
            mensagem_sucesso(f'Ativo {ativo.nome} e suas vulnerabilidades foram removidos.')

    def gerenciar_vulnerabilidades(self) -> None:
        # ATENÇÃO: passa o usuario para o submenu
        MenuVulnerabilidades(self.inventario, self.usuario_logado).executar()

    def gerenciar_riscos(self) -> None:
         # ATENÇÃO: passa o usuario para o submenu
        MenuRiscos(self.inventario, self.usuario_logado).executar()


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
            6: ('Consultar CVE na NVD e cadastrar', self.consultar_cve),
            7: ('Calcular CVSS e aplicar a uma vulnerabilidade', self.calcular_cvss),
            8: ('Voltar', None),
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
        vulnerabilidade.alterar_status(escolher_enum('Selecione o novo status:', StatusTratamento), modificado_por=self.usuario_logado)
        vulnerabilidade.ultima_modificacao_por_id = self.usuario_id
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

    def consultar_cve(self) -> None:
        cve_id = ler_texto('CVE a consultar (Enter cancela): ', obrigatorio=False)
        if not cve_id:
            return
        # Uma instância por submenu preserva o intervalo entre consultas.
        if not hasattr(self, '_cliente_nvd'):
            self._cliente_nvd = ClienteNVD()
        try:
            print('Consultando a NVD...')
            resultado = self._cliente_nvd.consultar(cve_id)
        except (ValueError, ErroConsultaCVE) as erro:
            mensagem_erro(str(erro))
            mensagem_aviso('O cadastro manual e o cálculo local continuam disponíveis.')
            return
        print(f'\n{resultado.cve_id} — {resultado.status}\n{resultado.descricao}')
        print(f'Fonte: {resultado.url}\nConsultado em: {resultado.consultado_em}')
        for indice, avaliacao in enumerate(resultado.avaliacoes, 1):
            print(f'\nAvaliação {indice}')
            mostrar_avaliacao(avaliacao)
        for aviso in resultado.avisos:
            mensagem_aviso(aviso)
        print('Confira no registro os produtos, versões e condições afetadas antes de associar ao ativo.')
        if not confirmar('Cadastrar este CVE em um ativo?'):
            return
        ativo = self._selecionar_ativo('Selecione o ativo afetado:')
        if ativo is None:
            return
        if any(v.cve_id == resultado.cve_id for v in ativo.vulnerabilidades):
            mensagem_aviso('Este CVE já está cadastrado neste ativo.')
            return
        avaliacao = None
        if len(resultado.avaliacoes) == 1:
            avaliacao = resultado.avaliacoes[0]
        elif resultado.avaliacoes:
            indice = ler_inteiro('Escolha a avaliação a registrar: ', minimo=1,
                                 maximo=len(resultado.avaliacoes))
            avaliacao = resultado.avaliacoes[indice - 1]
        categoria = ler_texto('Categoria da vulnerabilidade: ')
        status = escolher_enum('Status do tratamento:', StatusTratamento)
        vulnerabilidade = Vulnerabilidade(
            resultado.descricao, categoria, SeveridadeVulnerabilidade.NAO_AVALIADA, status,
            cve_id=resultado.cve_id, cvss=avaliacao, consultado_em=resultado.consultado_em,
            adicionado_por=self.usuario_logado, ultima_modificacao_por=self.usuario_logado,
            adicionado_por_id=self.usuario_id, ultima_modificacao_por_id=self.usuario_id)
        ativo.adicionar_vulnerabilidade(vulnerabilidade)
        if self._salvar():
            mensagem_sucesso('CVE cadastrado com sucesso.')

    def calcular_cvss(self) -> None:
        avaliacao = ler_avaliacao()
        if avaliacao is None:
            return
        mostrar_avaliacao(avaliacao)
        if not confirmar('Aplicar esta avaliação a uma vulnerabilidade cadastrada?'):
            return
        ativo = self._selecionar_ativo('Selecione o ativo:')
        if ativo is None:
            return
        vulnerabilidade = self._selecionar_vulnerabilidade(ativo, 'Número da vulnerabilidade: ')
        if vulnerabilidade is None:
            return
        cve_id = vulnerabilidade.cve_id
        if cve_id is None:
            while True:
                try:
                    cve_id = validar_cve(ler_texto('CVE associado (opcional; não verificado online): ', obrigatorio=False))
                    break
                except ValueError as erro:
                    mensagem_erro(str(erro))
            if cve_id and any(v is not vulnerabilidade and v.cve_id == cve_id for v in ativo.vulnerabilidades):
                mensagem_aviso('Este CVE já está cadastrado neste ativo. Avaliação não aplicada.')
                return
        if vulnerabilidade.cvss is not None:
            if not confirmar('Substituir a avaliação CVSS existente por este cálculo local?'):
                return
        vulnerabilidade.cvss = avaliacao
        vulnerabilidade.cve_id = cve_id
        vulnerabilidade.ultima_modificacao_por = self.usuario_logado
        vulnerabilidade.ultima_modificacao_por_id = self.usuario_id
        if self._salvar():
            mensagem_sucesso('CVSS aplicado; severidade atualizada automaticamente.')


class MenuRiscos(Menu):
    titulo = 'Análise de Risco e Dependências'

    def opcoes(self) -> dict:
        return {
            1: ('Cadastrar ou alterar dependência', self.definir_dependencia),
            2: ('Listar dependências', self.listar_dependencias),
            3: ('Remover dependência', self.remover_dependencia),
            4: ('Consultar risco próprio e efetivo de todos os ativos', self.consultar_riscos),
            5: ('Exibir matrizes e diagnóstico do cálculo', self.exibir_modelo),
            6: ('Voltar', None),
        }

    def definir_dependencia(self) -> None:
        if len(self.inventario) < 2:
            mensagem_aviso('Cadastre pelo menos dois ativos para definir dependências.')
            return
        destino = self._selecionar_ativo('Qual ativo DEPENDE de outro e RECEBERÁ parte do risco?')
        if destino is None:
            return
        origem = self._selecionar_ativo(f'De qual ativo {destino.nome} depende? (ORIGEM do risco)')
        if origem is None:
            return
        if origem.id_ativo == destino.id_ativo:
            mensagem_erro('Um ativo não pode depender de si mesmo (Aii deve ser zero).')
            return
        print(f'{destino.nome} receberá uma fração do risco efetivo de {origem.nome}.')
        print('Exemplo: 0,25 significa 25%. A soma dos pesos de cada ativo deve ser menor que 1.')
        while True:
            texto = ler_texto('Peso de 0 até menos de 1 (Enter cancela): ', obrigatorio=False)
            if not texto:
                return
            try:
                peso = float(texto.replace(',', '.'))
                if not math.isfinite(peso) or not 0 <= peso < 1:
                    raise ValueError()
                break
            except ValueError:
                mensagem_erro('Digite um número finito entre 0 (inclusive) e 1 (exclusive).')
        try:
            self.inventario.definir_dependencia(destino.id_ativo, origem.id_ativo, peso)
        except ValueError as erro:
            mensagem_erro(str(erro))
            return
        if self._salvar():
            mensagem_sucesso(f'{destino.nome} depende de {origem.nome}: peso {peso:.6g}.')

    def listar_dependencias(self) -> None:
        encontrou = False
        for destino in self.inventario.listar():
            for dependencia in destino.dependencias:
                origem = self.inventario.obter(dependencia.id_origem)
                print(f'{destino.id_formatado} — {destino.nome} depende de '
                      f'{origem.id_formatado} — {origem.nome}: '
                      f'recebe {dependencia.peso:.2%} do risco efetivo da origem.')
                encontrou = True
        if not encontrou:
            mensagem_aviso('Nenhuma dependência cadastrada. Nesse caso, o risco efetivo é igual ao próprio.')

    def remover_dependencia(self) -> None:
        destino = self._selecionar_ativo('Selecione o ativo que recebe o risco:')
        if destino is None:
            return
        dependencias = destino.dependencias
        if not dependencias:
            mensagem_aviso('Este ativo não possui dependências.')
            return
        for indice, dependencia in enumerate(dependencias, 1):
            origem = self.inventario.obter(dependencia.id_origem)
            print(f'{indice} - {origem.nome} ({origem.id_formatado}), peso {dependencia.peso:.6g}')
        opcao = ler_inteiro('Número da dependência (0 cancela): ', minimo=0, maximo=len(dependencias))
        if opcao == 0:
            return
        dependencia = dependencias[opcao - 1]
        if not confirmar('Remover essa dependência?'):
            return
        self.inventario.remover_dependencia(destino.id_ativo, dependencia.id_origem)
        if self._salvar():
            mensagem_sucesso('Dependência removida. O risco será recalculado na próxima consulta.')

    def _obter_resultado(self):
        try:
            return self.inventario.calcular_riscos()
        except ErroAnaliseRisco as erro:
            mensagem_erro(str(erro))
            return None

    def consultar_riscos(self) -> None:
        resultado = self._obter_resultado()
        if resultado is not None:
            self._mostrar_resultado(resultado)

    def _mostrar_resultado(self, resultado) -> None:
        print('\nRisco próprio b = M·v | Risco efetivo: (I - A)·x = b')
        print('Modelo do enunciado: todos os registros entram, inclusive os marcados como corrigidos.')
        print('São índices acumulados de risco; podem ultrapassar 10 e não são probabilidades.\n')
        print(f'{"ID":<8} {"Ativo":<26} {"Próprio":>12} {"Herdado":>12} {"Efetivo":>14}')
        for i, ativo in enumerate(resultado.modelo.equipamentos):
            proprio = resultado.modelo.b[i]
            if resultado.x is None:
                herdado, efetivo = '—', 'indisponível'
            else:
                herdado = f'{resultado.x[i] - proprio:.4f}'
                efetivo = f'{resultado.x[i]:.4f}'
            print(f'{ativo.id_formatado:<8} {ativo.nome[:26]:<26} '
                  f'{proprio:>12.4f} {herdado:>12} {efetivo:>14}')
        print(f'\nPosto de I - A: {resultado.posto}/{len(resultado.modelo.equipamentos)}')
        print(f'Número de condição: {resultado.condicao:.6g}')
        print(f'Determinante (apenas diagnóstico): {resultado.determinante:.6g}')
        if resultado.residuo_relativo is not None:
            print(f'Resíduo relativo da solução: {resultado.residuo_relativo:.3e}')
        for aviso in resultado.avisos:
            mensagem_aviso(aviso)
        if resultado.impedimento:
            mensagem_erro(resultado.impedimento)
        else:
            print('Invertibilidade verificada e sistema resolvido diretamente.')

    def exibir_modelo(self) -> None:
        resultado = self._obter_resultado()
        if resultado is None:
            return
        modelo = resultado.modelo
        print('\nOrdem das linhas de M e das linhas/colunas de A:')
        for i, ativo in enumerate(modelo.equipamentos, 1):
            print(f'{i}: {ativo.id_formatado} — {ativo.nome}')
        print('\nColunas de M e entradas de v (um registro de vulnerabilidade por coluna):')
        for j, coluna in enumerate(modelo.colunas, 1):
            print(f'{j}: {coluna.rotulo} | {coluna.descricao} | '
                  f'{coluna.origem_severidade} | peso {modelo.v[j - 1]:.6g}')
        print(f'\nM ({modelo.M.shape[0]} x {modelo.M.shape[1]}):')
        for linha in modelo.M:
            print('  [' + ', '.join(str(int(valor)) for valor in linha) + ']')
        print('\nv = [' + ', '.join(f'{valor:.6g}' for valor in modelo.v) + ']')
        for nome, matriz in [('A (linha recebe risco da coluna)', modelo.A), ('I - A', modelo.sistema)]:
            print(f'\n{nome}:')
            for linha in matriz:
                print('  [' + ', '.join(f'{valor:.6g}' for valor in linha) + ']')
        print('\nb = [' + ', '.join(f'{valor:.6g}' for valor in modelo.b) + ']')
        if resultado.x is not None:
            print('x = [' + ', '.join(f'{valor:.6g}' for valor in resultado.x) + ']')
        self._mostrar_resultado(resultado)
