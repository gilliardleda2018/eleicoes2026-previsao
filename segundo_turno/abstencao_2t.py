"""Redução da abstenção do 1º turno (4/10/2026) para o 2º turno (25/10/2026), em três níveis:

  • Federal  · Brasil e cada estado         (totais do TSE)
  • Estadual · Maranhão e cada município    (totais do TSE)
  • Municipal· Tuntum por bairro, povoado e seção (boletins de urna)

Regras de conta:
  - Abstenção (%) = quem não votou ÷ eleitores aptos.
  - No 2º turno, durante a apuração, a taxa vale para as seções já totalizadas: abstenção ÷ (abstenção + comparecimento),
    como o TSE publica. Leituras antigas sem a coluna de abstenção usam comparecimento ÷ eleitorado (com o % apurado).
  - Redução (pts) = abstenção no 1º turno − abstenção no 2º turno. Positivo = mais gente votou.
  - Eleitores a mais nas urnas = redução × eleitorado (estimativa que vale também com apuração parcial).
  - Em Tuntum a comparação é seção a seção, só nas seções com boletim do 2º turno já lido.
Sem streamlit aqui: o painel chama estas funções; o ensaio e o ao vivo passam pelo mesmo caminho.
"""
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .convencimento import NOMES_UF, REGIAO_UF
except ImportError:  # executado com a pasta no sys.path
    from convencimento import NOMES_UF, REGIAO_UF

AQUI = Path(__file__).resolve().parent
TSE_1T = AQUI / "dados" / "tse_1t_2026"
TUNTUM = "09393"


# ------------------------------------------------------------------ taxas
def _num(df, col, padrao=np.nan):
    return pd.to_numeric(df[col], errors="coerce") if col in df else pd.Series(padrao, index=df.index, dtype=float)


def taxa_2t(df, eleitorado_ref=None):
    """Abstenção (%) do 2º turno por linha de uma leitura ao vivo (UF ou município).
    Colunas usadas: comparecimento, abstencao (se houver), eleitorado (se houver), pst.
    eleitorado_ref: eleitorado do 1º turno, alinhado às linhas, para leituras sem eleitorado."""
    c = _num(df, "comparecimento")
    a = _num(df, "abstencao")
    e = _num(df, "eleitorado")
    if eleitorado_ref is not None:
        e = e.where(e > 0, pd.Series(np.asarray(eleitorado_ref, dtype=float), index=df.index))
    pst = _num(df, "pst", 0.0).fillna(0)
    pela_abst = 100 * a / (a + c)
    pelo_elei = 100 * (1 - c / (e * pst.clip(lower=1e-9) / 100))
    t = pela_abst.where((a + c) > 0, pelo_elei.where((pst > 0) & (e > 0) & (c > 0)))
    return t.where((c > 0) | (a > 0)).clip(0, 100)


def taxa_total(d):
    """Abstenção (%) de um total (dicionário do motor: Brasil, Maranhão). None se ainda não há dado."""
    if not d:
        return None
    df = pd.DataFrame([{k: d.get(k) for k in ("comparecimento", "abstencao", "eleitorado", "pst")}])
    v = taxa_2t(df).iloc[0]
    return None if pd.isna(v) else float(v)


def _completar(t, abst1, elei):
    t["abst_1t"] = abst1
    t["reducao"] = t.abst_1t - t.abst_2t
    t["a_mais"] = t.reducao / 100 * elei
    t["situacao"] = np.select([t.abst_2t.isna(), t.reducao > 0.05, t.reducao < -0.05],
                              ["aguardando", "caiu", "subiu"], "estável")
    return t


def _total(nome, elei1, comp1, d2):
    """Linha de resumo (Brasil, Maranhão, município) para os cartões."""
    a1 = 100 * (1 - comp1 / elei1) if elei1 else np.nan
    a2 = taxa_total(d2)
    elei = float(d2.get("eleitorado") or 0) if d2 else 0.0
    elei = elei if elei > 0 else float(elei1)
    red = None if a2 is None else a1 - a2
    return {"nome": nome, "abst_1t": a1, "abst_2t": a2, "reducao": red,
            "a_mais": None if red is None else red / 100 * elei, "eleitorado": elei,
            "faltaram_1t": float(elei1 - comp1), "pst": float(d2.get("pst") or 0) if d2 else 0.0,
            "totalizado": bool(d2.get("totalizado")) if d2 else False}


