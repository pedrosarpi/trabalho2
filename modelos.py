"""Enumerações do domínio e a classe Vulnerabilidade.

Este módulo não conhece o terminal nem o arquivo JSON: ele só descreve o que
é uma vulnerabilidade e quais valores são válidos para tipo, status e severidade.
"""
from __future__ import annotations

from enum import Enum

from seguranca import AvaliacaoCVSS, validar_cve


class TipoAtivo(Enum):
    EQUIPAMENTO = 1
    SISTEMA = 2
    SERVICO = 3
    DISPOSITIVO_DE_REDE = 4
    BANCO_DE_DADOS = 5


class StatusAtivo(Enum):
    ATIVO = 1
    INATIVO = 2
    EM_MANUTENCAO = 3


class SeveridadeVulnerabilidade(Enum):
    BAIXA = 1
    MEDIA = 2
    ALTA = 3
    CRITICA = 4
    NENHUMA = 5
    NAO_AVALIADA = 6


class StatusTratamento(Enum):
    ABERTA = 1
    EM_TRATAMENTO = 2
    CORRIGIDA = 3
    ACEITA_COMO_RISCO = 4


# --- Funções auxiliares para reconstruir objetos a partir do JSON ----------
# O arquivo pode ter sido editado à mão, então nada é assumido: cada campo é
# conferido e, se estiver errado, levanta ValueError com uma mensagem clara.

def campo_texto(dados: dict, chave: str, obrigatorio: bool = True) -> str:
    valor = dados.get(chave)
    if valor is None:
        valor = ''
    if not isinstance(valor, str):
        raise ValueError(f"o campo '{chave}' deve ser um texto")
    valor = valor.strip()
    if obrigatorio and not valor:
        raise ValueError(f"o campo '{chave}' está ausente ou vazio")
    return valor


def campo_enum(enum_classe: type[Enum], dados: dict, chave: str) -> Enum:
    nome = campo_texto(dados, chave)
    try:
        return enum_classe[nome]
    except KeyError:
        validos = ', '.join(item.name for item in enum_classe)
        raise ValueError(f"valor '{nome}' inválido no campo '{chave}' (válidos: {validos})") from None


class Vulnerabilidade:
    """Uma fragilidade registrada em um equipamento."""

    def __init__(self, descricao: str, categoria: str, severidade: SeveridadeVulnerabilidade,
                 status: StatusTratamento = StatusTratamento.ABERTA, *,
                 cve_id=None, cvss=None, consultado_em=None):
        self.descricao = descricao
        self.categoria = categoria
        self.cve_id = validar_cve(cve_id)
        self.cvss = AvaliacaoCVSS.from_dict(cvss.to_dict()) if cvss is not None else None
        if consultado_em is not None and not isinstance(consultado_em, str):
            raise ValueError("A data da consulta deve ser texto.")
        self.consultado_em = consultado_em
        self._severidade = severidade
        self.status = status

    @property
    def severidade(self):
        if self.cvss is not None:
            return SeveridadeVulnerabilidade[self.cvss.severidade]
        return self._severidade

    def alterar_status(self, novo_status: StatusTratamento) -> None:
        self.status = novo_status

    def to_dict(self) -> dict:
        # No JSON, os enums são gravados pelo nome (legível), não pelo número.
        return {
            'descricao': self.descricao,
            'categoria': self.categoria,
            'severidade': self.severidade.name,
            'status': self.status.name,
            'cve_id': self.cve_id,
            'cvss': self.cvss.to_dict() if self.cvss else None,
            'consultado_em': self.consultado_em,
        }

    @staticmethod
    def from_dict(dados: dict) -> Vulnerabilidade:
        if not isinstance(dados, dict):
            raise ValueError('a vulnerabilidade não é um objeto JSON')
        return Vulnerabilidade(
            descricao=campo_texto(dados, 'descricao'),
            categoria=campo_texto(dados, 'categoria'),
            severidade=campo_enum(SeveridadeVulnerabilidade, dados, 'severidade'),
            status=campo_enum(StatusTratamento, dados, 'status'),
            cve_id=dados.get('cve_id'),
            cvss=AvaliacaoCVSS.from_dict(dados['cvss']) if dados.get('cvss') is not None else None,
            consultado_em=dados.get('consultado_em'),
        )

    def __str__(self) -> str:
        return (f'Descrição: {self.descricao} | Categoria: {self.categoria} | '
                f'Severidade: {self.severidade.name} | Status: {self.status.name}'
                + (f' | CVE: {self.cve_id}' if self.cve_id else '')
                + (f' | CVSS Base {self.cvss.versao}: {self.cvss.nota:.1f}'
                   f' | Vetor: {self.cvss.vetor} | Fonte: {self.cvss.fonte}' if self.cvss else ' | CVSS: não avaliado')
                + (f' | Consultado em: {self.consultado_em}' if self.consultado_em else ''))
