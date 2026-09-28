"""Motor da apuração ao vivo: baixa resultados parciais do TSE e projeta o resultado final.

Fonte: API pública de divulgação do TSE (resultados.tse.jus.br) — a mesma usada para 2022.
- Nacional (presidente, cargo 1): um arquivo por UF (27) + Brasil.
- Estadual (governador MA, cargo 3): um arquivo por município (217) + estado.

Projeção do resultado final ("agulha"): nas unidades já apuradas mede-se o desvio entre o voto real e a projeção do
modelo (em logit, ponderado pelos votos já contados); esse desvio é aplicado aos votos que faltam em cada unidade.
A incerteza vem de reamostrar as unidades apuradas (bootstrap) + a dispersão dos desvios entre unidades.
"""
import json
import re
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

BASE = "https://resultados.tse.jus.br/oficial"
RAIZ = Path(__file__).resolve().parent.parent
UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ",
       "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
# Modo ensaio (2022): eleições e mapeamento dos candidatos de 2026 para os de 2022
ENSAIO = {"ciclo": "ele2022", "presidente": {1: "544", 2: "545"}, "governador": {1: "546", 2: None}}
ENSAIO_CAND = {"presidente": {"lula": "13", "flavio": "22"}, "governador": {"braide": "20", "orleans": "40"}}
NOMES_2026 = {"presidente": {"lula": ["LULA"], "flavio": ["FLÁVIO BOLSONARO", "FLAVIO BOLSONARO", "FLÁVIO"]},
              "governador": {"braide": ["BRAIDE"], "orleans": ["ORLEANS"]}}


