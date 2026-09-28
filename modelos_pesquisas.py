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
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel

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


# ------------------------------------------------------------------ modelos
def m_media_ponderada(y, df):
    w = np.sqrt(df.n) * np.exp(-df.dias_antes / 14)
    est = np.average(y, weights=w)
    dp = np.sqrt(np.average((y - est) ** 2, weights=w) / max(1, (w.sum() ** 2 / (w ** 2).sum()) - 1) + 1.0)
    return est, dp


def m_mediana_robusta(y, df):
    rec = df.assign(y=y)
    rec = rec[rec.dias_antes <= 38].sort_values("meio").groupby("instituto").tail(1)
    est = float(np.median(rec.y))
    boots = [np.median(rng.choice(rec.y.values, len(rec))) for _ in range(2000)]
    return est, float(np.std(boots)) + 0.5


def efeito_instituto(y, df, ancora=None, lam=0.02):
    """y = a + b·(dias_antes) + h_casa; efeitos com soma zero (ou zero no grupo-âncora). Ridge nos efeitos."""
    casas = sorted(df.instituto.unique())
    X = np.zeros((len(df), 2 + len(casas)))
    X[:, 0] = 1
    X[:, 1] = -df.dias_antes / 30  # inclinação por mês
    for j, c in enumerate(casas):
        X[df.instituto.values == c, 2 + j] = 1
    w = 1 / np.array([var_amostral(v, n) + 4.0 for v, n in zip(y, df.n)])  # +4 = erro não amostral
    W = np.diag(w)
    P = np.zeros((X.shape[1], X.shape[1]))
    P[2:, 2:] = lam * np.eye(len(casas))
    # restrição: soma dos efeitos (ou dos efeitos-âncora) = 0, imposta por penalidade forte
    r = np.zeros(X.shape[1])
    grupo = [j for j, c in enumerate(casas) if (ancora is None or c in ancora)]
    r[[2 + j for j in grupo]] = 1
    A = X.T @ W @ X + P + 1e6 * np.outer(r, r)
    beta = np.linalg.solve(A, X.T @ W @ y)
    cov = np.linalg.inv(A)
    efeitos = dict(zip(casas, beta[2:]))
    return beta, cov, efeitos


def m_regressao_instituto(y, df, ancora=None):
    beta, cov, efeitos = efeito_instituto(y, df, ancora)
    est = beta[0]  # dias_antes = 0 → dia da eleição
    return est, float(np.sqrt(cov[0, 0]) + 1.0), efeitos


def m_kalman(y_corr, df, q=0.08, r_extra=4.0):
    """Nível local: x_t = x_{t-1} + N(0, q·Δdias); pesquisas = x_t + ruído amostral."""
    x, P = y_corr[0], 25.0
    t_ant = df.meio.iloc[0]
    for yi, (_, lin) in zip(y_corr, df.iterrows()):
        dt = max((lin.meio - t_ant).days, 0)
        P += q * dt
        R = var_amostral(yi, lin.n) + r_extra
        K = P / (P + R)
        x, P = x + K * (yi - x), (1 - K) * P
        t_ant = lin.meio
    P += q * (ELEICAO - t_ant).days
    return float(x), float(np.sqrt(P))


def m_processo_gaussiano(y_corr, df):
    t = -df.dias_antes.values.reshape(-1, 1) / 30.0
    k = ConstantKernel(10.0, (0.01, 400)) * RBF(1.5, (0.5, 10)) + WhiteKernel(5.0, (0.01, 100))
    gp = GaussianProcessRegressor(kernel=k, normalize_y=True, random_state=SEMENTE, n_restarts_optimizer=5)
    gp.fit(t, y_corr)
    mu, sd = gp.predict(np.array([[0.0]]), return_std=True)
    return float(mu[0]), float(sd[0])


