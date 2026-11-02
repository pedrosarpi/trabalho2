"""Requisito 4: cenários resolvidos à mão, validação numérica e integração."""
import contextlib
import io
import json
from unittest.mock import patch

import numpy as np
import pytest

from app.dados import ArmazenamentoJSON, ErroArmazenamento
from app.equipamentos import Dependencia, Equipamento
from app.inventario import Inventario
from app.menus import MenuPrincipal, MenuRiscos, MenuVulnerabilidades
from app.modelos import SeveridadeVulnerabilidade as S, StatusTratamento, TipoAtivo, Vulnerabilidade
from app.riscos import AnalisadorRisco, ErroAnaliseRisco
from app.seguranca import calcular_cvss


VETOR = 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'


def ativo(identificador, severidade=None, dependencias=None):
    vulnerabilidades = [] if severidade is None else [Vulnerabilidade('Falha de teste', 'Teste', severidade)]
    return Equipamento.criar(TipoAtivo.SISTEMA, id_ativo=identificador, nome=f'Ativo {identificador}',
                             responsavel='Teste', setor_localizacao='Laboratório',
                             vulnerabilidades=vulnerabilidades, dependencias=dependencias)


def cenario():
    """b=(8,5,2), x3=2, x2=5+0.5*2=6, x1=8+0.25*6+0.1*2=9.7."""
    a, b, c = ativo(10, S.ALTA), ativo(30, S.MEDIA), ativo(90, S.BAIXA)
    a.definir_dependencia(30, 0.25)
    a.definir_dependencia(90, 0.1)
    b.definir_dependencia(90, 0.5)
    return [a, b, c]


def inventario(tmp_path, ativos=None):
    inv = Inventario(ArmazenamentoJSON(str(tmp_path / 'inventario.json')))
    for equipamento in ativos or []:
        inv.adicionar(equipamento)
    return inv


def executar(menu, entradas):
    saida = io.StringIO()
    with patch('builtins.input', side_effect=entradas), contextlib.redirect_stdout(saida):
        menu.executar()
    return saida.getvalue()


def test_cenario_manual_e_ordem_dos_ids():
    resultado = AnalisadorRisco().calcular(list(reversed(cenario())))
    modelo = resultado.modelo
    assert [e.id_ativo for e in modelo.equipamentos] == [10, 30, 90]
    np.testing.assert_array_equal(modelo.M, np.eye(3, dtype=int))
    np.testing.assert_array_equal(modelo.v, [8, 5, 2])
    np.testing.assert_array_equal(modelo.b, [8, 5, 2])
    np.testing.assert_allclose(modelo.A, [[0, .25, .1], [0, 0, .5], [0, 0, 0]])
    np.testing.assert_allclose(resultado.x, [9.7, 6, 2])
    np.testing.assert_allclose(modelo.sistema @ resultado.x, modelo.b)
    assert resultado.posto == 3 and resultado.impedimento is None
    assert resultado.determinante == pytest.approx(1)
    assert resultado.residuo_relativo < 1e-12


def test_direcao_e_ativo_sem_falhas_herda_risco():
    receptor, origem = ativo(1), ativo(2, S.ALTA)
    receptor.definir_dependencia(2, .5)
    r = AnalisadorRisco().calcular([origem, receptor])
    np.testing.assert_array_equal(r.modelo.M, [[0], [1]])
    np.testing.assert_allclose(r.modelo.b, [0, 8])
    np.testing.assert_allclose(r.x, [4, 8])


def test_ciclo_invertivel_resolvido_a_mao():
    # x1=8+.5*x2; x2=5+.25*x1 => x1=12; x2=8.
    a, b = ativo(1, S.ALTA), ativo(2, S.MEDIA)
    a.definir_dependencia(2, .5)
    b.definir_dependencia(1, .25)
    r = AnalisadorRisco().calcular([a, b])
    np.testing.assert_allclose(r.x, [12, 8])
    assert r.determinante == pytest.approx(.875)


