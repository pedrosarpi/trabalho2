"""Evidência amostral de disponibilidade; roda NO SERVIDOR sem dependências extras.

Não prova ausência de interrupções entre amostras. Registra também identidade,
uptime do processo e, opcionalmente, ID/início/reinícios/saúde do container Docker.
"""
import argparse
from datetime import datetime, timezone
from http.client import HTTPException
import json
import math
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen


def coletar(url, container=None):
    with urlopen(url, timeout=10) as resposta:
        dados = json.loads(resposta.read(100_000))
    if (not isinstance(dados, dict) or dados.get('status') != 'ok'
            or not isinstance(dados.get('instancia'), str) or not dados['instancia']):
        raise ValueError('Resposta de saúde inválida.')
    uptime = dados.get('uptime_seconds')
    if type(uptime) not in (int, float) or not math.isfinite(uptime) or uptime < 0:
        raise ValueError('Uptime inválido.')
    resultado = dict(instancia=dados['instancia'], uptime_seconds=uptime)
    if container:
        comando = subprocess.run(['docker', 'inspect', container], check=True, capture_output=True,
                                 text=True, timeout=10)
        info = json.loads(comando.stdout)[0]
        estado = info['State']
        resultado['docker'] = dict(id=info['Id'], inicio=estado['StartedAt'],
                                   reinicios=info['RestartCount'], estado=estado['Status'],
                                   saude=estado.get('Health', {}).get('Status', 'ausente'))
        if estado['Status'] != 'running' or resultado['docker']['saude'] != 'healthy':
            raise ValueError('Container parado ou sem estado healthy.')
    return resultado


def mudou(anterior, atual):
    if anterior is None:
        return False
    if anterior['instancia'] != atual['instancia'] or atual['uptime_seconds'] < anterior['uptime_seconds']:
        return True
    a, b = anterior.get('docker'), atual.get('docker')
    return bool(a and b and any(a[chave] != b[chave] for chave in ('id', 'inicio', 'reinicios')))


def monitorar(url, duracao, intervalo, saida, container=None, *, relogio=time.monotonic,
              esperar=time.sleep, coletor=coletar):
    if duracao <= 0 or intervalo <= 0 or not math.isfinite(duracao + intervalo):
        raise ValueError('Duração e intervalo devem ser positivos e finitos.')
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    resumo_path = saida.with_suffix('.resumo.json')
    if resumo_path.exists():
        raise FileExistsError('Já existe um resumo com este nome. Use uma nova saída.')
    inicio = relogio()
    anterior = None
    falhas = mudancas = amostras = 0
    with saida.open('x', encoding='utf-8', buffering=1) as arquivo:
        while True:
            decorrido = relogio() - inicio
            registro = dict(horario_utc=datetime.now(timezone.utc).isoformat(), decorrido_segundos=decorrido)
            try:
                dados = coletor(url, container)
                alterado = mudou(anterior, dados)
                mudancas += int(alterado)
                registro.update(ok=True, reinicio_detectado=alterado, **dados)
                anterior = dados
            except (OSError, HTTPException, ValueError, KeyError, IndexError, TypeError,
                    subprocess.SubprocessError) as erro:
                falhas += 1
                registro.update(ok=False, erro=str(erro))
            amostras += 1
            arquivo.write(json.dumps(registro, ensure_ascii=False) + '\n')
            print(f"Amostra {amostras}: {'OK' if registro['ok'] else 'FALHA'} ({decorrido/3600:.3f} h)", flush=True)
            if decorrido >= duracao:
                break
            esperar(min(intervalo, max(0.001, duracao - (relogio() - inicio))))
    resumo = dict(duracao_segundos=decorrido, amostras=amostras, falhas=falhas,
                  reinicios_detectados=mudancas, container_verificado=bool(container),
                  periodo_sem_falhas_amostradas=(falhas == 0 and mudancas == 0),
                  evidencia_24h=(decorrido >= 86400 and falhas == 0 and mudancas == 0 and bool(container)),
                  observacao='Evidência por amostragem; confira também os logs e os registros do servidor.')
    resumo_path.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding='utf-8')
    return resumo


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url', default='http://127.0.0.1:2201/healthz')
    p.add_argument('--horas', type=float, default=24)
    p.add_argument('--intervalo', type=float, default=60)
    p.add_argument('--saida', default='evidencias/monitoramento-24h.jsonl')
    p.add_argument('--container', help='ID obtido com docker compose ps -q inventario')
    args = p.parse_args()
    try:
        r = monitorar(args.url, args.horas * 3600, args.intervalo, args.saida, args.container)
    except (OSError, ValueError) as erro:
        p.exit(1, f'Monitoramento não iniciado/concluído: {erro}\n')
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r['periodo_sem_falhas_amostradas'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
