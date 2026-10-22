"""Projeto Convencimento: onde estão os eleitores de Lula que não foram votar no 1º turno (4/10/2026).

Estimativa (mesmo método das campanhas de mobilização): quem faltou num lugar é contado como eleitor de Lula na
mesma proporção dos votos válidos de Lula naquele lugar. Quanto menor o lugar (estado → município → seção), melhor
a estimativa. Fonte: resultados oficiais do TSE do 1º turno (boletins de urna em Tuntum).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
DADOS = AQUI / "dados"
TSE = DADOS / "tse_1t_2026"

NOMES_UF = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
            "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso",
            "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
            "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
            "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
            "SE": "Sergipe", "TO": "Tocantins"}
REGIAO_UF = {"AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
             "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste",
             "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
             "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
             "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
             "PR": "Sul", "RS": "Sul", "SC": "Sul"}


def _estimar(d, aptos="eleitorado"):
    d = d.copy()
    d["faltaram"] = (d[aptos] - d["comparecimento"]).clip(lower=0)
    d["lula_pct"] = 100 * d["lula"] / d["validos"].replace(0, np.nan)
    d["flavio_pct"] = 100 * d["flavio"] / d["validos"].replace(0, np.nan)
    d["lula_casa"] = d["faltaram"] * d["lula_pct"].fillna(0) / 100
    d["flavio_casa"] = d["faltaram"] * d["flavio_pct"].fillna(0) / 100
    d["abstencao_pct"] = 100 * d["faltaram"] / d[aptos].replace(0, np.nan)
    return d


def brasil():
    """(estados, totais). Exterior fica de fora (voto no exterior tem outra lógica de comparecimento)."""
    u = pd.read_csv(TSE / "presidente_1t_uf.csv")
    br = u[u.abrangencia == "br"].iloc[0]
    e = u[~u.abrangencia.isin(["br", "zz"])].copy()
    e["uf"] = e.abrangencia.str.upper()
    e["nome"] = e.uf.map(NOMES_UF)
    e["regiao"] = e.uf.map(REGIAO_UF)
    e = _estimar(e)
    tot = {"lula_1t": int(br.lula), "flavio_1t": int(br.flavio), "validos_1t": int(br.validos),
           "diferenca": int(br.flavio - br.lula), "faltaram": int(e.faltaram.sum()),
           "lula_casa": float(e.lula_casa.sum()), "flavio_casa": float(e.flavio_casa.sum()),
           "abstencao_pct": float(100 * (br.eleitorado - br.comparecimento) / br.eleitorado)}
    tot["fracao_para_virar"] = tot["diferenca"] / tot["lula_casa"] if tot["lula_casa"] else np.nan
    return e.sort_values("lula_casa", ascending=False), tot


def maranhao(mun):
    """mun: municípios do MA com eleitorado, comparecimento, validos, lula, flavio, municipio, cd_ibge."""
    reg = pd.read_csv(DADOS / "regioes_ibge_ma.csv", dtype={"cd_ibge": str})
    m = mun.drop(columns=[c for c in reg.columns if c in mun.columns and c != "cd_ibge"]).merge(reg, on="cd_ibge",
                                                                                               how="left")
    m = _estimar(m)
    return m.sort_values("lula_casa", ascending=False)


def tuntum(secoes):
    """secoes: seções de Tuntum com aptos, comparecimento, validos, lula, flavio, bairro, zona_tipo, Local."""
    return _estimar(secoes, aptos="aptos")


def centroides_uf():
    gj = json.loads((AQUI.parent / "nacional" / "dados" / "br_ufs.json").read_text(encoding="utf-8"))
    out = {}
    for f in gj["features"]:
        g = f["geometry"]
        polis = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        anel = max((p[0] for p in polis), key=len)  # maior anel externo
        xs, ys = zip(*[(c[0], c[1]) for c in anel])
        out[f["properties"]["uf"]] = (float(np.mean(ys)), float(np.mean(xs)))
    return out


def fmt_qtd(x):
    """14,8 milhões · 654 mil · 9.000 · 340"""
    x = float(x)
    if x >= 1e6:
        return f"{x / 1e6:.1f}".replace(".", ",") + " milhões"
    if x >= 1e5:
        return f"{round(x / 1e3):.0f} mil"
    if x >= 1e4:
        return f"{round(x / 1e3, 1):.1f}".replace(".", ",").replace(",0", "") + " mil"
    if x >= 1000:
        return f"{round(x, -2):,.0f}".replace(",", ".")
    return f"{round(x, -1) if x >= 100 else round(x):.0f}"
