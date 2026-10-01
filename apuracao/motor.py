"""Motor da apuração ao vivo: baixa resultados parciais do TSE e projeta o resultado final.

Fonte: API pública de divulgação do TSE (resultados.tse.jus.br). Leiaute conferido com a documentação técnica do
TSE para 2026 ("modelo de dados bastante semelhante ao da eleição anterior") e com arquivos reais:
- estado/Brasil: dados-simplificados/<uf>/<uf>-c<cargo>-e<eleição>-r.json  (pst, vv, cand[n, nm, vap, st])
- município:     dados/<uf>/<uf><mun 5 dígitos>-c<cargo>-e<eleição>-u.json  (s.pst, v.vv, carg[].agr[].par[].cand[])
Códigos 2026 (TSE): pleito 3220; eleição federal 6257 (presidente) e estadual 6259 (governador, deputados).
Ambiente de teste do TSE (simulado): TSE_AMBIENTE=simulado → resultados-sim.tse.jus.br (eleições 21270 / 21272).
- Nacional (presidente, cargo 1): um arquivo por UF (27) + Brasil.
- Estadual (governador MA, cargo 3): um arquivo por município (217) + estado.
- Assembleia (deputado estadual MA, cargo 7): mesmo formato; acompanha só Bruna Pessoa, Abigail Cunha e Eric Costa,
  em votos (não em %), comparando com a projeção do modelo da Bruna (resumo em apuracao/deputados_previsao.csv; o painel
  estratégico dela fica só no app próprio, bruna_api_webapp_v2_mapa).

Projeção do resultado final ("agulha"): nas unidades já apuradas mede-se o desvio entre o voto real e a projeção do
modelo (em logit, ponderado pelos votos já contados); esse desvio é aplicado aos votos que faltam em cada unidade.
A incerteza vem de reamostrar as unidades apuradas (bootstrap) + a dispersão dos desvios entre unidades.
"""
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

AMBIENTE = os.environ.get("TSE_AMBIENTE", "oficial").strip().lower()
BASES = {"oficial": "https://resultados.tse.jus.br/oficial",
         "simulado": "https://resultados-sim.tse.jus.br/simulado/simulado2026"}
BASE = BASES.get(AMBIENTE, BASES["oficial"])
# códigos publicados pelo TSE (página "Informações técnicas sobre a divulgação de resultados 2026"); usados quando o
# config ainda não lista a eleição (em 30/09 o config oficial ainda trazia só o ciclo de 2024)
CODIGOS_2026 = {"oficial": {"ciclo": "ele2026", "presidente": {1: "6257"}, "governador": {1: "6259"},
                            "deputado": {1: "6259"}},
                "simulado": {"ciclo": "ele2026", "presidente": {1: "21270"}, "governador": {1: "21272"},
                             "deputado": {1: "21272"}}}
RAIZ = Path(__file__).resolve().parent.parent
UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ",
       "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
# Modo ensaio (2022): eleições e mapeamento dos candidatos de 2026 para os de 2022
ENSAIO = {"ciclo": "ele2022", "presidente": {1: "544", 2: "545"}, "governador": {1: "546", 2: None}}
ENSAIO_CAND = {"presidente": {"lula": "13", "flavio": "22"}, "governador": {"braide": "20", "orleans": "40"}}
NOMES_2026 = {"presidente": {"lula": ["LULA"], "flavio": ["FLÁVIO BOLSONARO", "FLAVIO BOLSONARO", "FLÁVIO"]},
              "governador": {"braide": ["BRAIDE"], "orleans": ["ORLEANS"]},
              # do nome mais específico para o mais genérico (o primeiro que casar vale)
              "deputado": {"bruna": ["BRUNA PESSOA", "BRUNA"], "abigail": ["ABIGAIL CUNHA", "ABIGAIL"],
                           "eric": ["ERIC COSTA", "ERIC"]}}
# números de urna de 2026 (candidaturas deferidas): Bruna Pessoa 15800 (MDB), Abigail Cunha 15200 (MDB),
# Eric Costa 10800 (Republicanos). Se o número não aparecer na lista do TSE, procura pelo nome.
NUMEROS_FIXOS = {"deputado": {"bruna": "15800", "abigail": "15200", "eric": "10800"}}
CARGO = {"presidente": 1, "governador": 3, "deputado": 7}
MUNICIPIOS = {"governador": RAIZ / "resultados" / "municipios_previsao.csv",
              "deputado": RAIZ / "apuracao" / "deputados_previsao.csv"}
