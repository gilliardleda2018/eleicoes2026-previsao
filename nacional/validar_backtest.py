"""Avalia previsões históricas congeladas; não inventa treinamento nem dados.

python validar_backtest.py previsoes_historicas.csv
Colunas: eleicao, data_corte, data_eleicao, prob_pt, pt_venceu,
voto_pt_previsto, voto_pt_real, p10, p90.
Uma previsão por eleição; todos os percentuais em [0,100], prob_pt em [0,1].
O CSV deve vir de reexecuções temporais, nunca de ajuste com o resultado conhecido.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from validacao_modelo import escrever_json


def avaliar(p):
    cols = ["prob_pt", "pt_venceu", "voto_pt_previsto", "voto_pt_real", "p10", "p90"]
    if len(p) < 3 or p.eleicao.duplicated().any():
        raise ValueError("Ao menos três eleições distintas, uma previsão por eleição")
    if not np.isfinite(p[cols].to_numpy(dtype=float)).all():
        raise ValueError("Valores não finitos")
    if not p.pt_venceu.isin([0, 1]).all() or not p.prob_pt.between(0, 1).all():
        raise ValueError("Probabilidades ou desfechos inválidos")
    for c in cols[2:]:
        if not p[c].between(0, 100).all():
            raise ValueError("Percentuais fora do domínio")
    if (p.p10 > p.p90).any():
        raise ValueError("Intervalos invertidos")
    if not (pd.to_datetime(p.data_corte) < pd.to_datetime(p.data_eleicao)).all():
        raise ValueError("Vazamento temporal: corte deve anteceder a eleição")
    prob = np.clip(p.prob_pt.to_numpy(), 1e-12, 1-1e-12)
    y = p.pt_venceu.to_numpy()
    return {"eleicoes": len(p), "brier": float(np.mean((prob-y)**2)),
            "log_loss": float(-np.mean(y*np.log(prob)+(1-y)*np.log(1-prob))),
            "mae_voto_pts": float(np.mean(np.abs(p.voto_pt_previsto-p.voto_pt_real))),
            "cobertura_faixa_80": float(((p.voto_pt_real >= p.p10) & (p.voto_pt_real <= p.p90)).mean()),
            "baseline_brier_50_50": .25,
            "limite": "Métricas não verificam sozinhas a proveniência ou independência dos dados; poucas eleições geram grande incerteza."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--saida", type=Path, default=Path("resultados/backtest.json"))
    args = parser.parse_args()
    resultado = avaliar(pd.read_csv(args.csv))
    escrever_json(args.saida, resultado)
    print(resultado)