def _num(v):
    try:
        return float(str(v).replace(".", "").replace(",", ".")) if isinstance(v, str) and "," in v else float(v)
    except (TypeError, ValueError):
        return 0.0


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _sem_acento(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()


# ------------------------------------------------------------------ descoberta das eleições de 2026
def descobrir_2026():
    """Lê a configuração pública do TSE e procura as eleições gerais de 2026 (presidente e governador).
    Retorna {"ciclo": "ele2026", "presidente": {1: cod, 2: cod}, "governador": {1: cod, 2: cod}} ou None."""
    manual = RAIZ / "apuracao" / "codigos_2026.json"
    if manual.exists():  # permite fixar os códigos à mão, se necessário
        m = json.loads(manual.read_text(encoding="utf-8"))
        for k in ("presidente", "governador"):
            m[k] = {int(t): c for t, c in m.get(k, {}).items() if c}
        return m
    try:
        cfg = _get(f"{BASE}/comum/config/ele-c.json")
    except Exception:
        return None
    if "2026" not in str(cfg.get("c", "")):
        return None
    achado = {"ciclo": cfg["c"], "presidente": {}, "governador": {}}
    for pl in cfg.get("pl", []):
        for e in pl.get("e", []):
            cargos = {c.get("cd") for a in e.get("abr", []) for c in a.get("cp", [])}
            turno = int(e.get("t", 1))
            if "1" in cargos:
                achado["presidente"][turno] = e["cd"]
            if "3" in cargos:
                achado["governador"][turno] = e["cd"]
    return achado if achado["presidente"] or achado["governador"] else None


# ------------------------------------------------------------------ leitura dos arquivos
def _url_simplificado(ciclo, ele, uf, cargo):
    return f"{BASE}/{ciclo}/{ele}/dados-simplificados/{uf.lower()}/{uf.lower()}-c{cargo:04d}-e{int(ele):06d}-r.json"


def _url_municipio(ciclo, ele, uf, cdmun, cargo):
    return f"{BASE}/{ciclo}/{ele}/dados/{uf.lower()}/{uf.lower()}{cdmun}-c{cargo:04d}-e{int(ele):06d}-v.json"


def ler_total(ciclo, ele, abrang, cargo):
    """Total de uma abrangência (uf ou 'br'): % apurado, válidos e votos por número de candidato + nomes."""
    t = _get(_url_simplificado(ciclo, ele, abrang, cargo))
    return {"pst": _num(t.get("pst", "0")), "vv": _num(t.get("vv", 0)),
            "votos": {c["n"]: _num(c["vap"]) for c in t.get("cand", [])},
            "nomes": {c["n"]: c.get("nm", "") for c in t.get("cand", [])}}


def ler_municipio(ciclo, ele, uf, cdmun, cargo):
    t = _get(_url_municipio(ciclo, ele, uf, cdmun, cargo))
    a = next(x for x in t["abr"] if x.get("tpabr") == "MU")
    return {"cd": cdmun, "pst": _num(a.get("pst", "0")), "vv": _num(a.get("vv", 0)),
            "votos": {c["n"]: _num(c["vap"]) for c in a.get("cand", [])}}


def identificar_numeros(nomes, disputa):
    """Descobre o número de urna de cada candidato pelo nome publicado pelo TSE."""
    achados = {}
    for chave, padroes in NOMES_2026[disputa].items():
        for n, nm in nomes.items():
            if any(_sem_acento(p) in _sem_acento(nm) for p in padroes):
                achados[chave] = n
                break
    return achados


def baixar(disputa, turno, ensaio=False):
    """Baixa a apuração atual. Retorna (tabela por unidade, total geral, números dos candidatos, info)."""
    if ensaio:
        ciclo, ele = ENSAIO["ciclo"], ENSAIO[disputa][turno]
    else:
        cod = descobrir_2026()
        if not cod or not cod.get(disputa, {}).get(turno):
            return None, None, None, {"erro": "Os códigos da eleição de 2026 ainda não foram publicados pelo TSE."}
        ciclo, ele = cod["ciclo"], cod[disputa][turno]
    cargo = 1 if disputa == "presidente" else 3
    if disputa == "presidente":
        geral = ler_total(ciclo, ele, "br", cargo)
        with ThreadPoolExecutor(12) as ex:
            partes = list(ex.map(lambda u: (u, ler_total(ciclo, ele, u, cargo)), UFS))
        unidades = pd.DataFrame([{"unidade": u, "pst": d["pst"], "vv": d["vv"], **{f"v_{k}": v for k, v in d["votos"].items()}}
                                 for u, d in partes])
    else:
        geral = ler_total(ciclo, ele, "ma", cargo)
        mun = pd.read_csv(RAIZ / "resultados" / "municipios_previsao.csv")
        cods = mun.CD_MUNICIPIO.astype(int).map(lambda c: f"{c:05d}")

        def pega(c):
            try:
                return ler_municipio(ciclo, ele, "ma", c, cargo)
            except Exception:
                return {"cd": c, "pst": 0.0, "vv": 0.0, "votos": {}}

        with ThreadPoolExecutor(16) as ex:
            partes = list(ex.map(pega, cods))
        unidades = pd.DataFrame([{"unidade": int(d["cd"]), "pst": d["pst"], "vv": d["vv"],
                                  **{f"v_{k}": v for k, v in d["votos"].items()}} for d in partes])
    numeros = ENSAIO_CAND[disputa] if ensaio else identificar_numeros(geral["nomes"], disputa)
    return unidades.fillna(0), geral, numeros, {"ciclo": ciclo, "eleicao": ele, "ensaio": ensaio}


def simular_parcial(unidades, fracao, semente=0):
    """Modo ensaio: transforma o resultado final de 2022 numa apuração parcial (cada unidade num ritmo diferente)."""
    rng = np.random.default_rng(semente)
    u = unidades.copy()
    ritmo = np.clip(fracao * rng.lognormal(0, 0.6, len(u)), 0, 1)
    ritmo[rng.random(len(u)) > min(1.0, fracao * 1.6)] = 0  # parte das unidades ainda sem nenhuma seção
    for c in [c for c in u.columns if c.startswith("v_")] + ["vv"]:
        u[c] = u[c] * ritmo
    u["pst"] = 100 * ritmo
    return u


# ------------------------------------------------------------------ projeção do resultado final
def projetar(unidades, previsao, numeros, cand_a, cand_b, col_prev_a, col_prev_b, col_validos, chave_prev,
             turno=1, n_boot=3000, semente=0):
    """Compara a apuração com a projeção e estima o resultado final de cand_a e cand_b (% dos válidos)."""
    rng = np.random.default_rng(semente)
    na, nb = numeros.get(cand_a), numeros.get(cand_b)
    d = previsao.merge(unidades, left_on=chave_prev, right_on="unidade", how="left").fillna(
        {"pst": 0, "vv": 0})
    va = d.get(f"v_{na}", pd.Series(0, index=d.index)).fillna(0)
    vb = d.get(f"v_{nb}", pd.Series(0, index=d.index)).fillna(0)
    d["contado_a"], d["contado_b"], d["contado_vv"] = va, vb, d.vv
    d["real_a"] = np.where(d.vv > 0, 100 * va / d.vv.replace(0, np.nan), np.nan)
    d["real_b"] = np.where(d.vv > 0, 100 * vb / d.vv.replace(0, np.nan), np.nan)
    d["prev_a"], d["prev_b"] = d[col_prev_a], d[col_prev_b]
    d["desvio_a"] = d.real_a - d.prev_a
    d["desvio_b"] = d.real_b - d.prev_b
    # votos válidos que faltam em cada unidade
    esperado = d[col_validos].astype(float)
    falta_pst = np.where(d.pst > 0, d.vv * (100 - d.pst) / d.pst.clip(lower=0.01), esperado)
    d["falta"] = np.clip(np.where(d.pst >= 100, 0, np.minimum(falta_pst, np.maximum(esperado - d.vv, 0) * 1.5 + 1)), 0, None)

    ap = d[(d.vv > 50) & (d.real_a > 0) & (d.real_b > 0)]
    total_contado = d.vv.sum()
    res = {"apurado_pct_votos": float(100 * total_contado / max(total_contado + d.falta.sum(), 1)),
           "unidades_com_votos": int((d.vv > 0).sum()), "unidades": int(len(d))}
    if len(ap) < 3:
        res["sem_dados"] = True
        return d, res
    lg = lambda x: logit(np.clip(x / 100, 1e-4, 1 - 1e-4))
    swing_a = (lg(ap.real_a) - lg(ap.prev_a)).values
    swing_b = (lg(ap.real_b) - lg(ap.prev_b)).values
    w = ap.vv.values
    disp_a, disp_b = np.std(swing_a), np.std(swing_b)
    # no início da apuração as primeiras unidades não representam bem o resto: alarga a incerteza
    # (calibrado em apurações simuladas de 2022: faixa de 80% contém o real em ~80% das vezes)
    frac_contado = total_contado / max(total_contado + d.falta.sum(), 1)
    alarga = 1 + 0.6 * (1 - frac_contado) ** 3
    la, lb = lg(d.prev_a).values, lg(d.prev_b).values
    falta, tot = d.falta.values, total_contado + d.falta.sum()
    ca, cb = d.contado_a.sum(), d.contado_b.sum()
    idx = rng.choice(len(ap), (n_boot, len(ap)), p=w / w.sum())
    sa = swing_a[idx].mean(axis=1)[:, None] * 1.0
    sb = swing_b[idx].mean(axis=1)[:, None] * 1.0
    # cada unidade que falta tem o seu próprio desvio (dispersão observada entre as unidades já apuradas)
    ra = rng.normal(0, (disp_a + 0.02) * alarga, (n_boot, len(d)))
    rb = rng.normal(0, (disp_b + 0.02) * alarga, (n_boot, len(d)))
    choque = rng.normal(0, 0.06 * (alarga - 1), (n_boot, 1))  # incerteza comum ainda não vista nas urnas
    fa = 100 * (ca + (falta * expit(la + sa + ra + choque)).sum(axis=1)) / tot
    fb = 100 * (cb + (falta * expit(lb + sb + rb - choque)).sum(axis=1)) / tot
    res.update({
        "atual_a": float(100 * d.contado_a.sum() / max(total_contado, 1)),
        "atual_b": float(100 * d.contado_b.sum() / max(total_contado, 1)),
        "final_a": [float(np.percentile(fa, k)) for k in (10, 50, 90)],
        "final_b": [float(np.percentile(fb, k)) for k in (10, 50, 90)],
        "prob_a_na_frente": float((fa > fb).mean()),
        "prob_a_50": float((fa >= 50).mean()), "prob_b_50": float((fb >= 50).mean()),
        "desvio_medio_a": float(np.average(ap.desvio_a, weights=w)),
        "desvio_medio_b": float(np.average(ap.desvio_b, weights=w)),
        "previsto_a": float(np.average(d.prev_a, weights=esperado)),
        "previsto_b": float(np.average(d.prev_b, weights=esperado)),
    })
    return d, res