REFERENCIAS_ALEMA = {"menor eleito em 2022": 24800, "último eleito da chapa do governo em 2022": 38329,
                     "mediana dos eleitos em 2022": 44068}


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
    """Códigos das eleições de 2026: arquivo manual → config do TSE → códigos publicados pelo TSE.
    Retorna {"ciclo": "ele2026", "presidente": {1: cod, 2: cod}, "governador": {...}, "deputado": {...}, "origem": ...}."""
    manual = RAIZ / "apuracao" / "codigos_2026.json"
    if manual.exists():  # permite fixar os códigos à mão, se necessário
        m = json.loads(manual.read_text(encoding="utf-8"))
        for k in ("presidente", "governador", "deputado"):
            m[k] = {int(t): c for t, c in m.get(k, {}).items() if c}
        if not m["deputado"] and m["governador"].get(1):  # deputados saem na mesma eleição do governador (1º turno)
            m["deputado"] = {1: m["governador"][1]}
        m["origem"] = "codigos_2026.json"
        return m
    achado = {"ciclo": "ele2026", "presidente": {}, "governador": {}, "deputado": {}, "origem": "config do TSE"}
    try:
        cfg = _get(f"{BASE}/comum/config/ele-c.json")
        for pl in cfg.get("pl", []):
            if not str(pl.get("dt", "")).endswith("2026"):
                continue
            for e in pl.get("e", []):
                nome = _sem_acento(e.get("nm", "")).lower()
                if "suplementar" in nome or "consulta" in nome or str(e.get("tp")) in ("4", "7"):
                    continue
                cargos = {str(c.get("cd")) for a in e.get("abr", []) for c in a.get("cp", [])}
                turno = int(e.get("t", 1) or 1)
                for disputa, cargo in (("presidente", "1"), ("governador", "3"), ("deputado", "7")):
                    if cargo in cargos:
                        achado[disputa][turno] = str(e["cd"])
                        if e.get("cdt2") and disputa != "deputado":
                            achado[disputa][2] = str(e["cdt2"])
    except Exception:  # noqa: BLE001  (sem config: usa os códigos publicados)
        pass
    padrao = CODIGOS_2026.get(AMBIENTE, CODIGOS_2026["oficial"])
    for disputa in ("presidente", "governador", "deputado"):
        if not achado[disputa].get(1):
            achado[disputa][1] = padrao[disputa][1]
            achado["origem"] = "códigos publicados pelo TSE (config ainda sem 2026)"
    return achado


# ------------------------------------------------------------------ leitura dos arquivos
def _url_simplificado(ciclo, ele, uf, cargo):
    return f"{BASE}/{ciclo}/{ele}/dados-simplificados/{uf.lower()}/{uf.lower()}-c{cargo:04d}-e{int(ele):06d}-r.json"


def _url_municipio(ciclo, ele, uf, cdmun, cargo):
    return f"{BASE}/{ciclo}/{ele}/dados/{uf.lower()}/{uf.lower()}{cdmun}-c{cargo:04d}-e{int(ele):06d}-u.json"


def _url_total_unificado(ciclo, ele, abrang, cargo):
    return f"{BASE}/{ciclo}/{ele}/dados/{abrang.lower()}/{abrang.lower()}-c{cargo:04d}-e{int(ele):06d}-u.json"


def _ler_unificado(t, cargo):
    """Leiaute unificado (-u.json), usado no município e, em 2026, também no total do estado/Brasil."""
    votos, nomes, situacao = {}, {}, {}
    for carg in t.get("carg", []):
        if str(carg.get("cd")) != str(cargo):
            continue
        for agr in carg.get("agr", []):
            for par in agr.get("par", []):
                for c in par.get("cand", []):
                    n_ = str(c.get("n"))
                    votos[n_] = _num(c.get("vap", 0))
                    nomes[n_] = c.get("nmu") or c.get("nm", "")
                    situacao[n_] = c.get("st", "")
    s_, v_ = t.get("s", {}), t.get("v", {})
    return {"pst": _num(s_.get("pst", "0")), "vv": _num(v_.get("vv", 0)), "votos": votos, "nomes": nomes,
            "situacao": situacao,
            "eleito": {k: _sem_acento(v).lower().startswith("eleit") for k, v in situacao.items()},
            "totalizado": str(t.get("tf", "")).lower() == "s"}


_LEIAUTE = {}  # (ciclo, eleição) → "r" (dados-simplificados) ou "u" (unificado), descoberto na 1ª leitura