# ------------------------------------------------------------------ federal
def brasil(uf_v, br_v):
    """(tabela por estado, resumo do Brasil). Exterior (ZZ) fica de fora da tabela, mas entra no total do Brasil
    nos dois turnos (o TSE soma o exterior no total 'br')."""
    u1 = pd.read_csv(TSE_1T / "presidente_1t_uf.csv").set_index("abrangencia")
    est = u1.drop(index=["br", "zz"], errors="ignore").reset_index()
    est["uf"] = est.abrangencia.str.upper()
    t = pd.DataFrame({"uf": est.uf, "nome": est.uf.map(NOMES_UF), "regiao": est.uf.map(REGIAO_UF),
                      "eleitorado_1t": est.eleitorado.astype(float), "comp_1t": est.comparecimento.astype(float)})
    v = uf_v.copy() if uf_v is not None and len(uf_v) else pd.DataFrame({"unidade": []})
    v["uf"] = v.unidade.astype(str).str.upper()
    v = v[v.uf.isin(t.uf)]
    cols = [c for c in ("pst", "comparecimento", "abstencao", "eleitorado") if c in v]
    t = t.merge(v[["uf"] + cols], on="uf", how="left")
    t["pst"] = _num(t, "pst", 0.0).fillna(0)
    t["comp_2t"] = _num(t, "comparecimento")
    t["abst_2t"] = taxa_2t(t, t.eleitorado_1t)
    elei = _num(t, "eleitorado").where(lambda s: s > 0, t.eleitorado_1t)
    t = _completar(t, 100 * (1 - t.comp_1t / t.eleitorado_1t), elei)
    br = u1.loc["br"]
    return t.sort_values("reducao", ascending=False, na_position="last").reset_index(drop=True), \
        _total("Brasil", float(br.eleitorado), float(br.comparecimento), br_v)


# ------------------------------------------------------------------ estadual
def maranhao(mun_v, ma_v, nomes):
    """(tabela por município do MA, resumo do Maranhão).
    nomes: DataFrame com cd_tse, municipio e, se houver, regiao_imediata/regiao_intermediaria."""
    m1 = pd.read_csv(TSE_1T / "presidente_1t_ma_municipios.csv", dtype={"cd_tse": str})
    extra = [c for c in ("municipio", "regiao_imediata", "regiao_intermediaria") if c in nomes]
    t = m1[["cd_tse", "eleitorado", "comparecimento"]].rename(
        columns={"eleitorado": "eleitorado_1t", "comparecimento": "comp_1t"}).merge(
        nomes[["cd_tse"] + extra].drop_duplicates("cd_tse"), on="cd_tse", how="left")
    t[["eleitorado_1t", "comp_1t"]] = t[["eleitorado_1t", "comp_1t"]].astype(float)
    v = mun_v.copy() if mun_v is not None and len(mun_v) else pd.DataFrame({"unidade": []})
    v["cd_tse"] = v.unidade.astype(str).str.zfill(5)
    cols = [c for c in ("pst", "comparecimento", "abstencao", "eleitorado") if c in v]
    t = t.merge(v[["cd_tse"] + cols], on="cd_tse", how="left")
    t["pst"] = _num(t, "pst", 0.0).fillna(0)
    t["comp_2t"] = _num(t, "comparecimento")
    t["abst_2t"] = taxa_2t(t, t.eleitorado_1t)
    elei = _num(t, "eleitorado").where(lambda s: s > 0, t.eleitorado_1t)
    t = _completar(t, 100 * (1 - t.comp_1t / t.eleitorado_1t), elei)
    t = t.sort_values("reducao", ascending=False, na_position="last").reset_index(drop=True)
    t["posicao"] = t.reducao.rank(ascending=False, method="min")
    u1 = pd.read_csv(TSE_1T / "presidente_1t_uf.csv").set_index("abrangencia").loc["ma"]
    return t, _total("Maranhão", float(u1.eleitorado), float(u1.comparecimento), ma_v)


