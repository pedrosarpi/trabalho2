"""Smoke test HTTP do CI. Use apenas numa base de teste: cria conta e ativo."""
import argparse
from http.cookiejar import CookieJar
import json
from pathlib import Path
import re
import secrets
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url', required=True)
    grupo = p.add_mutually_exclusive_group(required=True)
    grupo.add_argument('--criar', action='store_true')
    grupo.add_argument('--verificar', action='store_true')
    p.add_argument('--estado', default='.smoke-estado.json')
    args = p.parse_args()
    url = args.url.rstrip('/')
    abrir = build_opener(HTTPCookieProcessor(CookieJar()))

    def get(rota):
        with abrir.open(url + rota, timeout=15) as resposta:
            return resposta.read().decode()

    def enviar(rota, dados, pagina):
        csrf = re.search(r'name="csrf" value="([^"]+)"', pagina).group(1)
        with abrir.open(url + rota, urlencode(dict(csrf=csrf, **dados)).encode(), timeout=15) as resposta:
            return resposta.read().decode()

    estado = Path(args.estado)
    if args.criar:
        if estado.exists():
            raise RuntimeError('Estado de teste já existe; use --verificar ou outra base.')
        cred = dict(login='smoke-' + secrets.token_hex(5), senha=secrets.token_urlsafe(20))
        enviar('/cadastro', dict(**cred, confirmacao=cred['senha']), get('/cadastro'))
        estado.write_text(json.dumps(cred), encoding='utf-8')
        estado.chmod(0o600)
    else:
        cred = json.loads(estado.read_text())
    enviar('/login', cred, get('/login'))
    if args.criar:
        form = get('/ativos/novo')
        revisao = re.search(r'name="revisao" value="([^"]+)"', form).group(1)
        enviar('/ativos/novo', dict(revisao=revisao, id_ativo=999998, nome='Persistencia-CI',
               responsavel='Teste CI', setor_localizacao='Ambiente descartável', tipo='SISTEMA', status='ATIVO'), form)
    dados = json.loads(get('/exportar'))
    assert any(a['id_ativo'] == 999998 and a['nome'] == 'Persistencia-CI' for a in dados)
    assert json.loads(get('/healthz'))['status'] == 'ok'
    print('OK: autenticação, JSON, ativo persistido e saúde HTTP.')


if __name__ == '__main__':
    main()