def ler_total(ciclo, ele, abrang, cargo):
    """Total de uma abrangência (uf ou 'br'): % apurado, válidos, votos por número de candidato, nomes e situação.
    Tenta o arquivo simplificado (-r); se não existir (404), usa o unificado (-u) e lembra a escolha."""
    chave = (ciclo, str(ele))
    if _LEIAUTE.get(chave) != "u":
        try:
            t = _get(_url_simplificado(ciclo, ele, abrang, cargo))
            _LEIAUTE[chave] = "r"
            return {"pst": _num(t.get("pst", "0")), "vv": _num(t.get("vv", 0)),
                    "votos": {str(c["n"]): _num(c["vap"]) for c in t.get("cand", [])},
                    "nomes": {str(c["n"]): c.get("nm", "") for c in t.get("cand", [])},
                    # situação ao fim da totalização (ex.: "Eleito por QP", "Suplente")
                    "situacao": {str(c["n"]): c.get("st", "") for c in t.get("cand", [])},
                    "eleito": {str(c["n"]): _sem_acento(c.get("st", "")).lower().startswith("eleit")
                               for c in t.get("cand", [])},
                    "totalizado": str(t.get("tf", "")).lower() == "s"}
        except urllib.error.HTTPError as e:
            if e.code != 404 or _LEIAUTE.get(chave) == "r":
                raise
    out = _ler_unificado(_get(_url_total_unificado(ciclo, ele, abrang, cargo)), cargo)
    _LEIAUTE[chave] = "u"
    return out


def ler_municipio(ciclo, ele, uf, cdmun, cargo):
    """Arquivo do município (leiaute -u.json): seções em s, votos em v, candidatos em carg[].agr[].par[].cand[]."""
    d = _ler_unificado(_get(_url_municipio(ciclo, ele, uf, cdmun, cargo)), cargo)
    return {"cd": cdmun, "pst": d["pst"], "vv": d["vv"], "votos": d["votos"], "nomes": d["nomes"]}


def identificar_numeros(nomes, disputa):
    """Descobre o número de urna de cada candidato pelo nome publicado pelo TSE."""
    achados = {}
    for chave, padroes in NOMES_2026[disputa].items():
        fixo = NUMEROS_FIXOS.get(disputa, {}).get(chave)
        if fixo and not nomes:  # lista ainda vazia (antes da apuração): usa o número conhecido
            achados[chave] = fixo
            continue
        if fixo and fixo in nomes:
            achados[chave] = fixo
            continue
        for p in padroes:  # o padrão mais específico primeiro
            n = next((n for n, nm in nomes.items() if _sem_acento(p) in _sem_acento(nm)), None)
            if n:
                achados[chave] = n
                break
    return achados


def baixar(disputa, turno, ensaio=False):
    """Baixa a apuração atual. Retorna (tabela por unidade, total geral, números dos candidatos, info)."""
    if ensaio and disputa == "deputado":
        return ensaio_deputados()
    if ensaio:  # 2022 sem internet: o TSE não serve mais os arquivos de 2022 no ambiente oficial
        return ensaio_2022(disputa, turno)
    cod = descobrir_2026()
    if not cod or not cod.get(disputa, {}).get(turno):
        return None, None, None, {"erro": "Os códigos da eleição de 2026 ainda não foram publicados pelo TSE."}
    ciclo, ele = cod["ciclo"], cod[disputa][turno]
    cargo = CARGO[disputa]
    if disputa == "presidente":
        geral = ler_total(ciclo, ele, "br", cargo)
        with ThreadPoolExecutor(12) as ex:
            partes = list(ex.map(lambda u: (u, ler_total(ciclo, ele, u, cargo)), UFS))
        unidades = pd.DataFrame([{"unidade": u, "pst": d["pst"], "vv": d["vv"], **{f"v_{k}": v for k, v in d["votos"].items()}}
                                 for u, d in partes])
    else:
        geral = ler_total(ciclo, ele, "ma", cargo)
        mun = pd.read_csv(MUNICIPIOS[disputa])
        cods = mun.CD_MUNICIPIO.astype(int).map(lambda c: f"{c:05d}")
        if geral["pst"] <= 0 and not ensaio:  # nada apurado: não pede 217 arquivos (evita bloqueio por excesso de 404)
            unidades = pd.DataFrame({"unidade": cods.astype(int), "pst": 0.0, "vv": 0.0})
            numeros = identificar_numeros(geral["nomes"], disputa)
            return unidades, geral, numeros, {"ciclo": ciclo, "eleicao": ele, "ensaio": ensaio}

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


