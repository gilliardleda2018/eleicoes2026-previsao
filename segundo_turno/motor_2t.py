"""Apuração ao vivo do 2º turno presidencial (25/10/2026): leitura do TSE com fallback em camadas.

Camadas, da preferida à última:
  1. Códigos da eleição: arquivo manual `segundo_turno/codigos_2t.json` → config do TSE (`ele-c.json`, eleição de
     turno 2 com cargo 1, ou `cdt2` da eleição do 1º turno) → códigos publicados pelo TSE (6258, pleito 3221).
  2. Totais (Brasil, UF, exterior e municípios): leiaute unificado `-u.json` → simplificado `-r.json`.
  3. Brasil: se o arquivo do Brasil falhar, soma das 27 UFs + exterior.
  4. Seções (qualquer município do MA, Tuntum por padrão): boletins de urna publicados em `arquivo-urna/` (o BU de
     uma seção totalizada não muda: fica em cache).
  5. Se o TSE não responder, devolve a última leitura boa gravada em disco, marcada como desatualizada.
Ambiente: TSE_AMBIENTE=simulado usa resultados-sim.tse.jus.br (testes do TSE).
Sem streamlit aqui: o painel chama estas funções.
"""
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from . import bu as _bu
except ImportError:  # executado como script ou com a pasta no sys.path
    import bu as _bu

AQUI = Path(__file__).resolve().parent
AMBIENTE = os.environ.get("TSE_AMBIENTE", "oficial").strip().lower()
BASES = {"oficial": "https://resultados.tse.jus.br/oficial",
         "simulado": "https://resultados-sim.tse.jus.br/simulado/simulado2026"}
BASE = BASES.get(AMBIENTE, BASES["oficial"])
CODIGOS = {"oficial": {"ciclo": "ele2026", "eleicao": "6258", "pleito": "3221", "eleicao_1t": "6257", "pleito_1t": "3220"},
           "simulado": {"ciclo": "ele2026", "eleicao": "21271", "pleito": "", "eleicao_1t": "21270", "pleito_1t": ""}}
CAND = {"lula": "13", "flavio": "22"}
UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
       "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO", "ZZ"]
TUNTUM = "09393"
CACHE = Path(os.environ.get("APURACAO_CACHE_DIR", "/tmp/eleicoes2026_2t"))
TENTATIVAS, ESPERA = 3, 0.6


# ------------------------------------------------------------------ rede
def _get(url, timeout=15, binario=False):
    erro = None
    for k in range(TENTATIVAS):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Aggilli Intelligence)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                dados = r.read()
            return dados if binario else json.loads(dados.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):  # arquivo ainda não publicado: não adianta insistir
                raise
            erro = e
        except Exception as e:  # noqa: BLE001  (rede instável no dia da eleição)
            erro = e
        time.sleep(ESPERA * (k + 1))
    raise erro


