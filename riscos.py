"""Modelo linear do requisito 4: b = M @ v e (I - A) @ x = b.

Não acessa terminal, arquivos ou rede. O inventário fornece os objetos
reconstruídos do JSON. Os resultados são recalculados, nunca salvos como cache.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from equipamentos import Equipamento, validar_referencias
from modelos import SeveridadeVulnerabilidade


# Política LOCAL para o cadastro qualitativo antigo, não uma conversão oficial
# para CVSS. Os números do Enum são opções de menu e NÃO são pesos de risco.
PESOS_MANUAIS = {
    SeveridadeVulnerabilidade.NENHUMA: 0.0,
    SeveridadeVulnerabilidade.BAIXA: 2.0,
    SeveridadeVulnerabilidade.MEDIA: 5.0,
    SeveridadeVulnerabilidade.ALTA: 8.0,
    SeveridadeVulnerabilidade.CRITICA: 10.0,
}
LIMITE_AVISO_CONDICAO = 1e8
LIMITE_BLOQUEIO_CONDICAO = 1e12
TOLERANCIA_RESIDUO = 1e-10


class ErroAnaliseRisco(ValueError):
    """Dados insuficientes ou inválidos para montar o modelo."""


@dataclass(frozen=True)
class ColunaVulnerabilidade:
    rotulo: str
    descricao: str
    origem_severidade: str


@dataclass(frozen=True)
class ModeloRisco:
    equipamentos: tuple[Equipamento, ...]
    colunas: tuple[ColunaVulnerabilidade, ...]
    M: np.ndarray
    v: np.ndarray
    A: np.ndarray
    b: np.ndarray
    sistema: np.ndarray
    avisos: tuple[str, ...]


@dataclass(frozen=True)
class ResultadoRisco:
    modelo: ModeloRisco
    x: np.ndarray | None
    posto: int
    condicao: float
    determinante: float
    residuo_relativo: float | None
    avisos: tuple[str, ...]
    impedimento: str | None = None


class AnalisadorRisco:
    """Monta as matrizes e verifica a solução antes de apresentá-la."""

    def montar_modelo(self, equipamentos: list[Equipamento]) -> ModeloRisco:
        ativos = tuple(sorted(equipamentos, key=lambda e: e.id_ativo))
        if not ativos:
            raise ErroAnaliseRisco('Nenhum ativo cadastrado para analisar.')
        ids = {ativo.id_ativo: i for i, ativo in enumerate(ativos)}
        if len(ids) != len(ativos):
            raise ErroAnaliseRisco('Existem IDs de ativos duplicados.')
        try:
            validar_referencias(ativos)
        except ValueError as erro:
            raise ErroAnaliseRisco(str(erro)) from erro
        n = len(ativos)
        m = sum(len(ativo.vulnerabilidades) for ativo in ativos)
        M = np.zeros((n, m), dtype=int)
        v = np.zeros(m, dtype=float)
        A = np.zeros((n, n), dtype=float)
        colunas, avisos, pendencias = [], [], []
        versoes_cvss = set()
        manuais = 0
        j = 0
        for i, ativo in enumerate(ativos):
            for numero, vulnerabilidade in enumerate(ativo.vulnerabilidades, 1):
                rotulo = f'{ativo.id_formatado}/V{numero}'
                if vulnerabilidade.cvss is not None:
                    peso = vulnerabilidade.cvss.nota
                    versao = vulnerabilidade.cvss.versao
                    origem = f'CVSS {versao} ({vulnerabilidade.cvss.fonte})'
                    versoes_cvss.add(versao)
                elif vulnerabilidade.severidade in PESOS_MANUAIS:
                    peso = PESOS_MANUAIS[vulnerabilidade.severidade]
                    origem = f'Escala local: {vulnerabilidade.severidade.name}'
                    manuais += 1
                else:
                    pendencias.append(f'{rotulo} — {ativo.nome}: {vulnerabilidade.descricao}')
                    # Não há solução parcial que trate desconhecido como zero.
                    continue
                if not np.isfinite(peso) or not 0 <= peso <= 10:
                    raise ErroAnaliseRisco(f'{rotulo}: severidade numérica inválida.')
                M[i, j] = 1
                v[j] = peso
                descricao = vulnerabilidade.descricao
                if vulnerabilidade.cve_id:
                    descricao = f'{vulnerabilidade.cve_id} — {descricao}'
                colunas.append(ColunaVulnerabilidade(rotulo, descricao, origem))
                j += 1
            for dependencia in ativo.dependencias:
                A[i, ids[dependencia.id_origem]] = dependencia.peso
        if pendencias:
            raise ErroAnaliseRisco(
                'Há vulnerabilidades NÃO AVALIADAS. Aplique um CVSS antes de calcular:\n'
                + '\n'.join(pendencias))
        if manuais:
            avisos.append(f'{manuais} registro(s) usam a escala local: NENHUMA=0, BAIXA=2, '
                          'MEDIA=5, ALTA=8, CRITICA=10. Esses pesos não são notas CVSS.')
        if len(versoes_cvss) > 1:
            avisos.append('Há notas de versões CVSS diferentes; o modelo soma as notas cadastradas, '
                          'sem convertê-las ou torná-las equivalentes.')
        if np.any(A.sum(axis=1) >= 1):
            avisos.append('Há soma de linha de A >= 1 nos dados importados. A dominância diagonal '
                          'estrita não está garantida; revise as dependências.')
        return ModeloRisco(ativos, tuple(colunas), M, v, A, M @ v, np.eye(n) - A, tuple(avisos))

    def calcular(self, equipamentos: list[Equipamento]) -> ResultadoRisco:
        modelo = self.montar_modelo(equipamentos)
        C, b = modelo.sistema, modelo.b
        n = len(modelo.equipamentos)
        avisos = list(modelo.avisos)
        # O posto usa SVD e tolerância proporcional à precisão de ponto flutuante.
        # O determinante é apenas diagnóstico: det == 0 é um teste frágil.
        try:
            posto = int(np.linalg.matrix_rank(C))
            condicao = float(np.linalg.cond(C))
            with np.errstate(over='ignore', under='ignore', invalid='ignore'):
                determinante = float(np.linalg.det(C))
        except np.linalg.LinAlgError as erro:
            raise ErroAnaliseRisco('Não foi possível verificar a estabilidade numérica de I - A.') from erro

        def resultado(x=None, residuo=None, impedimento=None):
            return ResultadoRisco(modelo, x, posto, condicao, determinante, residuo, tuple(avisos), impedimento)

        if posto < n:
            return resultado(impedimento='I - A não é invertível na precisão numérica utilizada '
                             f'(posto {posto} < {n}). Não há solução única confiável; reveja as dependências.')
        if not np.isfinite(condicao) or condicao >= LIMITE_BLOQUEIO_CONDICAO:
            return resultado(impedimento='I - A tem posto completo, mas está muito mal condicionada '
                             f'(condição >= {LIMITE_BLOQUEIO_CONDICAO:.0e}). '
                             'Cálculo bloqueado para não apresentar um risco pouco confiável.')
        if condicao >= LIMITE_AVISO_CONDICAO:
            avisos.append(f'Número de condição elevado ({condicao:.3e}): pequenas mudanças '
                          'nos dados podem alterar muito o resultado.')
        try:
            # Resolve diretamente: não forma inv(I - A).
            x = np.linalg.solve(C, b)
        except np.linalg.LinAlgError:
            return resultado(impedimento='O sistema não pôde ser resolvido numericamente. Reveja as dependências.')
        if not np.all(np.isfinite(x)):
            return resultado(impedimento='A solução contém valores não finitos e não será apresentada.')
        norma_residuo = float(np.linalg.norm(C @ x - b, ord=np.inf))
        escala = float(np.linalg.norm(C, ord=np.inf) * np.linalg.norm(x, ord=np.inf)
                       + np.linalg.norm(b, ord=np.inf))
        residuo = norma_residuo / escala if escala else 0.0
        if residuo > TOLERANCIA_RESIDUO:
            return resultado(residuo=residuo, impedimento='A solução falhou na verificação do resíduo numérico.')
        if np.any(x < -1e-10):
            avisos.append('A solução algébrica contém valores negativos: não é interpretável como risco. '
                          'Revise os pesos importados e mantenha a soma de cada linha menor que 1.')
        return resultado(x=x, residuo=residuo)