# ------------------------------------------------------------------ diagnóstico (antes do domingo)
def diagnostico():
    """Testa, deste servidor, cada peça da apuração ao vivo. Retorna lista de (etapa, ok, detalhe)."""
    out = []

    def passo(nome, f):
        try:
            ok, det = f()
        except Exception as e:  # noqa: BLE001
            ok, det = False, f"{type(e).__name__}: {e}"
        out.append((nome, ok, det))
        return ok

    passo("Ambiente", lambda: (True, f"{AMBIENTE} · {BASE}"))
    def _cfg():
        c = _get(f"{BASE}/comum/config/ele-c.json")
        anos = sorted({str(p.get("dt", ""))[-4:] for p in c.get("pl", [])})
        return True, f"gerado {c.get('dg', '?')} {c.get('hg', '')} · pleitos dos anos {', '.join(anos[-3:])}"
    passo("Config do TSE (ele-c.json)", _cfg)
    cod = descobrir_2026()
    passo("Códigos de 2026", lambda: (True, f"presidente {cod['presidente']} · governador {cod['governador']} · "
                                            f"deputado {cod['deputado']} ({cod['origem']})"))
    for disputa, abr in (("presidente", "br"), ("governador", "ma"), ("deputado", "ma")):
        def f(disputa=disputa, abr=abr):
            t = ler_total(cod["ciclo"], cod[disputa][1], abr, CARGO[disputa])
            nums = identificar_numeros(t["nomes"], disputa)
            achou = ", ".join(f"{k}={v}" + ("" if v in t["nomes"] else " (não está na lista)") for k, v in nums.items())
            lei = {"r": "simplificado", "u": "unificado"}.get(_LEIAUTE.get((cod["ciclo"], str(cod[disputa][1]))), "?")
            return True, (f"arquivo OK ({lei}) · {len(t['nomes'])} candidatos · {t['pst']:.2f}% apurado · {achou or '—'}")
        passo(f"Total {disputa} ({abr.upper()})", f)
    mun = pd.read_csv(MUNICIPIOS["deputado"])
    tun = mun[mun.municipio.astype(str).str.lower() == "tuntum"]
    if len(tun):
        cd = f"{int(tun.CD_MUNICIPIO.iloc[0]):05d}"
        passo(f"Município Tuntum ({cd}) · deputado",
              lambda: (True, (lambda m: f"arquivo OK · {len(m['votos'])} candidatos · {m['pst']:.2f}% apurado")(
                  ler_municipio(cod["ciclo"], cod["deputado"][1], "ma", cd, 7))))
        passo(f"Município Tuntum ({cd}) · governador",
              lambda: (True, (lambda m: f"arquivo OK · {len(m['votos'])} candidatos · {m['pst']:.2f}% apurado · "
                              f"Braide/Orleans: {', '.join(n for n, nm in m['nomes'].items() if any(x in _sem_acento(nm).upper() for x in ('BRAIDE', 'ORLEANS'))) or 'não achei pelo nome'}")(
                  ler_municipio(cod["ciclo"], cod["governador"][1], "ma", cd, 3))))
        passo(f"Município Tuntum ({cd}) · nossos deputados",
              lambda: (lambda m: (all(x in m["votos"] for x in NUMEROS_FIXOS["deputado"].values()),
                                  " · ".join(f"{k} {v}: {m['nomes'].get(v, 'NÃO ENCONTRADO')}"
                                             for k, v in NUMEROS_FIXOS["deputado"].items())))(
                  ler_municipio(cod["ciclo"], cod["deputado"][1], "ma", cd, 7)))
    passo("Ensaio (offline, 2022)", lambda: (True, (lambda r: f"presidente {len(r[0])} UFs · governador "
          f"{len(ensaio_2022('governador', 1)[0])} municípios")(ensaio_2022("presidente", 1))))
    return out


def ensaio_2022(disputa, turno):
    """Ensaio offline com o resultado real de 2022 (base do próprio modelo): Lula × Bolsonaro por UF;
    Lahésio (no lugar de Braide) × Brandão (no lugar de Orleans) por município."""
    if disputa == "presidente":
        u = pd.read_csv(RAIZ / "nacional" / "resultados" / "ufs_previsao.csv")
        t = f"{turno}t"
        vv = u[f"validos22_{t}"].astype(float)
        unidades = pd.DataFrame({"unidade": u.uf, "pst": 100.0, "vv": vv, "v_13": vv * u[f"lula22_{t}"] / 100,
                                 "v_22": vv * u[f"bolsonaro22_{t}"] / 100})
    else:
        m = pd.read_csv(MUNICIPIOS["governador"])
        vv = m.validos22.astype(float)
        unidades = pd.DataFrame({"unidade": m.CD_MUNICIPIO.astype(int), "pst": 100.0, "vv": vv,
                                 "v_20": vv * m.lahesio22 / 100, "v_40": vv * m.brandao22 / 100})
    geral = {"pst": 100.0, "vv": float(unidades.vv.sum()), "votos": {}, "nomes": {}, "situacao": {}, "eleito": {}}
    return unidades, geral, ENSAIO_CAND[disputa], {"ciclo": "ele2022", "eleicao": "2022 (offline)", "ensaio": True}


