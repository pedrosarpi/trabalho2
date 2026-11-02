"""Caminhos estáveis, independentes do diretório atual de execução."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def arquivo_dados(nome):
    # Uma instalação antiga pode ter dados na raiz. Mantém essa base em uso
    # até o usuário migrá-la explicitamente, evitando abrir uma base vazia.
    legado = RAIZ / nome
    return str(legado if legado.exists() else RAIZ / 'dados' / nome)
