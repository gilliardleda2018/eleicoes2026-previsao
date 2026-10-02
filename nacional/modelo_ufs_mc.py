"""Cenário nacional — previsão por estado + Monte Carlo do 1º e do 2º turno (espelha modelo_municipios_mc.py).

A) Geografia (os mesmos 5 modelos de ML do cenário estadual): aprendem como o mapa de 2018 previu o de 2022
   (desvio do voto no PT em cada UF em relação ao país); aplicados ao mapa de 2022 para 2026.
B) Calibração regional: recortes por região/UF das pesquisas de 2026, medidos em relação ao país na MESMA
   pesquisa (anula o viés do instituto) e comparados ao padrão de 2022 → ajuste da geografia.
C) Governadores (equivalente aos prefeitos): efeito sorteado a favor do candidato apoiado (hipótese, faixa larga).
D) Erro histórico das pesquisas presidenciais (2006–2022) por turno + cenário de alerta "padrão 2018/2022".
E) Monte Carlo com 20 mil cenários.

Saídas: resultados/ufs_previsao.csv, resultados/simulacao_nacional.json, resultados/geo_ml_nacional.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parent
D, RES = RAIZ / "dados", RAIZ / "resultados"
from validacao_modelo import (data_corte, filtrar_datas, validar_percentuais, transferencia_implicita,
                              sortear_transferencia, decidir, escrever_json)
RES.mkdir(parents=True, exist_ok=True)
SEMENTE, N_SIM = 42, 20_000
rng = np.random.default_rng(SEMENTE)

b = pd.read_csv(D / "base_ufs.csv")
if len(b) != 27 or b.uf.nunique() != 27 or b.regiao.nunique() < 2:
    raise ValueError("Base deve conter 27 UFs únicas e regiões válidas")
cols_base = ["haddad18_2t", "haddad18_1t", "ciro18_1t", "lula22_2t", "lula22_1t", "ciro22_1t"]
validar_percentuais(b, cols_base, "Base geográfica")
if not np.isfinite(b.validos22_2t).all() or (b.validos22_2t <= 0).any():
    raise ValueError("Pesos eleitorais inválidos")
cent = json.load(open(D / "centroides_ufs.json"))
b["lat"], b["lon"] = b.uf.map(lambda u: cent[u][0]), b.uf.map(lambda u: cent[u][1])
ens = json.load(open(RES / "ensemble_nacional.json", encoding="utf-8"))
if "data_corte" not in ens:
    raise ValueError("Agregação sem data de corte; regenere com a versão corrigida")
CORTE = pd.Timestamp(ens["data_corte"])
if CORTE > min(data_corte(), pd.Timestamp("2026-10-04")):
    raise ValueError("Agregação posterior ao corte permitido")
for chave in ("lula_1t", "flavio_1t", "lula_2t"):
    if chave not in ens["ensemble"]:
        continue
    e = ens["ensemble"][chave]
    if not np.isfinite([e["est"], e["dp"]]).all() or not 0 <= e["est"] <= 100 or e["dp"] <= 0:
        raise ValueError(f"Agregação inválida: {chave}")
w = b.validos22_2t.values / b.validos22_2t.sum()
b["log_validos"] = np.log(b.validos22_2t)


def desvio(col):
    return b[col] - np.average(b[col], weights=w)


# ------------------------------------------------------------------ A) geografia (ML)
X_treino = np.column_stack([desvio("haddad18_2t"), desvio("haddad18_1t"), desvio("ciro18_1t"), b.log_validos, b.lat, b.lon])
alvo = desvio("lula22_2t").values
X_2026 = np.column_stack([desvio("lula22_2t"), desvio("lula22_1t"), desvio("ciro22_1t"), b.log_validos, b.lat, b.lon])
modelos = {
    "Regressão linear": make_pipeline(StandardScaler(), LinearRegression()),
    "Ridge": make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20))),
    "Random Forest": RandomForestRegressor(n_estimators=500, min_samples_leaf=2, random_state=SEMENTE),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=200, max_depth=2, learning_rate=0.05, subsample=0.8,
                                                   random_state=SEMENTE),
    "KNN geográfico": make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=4, weights="distance")),
}
cv = list(LeaveOneGroupOut().split(X_treino, alvo, groups=b.regiao))
# Avaliação espacial, não backtest de uma eleição futura.
geo_ml, previsoes = {}, []
for nome, m in modelos.items():
    oof = cross_val_predict(m, X_treino, alvo, cv=cv)
    geo_ml[nome] = {"r2_cv": round(float(r2_score(alvo, oof)), 3),
                    "erro_medio_pts": round(float(mean_absolute_error(alvo, oof)), 2)}
    m.fit(X_treino, alvo)
    previsoes.append(m.predict(X_2026))
erro_baseline = float(mean_absolute_error(alvo, desvio("haddad18_2t")))
# Modelos piores que a persistência não devem piorar a geografia por serem complexos.
r2s = np.array([max(v["r2_cv"], 0.01) if v["erro_medio_pts"] <= erro_baseline else 0.0 for v in geo_ml.values()])
if not r2s.sum():
    raise ValueError("Nenhum modelo geográfico supera persistência; revise antes de publicar")
pesos_ml = r2s / r2s.sum()
b["inclinacao_pt"] = np.average(np.vstack(previsoes), axis=0, weights=pesos_ml)
b["inclinacao_pt"] -= np.average(b.inclinacao_pt, weights=w)
erro_geo = float(np.average([v["erro_medio_pts"] for v in geo_ml.values()], weights=pesos_ml))
geo_ml["_baseline"] = {"erro_medio_pts": round(float(mean_absolute_error(alvo, desvio("haddad18_2t"))), 2),
                       "descricao": "Persistência da geografia 2018; referência espacial"}
geo_ml["_validacao"] = {"tipo": "região deixada de fora", "temporal": False,
                        "observacao": "Não comprova acurácia eleitoral em 2026"}
geo_ml["_ensemble"] = {"pesos": dict(zip(modelos, pesos_ml.round(3))), "erro_medio_pts": round(erro_geo, 2)}

# ------------------------------------------------------------------ B) calibração regional pelas pesquisas de 2026
REG_UF = dict(zip(b.uf, b.regiao))
AJUSTE = {}  # uf -> (ajuste em logit, erro)
arq_reg = D / "pesquisas_presidente_regioes.csv"
if arq_reg.exists():
    rr = pd.read_csv(arq_reg)
    rr = filtrar_datas(rr, CORTE, inicio="inicio")
    if "status" in rr:
        rr = rr[rr.status == "confirmada"]
    for c in ("lula", "flavio"):
        rr[c] = pd.to_numeric(rr[c], errors="coerce")
    rr = rr.dropna(subset=["lula", "flavio"])
    rr = rr[rr.turno.astype(str) == "2"].copy()  # não mistura geografia de turnos diferentes
    validar_percentuais(rr, ["lula", "flavio"], "Recortes regionais")
    if ((rr.lula <= 0) | (rr.flavio <= 0)).any():
        raise ValueError("Recortes com zero não são compatíveis com logit")
    pn = pd.read_csv(D / "pesquisas_presidente.csv")
    pn = filtrar_datas(pn, CORTE)
    pn["fim"] = pn.fim.dt.strftime("%Y-%m-%d")
    rr["fim"] = rr.fim.dt.strftime("%Y-%m-%d")
    if "status" in pn:
        pn = pn[pn.status == "confirmada"]
    reg22 = b.groupby("regiao").apply(lambda d: np.average(d.lula22_2t, weights=d.validos22_2t), include_groups=False)
    nac22 = np.average(b.lula22_2t, weights=w)
    shifts = {}
    for (inst, fim), g in rr.groupby(["instituto", "fim"]):
        tot = pn[(pn.instituto == inst) & (pn.fim == fim) & (pn.turno.astype(str) == str(g.turno.iloc[0]))]
        if len(tot) != 1:
            continue
        validar_percentuais(tot, ["lula", "flavio"], "Pesquisa nacional pareada")
        if (tot.lula <= 0).any() or (tot.flavio <= 0).any():
            raise ValueError("Pesquisa nacional incompatível com logit")
        nac = float(pd.to_numeric(tot.lula).iloc[0]) / (float(pd.to_numeric(tot.lula).iloc[0]) +
                                                         float(pd.to_numeric(tot.flavio).iloc[0]))
        for _, lin in g.iterrows():
            rec = str(lin.recorte).strip()
            gap26 = logit(lin.lula / (lin.lula + lin.flavio)) - logit(nac)
            if rec in reg22.index:
                gap22 = logit(reg22[rec] / 100) - logit(nac22 / 100)
                shifts.setdefault(("R", rec), []).append(gap26 - gap22)
            elif rec.upper() in REG_UF:
                u = rec.upper()
                gap22 = logit(b.loc[b.uf == u, "lula22_2t"].iloc[0] / 100) - logit(nac22 / 100)
                shifts.setdefault(("U", u), []).append(gap26 - gap22)
    for (tipo, chave), vals in shifts.items():
        vals = np.array(vals)
        media, se = float(vals.mean()), float(0.15 / np.sqrt(len(vals)) + (vals.std() if len(vals) > 1 else 0.1))
        alvo_ufs = [u for u, r in REG_UF.items() if r == chave] if tipo == "R" else [chave]
        for u in alvo_ufs:
            if tipo == "U" or u not in AJUSTE:  # pesquisa estadual tem prioridade sobre a regional
                AJUSTE[u] = (media * 0.5, se)  # meio caminho: 2026 ainda é dominado pelo padrão de 2022
b["ajuste_regional"] = b.uf.map(lambda u: AJUSTE.get(u, (0, 0))[0])

# ------------------------------------------------------------------ estado do país: 1º e 2º turno
el, ef_ = ens["ensemble"]["lula_1t"], ens["ensemble"]["flavio_1t"]
cov = np.array([[el["dp"] ** 2, -0.5 * el["dp"] * ef_["dp"]], [-0.5 * el["dp"] * ef_["dp"], ef_["dp"] ** 2]])
lf = rng.multivariate_normal([el["est"], ef_["est"]], cov, N_SIM)

# D) erro histórico das pesquisas presidenciais (margem PT − adversário; + = subestimou o PT)
HIST = None
import sys
sys.path.insert(0, str(RAIZ))
from historico import carregar as carregar_historico  # noqa: E402
h = carregar_historico(D / "erro_historico_presidente.csv")
corr = h.groupby(["ano", "turno"]).erro_margem.mean().reset_index()
if corr.groupby("turno").ano.nunique().min() < 3:
    raise ValueError("Histórico insuficiente: ao menos três eleições por turno")
e1, e2 = corr[corr.turno == 1].erro_margem.values, corr[corr.turno == 2].erro_margem.values
e_2022 = h[(h.ano == 2022) & (h.turno == 1)].erro_margem.values          # alerta, 1º turno (por instituto)
pre2t = pd.read_csv(D / "erro_2t_antecipado_2022.csv")                     # alerta, 2º turno antecipado (2022)
e_pre2t_2022 = pd.to_numeric(pre2t.erro_margem, errors="raise").values
if not len(e_pre2t_2022) or not np.isfinite(e_pre2t_2022).all():
    raise ValueError("Histórico antecipado de 2022 inválido")

# Modelo principal: erro = persistência (0 a 100%, incerta) × erro de uma eleição real sorteada + ruído normal.
# O mesmo sorteio vale para o 1º turno e para o 2º (as pesquisas de 2º turno de hoje são feitas antes do 1º turno).
persist = rng.uniform(0, 1, N_SIM)
ruido_setor = rng.normal(0, 0.6 * e1.std(ddof=1), N_SIM)
# 1º turno: todas as eleições (2006–2022) — inclui o voto útil de última hora, fenômeno típico de 1º turno
erro1 = persist * rng.choice(e1, N_SIM) + ruido_setor
# 2º turno (confronto direto): só evidências da era polarizada — 1º turno de 2018 e 2022 (sem voto útil relevante)
# e o erro das simulações de 2º turno feitas antes do 1º turno de 2022
# Principal: erros observados do próprio segundo turno. A hipótese polarizada
# permanece apenas no cenário de alerta, até validação temporal independente.
erro2t = persist * rng.choice(e2, N_SIM) + rng.normal(0, 0.6 * e2.std(ddof=1), N_SIM)
# Cenário de alerta: o padrão de 2022 se repete integralmente
erro_alerta_1t = rng.choice(e_2022, N_SIM) + rng.normal(0, 1.5, N_SIM)
erro_alerta_2t = rng.choice(e_pre2t_2022, N_SIM) + rng.normal(0, 1.5, N_SIM)
HIST = {"pesquisas": int(len(h)), "eleicoes": sorted(int(a) for a in h.ano.unique()),
        "media_1t": round(float(e1.mean()), 1), "dp_1t": round(float(e1.std(ddof=1)), 1),
        "media_2t": round(float(e2.mean()), 1), "dp_2t": round(float(e2.std(ddof=1)), 1),
        "media_2018_2022": round(float(corr[(corr.turno == 1) & (corr.ano >= 2018)].erro_margem.mean()), 1), "media_2022_1t": round(float(e_2022.mean()), 1),
        "erro_2t_antecipado_2022": round(float(e_pre2t_2022.mean()), 1),
        "persistencia": "uniforme de 0% a 100%",
        "erros_usados_2t": [round(float(v), 1) for v in e2],
        "metodo_principal_2t": "erros das pesquisas finais de segundo turno; hipótese não calibrada temporalmente",
        "detalhe": {f"{int(a)} {int(t)}º t": round(float(v), 1) for a, t, v in corr.itertuples(index=False)}}

# O histórico está na base dos dois candidatos, não em todos os válidos.
# Converte a diferença de margem para a massa Lula+Flávio antes de aplicar.
delta1 = erro1 * lf.sum(axis=1) / 200
L1 = np.clip(lf[:, 0] + delta1, 20, 75)
F1 = np.clip(lf[:, 1] - delta1, 15, 70)
R1 = np.clip(100 - L1 - F1, 1, None)
tot = L1 + F1 + R1
L1, F1, R1 = 100 * L1 / tot, 100 * F1 / tot, 100 * R1 / tot

# 2º turno: 50% pesquisas de 2º turno (6 agregadores) + 50% transferência dos demais candidatos
# transferência MEDIDA: 52 pesquisas (ago/set) com 1º e 2º turno na mesma entrevista
pp = pd.read_csv(RES / "pesquisas_nacionais_tratadas.csv")
if (pd.to_datetime(pp.fim) > CORTE).any():
    raise ValueError("Pesquisas tratadas posteriores à agregação")
par = transferencia_implicita(pp)
T_N = int(len(par))
T_MED = float(par.t.mean()) if T_N >= 4 else None
T_DP = float(par.t.std(ddof=1)) if T_N >= 4 else None
transferencia_disponivel = T_N >= 4
if not transferencia_disponivel and "lula_2t" not in ens["ensemble"]:
    raise ValueError("Sem transferência suficiente e sem agregação de segundo turno")
t_out = sortear_transferencia(par.t.values, rng, N_SIM) if transferencia_disponivel else None
L0, F0 = lf[:, 0], lf[:, 1]                               # pesquisas cruas (sem erro histórico)
L2_transf = np.clip((L0 + t_out * np.clip(100 - L0 - F0, 0, None)) / 100, 0, 1) if transferencia_disponivel else None
if "lula_2t" in ens["ensemble"]:
    e2t = ens["ensemble"]["lula_2t"]
    L2_pesq = rng.normal(e2t["est"], e2t["dp"], N_SIM) / 100
else:
    L2_pesq = L2_transf
usa_pesq = rng.random(N_SIM) < 0.5 if transferencia_disponivel and "lula_2t" in ens["ensemble"] else np.full(N_SIM, "lula_2t" in ens["ensemble"])
if L2_transf is None:
    L2_transf = L2_pesq.copy()  # fallback declarado; não estima transferência
# 2º turno: erro da era polarizada (ver erro2t), com a mesma persistência sorteada do 1º turno
L2 = np.clip(np.where(usa_pesq, L2_pesq, L2_transf) + erro2t / 200 + rng.normal(0, 0.01, N_SIM), 0.3, 0.7)

vence_1t_l, vence_1t_f, havera_2t, lula_leva, flavio_leva = decidir(L1, F1, L2)
if not havera_2t.any():
    raise ValueError("Nenhum cenário de segundo turno: relatório condicional indisponível")
# cenário de alerta: as pesquisas erram exatamente como em 2022 (1º turno e simulações antecipadas de 2º turno)
delta1x = erro_alerta_1t * lf.sum(axis=1) / 200
L1x = np.clip(lf[:, 0] + delta1x, 20, 75)
F1x = np.clip(lf[:, 1] - delta1x, 15, 70)
R1x = np.clip(100 - L1x - F1x, 1, None)
tx = L1x + F1x + R1x
L1x, F1x, R1x = 100 * L1x / tx, 100 * F1x / tx, 100 * R1x / tx
L2x = np.clip(np.where(usa_pesq, L2_pesq, L2_transf) + erro_alerta_2t / 200 + rng.normal(0, 0.01, N_SIM), 0.3, 0.7)
_, _, _, lula_x, flavio_x = decidir(L1x, F1x, L2x)

# ------------------------------------------------------------------ estados
gov = pd.read_csv(D / "governadores_apoio_2026.csv") if (D / "governadores_apoio_2026.csv").exists() else None
if gov is not None:
    mapa = {"lula": 1, "flavio": -1}
    b["governador_apoia"] = b.uf.map(dict(zip(gov.uf, gov.apoio_2t_tendencia.fillna(gov.apoio_1t)))).fillna("Neutro")
    gsign = b.governador_apoia.str.lower().map(lambda s: 1 if "lula" in s else (-1 if "fl" in s else 0)).values
else:
    b["governador_apoia"] = "Neutro"
    gsign = np.zeros(len(b))

N_UF_SIM = 5000
sel = rng.choice(N_SIM, N_UF_SIM, replace=False)
beta_geo = rng.normal(1.0, 0.10, N_UF_SIM)[:, None]
efeito_gov = rng.uniform(0.0, 0.08, N_UF_SIM)[:, None]  # logit (~0 a 2 pts) — hipótese, não observado
ajuste = np.column_stack([rng.normal(AJUSTE.get(u, (0, 0))[0], AJUSTE.get(u, (0, 0.05))[1], N_UF_SIM) for u in b.uf])
ruido = rng.normal(0, erro_geo / 25, (N_UF_SIM, len(b)))
base_logit = beta_geo * (b.inclinacao_pt.values / 25)[None, :] + ajuste + efeito_gov * gsign[None, :] + ruido


def calibrar(logit_base, alvo_pais):
    c = np.zeros(logit_base.shape[0])
    for _ in range(30):
        s_ = expit(logit_base + c[:, None])
        c += logit(alvo_pais) - logit(np.clip((s_ * w).sum(axis=1), 1e-4, 1 - 1e-4))
    out = expit(logit_base + c[:, None])
    if not np.allclose((out * w).sum(axis=1), alvo_pais, atol=1e-8):
        raise ValueError("Calibração estadual não convergiu")
    return out


uf_l2p_1t = calibrar(base_logit, L1[sel] / (L1[sel] + F1[sel]))
uf_l2t = calibrar(base_logit, L2[sel])
resto = R1[sel][:, None]
q = lambda a, p_: np.percentile(a, p_, axis=0)
b["lula_1t"] = q((100 - resto) * uf_l2p_1t, 50).round(1)
b["flavio_1t"] = q((100 - resto) * (1 - uf_l2p_1t), 50).round(1)
b["lula_2t"] = (100 * q(uf_l2t, 50)).round(1)
b["lula_2t_p10"], b["lula_2t_p90"] = (100 * q(uf_l2t, 10)).round(1), (100 * q(uf_l2t, 90)).round(1)
b["prob_lula_vence_uf_2t"] = (uf_l2t > 0.5).mean(axis=0).round(3)
b["validos_26_est"] = (b.validos22_2t * 1.03).round()
b["votos_lula_2t"] = (b.validos_26_est * b.lula_2t / 100).round()
b["votos_flavio_2t"] = b.validos_26_est - b.votos_lula_2t
b["saldo_lula_2t"] = b.votos_lula_2t - b.votos_flavio_2t
b["favorito_2t"] = np.select([b.prob_lula_vence_uf_2t >= .65, b.prob_lula_vence_uf_2t <= .35],
                             ["Lula", "Flávio"], "Indefinido")

pct = lambda x: round(float(np.mean(x)), 3)
reg = b.groupby("regiao")[["votos_lula_2t", "votos_flavio_2t"]].sum()
sim = {
    "n_cenarios": N_SIM,
    "data_corte": str(CORTE.date()),
    "validacao_preditiva": "pendente: testes sintéticos não validam previsão real",
    "escopo": "Lula x Flávio; demais candidatos não têm vitória modelada; sem exterior",
    "transferencia_disponivel": transferencia_disponivel,
    "efeitos_estaduais": "redistribuem votos; não alteram probabilidade nacional",
    "primeiro_turno": {"lula_validos_p10_p50_p90": [round(float(np.percentile(L1, k)), 1) for k in (10, 50, 90)],
                       "flavio_validos_p10_p50_p90": [round(float(np.percentile(F1, k)), 1) for k in (10, 50, 90)],
                       "outros_validos_p50": round(float(np.median(R1)), 1),
                       "prob_lula_vence_1t": pct(vence_1t_l), "prob_flavio_vence_1t": pct(vence_1t_f),
                       "prob_segundo_turno": pct(havera_2t)},
    "segundo_turno": {"lula_validos_p10_p50_p90": [round(float(100 * np.percentile(L2[havera_2t], k)), 1)
                                                   for k in (10, 50, 90)],
                      "prob_lula_vence_se_2t": pct(L2[havera_2t] > 0.5),
                      "modelo_pesquisas_2t_p50": round(float(100 * np.median(L2_pesq)), 1),
                      "modelo_transferencia_p50": round(float(100 * np.median(L2_transf)), 1),
                      "transferencia_medida": {"lula": round(T_MED, 3) if T_MED is not None else None, "dp": round(T_DP, 3) if T_DP is not None else None, "pares": T_N, "metodo": "distribuição empírica da transferência implícita"}},
    "sem_correcao_historica": {"lula_2t_p50": round(float(100 * np.median(np.where(usa_pesq, L2_pesq, L2_transf))), 1),
                               "prob_lula": pct(np.where(usa_pesq, L2_pesq, L2_transf) > 0.5)},
    "resultado_final": {"prob_lula_presidente": pct(lula_leva), "prob_flavio_presidente": pct(flavio_leva)},
    "cenario_alerta": {"prob_lula_presidente": pct(lula_x), "prob_flavio_presidente": pct(flavio_x),
                       "lula_1t_p50": round(float(np.median(L1x)), 1), "flavio_1t_p50": round(float(np.median(F1x)), 1),
                       "lula_2t_p50": round(float(100 * np.median(L2x)), 1)},
    "erro_historico": HIST,
    "estados": {"favorito_lula": int((b.favorito_2t == "Lula").sum()), "favorito_flavio": int((b.favorito_2t == "Flávio").sum()),
                "indefinidos": int((b.favorito_2t == "Indefinido").sum())},
    "regioes_2t": {r: round(float(100 * v.votos_lula_2t / (v.votos_lula_2t + v.votos_flavio_2t)), 1) for r, v in reg.iterrows()},
    "ajustes_regionais": {u: [round(a, 3), round(s, 3)] for u, (a, s) in AJUSTE.items()},
}
json.dumps(sim, allow_nan=False)
json.dumps(geo_ml, allow_nan=False)
b.to_csv(RES / "ufs_previsao.csv", index=False, encoding="utf-8")
escrever_json(RES / "simulacao_nacional.json", sim)
escrever_json(RES / "geo_ml_nacional.json", geo_ml)
print(json.dumps(geo_ml, ensure_ascii=False, indent=1))
print(json.dumps({k: v for k, v in sim.items() if k != "ajustes_regionais"}, ensure_ascii=False, indent=1))
print(b[["uf", "governador_apoia", "lula22_2t", "lula_1t", "flavio_1t", "lula_2t", "prob_lula_vence_uf_2t"]].to_string(index=False))