def test_sem_dependencias_x_igual_b_e_soma_nao_limitada_a_dez():
    a = ativo(1, S.ALTA)
    a.adicionar_vulnerabilidade(Vulnerabilidade('Outra falha', 'Teste', S.MEDIA))
    r = AnalisadorRisco().calcular([a, ativo(2)])
    np.testing.assert_array_equal(r.modelo.M, [[1, 1], [0, 0]])
    np.testing.assert_allclose(r.x, [13, 0])
    np.testing.assert_array_equal(r.x, r.modelo.b)


def test_sem_vulnerabilidades_m_tem_zero_colunas():
    a, b = ativo(1), ativo(2)
    a.definir_dependencia(2, .25)
    r = AnalisadorRisco().calcular([a, b])
    assert r.modelo.M.shape == (2, 0) and r.modelo.v.shape == (0,)
    np.testing.assert_array_equal(r.x, [0, 0])


def test_vazio_gera_mensagem_clara():
    with pytest.raises(ErroAnaliseRisco, match='Nenhum ativo'):
        AnalisadorRisco().calcular([])


def test_cvss_tem_precedencia_e_nao_usa_numero_do_enum():
    a = ativo(1, S.BAIXA)
    a.vulnerabilidades[0].cvss = calcular_cvss(VETOR)
    a.adicionar_vulnerabilidade(Vulnerabilidade('Sem impacto', 'Teste', S.NENHUMA))
    r = AnalisadorRisco().calcular([a])
    np.testing.assert_allclose(r.modelo.v, [9.8, 0])
    assert r.x[0] == pytest.approx(9.8)
    assert 'CVSS 3.1' in r.modelo.colunas[0].origem_severidade


@pytest.mark.parametrize('severidade,peso', [(S.NENHUMA, 0), (S.BAIXA, 2), (S.MEDIA, 5), (S.ALTA, 8), (S.CRITICA, 10)])
def test_escala_manual_explicita(severidade, peso):
    r = AnalisadorRisco().calcular([ativo(1, severidade)])
    assert r.modelo.v[0] == peso
    assert 'escala local' in r.avisos[0]


def test_nao_avaliada_nao_vira_zero():
    with pytest.raises(ErroAnaliseRisco, match='000002/V1'):
        AnalisadorRisco().calcular([ativo(1, S.ALTA), ativo(2, S.NAO_AVALIADA)])


@pytest.mark.parametrize('status', list(StatusTratamento))
def test_modelo_literal_inclui_todos_os_registros(status):
    a = ativo(1, S.ALTA)
    a.vulnerabilidades[0].alterar_status(status)
    assert AnalisadorRisco().calcular([a]).x[0] == 8


def test_ocorrencias_com_mesmo_cve_nao_perdem_avaliacoes():
    a, b = ativo(1, S.ALTA), ativo(2, S.BAIXA)
    for e in [a, b]:
        e.vulnerabilidades[0].cve_id = 'CVE-2021-44228'
    r = AnalisadorRisco().calcular([a, b])
    assert len(r.modelo.colunas) == 2
    np.testing.assert_array_equal(r.modelo.M, np.eye(2))
    np.testing.assert_allclose(r.x, [8, 2])


def test_singular_detectada_antes_do_solve(tmp_path):
    # Aij=.5 para i != j => cada linha soma 1 => (I-A) * [1,1,1] = 0.
    ativos = [ativo(i, S.ALTA, [Dependencia(j, .5) for j in [1, 2, 3] if j != i]) for i in [1, 2, 3]]
    inv = inventario(tmp_path, ativos)
    inv.salvar()
    inv.carregar()  # Importação mantém os dados para permitir diagnóstico.
    with patch('app.riscos.np.linalg.solve') as resolver:
        r = inv.calcular_riscos()
    resolver.assert_not_called()
    assert r.x is None and r.posto == 2 and 'não é invertível' in r.impedimento
    np.testing.assert_allclose(r.modelo.b, [8, 8, 8])
    saida = executar(MenuRiscos(inv, 'teste'), ['4', '6'])
    assert 'indisponível' in saida and 'não é invertível' in saida


def test_mal_condicionada_bloqueada_antes_do_solve():
    a, b = ativo(1, S.ALTA), ativo(2, S.BAIXA)
    a.definir_dependencia(2, 1 - 1e-13)
    b.definir_dependencia(1, 1 - 1e-13)
    with patch('app.riscos.np.linalg.solve') as resolver:
        r = AnalisadorRisco().calcular([a, b])
    resolver.assert_not_called()
    assert r.posto == 2 and r.condicao > 1e12
    assert r.x is None and 'mal condicionada' in r.impedimento


