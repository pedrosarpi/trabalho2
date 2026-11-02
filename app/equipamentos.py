"""Hierarquia de equipamentos (ativos de TI).

`Equipamento` é a classe base (abstrata). Cada valor de `TipoAtivo` tem uma
subclasse própria. Cada ativo cadastrado é UM OBJETO de uma dessas subclasses,
e as suas vulnerabilidades ficam dentro dele (composição): remover o ativo
remove, naturalmente, as vulnerabilidades junto.
"""
from __future__ import annotations

import re
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.modelos import StatusAtivo, TipoAtivo, Vulnerabilidade, campo_enum, campo_texto

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


@dataclass(frozen=True)
class Dependencia:
    """O equipamento que guarda este objeto recebe peso * risco(id_origem)."""

    id_origem: int
    peso: float

    def __post_init__(self):
        object.__setattr__(self, 'id_origem', converter_id(self.id_origem))
        if isinstance(self.peso, bool) or not isinstance(self.peso, (int, float)):
            raise ValueError('O peso da dependência deve ser numérico.')
        if not math.isfinite(self.peso) or not 0 <= self.peso < 1:
            raise ValueError('O peso da dependência deve ser finito e estar em [0, 1).')
        object.__setattr__(self, 'peso', float(self.peso))

    def to_dict(self) -> dict:
        return {'id_origem': self.id_origem, 'peso': self.peso}

    @staticmethod
    def from_dict(dados: dict) -> Dependencia:
        if not isinstance(dados, dict):
            raise ValueError('A dependência deve ser um objeto JSON.')
        return Dependencia(dados.get('id_origem'), dados.get('peso'))


def validar_referencias(equipamentos) -> None:
    """Valida relações entre objetos depois que todos os IDs foram carregados."""
    ids = {e.id_ativo for e in equipamentos}
    for equipamento in equipamentos:
        for dependencia in equipamento.dependencias:
            if dependencia.id_origem not in ids:
                raise ValueError(
                    f'Ativo {equipamento.id_formatado}: dependência referencia '
                    f'o ativo inexistente {dependencia.id_origem:06d}.')