def m_bayes_gibbs(y, df, iters=6000, burn=1500):
    """y_i = a + b·t_i + h_casa + e_i;  h ~ N(0, τ²);  e_i ~ N(0, s_i² + σ0²). Priors fracos. Gibbs."""
    casas = sorted(df.instituto.unique())
    idx = np.array([casas.index(c) for c in df.instituto])
    t = -df.dias_antes.values / 30
    s2 = np.array([var_amostral(v, n) for v, n in zip(y, df.n)])
    a, b, h, tau2, sig0 = y.mean(), 0.0, np.zeros(len(casas)), 9.0, 4.0
    guard = []
    for it in range(iters):
        v = s2 + sig0
        # a, b | resto (regressão ponderada, prior N(0, 1e4))
        X = np.column_stack([np.ones_like(t), t])
        r = y - h[idx]
        Prec = X.T @ (X / v[:, None]) + np.eye(2) / 1e4
        mean = np.linalg.solve(Prec, X.T @ (r / v))
        a, b = rng.multivariate_normal(mean, np.linalg.inv(Prec))
        # h_c | resto
        res = y - a - b * t
        for c in range(len(casas)):
            m = idx == c
            prec = (1 / v[m]).sum() + 1 / tau2
            h[c] = rng.normal((res[m] / v[m]).sum() / prec, np.sqrt(1 / prec))
        # τ² | h  (Inv-Gamma(2, 8))
        tau2 = 1 / rng.gamma(2 + len(casas) / 2, 1 / (8 + (h ** 2).sum() / 2))
        # σ0 | resto  (Metropolis em log)
        e = y - a - b * t - h[idx]
        prop = sig0 * np.exp(rng.normal(0, 0.3))
        ll = lambda s: -0.5 * np.sum(np.log(s2 + s) + e ** 2 / (s2 + s)) - s / 20
        if np.log(rng.random()) < ll(prop) - ll(sig0) + np.log(prop / sig0):
            sig0 = prop
        if it >= burn:
            guard.append(a)  # dia da eleição (t = 0), instituto médio (h = 0)
    guard = np.array(guard)
    return float(guard.mean()), float(guard.std())


# ------------------------------------------------------------------ execução
resultado = {"fonte": "pesquisas_verificadas.csv + compilação", "n_pesquisas": int(len(p)),
             "n_conferidas": int((p.origem == "conferida").sum()), "institutos": sorted(p.instituto.unique()),
             "modelos": {}, "efeito_instituto": {}}
for cand in ("braide", "orleans"):
    y = p[f"{cand}_val"].values
    mods = {}
    mods["Média ponderada"] = m_media_ponderada(y, p)
    mods["Mediana robusta (últimos 30 dias)"] = m_mediana_robusta(y, p)
    est, dp, ef = m_regressao_instituto(y, p)
    mods["Regressão com efeito-instituto"] = (est, dp)
    est_n, dp_n, ef_n = m_regressao_instituto(y, p, ancora=NACIONAIS)
    resultado["efeito_instituto"][cand] = {k: round(float(v), 2) for k, v in ef.items()}
    y_corr = y - np.array([ef[c] for c in p.instituto])
    mods["Filtro de Kalman"] = m_kalman(y_corr, p)
    mods["Processo Gaussiano"] = m_processo_gaussiano(y_corr, p)
    mods["Bayesiano hierárquico (Gibbs)"] = m_bayes_gibbs(y, p)
    resultado["modelos"][cand] = {k: {"est": round(float(v[0]), 2), "dp": round(float(v[1]), 2)}
                                  for k, v in mods.items()}
    resultado["modelos"][cand]["_ancora_nacionais"] = {"est": round(float(est_n), 2), "dp": round(float(dp_n), 2)}

# ensemble (peso igual por modelo) + incerteza = dentro dos modelos + entre modelos
ens = {}
for cand in ("braide", "orleans"):
    m = {k: v for k, v in resultado["modelos"][cand].items() if not k.startswith("_")}
    ests = np.array([v["est"] for v in m.values()]); dps = np.array([v["dp"] for v in m.values()])
    ens[cand] = {"est": round(float(ests.mean()), 2),
                 "dp": round(float(np.sqrt((dps ** 2).mean() + ests.var(ddof=1))), 2),
                 "min_modelos": round(float(ests.min()), 2), "max_modelos": round(float(ests.max()), 2)}
resultado["ensemble"] = ens
resultado["outros_validos_recentes"] = {
    c: round(float(p.loc[p.dias_antes <= 38, f"{c}_val"].mean()), 2) for c in ("camarao", "rocha", "outros")}

p.to_csv(SAIDA / "pesquisas_tratadas.csv", index=False, encoding="utf-8")
json.dump(resultado, open(SAIDA / "ensemble_pesquisas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps({k: resultado[k] for k in ("n_pesquisas", "modelos", "ensemble", "efeito_instituto",
                                            "outros_validos_recentes")}, ensure_ascii=False, indent=1))