def _n(v):
    if v is None or v == "":
        return 0.0
    s = str(v)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _gravar(nome, obj):
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = CACHE / (nome + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        tmp.replace(CACHE / nome)
    except OSError:
        pass


def _ler_cache(nome):
    try:
        return json.loads((CACHE / nome).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ códigos
def codigos():
    padrao = dict(CODIGOS.get(AMBIENTE, CODIGOS["oficial"]))
    manual = AQUI / "codigos_2t.json"
    if manual.exists():
        try:
            return dict(padrao, **json.loads(manual.read_text(encoding="utf-8")), origem="codigos_2t.json")
        except ValueError:
            pass
    try:
        cfg = _get(f"{BASE}/comum/config/ele-c.json", timeout=10)
        for pl in cfg.get("pl", []):
            for e in pl.get("e", []):
                cargos = {str(c.get("cd")) for a in e.get("abr", []) for c in a.get("cp", [])}
                if "1" not in cargos:
                    continue
                if str(e.get("t")) == "2":
                    return dict(padrao, eleicao=str(e["cd"]), pleito=str(pl.get("cd", padrao["pleito"])),
                                origem="config do TSE")
                if e.get("cdt2") and str(pl.get("dt", "")).endswith("2026"):
                    padrao.update(eleicao=str(e["cdt2"]))
    except Exception:  # noqa: BLE001
        pass
    return dict(padrao, origem="códigos publicados pelo TSE")


# ------------------------------------------------------------------ totais
def _de_unificado(t):
    votos = {}
    for carg in t.get("carg", []):
        if str(carg.get("cd")) != "1":
            continue
        for agr in carg.get("agr", []):
            for par in agr.get("par", []):
                for c in par.get("cand", []):
                    votos[str(c.get("n"))] = _n(c.get("vap"))
    s, e, v = t.get("s", {}), t.get("e", {}), t.get("v", {})
    return {"pst": _n(s.get("pst")), "secoes": _n(s.get("ts")), "secoes_totalizadas": _n(s.get("st")),
            "eleitorado": _n(e.get("te")), "comparecimento": _n(e.get("c")), "abstencao": _n(e.get("a")),
            "validos": _n(v.get("vv")), "brancos": _n(v.get("vb")), "nulos": _n(v.get("tvn")), "votos": votos,
            "totalizado": str(t.get("tf", "")).lower() == "s", "hora": f"{t.get('dt', '')} {t.get('ht', '')}".strip(),
            "leiaute": "unificado"}


def _de_simplificado(t):
    votos = {str(c["n"]): _n(c.get("vap")) for c in t.get("cand", [])}
    return {"pst": _n(t.get("pst")), "secoes": _n(t.get("s")), "secoes_totalizadas": _n(t.get("st")),
            "eleitorado": _n(t.get("e")), "comparecimento": _n(t.get("c")), "abstencao": _n(t.get("a")),
            "validos": _n(t.get("vv")), "brancos": _n(t.get("vb")), "nulos": _n(t.get("tvn") or t.get("vn")),
            "votos": votos, "totalizado": str(t.get("tf", "")).lower() == "s",
            "hora": f"{t.get('dt', '')} {t.get('ht', '')}".strip(), "leiaute": "simplificado"}


def ler_total(cod, abr):
    """Total de uma abrangência: 'br', uf, 'zz' ou município 'ma09393'. Tenta -u e depois -r."""
    ciclo, ele = cod["ciclo"], cod["eleicao"]
    a = abr.lower()
    pasta = a[:2]
    urls = [(f"{BASE}/{ciclo}/{ele}/dados/{pasta}/{a}-c0001-e{int(ele):06d}-u.json", _de_unificado)]
    if len(a) == 2:
        urls.append((f"{BASE}/{ciclo}/{ele}/dados-simplificados/{a}/{a}-c0001-e{int(ele):06d}-r.json", _de_simplificado))
    erro = None
    for url, f in urls:
        try:
            return f(_get(url))
        except Exception as e:  # noqa: BLE001
            erro = e
    raise erro


def apuracao_nacional(cod=None):
    """Brasil + 27 UFs + exterior. Retorna (tabela por UF, total Brasil, info)."""
    cod = cod or codigos()
    info = {"eleicao": cod["eleicao"], "origem_codigos": cod.get("origem"), "consultado": time.time(), "avisos": []}
    with ThreadPoolExecutor(12) as ex:
        partes = list(ex.map(lambda u: (u, _tenta(lambda: ler_total(cod, u))), UFS))
    linhas = []
    for u, d in partes:
        if d is None:
            info["avisos"].append(f"{u}: sem resposta do TSE")
            continue
        linhas.append({"unidade": u, "pst": d["pst"], "vv": d["validos"], "comparecimento": d["comparecimento"],
                       "eleitorado": d["eleitorado"], "brancos": d["brancos"], "nulos": d["nulos"],
                       **{f"v_{n}": v for n, v in d["votos"].items()}})
    uf = pd.DataFrame(linhas).fillna(0)
    br = _tenta(lambda: ler_total(cod, "br"))
    if br is None and len(uf):
        info["avisos"].append("Brasil: arquivo indisponível, usando a soma das UFs")
        tot = uf.sum(numeric_only=True)
        br = {"pst": float(np.average(uf.pst, weights=uf.eleitorado.clip(lower=1))), "validos": tot.vv,
              "comparecimento": tot.comparecimento, "eleitorado": tot.eleitorado, "brancos": tot.brancos,
              "nulos": tot.nulos, "votos": {c[2:]: tot[c] for c in uf.columns if c.startswith("v_")},
              "totalizado": False, "hora": "", "leiaute": "soma das UFs"}
    if br is None:
        return _ultima("nacional", info)
    snap = {"uf": uf.to_dict("list"), "br": br, "info": info}
    _gravar("nacional.json", snap)
    return uf, br, info


def apuracao_ma(cod=None):
    """217 municípios do MA (pede os arquivos só quando o MA já começou a apurar)."""
    cod = cod or codigos()
    info = {"eleicao": cod["eleicao"], "consultado": time.time(), "avisos": []}
    ma = _tenta(lambda: ler_total(cod, "ma"))
    mun = pd.read_csv(AQUI / "dados" / "tse_1t_2026" / "presidente_1t_ma_municipios.csv", dtype={"cd_tse": str})
    if ma is None:
        return _ultima("ma", info)
    if ma["pst"] <= 0:
        return pd.DataFrame({"unidade": mun.cd_tse, "pst": 0.0, "vv": 0.0}), ma, info
    with ThreadPoolExecutor(16) as ex:
        partes = list(ex.map(lambda c: (c, _tenta(lambda: ler_total(cod, f"ma{c}"))), mun.cd_tse))
    linhas = []
    for c, d in partes:
        if d is None:
            linhas.append({"unidade": c, "pst": 0.0, "vv": 0.0})
            continue
        linhas.append({"unidade": c, "pst": d["pst"], "vv": d["validos"], "comparecimento": d["comparecimento"],
                       "brancos": d["brancos"], "nulos": d["nulos"], **{f"v_{n}": v for n, v in d["votos"].items()}})
    falhas = sum(d is None for _, d in partes)
    if falhas:
        info["avisos"].append(f"{falhas} municípios sem resposta nesta leitura")
    tab = pd.DataFrame(linhas).fillna(0)
    _gravar("ma.json", {"uf": tab.to_dict("list"), "br": ma, "info": info})
    return tab, ma, info


def _tenta(f):
    try:
        return f()
    except Exception:  # noqa: BLE001
        return None


def _ultima(nome, info):
    s = _ler_cache(f"{nome}.json")
    if not s:
        info["erro"] = "O TSE não respondeu e ainda não há leitura anterior guardada."
        return None, None, info
    info = dict(s["info"], desatualizado=True, avisos=s["info"].get("avisos", []) + ["TSE sem resposta: mostrando a última leitura"])
    return pd.DataFrame(s["uf"]), s["br"], info


# ------------------------------------------------------------------ seções (boletins de urna)
def secoes_publicadas(cod, cdmun=TUNTUM, uf="ma"):
    """Seções do município que já têm boletim publicado, com zona e horário."""
    pl = cod.get("pleito")
    if not pl:
        return []
    cs = _get(f"{BASE}/{cod['ciclo']}/arquivo-urna/{pl}/config/{uf}/{uf}-p{int(pl):06d}-cs.json")
    for abr in cs.get("abr", []):
        for m in abr.get("mu", []):
            if m.get("cd") == cdmun:
                return [(z["cd"], s["ns"], f"{s.get('da', '')} {s.get('ha', '')}".strip())
                        for z in m.get("zon", []) for s in z.get("sec", [])]
    return []


def boletim(cod, cdmun, zona, secao, uf="ma"):
    """Votos de uma seção pelo boletim de urna (cache em disco: BU totalizado não muda)."""
    pl, ele = cod["pleito"], int(cod["eleicao"])
    chave = f"bu_{pl}_{ele}_{uf}{cdmun}_{zona}_{secao}.json"
    salvo = _ler_cache(chave)
    if salvo:
        return salvo
    base = f"{BASE}/{cod['ciclo']}/arquivo-urna/{pl}/dados/{uf}/{cdmun}/{zona}/{secao}"
    aux = _get(f"{base}/p{int(pl):06d}-{uf}-m{cdmun}-z{zona}-s{secao}-aux.json")
    hashes = aux.get("hashes", [])
    h = next((x for x in hashes if str(x.get("st", "")).lower().startswith("totaliz")), hashes[-1] if hashes else None)
    if not h:
        return None
    arq = next((a["nm"] for a in h.get("arq", []) if a.get("tp") == "bu"), None)
    if not arq:
        return None
    dados = _get(f"{base}/{h['hash']}/{arq}", binario=True)
    r = _bu.extrair(dados, ele, int(cdmun))
    r.update(zona=zona, secao_txt=secao, situacao=aux.get("st", ""))
    if r["achou_eleicao"]:
        _gravar(chave, r)
    return r


def apuracao_secoes(cod=None, cdmun=TUNTUM):
    """Boletins das seções já publicadas de um município. Retorna (tabela, info)."""
    cod = cod or codigos()
    info = {"consultado": time.time(), "avisos": []}
    try:
        lista = secoes_publicadas(cod, cdmun)
    except Exception as e:  # noqa: BLE001
        info["avisos"].append(f"lista de seções indisponível ({type(e).__name__})")
        lista = []
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda zs: _tenta(lambda: boletim(cod, cdmun, zs[0], zs[1])), lista))
    linhas = []
    for (z, s, hora), r in zip(lista, res):
        if not r or not r.get("achou_eleicao"):
            continue
        linhas.append({"zona": z, "secao": s, "local": r["local"], "aptos": r["aptos"],
                       "comparecimento": r["comparecimento"], "lula": r["votos"].get(CAND["lula"], 0),
                       "flavio": r["votos"].get(CAND["flavio"], 0), "brancos": r["brancos"], "nulos": r["nulos"],
                       "hora": hora})
    info["publicadas"], info["lidas"] = len(lista), len(linhas)
    return pd.DataFrame(linhas), info


