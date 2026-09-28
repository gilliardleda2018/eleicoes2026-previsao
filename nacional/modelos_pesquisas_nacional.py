"""Cenário nacional — ensemble de agregadores (os mesmos 6 do cenário estadual, via agregadores.py).

1º turno: % de votos válidos de Lula e de Flávio Bolsonaro.
2º turno: % de Lula nos votos válidos Lula × Flávio (as pesquisas de 2º turno também passam pelos 6 agregadores).
Âncora alternativa do efeito-instituto: institutos que menos erraram em 2022 (medido em erro_historico_presidente.csv).

Saídas: resultados/ensemble_nacional.json, resultados/pesquisas_nacionais_tratadas.csv
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ.parent))
sys.path.insert(0, str(RAIZ))
from agregadores import rodar_ensemble  # noqa: E402

RES = RAIZ / "resultados"
RES.mkdir(exist_ok=True)
ELEICAO = pd.Timestamp("2026-10-04")
rng = np.random.default_rng(42)
META = {"turno", "instituto", "inicio", "fim", "amostra", "margem", "registro_tse", "contratante", "metodo",
        "brancos_nulos", "indecisos", "fonte_url", "status", "observacao"}

p = pd.read_csv(RAIZ / "dados" / "pesquisas_presidente.csv")
p = p[p.status.fillna("") != "nao_confirmada"].copy()
cands = [c for c in p.columns if c not in META]
for c in cands:
    p[c] = pd.to_numeric(p[c].astype(str).str.replace("<", "").str.replace(",", "."), errors="coerce")
p["fim"] = pd.to_datetime(p.fim)
p["inicio"] = pd.to_datetime(p.inicio).fillna(p.fim - pd.Timedelta(days=3))
p["meio"] = p.inicio + (p.fim - p.inicio) / 2
p["dias_antes"] = (ELEICAO - p.meio).dt.days
p["n"] = pd.to_numeric(p.amostra, errors="coerce").fillna(2000)
p = p.sort_values("meio").reset_index(drop=True)

# âncora: 3 institutos com menor erro médio absoluto na margem em 2022 (histórico)
ANCORA = None
hist = RAIZ / "dados" / "erro_historico_presidente.csv"
if hist.exists():
    from historico import carregar as carregar_historico, sem_acento
    h = carregar_historico(hist)
    h = h[h.ano == 2022]
    h["erro"] = h.erro_margem.abs()
    melhores = h.groupby(h.instituto.map(sem_acento)).erro.mean().sort_values()
    nomes_2026 = {sem_acento(i): i for i in p.instituto.unique()}
    ANCORA = {nomes_2026[i] for i in melhores.index[:4] if i in nomes_2026} or None

res = {"n_pesquisas_1t": 0, "n_pesquisas_2t": 0, "modelos": {}, "efeito_instituto": {}, "ensemble": {},
       "ancora": sorted(ANCORA) if ANCORA else None}

# ------------------------------------------------------------------ 1º turno
p1 = p[p.turno == 1].copy()
outros_c = [c for c in cands if c not in ("lula", "flavio")]
p1[outros_c] = p1[outros_c].fillna(0)
soma = p1[cands].sum(axis=1)
for c in cands:
    p1[f"{c}_val"] = 100 * p1[c] / soma
res["n_pesquisas_1t"] = int(len(p1))
for cand in ("lula", "flavio"):
    mods, ef, alt, ens = rodar_ensemble(p1[f"{cand}_val"].values, p1, rng, ELEICAO, ancora=ANCORA)
    res["modelos"][f"{cand}_1t"] = mods
    if alt:
        res["modelos"][f"{cand}_1t"]["_ancora"] = {"est": round(float(alt[0]), 2), "dp": round(float(alt[1]), 2)}
    res["efeito_instituto"][f"{cand}_1t"] = ef
    res["ensemble"][f"{cand}_1t"] = ens
recentes = p1[p1.dias_antes <= 38]
res["outros_validos_recentes"] = {c: round(float(recentes[f"{c}_val"].mean()), 2) for c in outros_c
                                  if recentes[f"{c}_val"].mean() > 0.2}

# ------------------------------------------------------------------ 2º turno (Lula × Flávio)
p2 = p[(p.turno == 2) & p.lula.notna() & p.flavio.notna()].copy()
p2["lula_2p"] = 100 * p2.lula / (p2.lula + p2.flavio)
res["n_pesquisas_2t"] = int(len(p2))
if len(p2) >= 4:
    mods, ef, alt, ens = rodar_ensemble(p2.lula_2p.values, p2, rng, ELEICAO, ancora=ANCORA)
    res["modelos"]["lula_2t"] = mods
    if alt:
        res["modelos"]["lula_2t"]["_ancora"] = {"est": round(float(alt[0]), 2), "dp": round(float(alt[1]), 2)}
    res["efeito_instituto"]["lula_2t"] = ef
    res["ensemble"]["lula_2t"] = ens
res["institutos"] = sorted(p.instituto.unique())
res["n_conferidas"] = int(p.status.isin(["confirmada", "divergente"]).sum())

pd.concat([p1.assign(turno=1), p2.assign(turno=2)]).to_csv(RES / "pesquisas_nacionais_tratadas.csv", index=False,
                                                           encoding="utf-8")
json.dump(res, open(RES / "ensemble_nacional.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps({k: res[k] for k in ("n_pesquisas_1t", "n_pesquisas_2t", "ancora", "ensemble",
                                      "outros_validos_recentes")}, ensure_ascii=False, indent=1))
