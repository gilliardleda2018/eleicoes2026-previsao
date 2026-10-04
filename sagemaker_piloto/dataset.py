"""Extrai mudanças factuais para rotulagem; não inventa relevância editorial."""
import argparse
import hashlib
import json
import math
import sqlite3
from pathlib import Path

FEATURES = ('volume', 'virada', 'revisao', 'percentual', 'delta_percentual')


def _numero(valor):
    if type(valor) not in (int, float) or not math.isfinite(valor):
        raise ValueError('Número não finito ou inválido')
    return valor


def extrair(chave, historico):
    if not chave.endswith('_False'):
        raise ValueError('Somente chave de acompanhamento oficial')
    linhas = []
    anterior = None
    for atual in sorted(historico, key=lambda x: x['consultado']):
        instante = _numero(atual['consultado'])
        if anterior and instante <= anterior['consultado']:
            continue
        if anterior:
            grupo = hashlib.sha256(f'{chave}:{instante}'.encode()).hexdigest()[:24]
            for nome, unidade in atual.get('unidades', {}).items():
                antes = anterior.get('unidades', {}).get(nome)
                if antes is None:
                    continue
                va, vb = antes['votos'], unidade['votos']
                deltas = [_numero(v)-_numero(va[k]) for k, v in vb.items() if k in va]
                pa, pb = _numero(antes['percentual']), _numero(unidade['percentual'])
                if not (0 <= pa <= 100 and 0 <= pb <= 100):
                    raise ValueError('Percentual inválido')
                volume = sum(abs(x) for x in deltas)
                if volume == 0 and pa == pb:
                    continue
                def lider(votos):
                    valores = {k: _numero(v) for k, v in votos.items()}
                    maior = max(valores.values(), default=0)
                    nomes = [k for k, v in valores.items() if v == maior]
                    return nomes[0] if maior > 0 and len(nomes) == 1 else None
                la, lb = lider(va), lider(vb)
                linhas.append({'grupo': grupo, 'instante': instante, 'disputa': chave,
                               'unidade': str(nome), 'volume': volume,
                               'virada': int(bool(la and lb and la != lb)),
                               'revisao': int(any(x < 0 for x in deltas)),
                               'percentual': pb, 'delta_percentual': pb-pa,
                               'relevancia': None, 'rotulador': None,
                               'origem': 'historico_oficial_painel'})
        anterior = atual
    return linhas


def ler_sqlite(arquivo):
    # Mode=ro evita criar uma base vazia ou escrever na base de produção.
    uri = Path(arquivo).resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(uri, uri=True) as db:
        dados = {}
        for chave, texto in db.execute('SELECT chave,dados FROM snapshots ORDER BY chave,instante'):
            if chave.endswith('_False'):
                dados.setdefault(chave, []).append(json.loads(texto))
    return [linha for chave, historico in dados.items() for linha in extrair(chave, historico)]


def dividir_rotulados(linhas, minimo_grupos=30):
    """Um grupo inteiro fica num único conjunto; corte global por tempo."""
    if not linhas:
        raise ValueError('Sem exemplos reais: treino não iniciado')
    instantes = {}
    for linha in linhas:
        if linha.get('origem') != 'historico_oficial_painel':
            raise ValueError('Origem não admitida para este treino')
        if type(linha.get('relevancia')) is not int or linha['relevancia'] not in range(4):
            raise ValueError('Rotule relevância de 0 a 3 antes do treino')
        if not isinstance(linha.get('rotulador'), str) or not linha['rotulador'].strip():
            raise ValueError('Falta responsável pela rotulagem')
        for feature in FEATURES:
            _numero(linha[feature])
        tempo = _numero(linha['instante'])
        if linha['grupo'] in instantes and instantes[linha['grupo']] != tempo:
            raise ValueError('Grupo com tempos inconsistentes')
        instantes[linha['grupo']] = tempo
    tempos = sorted(set(instantes.values()))
    if len(instantes) < minimo_grupos or len(tempos) < 5:
        raise ValueError('Grupos ou datas insuficientes para validação temporal')
    corte = tempos[max(1, int(len(tempos)*0.8))]
    treino = [x for x in linhas if x['instante'] < corte]
    teste = [x for x in linhas if x['instante'] >= corte]
    return treino, teste


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('banco')
    parser.add_argument('saida')
    args = parser.parse_args()
    linhas = ler_sqlite(args.banco)
    if not linhas:
        raise SystemExit('Nenhuma mudança oficial encontrada; arquivo de treino não criado')
    with open(args.saida, 'x', encoding='utf-8') as arquivo:
        for linha in linhas:
            arquivo.write(json.dumps(linha, ensure_ascii=False, allow_nan=False)+'\n')
