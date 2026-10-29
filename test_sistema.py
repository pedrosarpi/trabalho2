"""Testes automatizados (unittest; o pytest do CI também os executa)."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import main as aplicacao
from dados import ArmazenamentoJSON, ErroArmazenamento
from equipamentos import (CLASSES_POR_TIPO, BancoDeDados, DispositivoDeRede, Equipamento,
                          EquipamentoFisico, Sistema)
from inventario import Inventario
from menus import MenuPrincipal, MenuVulnerabilidades
from modelos import SeveridadeVulnerabilidade, StatusTratamento, TipoAtivo, Vulnerabilidade


def novo_equipamento(id_ativo=1, nome='Roteador', tipo=TipoAtivo.DISPOSITIVO_DE_REDE, **extras):
    return Equipamento.criar(tipo, id_ativo=id_ativo, nome=nome, responsavel='Ana',
                             setor_localizacao='Sala 1', **extras)


def nova_vulnerabilidade(descricao='Senha fraca'):
    return Vulnerabilidade(descricao, 'Autenticação', SeveridadeVulnerabilidade.ALTA)


class TestHierarquia(unittest.TestCase):
    def test_fabrica_cria_a_subclasse_do_tipo(self):
        self.assertIsInstance(novo_equipamento(tipo=TipoAtivo.BANCO_DE_DADOS), BancoDeDados)
        self.assertIsInstance(novo_equipamento(tipo=TipoAtivo.EQUIPAMENTO), EquipamentoFisico)
        for tipo in TipoAtivo:
            equipamento = novo_equipamento(tipo=tipo)
            self.assertIsInstance(equipamento, Equipamento)
            self.assertEqual(equipamento.tipo, tipo)

    def test_todo_tipo_tem_classe(self):
        self.assertEqual(set(CLASSES_POR_TIPO), set(TipoAtivo))

    def test_classe_base_nao_pode_ser_instanciada(self):
        with self.assertRaises(TypeError):
            Equipamento(1, 'x', 'y', 'z')

    def test_polimorfismo_categorias_diferem_por_tipo(self):
        rede = novo_equipamento(tipo=TipoAtivo.DISPOSITIVO_DE_REDE)
        banco = novo_equipamento(tipo=TipoAtivo.BANCO_DE_DADOS)
        self.assertNotEqual(rede.categorias_sugeridas, banco.categorias_sugeridas)

    def test_vulnerabilidades_expostas_como_tupla(self):
        equipamento = novo_equipamento()
        equipamento.adicionar_vulnerabilidade(nova_vulnerabilidade())
        self.assertIsInstance(equipamento.vulnerabilidades, tuple)
        self.assertEqual(len(equipamento.vulnerabilidades), 1)

    def test_converter_para_preserva_dados_e_vulnerabilidades(self):
        original = novo_equipamento(id_ativo=7)
        original.adicionar_vulnerabilidade(nova_vulnerabilidade())
        convertido = original.converter_para(TipoAtivo.SISTEMA)
        self.assertIsInstance(convertido, Sistema)
        self.assertEqual((convertido.id_ativo, convertido.nome), (7, 'Roteador'))
        self.assertEqual(len(convertido.vulnerabilidades), 1)

    def test_atualizar_ignora_vazios(self):
        equipamento = novo_equipamento()
        equipamento.atualizar(nome='', responsavel='Bruno')
        self.assertEqual((equipamento.nome, equipamento.responsavel), ('Roteador', 'Bruno'))


class TestSerializacao(unittest.TestCase):
    def test_ida_e_volta(self):
        original = novo_equipamento(id_ativo=3, descricao='Wi-Fi')
        original.adicionar_vulnerabilidade(nova_vulnerabilidade())
        copia = Equipamento.from_dict(json.loads(json.dumps(original.to_dict())))
        self.assertIsInstance(copia, DispositivoDeRede)
        self.assertEqual(copia.to_dict(), original.to_dict())

    def test_id_em_texto_do_formato_antigo_vira_inteiro(self):
        dados = novo_equipamento().to_dict()
        dados['id_ativo'] = '000001'
        equipamento = Equipamento.from_dict(dados)
        self.assertEqual(equipamento.id_ativo, 1)
        self.assertEqual(equipamento.to_dict()['id_ativo'], 1)

    def test_registros_invalidos_levantam_valueerror(self):
        base = novo_equipamento().to_dict()
        casos = {
            'campo ausente': {k: v for k, v in base.items() if k != 'responsavel'},
            'tipo inexistente': {**base, 'tipo': 'XPTO'},
            'id inválido': {**base, 'id_ativo': 'abc'},
            'id fora da faixa': {**base, 'id_ativo': 1_000_000},
            'vulnerabilidades não é lista': {**base, 'vulnerabilidades': 'x'},
            'vulnerabilidade sem severidade': {
                **base, 'vulnerabilidades': [{'descricao': 'a', 'categoria': 'b', 'status': 'ABERTA'}]},
        }
        for nome, dados in casos.items():
            with self.subTest(nome), self.assertRaises(ValueError):
                Equipamento.from_dict(dados)
        with self.assertRaises(ValueError):
            Equipamento.from_dict('não é objeto')


class TestInventario(unittest.TestCase):
    def setUp(self):
        self.inventario = Inventario(armazenamento=None)
        self.inventario.adicionar(novo_equipamento(1, 'Roteador'))
        self.inventario.adicionar(novo_equipamento(2, 'Servidor-DB', TipoAtivo.BANCO_DE_DADOS))

    def test_id_duplicado_e_recusado(self):
        with self.assertRaises(ValueError):
            self.inventario.adicionar(novo_equipamento(1, 'Outro'))

    def test_busca_por_id_e_por_nome(self):
        self.assertEqual([a.id_ativo for a in self.inventario.buscar('2')], [2])
        self.assertEqual([a.id_ativo for a in self.inventario.buscar('000001')], [1])
        self.assertEqual([a.id_ativo for a in self.inventario.buscar('servidor')], [2])
        self.assertEqual(self.inventario.buscar('zzz'), [])

    def test_nome_em_uso_ignora_o_proprio_ativo(self):
        self.assertTrue(self.inventario.nome_em_uso('ROTEADOR'))
        self.assertFalse(self.inventario.nome_em_uso('roteador', ignorar_id=1))

    def test_remover(self):
        self.inventario.remover(1)
        self.assertFalse(self.inventario.existe(1))
        self.assertEqual(len(self.inventario), 1)


class TestArmazenamento(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.caminho = os.path.join(self.pasta.name, 'dados.json')
        self.armazenamento = ArmazenamentoJSON(self.caminho)

    def test_arquivo_inexistente_gera_base_vazia(self):
        self.assertEqual(self.armazenamento.carregar(), [])

    def test_salva_array_de_objetos_json_e_recarrega(self):
        equipamento = novo_equipamento()
        equipamento.adicionar_vulnerabilidade(nova_vulnerabilidade())
        self.armazenamento.salvar([equipamento, novo_equipamento(2, 'Switch')])
        with open(self.caminho, encoding='utf-8') as arquivo:
            conteudo = json.load(arquivo)
        self.assertIsInstance(conteudo, list)
        self.assertTrue(all(isinstance(item, dict) for item in conteudo))
        recarregados = self.armazenamento.carregar()
        self.assertEqual([e.to_dict() for e in recarregados], conteudo)

    def test_arquivos_invalidos_levantam_erro_de_armazenamento(self):
        conteudos = ['{ não é json', '{"ativos": {}}', '[{"id_ativo": 1}]',
                     json.dumps([novo_equipamento().to_dict(), novo_equipamento(nome='Outro').to_dict()])]
        for conteudo in conteudos:
            with self.subTest(conteudo[:25]):
                with open(self.caminho, 'w', encoding='utf-8') as arquivo:
                    arquivo.write(conteudo)
                with self.assertRaises(ErroArmazenamento):
                    self.armazenamento.carregar()

    def test_guardar_copia(self):
        with open(self.caminho, 'w', encoding='utf-8') as arquivo:
            arquivo.write('lixo')
        copia = self.armazenamento.guardar_copia()
        self.assertTrue(copia and os.path.exists(copia))
        self.assertIsNone(ArmazenamentoJSON(os.path.join(self.pasta.name, 'nao-existe.json')).guardar_copia())


class TestMenus(unittest.TestCase):
    """Simula um usuário digitando no terminal."""

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.caminho = os.path.join(self.pasta.name, 'dados.json')
        self.inventario = Inventario(ArmazenamentoJSON(self.caminho))

    def executar(self, menu_classe, digitado):
        saida = io.StringIO()
        with patch('builtins.input', side_effect=digitado), contextlib.redirect_stdout(saida):
            menu_classe(self.inventario).executar()
        return saida.getvalue()

    def arquivo(self):
        with open(self.caminho, encoding='utf-8') as arquivo:
            return json.load(arquivo)

    def test_cadastro_com_vulnerabilidade_inicial_e_entradas_invalidas(self):
        digitado = ['1',
                    'abc', '1.5', '-1', '1000000', '5',          # IDs inválidos, depois o válido
                    '', 'Servidor-DB',                           # nome vazio, depois válido
                    'Ana', 'Datacenter',
                    '9', 'x', '5',                               # tipo inválido, depois BANCO_DE_DADOS
                    '1', 'Servidor de banco',                    # status ATIVO, descrição
                    's', 'Senha fraca', 'Autenticação', '4', '1',  # vulnerabilidade inicial
                    'n', '7']
        saida = self.executar(MenuPrincipal, digitado)
        ativo = self.inventario.obter(5)
        self.assertIsInstance(ativo, BancoDeDados)
        self.assertEqual(len(ativo.vulnerabilidades), 1)
        self.assertEqual(ativo.vulnerabilidades[0].severidade, SeveridadeVulnerabilidade.CRITICA)
        self.assertIn('Injeção de SQL', saida)  # sugestão polimórfica de categorias
        gravado = self.arquivo()
        self.assertEqual(gravado[0]['id_ativo'], 5)
        self.assertEqual(gravado[0]['tipo'], 'BANCO_DE_DADOS')

    def test_cadastro_recusa_id_e_nome_duplicados(self):
        self.inventario.adicionar(novo_equipamento(1, 'Roteador'))
        saida = self.executar(MenuPrincipal, ['1', '1', '7'])
        self.assertIn('Já existe um ativo com esse identificador.', saida)
        saida = self.executar(MenuPrincipal, ['1', '2', 'ROTEADOR', '7'])
        self.assertIn('Já existe um ativo com esse nome ou hostname.', saida)
        self.assertEqual(len(self.inventario), 1)

    def test_atualizar_recusa_nome_duplicado_e_troca_de_tipo(self):
        self.inventario.adicionar(novo_equipamento(1, 'Roteador'))
        self.inventario.adicionar(novo_equipamento(2, 'Switch'))
        digitado = ['4', '2',
                    'roteador', 'Switch-2',   # nome duplicado é recusado; depois aceita
                    'Bruno', '', '',          # responsável; setor e descrição inalterados
                    's', '2',                 # alterar tipo -> SISTEMA
                    'n',                      # status inalterado
                    '7']
        saida = self.executar(MenuPrincipal, digitado)
        self.assertIn('Já existe outro ativo com esse nome ou hostname.', saida)
        ativo = self.inventario.obter(2)
        self.assertIsInstance(ativo, Sistema)
        self.assertEqual((ativo.nome, ativo.responsavel), ('Switch-2', 'Bruno'))
        self.assertEqual(self.arquivo()[1]['tipo'], 'SISTEMA')

    def test_remover_ativo_remove_vulnerabilidades_do_arquivo(self):
        ativo = novo_equipamento()
        ativo.adicionar_vulnerabilidade(nova_vulnerabilidade())
        self.inventario.adicionar(ativo)
        self.inventario.salvar()
        self.executar(MenuPrincipal, ['5', '1', 'n', '5', '1', 's', '7'])
        self.assertEqual(len(self.inventario), 0)
        self.assertEqual(self.arquivo(), [])

    def test_busca_por_id_e_por_nome_no_menu(self):
        self.inventario.adicionar(novo_equipamento(1, 'Roteador'))
        self.assertIn('Responsável: Ana', self.executar(MenuPrincipal, ['3', '000001', '7']))
        self.assertIn('Responsável: Ana', self.executar(MenuPrincipal, ['3', 'rote', '7']))
        self.assertIn('Ativo não encontrado.', self.executar(MenuPrincipal, ['3', 'zzz', '7']))

    def test_menu_principal_rejeita_opcoes_invalidas(self):
        saida = self.executar(MenuPrincipal, ['abc', '', '1.5', '-1', '99', '7'])
        self.assertEqual(saida.count('Digite um número inteiro válido.'), 3)
        self.assertEqual(saida.count('Digite uma opção válida!'), 2)

    def test_vulnerabilidades_ciclo_completo(self):
        self.inventario.adicionar(novo_equipamento())
        saida = self.executar(MenuVulnerabilidades, ['3', '1', '6'])
        self.assertIn('sem vulnerabilidades registradas', saida)
        self.executar(MenuVulnerabilidades, ['1', '1', 'Patch pendente', 'Atualização', '2', '2', '6'])
        ativo = self.inventario.obter(1)
        self.assertEqual(ativo.vulnerabilidades[0].status, StatusTratamento.EM_TRATAMENTO)
        saida = self.executar(MenuVulnerabilidades, ['3', '1', '6'])
        self.assertIn('Patch pendente', saida)
        self.executar(MenuVulnerabilidades, ['4', '1', '1', '3', '6'])
        self.assertEqual(ativo.vulnerabilidades[0].status, StatusTratamento.CORRIGIDA)
        self.assertEqual(self.arquivo()[0]['vulnerabilidades'][0]['status'], 'CORRIGIDA')
        self.executar(MenuVulnerabilidades, ['5', '1', '1', '6'])
        self.assertEqual(self.arquivo()[0]['vulnerabilidades'], [])


class TestMain(unittest.TestCase):
    def test_ctrl_c_encerra_sem_traceback(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, 'dados.json')
            with open(caminho, 'w', encoding='utf-8') as arquivo:
                arquivo.write('{ quebrado')
            saida = io.StringIO()
            with patch.dict(os.environ, {'INVENTARIO_ARQUIVO': caminho}), \
                    patch('builtins.input', side_effect=KeyboardInterrupt), \
                    contextlib.redirect_stdout(saida):
                aplicacao.main()
            self.assertIn('Programa encerrado.', saida.getvalue())
            self.assertIn('JSON válido', saida.getvalue())       # avisou do arquivo quebrado
            self.assertTrue(any(nome.endswith('.bak') for nome in os.listdir(pasta)))  # e guardou cópia


if __name__ == '__main__':
    unittest.main()
