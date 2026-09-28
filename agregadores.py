"""Biblioteca comum dos 6 agregadores de pesquisas — usada pelo cenário estadual (MA) e pelo nacional.

Todos recebem `y` (série de % de votos válidos de um candidato, uma por pesquisa) e `df` (colunas: instituto,
meio (data), dias_antes, n) e devolvem (estimativa para o dia da eleição, desvio-padrão).
"""
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel

NOMES = ["Média ponderada", "Mediana robusta (últimos 30 dias)", "Regressão com efeito-instituto",
         "Filtro de Kalman", "Processo Gaussiano", "Bayesiano hierárquico (Gibbs)"]


def var_amostral(share, n, deff=1.6):
    s = share / 100
    return deff * s * (1 - s) / n * 1e4  # pontos percentuais²


def m_media_ponderada(y, df):
    w = np.sqrt(df.n) * np.exp(-df.dias_antes / 14)
    est = np.average(y, weights=w)
    dp = np.sqrt(np.average((y - est) ** 2, weights=w) / max(1, (w.sum() ** 2 / (w ** 2).sum()) - 1) + 1.0)
    return est, dp


def m_mediana_robusta(y, df, rng, janela=38):
    rec = df.assign(y=y)
    rec = rec[rec.dias_antes <= janela].sort_values("meio").groupby("instituto").tail(1)
    est = float(np.median(rec.y))
    boots = [np.median(rng.choice(rec.y.values, len(rec))) for _ in range(2000)]
    return est, float(np.std(boots)) + 0.5


def efeito_instituto(y, df, ancora=None, lam=0.02):
    """y = a + b·(dias_antes/30) + h_casa; efeitos somam zero (ou zero no grupo-âncora); ridge leve nos efeitos."""
    casas = sorted(df.instituto.unique())
    X = np.zeros((len(df), 2 + len(casas)))
    X[:, 0] = 1
    X[:, 1] = -df.dias_antes / 30
    for j, c in enumerate(casas):
        X[df.instituto.values == c, 2 + j] = 1
    w = 1 / np.array([var_amostral(v, n) + 4.0 for v, n in zip(y, df.n)])
    W = np.diag(w)
    P = np.zeros((X.shape[1], X.shape[1]))
    P[2:, 2:] = lam * np.eye(len(casas))
    r = np.zeros(X.shape[1])
    grupo = [j for j, c in enumerate(casas) if (ancora is None or c in ancora)]
    r[[2 + j for j in grupo]] = 1
    A = X.T @ W @ X + P + 1e6 * np.outer(r, r)
    beta = np.linalg.solve(A, X.T @ W @ y)
    return beta, np.linalg.inv(A), dict(zip(casas, beta[2:]))


def m_regressao_instituto(y, df, ancora=None):
    beta, cov, efeitos = efeito_instituto(y, df, ancora)
    return beta[0], float(np.sqrt(cov[0, 0]) + 1.0), efeitos


def m_kalman(y_corr, df, eleicao, q=0.08, r_extra=4.0):
    x, P = y_corr[0], 25.0
    t_ant = df.meio.iloc[0]
    for yi, (_, lin) in zip(y_corr, df.iterrows()):
        P += q * max((lin.meio - t_ant).days, 0)
        R = var_amostral(yi, lin.n) + r_extra
        K = P / (P + R)
        x, P = x + K * (yi - x), (1 - K) * P
        t_ant = lin.meio
    P += q * (eleicao - t_ant).days
    return float(x), float(np.sqrt(P))


def m_processo_gaussiano(y_corr, df, semente=42):
    t = -df.dias_antes.values.reshape(-1, 1) / 30.0
    k = ConstantKernel(10.0, (0.01, 400)) * RBF(1.5, (0.5, 10)) + WhiteKernel(5.0, (0.01, 100))
    gp = GaussianProcessRegressor(kernel=k, normalize_y=True, random_state=semente, n_restarts_optimizer=5)
    gp.fit(t, y_corr)
    mu, sd = gp.predict(np.array([[0.0]]), return_std=True)
    return float(mu[0]), float(sd[0])


def m_bayes_gibbs(y, df, rng, iters=6000, burn=1500):
    """y_i = a + b·t_i + h_casa + e_i;  h ~ N(0, τ²);  e_i ~ N(0, s_i² + σ0²). Amostrador de Gibbs."""
    casas = sorted(df.instituto.unique())
    idx = np.array([casas.index(c) for c in df.instituto])
    t = -df.dias_antes.values / 30
    s2 = np.array([var_amostral(v, n) for v, n in zip(y, df.n)])
    a, b, h, tau2, sig0 = y.mean(), 0.0, np.zeros(len(casas)), 9.0, 4.0
    guarda = []
    X = np.column_stack([np.ones_like(t), t])
    for it in range(iters):
        v = s2 + sig0
        r = y - h[idx]
        Prec = X.T @ (X / v[:, None]) + np.eye(2) / 1e4
        a, b = rng.multivariate_normal(np.linalg.solve(Prec, X.T @ (r / v)), np.linalg.inv(Prec))
        res = y - a - b * t
        for c in range(len(casas)):
            m = idx == c
            prec = (1 / v[m]).sum() + 1 / tau2
            h[c] = rng.normal((res[m] / v[m]).sum() / prec, np.sqrt(1 / prec))
        tau2 = 1 / rng.gamma(2 + len(casas) / 2, 1 / (8 + (h ** 2).sum() / 2))
        e = y - a - b * t - h[idx]
        prop = sig0 * np.exp(rng.normal(0, 0.3))
        ll = lambda s: -0.5 * np.sum(np.log(s2 + s) + e ** 2 / (s2 + s)) - s / 20
        if np.log(rng.random()) < ll(prop) - ll(sig0) + np.log(prop / sig0):
            sig0 = prop
        if it >= burn:
            guarda.append(a)
    guarda = np.array(guarda)
    return float(guarda.mean()), float(guarda.std())


def rodar_ensemble(y, df, rng, eleicao, ancora=None):
    """Roda os 6 agregadores sobre a série y. Devolve (modelos, efeitos-instituto, âncora alternativa, ensemble)."""
    mods = {NOMES[0]: m_media_ponderada(y, df), NOMES[1]: m_mediana_robusta(y, df, rng)}
    est, dp, ef = m_regressao_instituto(y, df)
    mods[NOMES[2]] = (est, dp)
    alt = m_regressao_instituto(y, df, ancora=ancora)[:2] if ancora else None
    y_corr = y - np.array([ef[c] for c in df.instituto])
    mods[NOMES[3]] = m_kalman(y_corr, df, eleicao)
    mods[NOMES[4]] = m_processo_gaussiano(y_corr, df)
    mods[NOMES[5]] = m_bayes_gibbs(y, df, rng)
    ests = np.array([v[0] for v in mods.values()])
    dps = np.array([v[1] for v in mods.values()])
    ens = {"est": round(float(ests.mean()), 2), "dp": round(float(np.sqrt((dps ** 2).mean() + ests.var(ddof=1))), 2),
           "min_modelos": round(float(ests.min()), 2), "max_modelos": round(float(ests.max()), 2)}
    mods = {k: {"est": round(float(v[0]), 2), "dp": round(float(v[1]), 2)} for k, v in mods.items()}
    return mods, {k: round(float(v), 2) for k, v in ef.items()}, alt, ens