# ------------------------------------------------------------------ projeção do final
def projetar(unidades, previsao, chave, semente=0):
    """Apuração parcial × previsão do modelo → final estimado (usa o projetor do 1º turno, apuracao/motor.py).
    previsao: tabela do modelo (ufs_2t / ma_municipios_2t) com `chave`, lula_2t, flavio_2t e validos_2t_est."""
    import sys
    sys.path.insert(0, str(AQUI.parent / "apuracao"))
    import motor as _m1  # noqa: E402
    prev = previsao[[chave, "lula_2t", "flavio_2t", "validos_2t_est"]].copy()
    prev[chave] = prev[chave].astype(str)
    u = unidades.copy()
    u["unidade"] = u["unidade"].astype(str)
    return _m1.projetar(u, prev, CAND, "lula", "flavio", "lula_2t", "flavio_2t", "validos_2t_est", chave,
                        turno=2, semente=semente)


# ------------------------------------------------------------------ ensaio (sem internet)
def ensaio(fracao, semente=7, cenario=None):
    """Apuração simulada a partir de um cenário do modelo (para testar o painel antes de domingo).
    Retorna (uf, br, mun, ma, secoes) no mesmo formato das funções ao vivo."""
    rng = np.random.default_rng(semente)
    res = AQUI / "resultados"
    u = pd.read_csv(res / "ufs_2t.csv")
    m = pd.read_csv(res / "ma_municipios_2t.csv", dtype={"cd_tse": str})
    s = pd.read_csv(res / "tuntum_secoes_2t.csv", dtype={"zona": str, "secao": str})
    choque = rng.normal(0, 0.15) if cenario is None else cenario  # desvio comum em logit

    def apurar(df, chave, col_validos="validos_2t_est"):
        p = np.clip(df.lula_2t / 100, .01, .99)
        p = 1 / (1 + np.exp(-(np.log(p / (1 - p)) + choque + rng.normal(0, .05, len(df)))))
        ritmo = np.clip(fracao * rng.lognormal(0, .5, len(df)), 0, 1)
        ritmo[rng.random(len(df)) > min(1, fracao * 1.7)] = 0
        if fracao >= 1:
            ritmo[:] = 1.0
        vv = np.round(df[col_validos].values * ritmo)
        lula = np.round(vv * p)
        return pd.DataFrame({"unidade": df[chave].values, "pst": 100 * ritmo, "vv": vv,
                             "v_13": lula, "v_22": vv - lula})

    uf = apurar(u, "uf")
    mun = apurar(m, "cd_tse")
    sec = s.copy()
    publicada = rng.random(len(sec)) < min(1, fracao * 1.2)
    sec = sec[publicada].copy()
    p = np.clip(sec.lula_2t / 100 + rng.normal(choque / 4, .03, len(sec)), .02, .98)
    vv = np.round(sec.validos_2t_est)
    sec_out = pd.DataFrame({"zona": sec.zona, "secao": sec.secao, "local": sec.local, "aptos": sec.aptos,
                            "comparecimento": np.round(vv * 1.04), "lula": np.round(vv * p),
                            "flavio": vv - np.round(vv * p), "brancos": np.round(vv * .01), "nulos": np.round(vv * .03),
                            "hora": "ensaio"})
    tot = lambda df: {"pst": float(100 * df.vv.sum() / max(u.validos_2t_est.sum(), 1)), "validos": float(df.vv.sum()),
                      "votos": {"13": float(df.v_13.sum()), "22": float(df.v_22.sum())}, "totalizado": fracao >= 1,
                      "hora": "ensaio", "leiaute": "ensaio"}
    br = tot(uf)
    ma = {"pst": float(100 * mun.vv.sum() / max(m.validos_2t_est.sum(), 1)), "validos": float(mun.vv.sum()),
          "votos": {"13": float(mun.v_13.sum()), "22": float(mun.v_22.sum())}, "totalizado": fracao >= 1,
          "hora": "ensaio", "leiaute": "ensaio"}
    return uf, br, mun, ma, sec_out


