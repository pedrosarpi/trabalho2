"""Gera um .env privado. Nunca imprime a chave nem substitui um arquivo existente."""
import argparse
import os
from pathlib import Path
import re
import secrets


def configurar(caminho, projeto, porta):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{1,62}', projeto):
        raise ValueError('Projeto: use 2 a 63 letras minúsculas, números, hífens ou sublinhados.')
    if not 1024 <= porta <= 65535:
        raise ValueError('Use uma porta entre 1024 e 65535, disponível e autorizada no servidor.')
    texto = (f'COMPOSE_PROJECT_NAME={projeto}\nPORTA_WEB={porta}\nSECRET_KEY={secrets.token_hex(32)}\n'
             'PERMITIR_CADASTRO=true\nCOOKIE_SEGURO=false\nNVD_API_KEY=\n')
    fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as arquivo:
        arquivo.write(texto)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--projeto', required=True, help='Nome único no servidor, ex.: orthocrud-seu-identificador')
    parser.add_argument('--porta', type=int, default=2201)
    args = parser.parse_args()
    try:
        configurar(Path('.env'), args.projeto, args.porta)
    except (ValueError, OSError) as erro:
        parser.exit(1, f'Não foi possível configurar: {erro}\n')
    print('.env criado. Guarde-o fora do Git e execute docker compose up -d --build.')


if __name__ == '__main__':
    main()
