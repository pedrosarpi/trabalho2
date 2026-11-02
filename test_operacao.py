import json
from pathlib import Path
from unittest.mock import patch

import pytest

from dados import ArmazenamentoJSON, ErroArmazenamento
from scripts.configurar import configurar
from scripts.monitorar_24h import monitorar
from test_sistema import novo_equipamento


def test_falha_escrita_atomica_preserva_json(tmp_path):
    caminho = tmp_path / 'dados.json'
    arm = ArmazenamentoJSON(str(caminho))
    arm.salvar([novo_equipamento()])
    anterior = caminho.read_bytes()
    with patch('persistencia.os.replace', side_effect=OSError('disco indisponível')):
        with pytest.raises(ErroArmazenamento):
            arm.salvar([])
    assert caminho.read_bytes() == anterior
    assert not list(tmp_path.glob('*.tmp'))


def test_env_nao_sobrescreve_segredo(tmp_path):
    caminho = tmp_path / '.env'
    configurar(caminho, 'inventario-teste', 18080)
    texto = caminho.read_text()
    assert 'COMPOSE_PROJECT_NAME=inventario-teste' in texto
    assert len(next(linha.split('=', 1)[1] for linha in texto.splitlines() if linha.startswith('SECRET_KEY='))) == 64
    with pytest.raises(FileExistsError):
        configurar(caminho, 'inventario-outro', 18081)
    assert caminho.read_text() == texto


@pytest.mark.parametrize('projeto,porta', [('UPPER', 18080), ('a', 18080), ('nome;comando', 18080),
                                         ('inventario-teste', 80), ('inventario-teste', 70000)])
def test_env_invalido(tmp_path, projeto, porta):
    with pytest.raises(ValueError):
        configurar(tmp_path / '.env', projeto, porta)


def simular_monitor(tmp_path, *, falha=False, reinicio=False, duracao=86400):
    tempo = [0]
    def esperar(segundos):
        tempo[0] += segundos
    def coletor(url, container):
        if falha and tempo[0] == 43200:
            raise OSError('indisponível')
        return {'instancia': 'nova' if reinicio and tempo[0] > 0 else 'original', 'uptime_seconds': tempo[0] + 5,
                'docker': dict(id='id-do-container', inicio='inicio', reinicios=0, estado='running', saude='healthy')}
    return monitorar('http://teste/healthz', duracao, 43200, tmp_path / 'monitor.jsonl', 'id-do-container',
                     relogio=lambda: tempo[0], esperar=esperar, coletor=coletor)


def test_monitor_janela_completa_simulada(tmp_path):
    resultado = simular_monitor(tmp_path)
    assert resultado['evidencia_24h'] and resultado['amostras'] == 3
    assert len((tmp_path / 'monitor.jsonl').read_text().splitlines()) == 3
    assert json.loads((tmp_path / 'monitor.resumo.json').read_text()) == resultado


def test_monitor_falha_nao_aprova(tmp_path):
    r = simular_monitor(tmp_path, falha=True)
    assert not r['evidencia_24h'] and r['falhas'] == 1


def test_monitor_reinicio_nao_aprova(tmp_path):
    r = simular_monitor(tmp_path, reinicio=True)
    assert not r['evidencia_24h'] and r['reinicios_detectados'] == 1


def test_monitor_menos_de_24h_nao_aprova(tmp_path):
    assert not simular_monitor(tmp_path, duracao=30)['evidencia_24h']