def ensaio_deputados(semente=7):
    """Ensaio offline dos deputados: Abigail e Eric com os votos reais de 2022 por município (TSE); a Bruna não
    disputou em 2022, então os votos dela são a projeção do modelo com um sorteio de ±35% por cidade (fictício)."""
    rng = np.random.default_rng(semente)
    b = pd.read_csv(MUNICIPIOS["deputado"])
    bruna = np.round(b.votos_projetados.fillna(0) * rng.lognormal(0, 0.35, len(b)))
    unidades = pd.DataFrame({"unidade": b.CD_MUNICIPIO.astype(int), "pst": 100.0,
                             "vv": b.total_dep_est_2022.astype(float), "v_15800": bruna,
                             "v_ABIGAIL2022": b.abigail_2022.astype(float), "v_ERIC2022": b.eric_costa_2022.astype(float)})
    geral = {"pst": 100.0, "vv": float(unidades.vv.sum()), "votos": {}, "nomes": {}}
    numeros = {"bruna": "15800", "abigail": "ABIGAIL2022", "eric": "ERIC2022"}
    return unidades, geral, numeros, {"ciclo": "ele2022", "eleicao": "546 (offline)", "ensaio": True}


def projetar_votos(unidades, previsao, numeros, colunas_prev, chave_prev="CD_MUNICIPIO", col_total="total_esperado",
                   n_boot=3000, semente=0, forca_prior=3000):
    """Deputados: projeta o total de VOTOS de cada candidato a partir da apuração parcial.

    Em cada município, "esperado até agora" = projeção do modelo × fração apurada. O ritmo do candidato
    (votos reais ÷ esperado, reamostrado entre os municípios já apurados e puxado para 1 no começo) corrige a projeção
    dos votos que faltam; em município já bem apurado vale o ritmo do próprio município."""
    rng = np.random.default_rng(semente)
    d = previsao.merge(unidades, left_on=chave_prev, right_on="unidade", how="left").fillna({"pst": 0, "vv": 0})
    p = (d.pst.astype(float) / 100).clip(0, 1).values
    tot = d[col_total].astype(float).values
    frac = float((p * tot).sum() / max(tot.sum(), 1))
    alarga = 0.20 * (1 - frac) ** 2  # incerteza comum (desvio em log) que ainda não apareceu nas urnas
    res = {"apurado_pct": 100 * frac, "unidades_com_votos": int((p > 0).sum()), "unidades": int(len(d)), "cand": {}}
    ap = np.flatnonzero(p > 0)
    boot = rng.integers(0, max(len(ap), 1), (n_boot, max(len(ap), 1)))
    peso_proprio = np.clip(p / 0.5, 0, 1)  # com metade das seções apuradas, a própria cidade já basta
    for k, col in colunas_prev.items():
        v = d.get(f"v_{numeros.get(k)}", pd.Series(0.0, index=d.index)).fillna(0).astype(float).values
        prev = d[col].fillna(0).astype(float).values
        esp = prev * p
        d[f"real_{k}"], d[f"prev_{k}"], d[f"esp_{k}"] = v, prev, esp
        d[f"ritmo_{k}"] = np.where(esp > 5, v / np.maximum(esp, 1e-9), np.nan)
        if len(ap):
            r = (v[ap][boot].sum(1) + forca_prior) / (esp[ap][boot].sum(1) + forca_prior)
        else:
            r = np.ones(n_boot)
        proprio = np.where(p > 0, v / np.maximum(p, 1e-6) * (1 - p), 0.0)
        falta = peso_proprio * proprio + (1 - peso_proprio) * prev * (1 - p) * r[:, None]
        choque = rng.lognormal(0, alarga, (n_boot, 1)) if alarga > 0 else 1.0
        final = v.sum() + (falta * choque).sum(1)
        res["cand"][k] = {
            "contado": float(v.sum()), "previsto": float(prev.sum()), "esperado_ate_agora": float(esp.sum()),
            "ritmo": float(v.sum() / esp.sum()) if esp.sum() > 0 else None,
            "final": [float(np.percentile(final, q)) for q in (10, 50, 90)],
            "prob_acima": {nome: float((final >= corte).mean()) for nome, corte in REFERENCIAS_ALEMA.items()},
            "_amostras": final,
        }
    return d, res


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
