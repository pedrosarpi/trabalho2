"""Persistência: lê e grava o inventário em um arquivo JSON.

Formato do arquivo: um array (lista) de objetos JSON, um por equipamento.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime

from equipamentos import Equipamento


class ErroArmazenamento(Exception):
    """Falha ao ler ou gravar o arquivo de dados."""


class ArmazenamentoJSON:
    def __init__(self, caminho: str):
        self.caminho = caminho

    def carregar(self) -> list[Equipamento]:
        if not os.path.exists(self.caminho):
            return []
        try:
            with open(self.caminho, 'r', encoding='utf-8') as arquivo:
                conteudo = json.load(arquivo)
        except OSError as erro:
            raise ErroArmazenamento(f'Não foi possível ler o arquivo de dados: {erro}') from erro
        except (json.JSONDecodeError, UnicodeDecodeError) as erro:
            raise ErroArmazenamento(f'O arquivo de dados não contém um JSON válido: {erro}') from erro
        if not isinstance(conteudo, list):
            raise ErroArmazenamento('O arquivo de dados deve conter uma lista (array) de objetos JSON.')

        equipamentos = []
        ids_vistos = set()
        for posicao, item in enumerate(conteudo, 1):
            try:
                equipamento = Equipamento.from_dict(item)
            except ValueError as erro:
                raise ErroArmazenamento(f'Registro {posicao} do arquivo de dados é inválido: {erro}') from erro
            if equipamento.id_ativo in ids_vistos:
                raise ErroArmazenamento(
                    f'Registro {posicao} do arquivo de dados repete o identificador {equipamento.id_formatado}.')
            ids_vistos.add(equipamento.id_ativo)
            equipamentos.append(equipamento)
        return equipamentos

    def salvar(self, equipamentos: list[Equipamento]) -> None:
        dados = [equipamento.to_dict() for equipamento in equipamentos]
        temporario = self.caminho + '.tmp'
        try:
            # Grava num arquivo temporário e só então troca: se algo falhar no
            # meio da gravação, o arquivo bom anterior continua intacto.
            with open(temporario, 'w', encoding='utf-8') as arquivo:
                json.dump(dados, arquivo, ensure_ascii=False, indent=4)
            os.replace(temporario, self.caminho)
        except OSError as erro:
            try:
                os.remove(temporario)
            except OSError:
                pass
            raise ErroArmazenamento(f'Não foi possível salvar o arquivo de dados: {erro}') from erro

    def guardar_copia(self) -> str | None:
        """Copia o arquivo atual para um .bak com data/hora. Devolve o caminho, ou None se falhar."""
        carimbo = datetime.now().strftime('%Y%m%d-%H%M%S')
        destino = f'{self.caminho}.{carimbo}.bak'
        try:
            shutil.copy2(self.caminho, destino)
        except OSError:
            return None
        return destino