class Equipamento(ABC):
    """Classe base: tudo o que é comum a qualquer ativo de TI."""

    def __init__(self, id_ativo: int, nome: str, responsavel: str, setor_localizacao: str,
                 status: StatusAtivo = StatusAtivo.ATIVO, descricao: str = '',
                 vulnerabilidades: list[Vulnerabilidade] | None = None,
                 dependencias: list[Dependencia] | None = None,
                 adicionado_por: str = '', ultima_modificacao_por: str = '',
                 adicionado_por_id: str = '', ultima_modificacao_por_id: str = '',
                 responsavel_id: str = ''):
        self.id_ativo = converter_id(id_ativo)
        self.nome = campo_texto({'nome': nome}, 'nome')
        self.responsavel = campo_texto({'responsavel': responsavel}, 'responsavel')
        self.setor_localizacao = campo_texto({'setor': setor_localizacao}, 'setor')
        if not isinstance(status, StatusAtivo):
            raise ValueError('Status de ativo inválido.')
        for valor in (descricao, adicionado_por, ultima_modificacao_por, adicionado_por_id,
                      ultima_modificacao_por_id, responsavel_id):
            if not isinstance(valor, str):
                raise ValueError('Descrição e campos de autoria/responsável devem ser textos.')
        self.responsavel_id = responsavel_id
        self.adicionado_por_id = adicionado_por_id
        self.ultima_modificacao_por_id = ultima_modificacao_por_id or adicionado_por_id
        self.status = status
        self.descricao = descricao
        self.adicionado_por = adicionado_por
        self.ultima_modificacao_por = ultima_modificacao_por or adicionado_por
        self._vulnerabilidades = list(vulnerabilidades or [])
        self._dependencias: dict[int, Dependencia] = {}
        for dependencia in dependencias or []:
            if dependencia.id_origem == self.id_ativo:
                raise ValueError('Um ativo não pode depender de si mesmo (Aii deve ser zero).')
            if dependencia.id_origem in self._dependencias:
                raise ValueError('Dependência duplicada para o mesmo ativo de origem.')
            self._dependencias[dependencia.id_origem] = dependencia
        # Na leitura, preservamos linhas com soma >= 1 para diagnosticá-las no
        # cálculo. A regra de soma < 1 é imposta ao cadastrar/editar pelo sistema.

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
        if not isinstance(vulnerabilidade, Vulnerabilidade):
            raise ValueError('Vulnerabilidade inválida.')
        if vulnerabilidade.cve_id and any(v.cve_id == vulnerabilidade.cve_id for v in self.vulnerabilidades):
            raise ValueError('Este CVE já está cadastrado neste ativo.')
        self._vulnerabilidades.append(vulnerabilidade)

    def substituir_vulnerabilidade(self, indice: int, vulnerabilidade: Vulnerabilidade) -> None:
        if not 0 <= indice < len(self._vulnerabilidades):
            raise ValueError('Vulnerabilidade não encontrada.')
        if vulnerabilidade.cve_id and any(i != indice and v.cve_id == vulnerabilidade.cve_id
                                          for i, v in enumerate(self.vulnerabilidades)):
            raise ValueError('Este CVE já está cadastrado neste ativo.')
        self._vulnerabilidades[indice] = vulnerabilidade

    def remover_vulnerabilidade(self, vulnerabilidade: Vulnerabilidade) -> None:
        self._vulnerabilidades.remove(vulnerabilidade)

    @property
    def dependencias(self) -> tuple[Dependencia, ...]:
        return tuple(self._dependencias.values())

    def definir_dependencia(self, id_origem: int, peso: float) -> None:
        dependencia = Dependencia(id_origem, peso)
        if dependencia.id_origem == self.id_ativo:
            raise ValueError('Um ativo não pode depender de si mesmo (Aii deve ser zero).')
        soma = math.fsum([d.peso for d in self.dependencias if d.id_origem != dependencia.id_origem]
                         + [dependencia.peso])
        if soma >= 1:
            raise ValueError(f'A soma dos pesos deste ativo seria {soma:.6g}; ela deve ser menor que 1.')
        self._dependencias[dependencia.id_origem] = dependencia

    def remover_dependencia(self, id_origem: int) -> None:
        if id_origem not in self._dependencias:
            raise ValueError('Este ativo não possui essa dependência.')
        del self._dependencias[id_origem]

    def atualizar(self, nome: str | None = None, responsavel: str | None = None,
                  setor_localizacao: str | None = None, descricao: str | None = None,
                  status: StatusAtivo | None = None, ultima_modificacao_por: str | None = None) -> None:
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
        if ultima_modificacao_por:
            self.ultima_modificacao_por = ultima_modificacao_por

    def converter_para(self, novo_tipo: TipoAtivo) -> Equipamento:
        return Equipamento.criar(
            novo_tipo, id_ativo=self.id_ativo, nome=self.nome, responsavel=self.responsavel,
            setor_localizacao=self.setor_localizacao, status=self.status,
            descricao=self.descricao, vulnerabilidades=self._vulnerabilidades,
            dependencias=list(self.dependencias), 
            adicionado_por=self.adicionado_por, ultima_modificacao_por=self.ultima_modificacao_por,
            adicionado_por_id=self.adicionado_por_id, ultima_modificacao_por_id=self.ultima_modificacao_por_id,
            responsavel_id=self.responsavel_id)

    def detalhes(self) -> str:
        base = (f'ID: {self.id_formatado}\n'
                f'Nome/hostname: {self.nome}\n'
                f'Responsável: {self.responsavel}\n'
                f'Setor/localização: {self.setor_localizacao}\n'
                f'Tipo: {self.tipo.name}\n'
                f'Status: {self.status.name}\n'
                f'Descrição: {self.descricao or "Não informada"}\n'
                f'Vulnerabilidades: {len(self._vulnerabilidades)}\n'
                f'Dependências: {len(self._dependencias)}')
        
        auditoria = f'\nAdicionado por: {self.adicionado_por}' if self.adicionado_por else ''
        if self.ultima_modificacao_por and self.ultima_modificacao_por != self.adicionado_por:
            auditoria += f'\nÚltima modificação por: {self.ultima_modificacao_por}'
            
        return base + auditoria

    def __str__(self) -> str:
        base = f'{self.id_formatado} - {self.nome} | Tipo: {self.tipo.name} | Status: {self.status.name}'
        return base + (f' | Adicionado por: {self.adicionado_por}' if self.adicionado_por else '')

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
            'dependencias': [d.to_dict() for d in self.dependencias],
            'adicionado_por_id': self.adicionado_por_id,
            'ultima_modificacao_por_id': self.ultima_modificacao_por_id,
            'responsavel_id': self.responsavel_id,
            'adicionado_por': self.adicionado_por,
            'ultima_modificacao_por': self.ultima_modificacao_por,
        }

    @staticmethod
    def criar(tipo: TipoAtivo, **campos) -> Equipamento:
        return CLASSES_POR_TIPO[tipo](**campos)

    @staticmethod
    def from_dict(dados: dict) -> Equipamento:
        if not isinstance(dados, dict):
            raise ValueError('o registro não é um objeto JSON')
        lista = dados.get('vulnerabilidades', [])
        if not isinstance(lista, list):
            raise ValueError("o campo 'vulnerabilidades' deve ser uma lista")
        vulnerabilidades = []
        for posicao, item in enumerate(lista, 1):
            try:
                vulnerabilidades.append(Vulnerabilidade.from_dict(item))
            except ValueError as erro:
                raise ValueError(f'vulnerabilidade {posicao}: {erro}') from erro
        dependencias = dados.get('dependencias', [])
        if not isinstance(dependencias, list):
            raise ValueError("o campo 'dependencias' deve ser uma lista")
            
        # Tratamento retroativo caso tenha ficado salvo como 'modificado_por'
        add_por = dados.get('adicionado_por', dados.get('modificado_por', ''))
        ult_mod = dados.get('ultima_modificacao_por', dados.get('modificado_por', ''))
            
        return Equipamento.criar(
            campo_enum(TipoAtivo, dados, 'tipo'),
            id_ativo=converter_id(dados.get('id_ativo')),
            nome=campo_texto(dados, 'nome'),
            responsavel=campo_texto(dados, 'responsavel'),
            setor_localizacao=campo_texto(dados, 'setor_localizacao'),
            status=campo_enum(StatusAtivo, dados, 'status'),
            descricao=campo_texto(dados, 'descricao', obrigatorio=False),
            vulnerabilidades=vulnerabilidades,
            dependencias=[Dependencia.from_dict(d) for d in dependencias],
            adicionado_por_id=dados.get('adicionado_por_id', ''),
            ultima_modificacao_por_id=dados.get('ultima_modificacao_por_id', ''),
            responsavel_id=dados.get('responsavel_id', ''),
            adicionado_por=add_por,
            ultima_modificacao_por=ult_mod)


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
