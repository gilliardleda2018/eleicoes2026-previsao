"""Previsão por município + Monte Carlo do 1º e do 2º turno — Governo MA 2026.

A) Geografia política (ML): modelos aprendem como o mapa de 2018 previu o de 2022
   (desvio do voto governista de cada município em relação ao estado). Validação cruzada.
   O ensemble é aplicado ao mapa de 2022 para gerar o "índice de inclinação governista" de 2026.
     governista anterior: 2018 = Dino | 2022 = Brandão + Weverton (ambos hoje com Orleans)
     oposição anterior:   2018 = Roseana + Maura | 2022 = Lahésio + Edivaldo
B) Efeitos adicionais: apoio do prefeito (prior, não observado em 2022), São Luís calibrada pela
   pesquisa IPSensus da capital (Braide 53,5% × Orleans 37,6% dos válidos) e Grande Ilha.
C) Monte Carlo (20 mil cenários): estado (ensemble de pesquisas + erro sistemático do setor),
   transferência de votos para o 2º turno, efeitos municipais e ruído.

Saídas: resultados/municipios_previsao.csv, resultados/simulacao.json, resultados/geo_ml.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parent
RES = RAIZ / "resultados"
SEMENTE, N_SIM = 42, 20_000
rng = np.random.default_rng(SEMENTE)

b = pd.read_csv(RAIZ / "dados" / "base_municipios.csv")
ens = json.load(open(RES / "ensemble_pesquisas.json", encoding="utf-8"))
w = b.validos22.values / b.validos22.sum()

# ------------------------------------------------------------------ A) geografia política (ML)
b["gov18"], b["opo18"] = b.dino18, b.roseana18 + b.maura18
b["gov22"], b["opo22"] = b.brandao22 + b.weverton22, b.lahesio22 + b.edivaldo22
b["log_validos"] = np.log(b.validos22)


def desvio(col):  # desvio em relação à média estadual ponderada
    return b[col] - np.average(b[col], weights=w)


X_treino = np.column_stack([desvio("gov18"), desvio("opo18"), b.log_validos, b.lat, b.lon, b.grande_ilha])
alvo = desvio("brandao22").values  # geografia do candidato governista seguinte (2022)
X_2026 = np.column_stack([desvio("gov22"), desvio("opo22"), b.log_validos, b.lat, b.lon, b.grande_ilha])

modelos = {
    "Regressão linear": make_pipeline(StandardScaler(), LinearRegression()),
    "Ridge": make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20))),
    "Random Forest": RandomForestRegressor(n_estimators=500, min_samples_leaf=4, random_state=SEMENTE),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=300, max_depth=2, learning_rate=0.05,
                                                   subsample=0.8, random_state=SEMENTE),
    "KNN geográfico": make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=8, weights="distance")),
}
cv = KFold(5, shuffle=True, random_state=SEMENTE)
geo_ml, previsoes = {}, []
for nome, m in modelos.items():
    oof = cross_val_predict(m, X_treino, alvo, cv=cv)
    geo_ml[nome] = {"r2_cv": round(float(r2_score(alvo, oof)), 3),
                    "erro_medio_pts": round(float(mean_absolute_error(alvo, oof)), 2)}
    m.fit(X_treino, alvo)
    previsoes.append(m.predict(X_2026))
r2s = np.array([max(v["r2_cv"], 0.01) for v in geo_ml.values()])
pesos_ml = r2s / r2s.sum()
b["inclinacao_gov"] = np.average(np.vstack(previsoes), axis=0, weights=pesos_ml)  # pts de desvio (escala % válidos)
b["inclinacao_gov"] -= np.average(b.inclinacao_gov, weights=w)
erro_geo = float(np.average([v["erro_medio_pts"] for v in geo_ml.values()], weights=pesos_ml))
geo_ml["_ensemble"] = {"pesos": dict(zip(modelos, pesos_ml.round(3))), "erro_medio_pts": round(erro_geo, 2)}

# ------------------------------------------------------------------ estado: 1º turno
eb, eo = ens["ensemble"]["braide"], ens["ensemble"]["orleans"]
cov = np.array([[eb["dp"] ** 2, -0.6 * eb["dp"] * eo["dp"]], [-0.6 * eb["dp"] * eo["dp"], eo["dp"] ** 2]])
bo = rng.multivariate_normal([eb["est"], eo["est"]], cov, N_SIM)
# Erro sistemático das pesquisas: distribuição REAL medida nas eleições para governador do Nordeste
# (erro na margem governo − oposição em votos válidos; positivo = pesquisas subestimaram o candidato do governo).
HIST = RAIZ / "dados" / "erro_historico_pesquisas.csv"
EXCLUIR_HIST = {(2014, "RN", 1), (2014, "RN", 2), (2022, "SE", 1)}  # situação indefinida / candidatura anulada
h = pd.read_csv(HIST)
for c in ("pesq_governo", "pesq_oposicao", "urna_governo_validos", "urna_oposicao_validos"):
    h[c] = pd.to_numeric(h[c], errors="coerce")
h = h.dropna(subset=["pesq_governo", "pesq_oposicao", "urna_governo_validos", "urna_oposicao_validos"])
h = h[[(a_, u, t) not in EXCLUIR_HIST for a_, u, t in zip(h.ano, h.uf, h.turno)]]
pg = 100 * h.pesq_governo / (h.pesq_governo + h.pesq_oposicao)       # só os dois principais, normalizados
ug = 100 * h.urna_governo_validos / (h.urna_governo_validos + h.urna_oposicao_validos)
h["erro_margem"] = 2 * (ug - pg)                                       # pts na margem gov − opo (+ = subestimou governo)
corridas = (h.groupby(["ano", "uf", "turno"])
            .agg(erro=("erro_margem", "mean"), ex_prefeito=("oposicao_ex_prefeito_capital", "first")).reset_index())
e1 = corridas.loc[corridas.turno == 1, "erro"].values
e2 = corridas.loc[corridas.turno == 2, "erro"].values
e_ex = corridas.loc[(corridas.turno == 1) & (corridas.ex_prefeito.astype(str).str.lower() == "sim"), "erro"].values


# Modelo principal (mesma regra do cenário nacional): erro = persistência incerta (0 a 100%) × erro de uma
# disputa real sorteada + ruído normal. O mesmo sorteio vale para o 1º e o 2º turno.
persist = rng.uniform(0, 1, N_SIM)
erro_margem = persist * rng.choice(e1, N_SIM) + rng.normal(0, 0.6 * e1.std(ddof=1), N_SIM)
# Cenário de alerta: padrão "ex-prefeito da capital" (BA 2022, PI 2022) se repete integralmente
erro_margem_ex = rng.choice(e_ex, N_SIM) + rng.normal(0, 1.5, N_SIM)
corr_txt = lambda d: {f"{a_} {u} {t}º t": round(float(v), 1) for a_, u, t, v in zip(d.ano, d.uf, d.turno, d.erro)}
HISTORICO = {"pesquisas": int(len(h)), "corridas_1t": int(len(e1)), "corridas_2t": int(len(e2)),
             "media_1t": round(float(e1.mean()), 1), "dp_1t": round(float(e1.std(ddof=1)), 1),
             "media_2t": round(float(e2.mean()), 1), "dp_2t": round(float(e2.std(ddof=1)), 1),
             "pct_subestimou_governo_1t": round(float((e1 > 0).mean()), 3),
             "ex_prefeito_corridas": int(len(e_ex)), "ex_prefeito_media": round(float(e_ex.mean()), 1),
             "persistencia": "uniforme de 0% a 100%", "corridas_detalhe": corr_txt(corridas)}
erro_setor = -erro_margem  # positivo favorece Braide (oposição); Orleans é o candidato do governo
B1 = np.clip(bo[:, 0] + erro_setor / 2, 20, 75)
O1 = np.clip(bo[:, 1] - erro_setor / 2, 15, 70)
resto = np.clip(100 - B1 - O1, 3, None)
outros = ens["outros_validos_recentes"]
frac_c = outros["camarao"] / sum(outros.values())
frac_r = outros["rocha"] / sum(outros.values())
C1, R1, X1 = resto * frac_c, resto * frac_r, resto * (1 - frac_c - frac_r)
tot = B1 + O1 + resto
B1, O1, C1, R1, X1 = (v * 100 / tot for v in (B1, O1, C1, R1, X1))


# ------------------------------------------------------------------ estado: 2º turno
def beta(media, dp, n):
    k = media * (1 - media) / dp ** 2 - 1
    return rng.beta(media * k, (1 - media) * k, n)


# transferência MEDIDA nas pesquisas que perguntaram 1º e 2º turno na mesma entrevista
pt1 = pd.read_csv(RES / "pesquisas_tratadas.csv")
pt2 = pd.read_csv(RES / "pesquisas_2t_tratadas.csv")
par = pt1.merge(pt2[["instituto", "fim", "braide_2p"]], on=["instituto", "fim"])
par["resto"] = 100 - par.braide_val - par.orleans_val
par = par[par.resto > 3]
par["t"] = (par.braide_2p - par.braide_val) / par.resto
T_MED, T_DP, T_N = float(par.t.mean()), float(max(par.t.std(), 0.04)), int(len(par))
t_out = beta(T_MED, T_DP, N_SIM)
B0, O0 = bo[:, 0], bo[:, 1]  # pesquisas cruas (sem erro histórico)
share_transf = (B0 + t_out * np.clip(100 - B0 - O0, 3, None)) / 100
e2t = ens["ensemble"]["braide_2t"]  # 6 agregadores sobre as pesquisas de 2º turno
b2p_pesq = e2t["est"]
share_pesq = rng.normal(e2t["est"], e2t["dp"], N_SIM) / 100
usa_pesq = rng.random(N_SIM) < 0.5  # ensemble 50/50 entre pesquisas de 2º turno e transferência
B2_bruto = np.where(usa_pesq, share_pesq, share_transf)
# as pesquisas de 2º turno de hoje são feitas antes do 1º turno: herdam o MESMO erro sorteado para o 1º turno
B2 = np.clip(B2_bruto - erro_margem / 200 + rng.normal(0, 0.015, N_SIM), 0.2, 0.9)

# cenário "padrão ex-prefeito da capital"
B1x = np.clip(bo[:, 0] - erro_margem_ex / 2, 20, 75)
O1x = np.clip(bo[:, 1] + erro_margem_ex / 2, 15, 70)
Rx = np.clip(100 - B1x - O1x, 3, None)
tx = B1x + O1x + Rx
B1x, O1x, Rx = 100 * B1x / tx, 100 * O1x / tx, 100 * Rx / tx
B2x = np.clip(B2_bruto - erro_margem_ex / 200 + rng.normal(0, 0.015, N_SIM), 0.2, 0.9)
leva_x = (B1x >= 50) | ((B1x < 50) & (O1x < 50) & (B2x > 0.5))
leva_orleans_x = (O1x >= 50) | ((B1x < 50) & (O1x < 50) & (B2x < 0.5))

vence_1t = B1 >= 50
havera_2t = ~vence_1t & (O1 < 50)
braide_leva = vence_1t | (havera_2t & (B2 > 0.5))
orleans_leva = (O1 >= 50) | (havera_2t & (B2 < 0.5))

# ------------------------------------------------------------------ municípios
# --- calibração regional pelas pesquisas com recorte (diferença de cada região em relação ao estado, na MESMA pesquisa,
#     o que cancela o viés do instituto) ---
MESO = {  # regiões imediatas (IBGE 2017) -> mesorregiões usadas pelo IPPI
    "São Luís": "Norte", "Barreirinhas": "Norte", "Itapecuru Mirim": "Norte", "Pinheiro": "Norte", "Cururupu": "Norte",
    "Viana": "Norte", "Imperatriz": "Oeste", "Açailândia": "Oeste", "Santa Inês": "Oeste",
    "Governador Nunes Freire": "Oeste", "Bacabal": "Centro", "Pedreiras": "Centro", "Presidente Dutra": "Centro",
    "Barra do Corda": "Centro", "Caxias": "Leste", "Codó": "Leste", "Timon": "Leste", "Chapadinha": "Leste",
    "Tutóia - Araioses": "Leste", "Colinas": "Leste", "São João dos Patos": "Leste", "Balsas": "Sul"}
b["meso"] = b.regiao_imediata.map(MESO)
rec = pd.read_csv(RAIZ / "dados" / "pesquisas_recortes_regionais.csv")


def o2p(bra, orl):
    return orl / (bra + orl)


def gap_e_erro(bra, orl, bra_est, orl_est, n):
    """Diferença em logit (região − estado da mesma pesquisa) e erro-padrão (amostra com efeito de desenho 1,6)."""
    pr = o2p(bra, orl)
    se = np.sqrt(1.6 / (n * (bra + orl) / 100 * pr * (1 - pr)))
    return float(logit(pr) - logit(o2p(bra_est, orl_est))), float(se)


IPPI_EST = (44.0, 25.9)  # IPPI 6–10/08, estado (mesmo levantamento dos recortes)
N_MESO = {"Norte": 596, "Oeste": 313, "Leste": 306, "Centro": 211, "Sul": 74}
GAP = {}
for meso, n_ in N_MESO.items():
    lin = rec[rec.recorte.str.contains(f"Mesorregião {meso}")].iloc[0]
    GAP[meso] = gap_e_erro(lin.braide, lin.orleans, *IPPI_EST, n_)
ips = rec[(rec.instituto == "IPSensus") & (rec.base == "total")]
sl, imp = ips[ips.recorte.str.startswith("São Luís")].iloc[0], ips[ips.recorte.str.startswith("Imperatriz")].iloc[0]
IPS_EST = (35.7, 43.6)  # IPSensus estadual 14–18/09
GAP_SL = gap_e_erro(sl.braide, sl.orleans, *IPS_EST, 800)
GAP_IMP = gap_e_erro(imp.braide, imp.orleans, *IPS_EST, 350)
REGIONAL = {"mesorregioes_ippi": {k: [round(v[0], 3), round(v[1], 3)] for k, v in GAP.items()},
            "sao_luis_ipsensus": [round(GAP_SL[0], 3), round(GAP_SL[1], 3)],
            "imperatriz_ipsensus": [round(GAP_IMP[0], 3), round(GAP_IMP[1], 3)]}

mayor = b.prefeito_apoia.map({"Orleans": 1, "Braide": -1, "Neutro": 0}).values
pequeno = np.clip(1 - (b.log_validos.values - np.log(5_000)) / (np.log(200_000) - np.log(5_000)), 0.15, 1)
n_mun = len(b)
IDX_SL = int(np.flatnonzero(b.sao_luis.values == 1)[0])
N_MUN_SIM = 4000  # cenários municipais (subamostra dos 20 mil) para caber em memória
sel = rng.choice(N_SIM, N_MUN_SIM, replace=False)


def calibrar(logit_base, alvo_estado):
    """Ajusta o intercepto para que a média ponderada dos municípios bata com o estado."""
    c = np.zeros(logit_base.shape[0])
    for _ in range(30):
        s = expit(logit_base + c[:, None])
        c += (logit(alvo_estado) - logit(np.clip((s * w).sum(axis=1), 1e-4, 1 - 1e-4)))
    return expit(logit_base + c[:, None])


beta_geo = rng.normal(1.0, 0.25, N_MUN_SIM)[:, None]          # persistência da geografia governista
efeito_pref = rng.uniform(0.02, 0.30, N_MUN_SIM)[:, None]       # logit (~0,5 a 7 pts) — prior, não observado
ruido = rng.normal(0, erro_geo / 25, (N_MUN_SIM, n_mun))       # ruído municipal ~ erro dos modelos geográficos
incl_dentro = (b.inclinacao_gov - b.groupby("meso").inclinacao_gov.transform(
    lambda s_: np.average(s_, weights=b.loc[s_.index, "validos22"]))).values
gap_meso = np.column_stack([rng.normal(GAP[m][0], GAP[m][1], N_MUN_SIM) for m in b.meso])
base_logit = (gap_meso + beta_geo * (incl_dentro / 25)[None, :]
              + efeito_pref * mayor[None, :] * pequeno[None, :] + ruido)
# São Luís e Imperatriz: pesquisa da própria cidade combinada com a da mesorregião (média ponderada pela precisão).
# A pesquisa já contém o perfil da cidade: substitui a inclinação histórica e o efeito do prefeito.
IDX_IMP = int(np.flatnonzero(b.imperatriz.values == 1)[0])
for idx, (g_c, se_c), meso in [(IDX_SL, GAP_SL, "Norte"), (IDX_IMP, GAP_IMP, "Oeste")]:
    g_m, se_m = GAP[meso]
    w_c, w_m = 1 / se_c ** 2, 1 / se_m ** 2
    g, se = (w_c * g_c + w_m * g_m) / (w_c + w_m), np.sqrt(1 / (w_c + w_m)) + 0.10
    base_logit[:, idx] = rng.normal(g, se, N_MUN_SIM) + ruido[:, idx] * 0.5
    REGIONAL[f"combinado_{b.municipio[idx]}"] = [round(float(g), 3), round(float(se), 3)]

o2p_1t = O1[sel] / (B1[sel] + O1[sel])
mun_o2p_1t = calibrar(base_logit, o2p_1t)                      # Orleans / (Braide + Orleans), 1º turno
mun_o2p_2t = calibrar(base_logit, 1 - B2[sel])                  # Orleans no 2º turno
resto_mun = (100 - B1[sel] - O1[sel])[:, None]
mun_O1 = (100 - resto_mun) * mun_o2p_1t
mun_B1 = (100 - resto_mun) * (1 - mun_o2p_1t)

val_26 = (b.eleitores_26 * (b.validos22 / b.comparecimento22)).values
q = lambda a, p_: np.percentile(a, p_, axis=0)
b["braide_1t"], b["orleans_1t"] = q(mun_B1, 50).round(1), q(mun_O1, 50).round(1)
b["outros_1t"] = (100 - b.braide_1t - b.orleans_1t).round(1)
b["braide_2t"] = (100 * q(1 - mun_o2p_2t, 50)).round(1)
b["braide_2t_p10"], b["braide_2t_p90"] = (100 * q(1 - mun_o2p_2t, 10)).round(1), (100 * q(1 - mun_o2p_2t, 90)).round(1)
b["prob_braide_vence_cidade_2t"] = ((1 - mun_o2p_2t) > 0.5).mean(axis=0).round(3)
b["validos_26_est"] = val_26.round()
b["votos_braide_1t"] = (val_26 * b.braide_1t / 100).round()
b["votos_orleans_1t"] = (val_26 * b.orleans_1t / 100).round()
b["votos_braide_2t"] = (val_26 * b.braide_2t / 100).round()
b["votos_orleans_2t"] = (val_26 - b.votos_braide_2t).round()
b["saldo_2t"] = b.votos_braide_2t - b.votos_orleans_2t
b["favorito_2t"] = np.select([b.prob_braide_vence_cidade_2t >= .65, b.prob_braide_vence_cidade_2t <= .35],
                             ["Braide", "Orleans"], "Indefinido")

# ------------------------------------------------------------------ resumo
pct = lambda x: round(float(np.mean(x)), 3)
regiao = (b.assign(vb=b.votos_braide_2t, vo=b.votos_orleans_2t)
          .groupby("regiao_intermediaria")[["vb", "vo", "validos_26_est"]].sum())
regiao["braide_2t"] = (100 * regiao.vb / (regiao.vb + regiao.vo)).round(1)
sim = {
    "n_cenarios": N_SIM,
    "primeiro_turno": {
        "braide_validos_p10_p50_p90": [round(float(np.percentile(B1, k)), 1) for k in (10, 50, 90)],
        "orleans_validos_p10_p50_p90": [round(float(np.percentile(O1, k)), 1) for k in (10, 50, 90)],
        "camarao_validos_p50": round(float(np.median(C1)), 1), "rocha_validos_p50": round(float(np.median(R1)), 1),
        "prob_braide_vence_1t": pct(vence_1t), "prob_orleans_vence_1t": pct(O1 >= 50), "prob_segundo_turno": pct(havera_2t),
    },
    "segundo_turno": {
        "braide_validos_p10_p50_p90": [round(float(100 * np.percentile(B2[havera_2t], k)), 1) for k in (10, 50, 90)],
        "prob_braide_vence_se_2t": pct(B2[havera_2t] > 0.5),
        "modelo_transferencia_p50": round(float(100 * np.median(share_transf)), 1),
        "modelo_pesquisas_2t_p50": round(b2p_pesq, 1),
        "transferencia_medida": {"braide": round(T_MED, 3), "dp": round(T_DP, 3), "pares": T_N},
    },
    "resultado_final": {"prob_braide_governador": pct(braide_leva), "prob_orleans_governador": pct(orleans_leva)},
    "sem_correcao_historica": {"braide_2t_p50": round(float(100 * np.median(B2_bruto)), 1),
                               "prob_braide": pct(((bo[:, 0] >= 50)) | ((bo[:, 0] < 50) & (B2_bruto > .5)))},
    "erro_historico": HISTORICO,
    "cenario_ex_prefeito": {"prob_braide_governador": pct(leva_x), "prob_orleans_governador": pct(leva_orleans_x),
                            "braide_1t_p50": round(float(np.median(B1x)), 1), "orleans_1t_p50": round(float(np.median(O1x)), 1),
                            "prob_orleans_vence_1t": pct(O1x >= 50), "prob_segundo_turno": pct((B1x < 50) & (O1x < 50)),
                            "braide_2t_p50": round(float(100 * np.median(B2x)), 1)},
    "sensibilidade": {
        "persistencia_do_vies": "uniforme de 0% a 100%",
        "ancora_institutos_nacionais_braide_1t": ens["modelos"]["braide"]["_ancora_nacionais"]["est"],
    },
    "municipios": {"favorito_braide": int((b.favorito_2t == "Braide").sum()),
                   "favorito_orleans": int((b.favorito_2t == "Orleans").sum()),
                   "indefinidos": int((b.favorito_2t == "Indefinido").sum())},
    "regioes_2t": regiao.braide_2t.to_dict(),
    "calibracao_regional": REGIONAL,
}
cx = sim["cenario_ex_prefeito"]
br = lambda v, casas=1: f"{v:.{casas}f}".replace(".", ",")
sim["cenario_historico"] = {"texto": (
    f"Em {HISTORICO['corridas_1t']} disputas de 1º turno para governador no Nordeste (2014–2022, {HISTORICO['pesquisas']} "
    f"pesquisas finais), as pesquisas subestimaram o candidato do governo em média {br(HISTORICO['media_1t'])} pontos na "
    f"margem (dispersão de ±{br(HISTORICO['dp_1t'], 0)}). Esse erro já está no modelo principal. Mas quando a oposição era um "
    f"<b>ex-prefeito da capital</b> (Bahia e Piauí em 2022), o erro foi de <b>{br(HISTORICO['ex_prefeito_media'], 0)} pontos</b> "
    f"a favor do governo. Se 2026 repetir esse padrão, a chance de Braide cai para <b>{br(100 * cx['prob_braide_governador'], 0)}%</b> "
    f"e a de Orleans sobe para <b>{br(100 * cx['prob_orleans_governador'], 0)}%</b> (1º turno: Braide {br(cx['braide_1t_p50'])}% × "
    f"Orleans {br(cx['orleans_1t_p50'])}%). São só {HISTORICO['ex_prefeito_corridas']} disputas: é um alerta, não uma regra.")}
b.to_csv(RES / "municipios_previsao.csv", index=False, encoding="utf-8")
json.dump(sim, open(RES / "simulacao.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(geo_ml, open(RES / "geo_ml.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(geo_ml, ensure_ascii=False, indent=1))
print(json.dumps(sim, ensure_ascii=False, indent=1))
print(json.dumps(REGIONAL, ensure_ascii=False))
print(b.nlargest(12, "validos22")[["municipio", "prefeito_apoia", "braide_1t", "orleans_1t", "braide_2t",
                                   "prob_braide_vence_cidade_2t", "saldo_2t"]].to_string(index=False))