def diagnostico():
    """Testa cada camada a partir deste servidor. Lista de (etapa, ok, detalhe)."""
    out = []

    def passo(nome, f):
        try:
            out.append((nome, True, f()))
        except Exception as e:  # noqa: BLE001
            out.append((nome, False, f"{type(e).__name__}: {e}"))

    passo("Ambiente", lambda: f"{AMBIENTE} · {BASE}")
    cod = codigos()
    passo("Códigos", lambda: f"eleição {cod['eleicao']} · pleito {cod['pleito']} ({cod['origem']})")
    passo("Brasil", lambda: (lambda t: f"{t['leiaute']} · {t['pst']:.2f}% apurado · {len(t['votos'])} candidatos")(
        ler_total(cod, "br")))
    passo("Maranhão", lambda: (lambda t: f"{t['leiaute']} · {t['pst']:.2f}% apurado")(ler_total(cod, "ma")))
    passo("Tuntum (município)", lambda: (lambda t: f"{t['pst']:.2f}% apurado")(ler_total(cod, f"ma{TUNTUM}")))
    passo("Tuntum (lista de seções)", lambda: f"{len(secoes_publicadas(cod))} seções com boletim publicado")
    passo("Cache em disco", lambda: f"{CACHE} ({'gravável' if os.access(CACHE.parent, os.W_OK) else 'sem escrita'})")
    # o 1º turno continua publicado: prova que a leitura de boletins funciona neste servidor
    cod1 = dict(cod, eleicao=cod.get("eleicao_1t", "6257"), pleito=cod.get("pleito_1t", "3220"))
    passo("Boletim de urna (1º turno, Tuntum 79/0001)", lambda: (lambda r: f"Lula {r['votos'].get('13')} · "
          f"Flávio {r['votos'].get('22')} (esperado 160 · 69)")(boletim(cod1, TUNTUM, "0079", "0001")))
    return out
