"""Snapshots oficiais compartilhados; SQLite local ou caminho de volume configurado."""
import json
import os
from pathlib import Path
import sqlite3


def caminho():
    return Path(os.environ.get('APURACAO_HISTORICO_DB', '/tmp/eleicoes2026_historico.sqlite3'))


def gravar_ler(chave, snapshot=None, arquivo=None):
    arquivo = Path(arquivo) if arquivo else caminho()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(arquivo), timeout=5) as db:
        db.execute('CREATE TABLE IF NOT EXISTS snapshots (chave TEXT, instante REAL, dados TEXT, PRIMARY KEY(chave, instante))')
        if snapshot is not None:
            db.execute('INSERT OR IGNORE INTO snapshots VALUES (?,?,?)',
                       (chave, snapshot['consultado'], json.dumps(snapshot, allow_nan=False)))
            db.execute('DELETE FROM snapshots WHERE chave=? AND instante NOT IN (SELECT instante FROM snapshots WHERE chave=? ORDER BY instante DESC LIMIT 960)', (chave, chave))
        return [json.loads(r[0]) for r in db.execute('SELECT dados FROM snapshots WHERE chave=? ORDER BY instante', (chave,))]


def selos(geral, ensaio=False):
    """Não infere eleição a partir de votos, projeções ou percentual apurado."""
    if ensaio:
        return [('Ensaio · resultado simulado', '')]
    out = []
    if geral.get('totalizado') is True:
        out.append(('Totalizado · informado pelo TSE', ''))
    for numero, situacao in geral.get('situacao', {}).items():
        texto = str(situacao).strip()
        normal = texto.casefold()
        nome = str(geral.get('nomes', {}).get(numero, f'Candidato {numero}'))
        if normal.startswith('eleito') or '2º turno' in normal or '2° turno' in normal or 'segundo turno' in normal or normal == '2 turno':
            out.append((nome, texto + ' · TSE'))
    return out
