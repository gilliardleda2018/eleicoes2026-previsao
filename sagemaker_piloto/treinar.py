"""Treino local opcional: só publica artefato se superar regras em teste temporal."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import ndcg_score
import joblib
from .dataset import FEATURES, dividir_rotulados


def validar(linhas):
    treino, teste = dividir_rotulados(linhas)
    if len({x['relevancia'] for x in treino}) < 2:
        raise ValueError('Treino sem variação de relevância')
    def matriz(itens):
        return [[x[f] for f in FEATURES] for x in itens]
    modelo = GradientBoostingRegressor(n_estimators=50, max_depth=2,
                                      random_state=2026, loss='huber')
    modelo.fit(matriz(treino), [x['relevancia'] for x in treino])
    grupos = defaultdict(list)
    for linha, score in zip(teste, modelo.predict(matriz(teste))):
        grupos[linha['grupo']].append((linha, float(score)))
    metricas = []
    for itens in grupos.values():
        if len(itens) < 2 or sum(x['relevancia'] for x, _ in itens) == 0:
            continue
        y = [[x['relevancia'] for x, _ in itens]]
        scores = [[s for _, s in itens]]
        ordem = sorted(range(len(itens)), key=lambda i:
                       (-itens[i][0]['virada'], -itens[i][0]['volume'], itens[i][0]['unidade']))
        baseline = [0]*len(itens)
        for pos, idx in enumerate(ordem):
            baseline[idx] = len(itens)-pos
        metricas.append((ndcg_score(y, scores, k=5), ndcg_score(y, [baseline], k=5)))
    if len(metricas) < 5:
        raise ValueError('Teste com menos de cinco grupos comparáveis')
    aprendido, regras = np.mean(metricas, axis=0)
    relatorio = {'grupos_teste': len(metricas), 'ndcg5_modelo': float(aprendido),
                 'ndcg5_regras': float(regras), 'aprovado': bool(aprendido > regras+0.02),
                 'criterio': 'melhoria mínima 0,02 no teste temporal; exige revisão humana'}
    return modelo, relatorio


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset')
    parser.add_argument('saida')
    args = parser.parse_args()
    with open(args.dataset, encoding='utf-8') as arquivo:
        linhas = [json.loads(x) for x in arquivo if x.strip()]
    modelo, relatorio = validar(linhas)
    print(json.dumps(relatorio, ensure_ascii=False, allow_nan=False))
    if not relatorio['aprovado']:
        raise SystemExit('Regras mantidas; artefato não publicado')
    destino = Path(args.saida)
    if destino.exists():
        raise SystemExit('Destino já existe; não sobrescrever modelo')
    destino.mkdir(parents=True)
    joblib.dump({'modelo': modelo, 'features': FEATURES}, destino/'model.joblib')
    (destino/'validacao.json').write_text(json.dumps(relatorio, indent=2), encoding='utf-8')
