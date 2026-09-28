"""Ensemble de agregadores de pesquisas — Governo MA 2026 (1º turno, votos válidos).

Seis modelos independentes estimam o % de votos válidos de Braide e de Orleans em 04/10/2026:
  1. Média ponderada (amostra × recência)
  2. Mediana robusta (última pesquisa de cada instituto nos últimos 30 dias)
  3. Regressão com efeito-instituto (ridge; tendência linear + viés de cada casa)
  4. Filtro de Kalman (nível local) sobre as pesquisas corrigidas pelo efeito-instituto
  5. Processo Gaussiano (sklearn) sobre as pesquisas corrigidas
  6. Bayesiano hierárquico (Gibbs): tendência + efeito-instituto aleatório + ruído extra

Efeito-instituto: por padrão a "verdade" é a média dos institutos (efeitos somam zero).
Rodamos também a âncora alternativa "institutos nacionais" (Quaest, AtlasIntel, Paraná, Real Time Big Data),
porque a divergência entre casas é a maior fonte de incerteza desta eleição.

Saída: resultados/ensemble_pesquisas.json, resultados/pesquisas_tratadas.csv
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "resultados"
SAIDA.mkdir(exist_ok=True)
ELEICAO = pd.Timestamp("2026-10-04")
SEMENTE = 42
rng = np.random.default_rng(SEMENTE)
NACIONAIS = {"Quaest", "AtlasIntel", "Paraná Pesquisas", "Real Time Big Data"}
CAND = ["braide", "orleans", "camarao", "rocha", "outros"]

# ------------------------------------------------------------------ dados
# conferidas pelo levantamento (prioridade) + compilação pública para o que não foi conferido (tendência)
ver = pd.read_csv(RAIZ / "dados" / "pesquisas_verificadas.csv")
ver = ver[ver.status != "nao_confirmada"].assign(origem="conferida")
wik = pd.read_csv(RAIZ / "dados" / "pesquisas_governo_ma_2026.csv").assign(origem="compilação (não conferida)")
chave = lambda d: d.turno.astype(str) + "|" + d.instituto + "|" + d.fim.astype(str)
p = pd.concat([ver, wik[~chave(wik).isin(chave(ver))]], ignore_index=True)
fonte = RAIZ / "dados" / "pesquisas_verificadas.csv"
p = p[p.turno == 1].copy()
for c in CAND:
    p[c] = pd.to_numeric(p[c].astype(str).str.replace("<", "").str.replace(",", "."), errors="coerce")
    if c != "braide" and c != "orleans":
        p.loc[p[c].astype(str).str.contains("<1", na=False), c] = 0.5
p["fim"] = pd.to_datetime(p.fim)
p["inicio"] = pd.to_datetime(p.inicio)
p["meio"] = p.inicio + (p.fim - p.inicio) / 2
p["dias_antes"] = (ELEICAO - p.meio).dt.days
# pesquisas sem Camarão/Rocha divulgados (ex.: Doxa): usa a média dos demais candidatos nas outras pesquisas
completas = p.camarao.notna() & p.rocha.notna()
p["outros"] = p.outros.fillna(0)
media_menores = p.loc[completas, ["camarao", "rocha", "outros"]].div(p.loc[completas, CAND].sum(axis=1), axis=0).mean()
for c in ("camarao", "rocha"):
    p[c] = p[c].astype(float)
incomp = ~completas
bo = p.loc[incomp, "braide"] + p.loc[incomp, "orleans"]
fator = bo / (1 - media_menores.sum())
for c in ("camarao", "rocha", "outros"):
    p.loc[incomp, c] = fator * media_menores[c]
p["candidatos_estimados"] = incomp
soma = p[CAND].sum(axis=1)
for c in CAND:
    p[f"{c}_val"] = 100 * p[c] / soma  # indecisos/brancos distribuídos proporcionalmente
p["n"] = pd.to_numeric(p.amostra, errors="coerce").fillna(1000)
p = p.sort_values("meio").reset_index(drop=True)


def var_amostral(share, n, deff=1.6):
    s = share / 100
    return deff * s * (1 - s) / n * 1e4  # em pontos percentuais²


# ------------------------------------------------------------------ modelos (biblioteca comum aos dois cenários)
import sys
sys.path.insert(0, str(RAIZ))
from agregadores import rodar_ensemble  # noqa: E402

# ------------------------------------------------------------------ execução
resultado = {"fonte": "pesquisas_verificadas.csv + compilação", "n_pesquisas": int(len(p)),
             "n_conferidas": int((p.origem == "conferida").sum()), "institutos": sorted(p.instituto.unique()),
             "modelos": {}, "efeito_instituto": {}}
for cand in ("braide", "orleans"):
    mods, ef, alt, ens_c = rodar_ensemble(p[f"{cand}_val"].values, p, rng, ELEICAO, ancora=NACIONAIS)
    resultado["modelos"][cand] = mods
    resultado["modelos"][cand]["_ancora_nacionais"] = {"est": round(float(alt[0]), 2), "dp": round(float(alt[1]), 2)}
    resultado["efeito_instituto"][cand] = ef
    resultado.setdefault("ensemble", {})[cand] = ens_c
resultado["outros_validos_recentes"] = {
    c: round(float(p.loc[p.dias_antes <= 38, f"{c}_val"].mean()), 2) for c in ("camarao", "rocha", "outros")}

p.to_csv(SAIDA / "pesquisas_tratadas.csv", index=False, encoding="utf-8")
json.dump(resultado, open(SAIDA / "ensemble_pesquisas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps({k: resultado[k] for k in ("n_pesquisas", "modelos", "ensemble", "efeito_instituto",
                                            "outros_validos_recentes")}, ensure_ascii=False, indent=1))
