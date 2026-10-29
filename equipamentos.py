"""Hierarquia de equipamentos (ativos de TI).

`Equipamento` é a classe base (abstrata). Cada valor de `TipoAtivo` tem uma
subclasse própria. Cada ativo cadastrado é UM OBJETO de uma dessas subclasses,
e as suas vulnerabilidades ficam dentro dele (composição): remover o ativo
remove, naturalmente, as vulnerabilidades junto.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod

from modelos import StatusAtivo, TipoAtivo, Vulnerabilidade, campo_enum, campo_texto

ID_MAXIMO = 999_999


def converter_id(valor) -> int:
    """Aceita int ou texto só com dígitos (ex.: "000001" do formato antigo do JSON)."""
    if isinstance(valor, int) and not isinstance(valor, bool):
        identificador = valor
    elif isinstance(valor, str) and re.fullmatch(r'[0-9]+', valor.strip()):
        identificador = int(valor.strip())
    else:
        raise ValueError("o campo 'id_ativo' deve ser um número inteiro")
    if not 0 <= identificador <= ID_MAXIMO:
        raise ValueError(f"o campo 'id_ativo' deve estar entre 0 e {ID_MAXIMO}")
    return identificador


class Equipamento(ABC):
    """Classe base: tudo o que é comum a qualquer ativo de TI."""

    def __init__(self, id_ativo: int, nome: str, responsavel: str, setor_localizacao: str,
                 status: StatusAtivo = StatusAtivo.ATIVO, descricao: str = '',
                 vulnerabilidades: list[Vulnerabilidade] | None = None):
        self.id_ativo = id_ativo
        self.nome = nome
        self.responsavel = responsavel
        self.setor_localizacao = setor_localizacao
        self.status = status
        self.descricao = descricao
        self._vulnerabilidades = list(vulnerabilidades or [])

    # --- O que cada subclasse é obrigada a definir (polimorfismo) -----------

    @property
    @abstractmethod
    def tipo(self) -> TipoAtivo:
        """Qual TipoAtivo esta classe representa."""

    @property
    @abstractmethod
    def categorias_sugeridas(self) -> tuple[str, ...]:
        """Categorias de vulnerabilidade mais comuns para este tipo de ativo."""

    # --- Comportamento comum -----------------------------------------------

    @property
    def id_formatado(self) -> str:
        return f'{self.id_ativo:06d}'

    @property
    def vulnerabilidades(self) -> tuple[Vulnerabilidade, ...]:
        # Devolve uma tupla: quem está fora não altera a lista interna por engano.
        return tuple(self._vulnerabilidades)

    def adicionar_vulnerabilidade(self, vulnerabilidade: Vulnerabilidade) -> None:
        self._vulnerabilidades.append(vulnerabilidade)

    def remover_vulnerabilidade(self, vulnerabilidade: Vulnerabilidade) -> None:
        self._vulnerabilidades.remove(vulnerabilidade)

    def atualizar(self, nome: str | None = None, responsavel: str | None = None,
                  setor_localizacao: str | None = None, descricao: str | None = None,
                  status: StatusAtivo | None = None) -> None:
        """Altera só o que for informado (None ou texto vazio = manter o valor atual)."""
        if nome:
            self.nome = nome
        if responsavel:
            self.responsavel = responsavel
        if setor_localizacao:
            self.setor_localizacao = setor_localizacao
        if descricao:
            self.descricao = descricao
        if status is not None:
            self.status = status

    def converter_para(self, novo_tipo: TipoAtivo) -> Equipamento:
        """Cria um objeto da subclasse do novo tipo, com os mesmos dados.

        Em Python, o tipo de um objeto não muda depois de criado; por isso,
        trocar o tipo de um ativo significa criar um novo objeto equivalente.
        """
        return Equipamento.criar(
            novo_tipo, id_ativo=self.id_ativo, nome=self.nome, responsavel=self.responsavel,
            setor_localizacao=self.setor_localizacao, status=self.status,
            descricao=self.descricao, vulnerabilidades=self._vulnerabilidades)

    def detalhes(self) -> str:
        return (f'ID: {self.id_formatado}\n'
                f'Nome/hostname: {self.nome}\n'
                f'Responsável: {self.responsavel}\n'
                f'Setor/localização: {self.setor_localizacao}\n'
                f'Tipo: {self.tipo.name}\n'
                f'Status: {self.status.name}\n'
                f'Descrição: {self.descricao or "Não informada"}\n'
                f'Vulnerabilidades: {len(self._vulnerabilidades)}')

    def __str__(self) -> str:
        return f'{self.id_formatado} - {self.nome} | Tipo: {self.tipo.name} | Status: {self.status.name}'

    # --- Conversão de/para JSON --------------------------------------------

    def to_dict(self) -> dict:
        return {
            'id_ativo': self.id_ativo,
            'nome': self.nome,
            'responsavel': self.responsavel,
            'setor_localizacao': self.setor_localizacao,
            'tipo': self.tipo.name,
            'status': self.status.name,
            'descricao': self.descricao,
            'vulnerabilidades': [v.to_dict() for v in self._vulnerabilidades],
        }

    @staticmethod
    def criar(tipo: TipoAtivo, **campos) -> Equipamento:
        """Fábrica: escolhe a subclasse certa a partir do TipoAtivo."""
        return CLASSES_POR_TIPO[tipo](**campos)

    @staticmethod
    def from_dict(dados: dict) -> Equipamento:
        if not isinstance(dados, dict):
            raise ValueError('o registro não é um objeto JSON')
        lista = dados.get('vulnerabilidades')
        if lista is None:
            lista = []
        if not isinstance(lista, list):
            raise ValueError("o campo 'vulnerabilidades' deve ser uma lista")
        vulnerabilidades = []
        for posicao, item in enumerate(lista, 1):
            try:
                vulnerabilidades.append(Vulnerabilidade.from_dict(item))
            except ValueError as erro:
                raise ValueError(f'vulnerabilidade {posicao}: {erro}') from erro
        return Equipamento.criar(
            campo_enum(TipoAtivo, dados, 'tipo'),
            id_ativo=converter_id(dados.get('id_ativo')),
            nome=campo_texto(dados, 'nome'),
            responsavel=campo_texto(dados, 'responsavel'),
            setor_localizacao=campo_texto(dados, 'setor_localizacao'),
            status=campo_enum(StatusAtivo, dados, 'status'),
            descricao=campo_texto(dados, 'descricao', obrigatorio=False),
            vulnerabilidades=vulnerabilidades)


class EquipamentoFisico(Equipamento):
    @property
    def tipo(self) -> TipoAtivo:
        return TipoAtivo.EQUIPAMENTO

    @property
    def categorias_sugeridas(self) -> tuple[str, ...]:
        return ('Firmware desatualizado', 'Senha padrão ou fraca', 'Acesso físico indevido')


class Sistema(Equipamento):
    @property
    def tipo(self) -> TipoAtivo:
        return TipoAtivo.SISTEMA

    @property
    def categorias_sugeridas(self) -> tuple[str, ...]:
        return ('Software desatualizado', 'Falha de configuração', 'Permissão de acesso inadequada')


class Servico(Equipamento):
    @property
    def tipo(self) -> TipoAtivo:
        return TipoAtivo.SERVICO

    @property
    def categorias_sugeridas(self) -> tuple[str, ...]:
        return ('Exposição indevida de serviço', 'Autenticação fraca', 'Configuração insegura')


class DispositivoDeRede(Equipamento):
    @property
    def tipo(self) -> TipoAtivo:
        return TipoAtivo.DISPOSITIVO_DE_REDE

    @property
    def categorias_sugeridas(self) -> tuple[str, ...]:
        return ('Firmware desatualizado', 'Porta ou serviço exposto', 'Senha padrão ou fraca')


class BancoDeDados(Equipamento):
    @property
    def tipo(self) -> TipoAtivo:
        return TipoAtivo.BANCO_DE_DADOS

    @property
    def categorias_sugeridas(self) -> tuple[str, ...]:
        return ('Injeção de SQL', 'Permissão de acesso inadequada', 'Dados sem criptografia')


# Dicionário usado pela fábrica: TipoAtivo -> subclasse correspondente.
CLASSES_POR_TIPO = {
    TipoAtivo.EQUIPAMENTO: EquipamentoFisico,
    TipoAtivo.SISTEMA: Sistema,
    TipoAtivo.SERVICO: Servico,
    TipoAtivo.DISPOSITIVO_DE_REDE: DispositivoDeRede,
    TipoAtivo.BANCO_DE_DADOS: BancoDeDados,
}
