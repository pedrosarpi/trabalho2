"""Unidade de trabalho para a web: recarrega, valida revisão e salva sob lock.

O arquivo continua sendo o array JSON exigido no trabalho. A revisão impede
que um formulário antigo sobrescreva alterações ou atinja outra vulnerabilidade.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path

from filelock import FileLock

from app.dados import ArmazenamentoJSON, ErroArmazenamento
from app.inventario import Inventario


class ConflitoEdicao(ValueError):
    pass


class ServicoInventario:
    def __init__(self, caminho):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.caminho) + '.lock', timeout=10)
        self.armazenamento = ArmazenamentoJSON(str(self.caminho))

    def revisao(self):
        try:
            dados = self.caminho.read_bytes() if self.caminho.exists() else b'[]'
            return hashlib.sha256(dados).hexdigest()
        except OSError as erro:
            raise ErroArmazenamento('Não foi possível ler o inventário.') from erro

    def _carregar(self):
        inventario = Inventario(self.armazenamento)
        inventario.carregar()
        return inventario

    def ler(self):
        with self.lock:
            return self._carregar(), self.revisao()

    @contextmanager
    def editar(self, revisao):
        with self.lock:
            if not revisao or revisao != self.revisao():
                raise ConflitoEdicao('Os dados mudaram desde que esta página foi aberta. Recarregue a página e tente novamente.')
            inventario = self._carregar()
            yield inventario
            inventario.salvar()