def test_condicao_alta_ainda_resolvida_com_aviso():
    a, b = ativo(1, S.ALTA), ativo(2, S.BAIXA)
    a.definir_dependencia(2, 1 - 1e-9)
    b.definir_dependencia(1, 1 - 1e-9)
    r = AnalisadorRisco().calcular([a, b])
    assert r.x is not None
    assert any('condição elevado' in aviso for aviso in r.avisos)


def test_determinante_pequeno_nao_e_prova_de_singularidade():
    ativos = []
    for i in range(1, 21, 2):
        a, b = ativo(i, S.BAIXA), ativo(i + 1, S.BAIXA)
        a.definir_dependencia(i + 1, .99)
        b.definir_dependencia(i, .99)
        ativos.extend([a, b])
    r = AnalisadorRisco().calcular(ativos)
    assert abs(r.determinante) < 1e-12 and r.posto == 20
    np.testing.assert_allclose(r.x, np.full(20, 200))


def test_soma_de_linha_maior_que_um_nao_prova_singularidade():
    ativos = [ativo(1, S.ALTA, [Dependencia(2, .6), Dependencia(3, .6)]),
              ativo(2, S.MEDIA), ativo(3, S.BAIXA)]
    r = AnalisadorRisco().calcular(ativos)
    np.testing.assert_allclose(r.x, [12.2, 5, 2])
    assert any('dominância' in aviso for aviso in r.avisos)


def test_solucao_negativa_importada_exibe_aviso_sem_truncar():
    ativos = [ativo(i, S.BAIXA, [Dependencia(j, .75) for j in [1, 2, 3] if i != j]) for i in [1, 2, 3]]
    r = AnalisadorRisco().calcular(ativos)
    np.testing.assert_allclose(r.x, [-4, -4, -4])
    assert any('não é interpretável como risco' in aviso for aviso in r.avisos)


@pytest.mark.parametrize('peso', [-.1, 1, 1.1, float('nan'), float('inf'), True, '.5', None])
def test_pesos_invalidos(peso):
    with pytest.raises(ValueError):
        Dependencia(2, peso)


def test_autodependencia_soma_e_atualizacao_atomica(tmp_path):
    inv = inventario(tmp_path, [ativo(i) for i in [1, 2, 3, 4]])
    with pytest.raises(ValueError, match='si mesmo'):
        inv.definir_dependencia(1, 1, .1)
    with pytest.raises(ValueError, match='cadastrados'):
        inv.definir_dependencia(1, 99, .1)
    inv.definir_dependencia(1, 2, .5)
    inv.definir_dependencia(1, 2, .7)  # substitui, não soma com o peso antigo
    with pytest.raises(ValueError, match='menor que 1'):
        inv.definir_dependencia(1, 3, .3)
    assert inv.obter(1).dependencias == (Dependencia(2, .7),)
    inv.definir_dependencia(1, 2, .1)
    inv.definir_dependencia(1, 3, .2)
    with pytest.raises(ValueError, match='menor que 1'):
        inv.definir_dependencia(1, 4, .7)


def test_peso_zero_permitido():
    a = ativo(1)
    a.definir_dependencia(2, 0)
    assert a.dependencias == (Dependencia(2, 0),)


@pytest.mark.parametrize('deps', [None, {}, 'texto', [1], [{'id_origem': 1, 'peso': .5}],
                                  [{'id_origem': 2, 'peso': .5}, {'id_origem': 2, 'peso': .1}],
                                  [{'id_origem': True, 'peso': .5}]])
def test_json_dependencias_invalidas(deps):
    dados = ativo(1).to_dict()
    dados['dependencias'] = deps
    with pytest.raises(ValueError):
        Equipamento.from_dict(dados)


def test_referencia_inexistente_e_rejeitada_na_leitura_e_gravacao(tmp_path):
    armazenamento = ArmazenamentoJSON(str(tmp_path / 'invalido.json'))
    a = ativo(1, S.ALTA, [Dependencia(99, .5)])
    (tmp_path / 'invalido.json').write_text(json.dumps([a.to_dict()]))
    with pytest.raises(ErroArmazenamento, match='inexistente'):
        armazenamento.carregar()
    with pytest.raises(ErroArmazenamento, match='inexistente'):
        armazenamento.salvar([a])
    with pytest.raises(ErroAnaliseRisco, match='inexistente'):
        AnalisadorRisco().calcular([a])


