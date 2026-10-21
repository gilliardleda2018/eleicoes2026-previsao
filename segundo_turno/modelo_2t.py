"""Modelo do 2º turno presidencial 2026 (Lula × Flávio Bolsonaro) — nacional, por UF, Maranhão por município e
Tuntum por seção eleitoral.

É o modelo nacional do 1º turno (mesmos 6 agregadores, mesmo erro histórico com persistência incerta, mesma
calibração em logit), agora ancorado no RESULTADO OFICIAL do 1º turno:

1. Pesquisas do 2º turno (campo a partir de 3/10): os 6 agregadores de `agregadores.py`.
2. Estrutural: votos reais do 1º turno + transferência medida (eleitores de Cury, Renan, Caiado, Zema e demais,
   cruzamentos AtlasIntel e Quaest) + pequena troca entre as bases e efeito do comparecimento.
3. Erro das pesquisas: persistência incerta (0 a 100%) × erro sorteado de um conjunto com dois tipos de evidência:
   erros das pesquisas finais de 2º turno (2006–2022) e erros de cada instituto no 1º turno de 2026
   (eles superestimaram Lula na disputa direta). Peso de cada tipo: PESO_ERRO_2026.
4. Mistura por cenário: PESO_PESQUISAS do cenário vem das pesquisas, o resto do estrutural.
5. Geografia: cada UF, município do MA e seção de Tuntum parte do próprio 1º turno com a transferência sorteada,
   recebe o padrão de "polarização" medido de 2022 (1º→2º turno por UF), o recorte regional do Datafolha (meio
   caminho) e ruído do tamanho medido em 2022; depois é calibrada em logit para bater com o nível acima
   (Brasil → UF → município → seção).

Saídas em segundo_turno/resultados/.
Rodar: python segundo_turno/modelo_2t.py   (MODELO_DATA_CORTE=AAAA-MM-DD para reproduzir um corte)
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "nacional"))
from agregadores import rodar_ensemble  # noqa: E402
from historico import carregar as carregar_historico  # noqa: E402
from validacao_modelo import escrever_json  # noqa: E402

D, RES = AQUI / "dados", AQUI / "resultados"
RES.mkdir(exist_ok=True)
T1 = D / "tse_1t_2026"
ELEICAO = pd.Timestamp("2026-10-25")
INICIO_2T = pd.Timestamp("2026-10-03")  # campo que termina antes disso é pesquisa de 1º turno
SEMENTE, N_SIM, N_GEO = 42, 20_000, 4_000
PESO_PESQUISAS = 0.6       # fração dos cenários que parte das pesquisas (o resto, do estrutural)
PESO_ERRO_2026 = 0.5       # chance de o erro sorteado vir do 1º turno de 2026 (o resto, dos 2º turnos 2006–2022)
CRUZA_MAX = 0.02           # troca máxima entre as bases de Lula e Flávio do 1º para o 2º turno
OUTROS = ["cury", "renan", "caiado", "zema", "outros"]
REGIAO = {"AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
          "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste", "PE": "Nordeste",
          "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste", "DF": "Centro-Oeste", "GO": "Centro-Oeste",
          "MT": "Centro-Oeste", "MS": "Centro-Oeste", "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste",
          "SP": "Sudeste", "PR": "Sul", "RS": "Sul", "SC": "Sul", "ZZ": "Exterior"}


def data_corte():
    return pd.Timestamp(os.environ.get("MODELO_DATA_CORTE", pd.Timestamp.now(tz="America/Sao_Paulo").date()))


def checar(cond, msg):
    if not cond:
        raise ValueError(msg)


# ------------------------------------------------------------------ dados oficiais do 1º turno (TSE)
def carregar_1t():
    uf = pd.read_csv(T1 / "presidente_1t_uf.csv")
    mun = pd.read_csv(T1 / "presidente_1t_ma_municipios.csv", dtype={"cd_tse": str})
    sec = pd.read_csv(T1 / "presidente_1t_tuntum_secoes.csv", dtype={"zona": str, "secao": str})
    cands = ["lula", "flavio"] + OUTROS
    for nome, df in (("UF", uf), ("municípios", mun)):
        checar((df[cands].sum(axis=1) == df.validos).all(), f"1º turno {nome}: soma dos candidatos ≠ válidos")
    br = uf[uf.abrangencia == "br"].iloc[0]
    partes = uf[uf.abrangencia != "br"]
    checar((partes[cands + ["validos"]].sum() == br[cands + ["validos"]]).all(), "UFs + exterior ≠ Brasil")
    ma = uf[uf.abrangencia == "ma"].iloc[0]
    checar((mun[cands + ["validos"]].sum() == ma[cands + ["validos"]]).all(), "municípios ≠ total do MA")
    tun = mun[mun.cd_tse == "09393"].iloc[0]
    checar(sec[["lula", "flavio", "validos"]].sum().tolist() == [tun.lula, tun.flavio, tun.validos],
           "seções de Tuntum ≠ total do município")
    uf = partes.assign(uf=partes.abrangencia.str.upper()).reset_index(drop=True)
    uf["regiao"] = uf.uf.map(REGIAO)
    return uf, mun, sec, br


# ------------------------------------------------------------------ pesquisas do 2º turno
def pesquisas(corte):
    p = pd.read_csv(D / "pesquisas_2t_2026.csv")
    p = p[p.status == "confirmada"].copy()
    p["inicio"], p["fim"] = pd.to_datetime(p.inicio), pd.to_datetime(p.fim)
    p = p[(p.fim >= INICIO_2T) & (p.fim <= corte)]
    checar(not p.registro_tse.duplicated().any(), "pesquisa repetida (mesmo registro no TSE)")
    soma = p.lula_validos + p.flavio_validos
    checar(soma.between(99, 101).all(), "válidos de Lula + Flávio devem somar 100")
    p["lula_2p"] = 100 * p.lula_validos / soma
    p["meio"] = p.inicio + (p.fim - p.inicio) / 2
    p["dias_antes"] = (ELEICAO - p.meio).dt.days
    p["n"] = p.amostra.astype(float)
    checar(len(p) >= 4, "são necessárias ao menos 4 pesquisas de 2º turno")
    return p.sort_values("meio").reset_index(drop=True)


def erro_1t_2026():
    """Erro de cada instituto no 1º turno de 2026, na disputa direta (margem Lula − Flávio, pontos):
    última pesquisa confirmada de cada instituto até a véspera × resultado oficial."""
    p = pd.read_csv(RAIZ / "nacional" / "dados" / "pesquisas_presidente.csv")
    p = p[(p.turno == 1) & (p.status == "confirmada")].copy()
    p["fim"] = pd.to_datetime(p.fim)
    p = p[(p.fim >= "2026-09-15") & (p.fim <= "2026-10-03")]
    for c in ("lula", "flavio"):
        p[c] = pd.to_numeric(p[c].astype(str).str.replace(",", "."), errors="coerce")
    p = p.dropna(subset=["lula", "flavio"]).sort_values("fim").groupby("instituto").tail(1)
    real = 100 * 53_879_538 / (53_879_538 + 56_104_503)  # TSE, 1º turno (válidos)
    p["erro_margem"] = 2 * (real - 100 * p.lula / (p.lula + p.flavio))
    return p[["instituto", "fim", "lula", "flavio", "erro_margem"]].reset_index(drop=True), real


# ------------------------------------------------------------------ transferência dos demais candidatos
def transferencia():
    t = pd.read_csv(D / "transferencia_2t.csv")
    t["decide"] = (t.lula + t.flavio) / 100                 # quem escolhe um dos dois
    t["lula_entre"] = t.lula / (t.lula + t.flavio)          # Lula entre os que escolhem
    t["peso"] = np.sqrt(t.amostra) * np.where(t.instituto == "Quaest", 0.5, 1.0)  # subamostras Quaest ~2%
    mapa = {"cury": "cury", "renan": "renan", "caiado": "caiado", "zema": "outros", "outros": "outros"}
    tab = {}
    for c in OUTROS:
        g = t[t.eleitor_1t == mapa[c]]
        tab[c] = {"lula_entre": float(np.average(g.lula_entre, weights=g.peso)),
                  "decide": float(np.average(g.decide, weights=g.peso)),
                  "dispersao": float(max(g.lula_entre.std(ddof=0) if len(g) > 1 else 0.0, 0.06)),
                  "fontes": sorted(g.instituto.unique())}
    return tab


def sortear_transferencia(tab, rng, n):
    """Por cenário: fração de Lula entre os que escolhem e fração que escolhe, para cada grupo de eleitores."""
    out = {}
    for c, v in tab.items():
        lula = np.clip(rng.normal(v["lula_entre"], v["dispersao"], n), 0.05, 0.95)
        decide = np.clip(rng.normal(v["decide"], 0.08, n), 0.4, 1.0)
        out[c] = (lula, decide)
    return out


def parcela_estrutural(L1, F1, O, tr, cruza_l, cruza_f):
    """Lula nos válidos do 2º turno a partir dos votos do 1º turno.
    L1, F1: (unidades,); O: dict candidato → (unidades,); tr: dict → ((sims,), (sims,)); cruza: (sims,).
    Retorna (sims, unidades) com a parcela de Lula e o total de válidos esperado."""
    L1, F1 = np.asarray(L1, float)[None, :], np.asarray(F1, float)[None, :]
    lula = L1 * (1 - cruza_l[:, None]) + F1 * cruza_f[:, None]
    total = L1 + F1
    for c, (frac, decide) in tr.items():
        o = np.asarray(O[c], float)[None, :]
        lula = lula + o * decide[:, None] * frac[:, None]
        total = total + o * decide[:, None]
    return lula / total, total


def calibrar(base_logit, alvo, pesos):
    """Desloca o logit de cada cenário para que a média ponderada das unidades bata com o alvo (sims,)."""
    w = pesos / pesos.sum(axis=-1, keepdims=True)
    c = np.zeros(base_logit.shape[0])
    for _ in range(40):
        s = expit(base_logit + c[:, None])
        c += logit(alvo) - logit(np.clip((s * w).sum(axis=1), 1e-6, 1 - 1e-6))
    out = expit(base_logit + c[:, None])
    checar(np.allclose((out * w).sum(axis=1), alvo, atol=1e-6), "calibração não convergiu")
    return out


def polarizacao_2022():
    """Quanto o 2º turno de 2022 'esticou' a geografia do 1º turno por UF (coeficiente em logit) e o ruído
    restante. Transferência única ajustada aos dados; não usa nada de 2026."""
    b = pd.read_csv(RAIZ / "nacional" / "dados" / "base_ufs.csv")
    L1, B1 = b.lula22_1t * b.validos22_1t / 100, b.bolsonaro22_1t * b.validos22_1t / 100
    O, real, w = b.validos22_1t - L1 - B1, b.lula22_2t / 100, b.validos22_2t.values
    melhor = None
    for t in np.linspace(0, 1, 201):
        s = (L1 + t * O) / (L1 + B1 + O)
        x = (logit(s) - np.average(logit(s), weights=w)).values
        r = (logit(real) - logit(s)).values
        X = np.column_stack([np.ones_like(x), x])
        beta = np.linalg.lstsq(X * np.sqrt(w)[:, None], r * np.sqrt(w), rcond=None)[0]
        res = r - X @ beta
        sd = float(np.sqrt(np.average(res ** 2, weights=w)))
        if melhor is None or sd < melhor["ruido_logit"]:
            se = sd / np.sqrt(w.sum() / w.max()) / max(np.sqrt(np.average((x - np.average(x, weights=w)) ** 2, weights=w)), 1e-6)
            melhor = {"transferencia": float(t), "k": float(beta[1]), "k_ep": float(se), "ruido_logit": sd}
    return melhor


def resumo(x):
    return [round(float(np.percentile(x, q)), 2) for q in (10, 50, 90)]


def rodar(corte=None, salvar=True):
    corte = min(corte or data_corte(), ELEICAO - pd.Timedelta(days=1))
    rng = np.random.default_rng(SEMENTE)
    uf, mun, sec, br = carregar_1t()

    # ---------------- 1) pesquisas
    p = pesquisas(corte)
    mods, efeitos, _, ens = rodar_ensemble(p.lula_2p.values, p, rng, ELEICAO)
    share_pesq = rng.normal(ens["est"], ens["dp"], N_SIM) / 100

    # ---------------- 3) erro das pesquisas (margem Lula − Flávio, pontos; + = subestimaram Lula)
    h = carregar_historico(RAIZ / "nacional" / "dados" / "erro_historico_presidente.csv")
    e_2t = h[h.turno == 2].groupby("ano").erro_margem.mean().values
    e26, real_1t = erro_1t_2026()
    de_2026 = rng.random(N_SIM) < PESO_ERRO_2026
    sorteio = np.where(de_2026, rng.choice(e26.erro_margem.values, N_SIM), rng.choice(e_2t, N_SIM))
    persist = rng.uniform(0, 1, N_SIM)
    erro = persist * sorteio + rng.normal(0, 0.6 * e_2t.std(ddof=1), N_SIM)
    share_pesq_corr = share_pesq + erro / 200

    # ---------------- 2) estrutural: votos do 1º turno + transferência medida
    tab = transferencia()
    tr = sortear_transferencia(tab, rng, N_SIM)
    cruza_l, cruza_f = rng.uniform(0, CRUZA_MAX, N_SIM), rng.uniform(0, CRUZA_MAX, N_SIM)
    O_br = {c: [br[c]] for c in OUTROS}
    s_struct, _ = parcela_estrutural([br.lula], [br.flavio], O_br, tr, cruza_l, cruza_f)
    comparecimento = rng.normal(0, 0.010, N_SIM)  # quem volta a votar no 2º turno (diferença entre as bases)
    share_struct = s_struct[:, 0] + comparecimento

    # ---------------- 4) mistura
    usa_pesq = rng.random(N_SIM) < PESO_PESQUISAS
    L2 = np.clip(np.where(usa_pesq, share_pesq_corr, share_struct), 0.30, 0.70)
    checar(np.isfinite(L2).all(), "simulação com valores inválidos")
    checar(not (L2 == 0.5).any(), "empate exato sem regra de desempate")

    # sensibilidade
    sens = {
        "so_pesquisas_sem_correcao": {"lula_p50": round(100 * float(np.median(share_pesq)), 2),
                                      "prob_lula": round(float((share_pesq > .5).mean()), 3)},
        "so_pesquisas_com_correcao": {"lula_p50": round(100 * float(np.median(share_pesq_corr)), 2),
                                      "prob_lula": round(float((share_pesq_corr > .5).mean()), 3)},
        "so_estrutural": {"lula_p50": round(100 * float(np.median(share_struct)), 2),
                          "prob_lula": round(float((share_struct > .5).mean()), 3)},
    }
    alerta = np.clip(share_pesq + float(e26.erro_margem.mean()) / 200 + rng.normal(0, .005, N_SIM), .3, .7)
    sens["alerta_vies_1t_se_repete"] = {"lula_p50": round(100 * float(np.median(alerta)), 2),
                                        "prob_lula": round(float((alerta > .5).mean()), 3)}

    # ---------------- 5) geografia: UF (Brasil) → município (MA) → seção (Tuntum)
    pol = polarizacao_2022()
    sel = rng.choice(N_SIM, N_GEO, replace=False)
    trs = {c: (v[0][sel], v[1][sel]) for c, v in tr.items()}
    cl, cf = cruza_l[sel], cruza_f[sel]
    k = rng.normal(pol["k"], max(pol["k_ep"], 0.05), N_GEO)[:, None]

    def base_geo(df, ruido_sd):
        s, tot = parcela_estrutural(df.lula.values, df.flavio.values, {c: df[c].values for c in OUTROS}, trs, cl, cf)
        lg = logit(np.clip(s, 1e-4, 1 - 1e-4))
        media = (lg * tot).sum(axis=1, keepdims=True) / tot.sum(axis=1, keepdims=True)
        return lg + k * (lg - media) + rng.normal(0, 1, lg.shape) * ruido_sd, tot

    # recorte regional do Datafolha (meio caminho, como no modelo do 1º turno)
    reg = pd.read_csv(D / "pesquisas_2t_regioes.csv")
    lg_uf, tot_uf = base_geo(uf, pol["ruido_logit"])
    s_mediano = expit(np.median(lg_uf, axis=0))
    w_uf = np.median(tot_uf, axis=0)
    nac_pesq = 49 / 100
    ajuste, ep_uf = np.zeros(len(uf)), np.full(len(uf), 0.05)
    regionais = {}
    for _, r in reg.iterrows():
        regs = r.recorte.split("+")
        m = uf.regiao.isin(regs).values
        nosso = np.average(s_mediano[m], weights=w_uf[m])
        nosso_nac = np.average(s_mediano[uf.uf != "ZZ"], weights=w_uf[uf.uf != "ZZ"])
        pr = r.lula_validos / 100
        gap = (logit(pr) - logit(nac_pesq)) - (logit(nosso) - logit(nosso_nac))
        n_reg = r.amostra * w_uf[m].sum() / w_uf.sum()
        ep = float(np.sqrt(1.6 / (n_reg * pr * (1 - pr))))
        ajuste[m], ep_uf[m] = 0.5 * gap, ep
        regionais[r.recorte] = {"datafolha": float(r.lula_validos), "estrutural": round(100 * float(nosso), 1),
                                "ajuste_logit": round(0.5 * float(gap), 3), "ep": round(ep, 3)}
    # mesmo sorteio para todas as UFs de uma região (o recorte é um só número por região)
    regioes = sorted(uf.regiao.unique())
    z = rng.normal(0, 1, (N_GEO, len(regioes)))
    z_uf = z[:, [regioes.index(r_) for r_ in uf.regiao]]
    uf_l2 = calibrar(lg_uf + ajuste[None, :] + 0.5 * ep_uf[None, :] * z_uf, L2[sel], tot_uf)

    # Maranhão por município, calibrado no MA de cada cenário
    i_ma = int(np.flatnonzero(uf.uf.values == "MA")[0])
    tam = np.clip(np.sqrt(np.median(mun.validos) / mun.validos.values), 0.5, 3.0)
    lg_mun, tot_mun = base_geo(mun, 0)
    lg_mun = lg_mun + rng.normal(0, 1, lg_mun.shape) * pol["ruido_logit"] * 1.5 * tam[None, :]
    mun_l2 = calibrar(lg_mun, uf_l2[:, i_ma], tot_mun)

    # Tuntum por seção, calibrado no município de cada cenário
    i_tun = int(np.flatnonzero(mun.cd_tse.values == "09393")[0])
    lg_sec, tot_sec = base_geo(sec, 0)
    p_sec = np.clip(expit(lg_sec), .02, .98)
    lg_sec = lg_sec + rng.normal(0, 1, lg_sec.shape) * (
        np.sqrt(1 / (sec.validos.values[None, :] * p_sec * (1 - p_sec))) + 0.03)
    sec_l2 = calibrar(lg_sec, mun_l2[:, i_tun], tot_sec)

    # ---------------- saídas
    def tabela_unidades(df, sims, tot):
        out = df.copy()
        out["lula_1t_pct"] = (100 * df.lula / df.validos).round(2)
        out["flavio_1t_pct"] = (100 * df.flavio / df.validos).round(2)
        out["lula_2t"] = (100 * np.median(sims, axis=0)).round(2)
        out["lula_2t_p10"] = (100 * np.percentile(sims, 10, axis=0)).round(2)
        out["lula_2t_p90"] = (100 * np.percentile(sims, 90, axis=0)).round(2)
        out["flavio_2t"] = (100 - out.lula_2t).round(2)
        out["prob_lula"] = (sims > .5).mean(axis=0).round(3)
        out["validos_2t_est"] = np.median(tot, axis=0).round()
        out["votos_lula_2t"] = (out.validos_2t_est * out.lula_2t / 100).round()
        out["votos_flavio_2t"] = (out.validos_2t_est - out.votos_lula_2t).round()
        out["saldo_lula_2t"] = out.votos_lula_2t - out.votos_flavio_2t
        out["favorito"] = np.select([out.prob_lula >= .65, out.prob_lula <= .35], ["Lula", "Flávio"], "Indefinido")
        return out

    t_uf = tabela_unidades(uf, uf_l2, tot_uf)
    t_mun = tabela_unidades(mun, mun_l2, tot_mun)
    t_sec = tabela_unidades(sec, sec_l2, tot_sec)
    loc = t_sec.groupby("local", as_index=False).agg(
        secoes=("secao", "count"), aptos=("aptos", "sum"), validos=("validos", "sum"), lula=("lula", "sum"),
        flavio=("flavio", "sum"), votos_lula_2t=("votos_lula_2t", "sum"), votos_flavio_2t=("votos_flavio_2t", "sum"))
    loc["lula_1t_pct"] = (100 * loc.lula / loc.validos).round(2)
    loc["lula_2t"] = (100 * loc.votos_lula_2t / (loc.votos_lula_2t + loc.votos_flavio_2t)).round(2)

    vence_l = L2 > .5
    sim = {
        "gerado_em": pd.Timestamp.now(tz="America/Sao_Paulo").isoformat(timespec="minutes"),
        "data_corte": str(corte.date()), "eleicao": str(ELEICAO.date()), "n_cenarios": N_SIM,
        "resultado": {"prob_lula": round(float(vence_l.mean()), 3), "prob_flavio": round(float(1 - vence_l.mean()), 3),
                      "lula_validos_p10_p50_p90": [round(100 * v, 2) for v in np.percentile(L2, [10, 50, 90])],
                      "flavio_validos_p50": round(100 * (1 - float(np.median(L2))), 2),
                      "votos_lula_p50": int(np.median(L2) * float(t_uf.validos_2t_est.sum())),
                      "votos_flavio_p50": int((1 - np.median(L2)) * float(t_uf.validos_2t_est.sum())),
                      "validos_esperados": int(t_uf.validos_2t_est.sum())},
        "componentes": {
            "pesquisas": {"n": int(len(p)), "institutos": sorted(p.instituto.unique()), "ensemble": ens,
                          "modelos": mods, "efeito_instituto": efeitos,
                          "primeira": str(p.fim.min().date()), "ultima": str(p.fim.max().date())},
            "erro": {"historico_2t_por_eleicao": dict(zip(map(str, sorted(h[h.turno == 2].ano.unique())),
                                                          [round(float(x), 2) for x in e_2t])),
                     "erro_1t_2026_por_instituto": {r.instituto: round(float(r.erro_margem), 2)
                                                    for r in e26.itertuples()},
                     "erro_1t_2026_medio": round(float(e26.erro_margem.mean()), 2),
                     "lula_1t_real_disputa_direta": round(real_1t, 2),
                     "peso_erro_2026": PESO_ERRO_2026, "persistencia": "uniforme de 0% a 100%",
                     "aplicado_medio_pts_lula": round(float(np.mean(erro)) / 2, 2)},
            "estrutural": {"transferencia": tab, "troca_entre_bases_max": CRUZA_MAX,
                           "lula_p10_p50_p90": [round(100 * v, 2) for v in np.percentile(share_struct, [10, 50, 90])]},
            "peso_pesquisas": PESO_PESQUISAS,
        },
        "sensibilidade": sens,
        "geografia": {"polarizacao_2022": pol, "regioes_datafolha": regionais},
        "regioes": {r: round(100 * float(g.votos_lula_2t.sum() / g.validos_2t_est.sum()), 2)
                    for r, g in t_uf.groupby("regiao")},
        "maranhao": {"prob_lula": round(float((uf_l2[:, i_ma] > .5).mean()), 3),
                     "lula_p10_p50_p90": resumo(100 * uf_l2[:, i_ma]),
                     "municipios_favorito_lula": int((t_mun.favorito == "Lula").sum()),
                     "municipios_favorito_flavio": int((t_mun.favorito == "Flávio").sum()),
                     "municipios_indefinidos": int((t_mun.favorito == "Indefinido").sum())},
        "tuntum": {"lula_p10_p50_p90": resumo(100 * mun_l2[:, i_tun]), "secoes": int(len(sec)),
                   "locais": int(sec.local.nunique()),
                   "votos_lula_p50": int(t_sec.votos_lula_2t.sum()), "votos_flavio_p50": int(t_sec.votos_flavio_2t.sum())},
        "limites": ["Probabilidades descrevem as premissas do modelo, não certeza.",
                    "Cruzamentos de transferência têm subamostras pequenas.",
                    "O erro das pesquisas pode se repetir mais ou menos do que no 1º turno."],
    }
    json.dumps(sim, allow_nan=False)
    if salvar:
        p.to_csv(RES / "pesquisas_2t_tratadas.csv", index=False)
        t_uf.to_csv(RES / "ufs_2t.csv", index=False)
        t_mun.to_csv(RES / "ma_municipios_2t.csv", index=False)
        t_sec.to_csv(RES / "tuntum_secoes_2t.csv", index=False)
        loc.to_csv(RES / "tuntum_locais_2t.csv", index=False)
        np.save(RES / "cenarios_lula_2t.npy", np.round(L2[:5000], 4))
        escrever_json(RES / "simulacao_2t.json", sim)
    return sim


if __name__ == "__main__":
    s = rodar()
    print(json.dumps({k: s[k] for k in ("data_corte", "resultado", "sensibilidade", "regioes", "maranhao", "tuntum")},
                     ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in s["componentes"].items() if k != "pesquisas"}, ensure_ascii=False, indent=1)[:3000])
    print(json.dumps(s["componentes"]["pesquisas"]["ensemble"]), s["geografia"])
