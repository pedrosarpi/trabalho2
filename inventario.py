"""Inventario: a coleção de equipamentos em memória e as buscas sobre ela.

Esta classe não imprime nada e não sabe onde os dados são gravados: quem
cuida do disco é o `armazenamento` recebido no construtor.
"""
from __future__ import annotations

import re

from equipamentos import Equipamento


class Inventario:
    def __init__(self, armazenamento):
        self._armazenamento = armazenamento
        # dict {id_ativo: Equipamento}: acesso direto pelo identificador único.
        self._ativos: dict[int, Equipamento] = {}

    # --- Persistência -------------------------------------------------------

    def carregar(self) -> None:
        self._ativos = {equip.id_ativo: equip for equip in self._armazenamento.carregar()}

    def salvar(self) -> None:
        self._armazenamento.salvar(self.listar())

    # --- Operações do CRUD --------------------------------------------------

    def adicionar(self, equipamento: Equipamento) -> None:
        if equipamento.id_ativo in self._ativos:
            raise ValueError('Já existe um ativo com esse identificador.')
        self._ativos[equipamento.id_ativo] = equipamento

    def obter(self, id_ativo: int) -> Equipamento | None:
        return self._ativos.get(id_ativo)

    def existe(self, id_ativo: int) -> bool:
        return id_ativo in self._ativos

    def substituir(self, equipamento: Equipamento) -> None:
        """Troca o objeto de um ativo existente (usado quando o tipo muda)."""
        if equipamento.id_ativo not in self._ativos:
            raise KeyError(equipamento.id_ativo)
        self._ativos[equipamento.id_ativo] = equipamento

    def remover(self, id_ativo: int) -> Equipamento:
        # As vulnerabilidades vivem dentro do objeto, então saem junto com ele.
        removido = self._ativos.pop(id_ativo)
        for ativo in self._ativos.values():
            if any(d.id_origem == id_ativo for d in ativo.dependencias):
                ativo.remover_dependencia(id_ativo)
        return removido

    def definir_dependencia(self, id_destino: int, id_origem: int, peso: float) -> None:
        """Destino depende da origem: A[destino, origem] = peso."""
        if id_destino not in self._ativos or id_origem not in self._ativos:
            raise ValueError('Os dois ativos da dependência devem estar cadastrados.')
        self._ativos[id_destino].definir_dependencia(id_origem, peso)

    def remover_dependencia(self, id_destino: int, id_origem: int) -> None:
        if id_destino not in self._ativos:
            raise ValueError('Ativo de destino não encontrado.')
        self._ativos[id_destino].remover_dependencia(id_origem)

    def calcular_riscos(self):
        from riscos import AnalisadorRisco
        return AnalisadorRisco().calcular(self.listar())

    def listar(self) -> list[Equipamento]:
        return list(self._ativos.values())

    def __len__(self) -> int:
        return len(self._ativos)

    # --- Consultas ----------------------------------------------------------

    def nome_em_uso(self, nome: str, ignorar_id: int | None = None) -> bool:
        alvo = nome.strip().casefold()
        return any(ativo.nome.casefold() == alvo and ativo.id_ativo != ignorar_id
                   for ativo in self._ativos.values())

    def buscar(self, termo: str) -> list[Equipamento]:
        """Busca por ID (exato) ou por trecho do nome/hostname."""
        termo = termo.strip()
        encontrados: dict[int, Equipamento] = {}
        if re.fullmatch(r'[0-9]+', termo):
            ativo = self.obter(int(termo))  # busca direta no dict, sem percorrer a lista
            if ativo is not None:
                encontrados[ativo.id_ativo] = ativo
        alvo = termo.casefold()
        for ativo in self._ativos.values():
            if alvo in ativo.nome.casefold():
                encontrados[ativo.id_ativo] = ativo
        return list(encontrados.values())