def test_roundtrip_recalcula_a_partir_do_json(tmp_path):
    inv = inventario(tmp_path, cenario())
    inv.salvar()
    dados = json.loads((tmp_path / 'inventario.json').read_text())
    assert isinstance(dados, list)
    assert dados[0]['dependencias'] == [{'id_origem': 30, 'peso': .25}, {'id_origem': 90, 'peso': .1}]
    inv.carregar()
    np.testing.assert_allclose(inv.calcular_riscos().x, [9.7, 6, 2])
    inv.obter(90).adicionar_vulnerabilidade(Vulnerabilidade('Nova', 'Teste', S.BAIXA))
    np.testing.assert_allclose(inv.calcular_riscos().x, [10.15, 7, 4])


def test_json_antigo_sem_dependencias_continua_valido(tmp_path):
    dados = ativo(1, S.ALTA).to_dict()
    dados.pop('dependencias')
    dados['vulnerabilidades'][0] = dict(descricao='Falha antiga', categoria='Teste', severidade='ALTA', status='ABERTA')
    (tmp_path / 'inventario.json').write_text(json.dumps([dados]))
    inv = inventario(tmp_path)
    inv.carregar()
    assert inv.obter(1).dependencias == ()
    assert inv.calcular_riscos().x[0] == 8


def test_troca_de_tipo_e_remocao_preservam_integridade(tmp_path):
    inv = inventario(tmp_path, cenario())
    inv.substituir(inv.obter(10).converter_para(TipoAtivo.SERVICO))
    assert len(inv.obter(10).dependencias) == 2
    inv.remover(30)
    inv.salvar()
    inv.carregar()
    assert inv.obter(10).dependencias == (Dependencia(90, .1),)
    np.testing.assert_allclose(inv.calcular_riscos().x, [8.2, 2])


def test_menus_ciclo_completo_com_persistencia(tmp_path):
    inv = inventario(tmp_path, [ativo(1), ativo(2, S.ALTA)])
    saida = executar(MenuRiscos(inv, 'teste'), ['1', '1', '2', 'nan', '1', '0,5', '2', '4', '5', '6'])
    assert 'finito' in saida and '4.0000' in saida and '8.0000' in saida
    assert 'I - A' in saida and 'M (2 x 1)' in saida and '000002/V1' in saida
    inv.carregar()
    assert inv.obter(1).dependencias == (Dependencia(2, .5),)
    executar(MenuRiscos(inv, 'teste'), ['3', '1', '1', 'n', '6'])
    assert len(inv.obter(1).dependencias) == 1
    executar(MenuRiscos(inv, 'teste'), ['3', '1', '1', 's', '6'])
    inv.carregar()
    assert inv.obter(1).dependencias == ()


def test_menu_principal_abre_riscos_e_preserva_saidas(tmp_path):
    inv = inventario(tmp_path)
    # Ajustado para fornecer o número exato de entradas exigidas pelo menu atualizado
    saida = executar(MenuPrincipal(inv, 'teste'), ['7', '4', '6', '6', '8', '9'])
    assert 'Nenhum ativo cadastrado para analisar' in saida
    assert MenuPrincipal(inv, 'teste').opcoes()[9][1] is None
    assert list(MenuPrincipal(inv, 'teste').opcoes())[-1] == 9
    assert saida.index('7 - Análise de risco e dependências') < saida.index('9 - Sair')
    assert MenuVulnerabilidades(inv, 'teste').opcoes()[8][1] is None


def test_menu_pendencia_e_cancelamento(tmp_path):
    inv = inventario(tmp_path, [ativo(1, S.NAO_AVALIADA), ativo(2)])
    saida = executar(MenuRiscos(inv, 'teste'), ['4', '1', '1', '1', '1', '1', '2', '', '6'])
    assert 'NÃO AVALIADAS' in saida and 'si mesmo' in saida
    assert inv.obter(1).dependencias == ()