def municipio(tab_ma, cd_tse):
    """Resumo de um município a partir da tabela do Maranhão (mesmo formato do resumo do Brasil e do MA)."""
    r = tab_ma[tab_ma.cd_tse == cd_tse]
    if not len(r):
        return None
    r = r.iloc[0]
    tem = pd.notna(r.abst_2t)
    return {"nome": str(r.get("municipio", cd_tse)), "abst_1t": float(r.abst_1t),
            "abst_2t": float(r.abst_2t) if tem else None, "reducao": float(r.reducao) if tem else None,
            "a_mais": float(r.a_mais) if tem else None, "eleitorado": float(r.eleitorado_1t),
            "faltaram_1t": float(r.eleitorado_1t - r.comp_1t), "pst": float(r.pst),
            "totalizado": float(r.pst) >= 99.99, "posicao": int(r.posicao) if tem else None,
            "de": int(tab_ma.abst_2t.notna().sum())}


# ------------------------------------------------------------------ municipal (seções)
def secoes(base_t, sec_v):
    """Seção a seção: base_t = seções do 1º turno (secao, aptos, comparecimento, bairro, zona_tipo, Local);
    sec_v = boletins do 2º turno já lidos (secao, aptos, comparecimento)."""
    s = base_t[["secao", "bairro", "zona_tipo", "Local", "aptos", "comparecimento"]].rename(
        columns={"aptos": "aptos_1t", "comparecimento": "comp_1t"}).copy()
    s["secao"] = s.secao.astype(str).str.zfill(4)
    if sec_v is not None and len(sec_v):
        v = sec_v.assign(secao=sec_v.secao.astype(str).str.zfill(4))[["secao", "aptos", "comparecimento"]]
        v = v.rename(columns={"aptos": "aptos_2t", "comparecimento": "comp_2t"}).drop_duplicates("secao")
        s = s.merge(v, on="secao", how="left")
    else:
        s["aptos_2t"], s["comp_2t"] = np.nan, np.nan
    s["aptos_2t"] = pd.to_numeric(s.aptos_2t, errors="coerce")
    s["aptos_2t"] = s.aptos_2t.where(s.aptos_2t > 0, s.aptos_1t.where(s.comp_2t.notna()))
    s["lida"] = s.comp_2t.notna()
    s["abst_1t"] = 100 * (1 - s.comp_1t / s.aptos_1t)
    s["abst_2t"] = 100 * (1 - s.comp_2t / s.aptos_2t)
    s["reducao"] = s.abst_1t - s.abst_2t
    s["a_mais"] = s.comp_2t - s.comp_1t
    return s


def por_grupo(s, chave):
    """Soma por bairro/povoado, local ou zona, só nas seções já lidas (as duas taxas nas mesmas seções)."""
    lid = s[s.lida]
    g = s.groupby(chave, as_index=False).agg(secoes=("secao", "count"), aptos=("aptos_1t", "sum"))
    if len(lid):
        a = lid.groupby(chave, as_index=False).agg(lidas=("secao", "count"), aptos_1t=("aptos_1t", "sum"),
                                                   comp_1t=("comp_1t", "sum"), aptos_2t=("aptos_2t", "sum"),
                                                   comp_2t=("comp_2t", "sum"))
        g = g.merge(a, on=chave, how="left")
    else:
        g = g.assign(lidas=0, aptos_1t=np.nan, comp_1t=np.nan, aptos_2t=np.nan, comp_2t=np.nan)
    g["lidas"] = g.lidas.fillna(0).astype(int)
    g["abst_1t"] = 100 * (1 - g.comp_1t / g.aptos_1t)
    g["abst_2t"] = 100 * (1 - g.comp_2t / g.aptos_2t)
    g["reducao"] = g.abst_1t - g.abst_2t
    g["a_mais"] = g.comp_2t - g.comp_1t
    return g.sort_values("reducao", ascending=False, na_position="last").reset_index(drop=True)


def resumo_secoes(s, nome="Tuntum"):
    """Resumo do município pelas seções lidas (mesmo formato dos outros resumos)."""
    lid = s[s.lida]
    if not len(lid):
        return {"nome": nome, "abst_1t": float(100 * (1 - s.comp_1t.sum() / s.aptos_1t.sum())), "abst_2t": None,
                "reducao": None, "a_mais": None, "lidas": 0, "secoes": len(s)}
    a1 = 100 * (1 - lid.comp_1t.sum() / lid.aptos_1t.sum())
    a2 = 100 * (1 - lid.comp_2t.sum() / lid.aptos_2t.sum())
    return {"nome": nome, "abst_1t": float(a1), "abst_2t": float(a2), "reducao": float(a1 - a2),
            "a_mais": float(lid.comp_2t.sum() - lid.comp_1t.sum()), "lidas": int(len(lid)), "secoes": int(len(s))}
