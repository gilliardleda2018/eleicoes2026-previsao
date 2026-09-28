"""Base municipal (217 municípios) para o modelo Governo MA 2026: Braide × Orleans.

Junta: TSE governador 2018 e 2022 (% dos válidos por município), apoio declarado dos prefeitos (set/2026)
e geografia IBGE (centroide, regiões).

Saída: dados/base_municipios.csv
"""
import json
import unicodedata
from pathlib import Path

import pandas as pd
from shapely.geometry import shape

D = Path(__file__).resolve().parent / "dados"
GOV22 = {40: "brandao22", 20: "lahesio22", 12: "weverton22", 55: "edivaldo22"}
GOV18 = {65: "dino18", 15: "roseana18", 17: "maura18", 45: "rocha18"}
GRANDE_ILHA = {"sao luis", "sao jose de ribamar", "paco do lumiar", "raposa"}
ALIASES = {"sao joao do soter": "sao joao do soter", "olho d agua das cunhas": "olho d agua das cunhas"}


def norm(nome):
    s = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    s = " ".join(s.replace("-", " ").replace("'", " ").lower().split())
    return ALIASES.get(s, s)


def governador(ano, mapa):
    v = pd.read_csv(D / "tse" / f"votos_{ano}_municipio.csv")
    v = v[v.DS_CARGO == "Governador"]
    validos = v[~v.NR_VOTAVEL.isin([95, 96])].groupby("CD_MUNICIPIO").QT_VOTOS.sum().rename(f"validos{ano % 100}")
    total = v.groupby("CD_MUNICIPIO").QT_VOTOS.sum().rename(f"comparecimento{ano % 100}")
    tab = pd.concat([validos, total], axis=1)
    for num, col in mapa.items():
        s = v[v.NR_VOTAVEL == num].groupby("CD_MUNICIPIO").QT_VOTOS.sum()
        tab[col] = (100 * s / tab[f"validos{ano % 100}"]).reindex(tab.index).fillna(0).round(2)
    nomes = v.groupby("CD_MUNICIPIO").NM_MUNICIPIO.first()
    return tab.join(nomes)


g22 = governador(2022, GOV22)
g18 = governador(2018, GOV18).drop(columns="NM_MUNICIPIO")
base = g22.join(g18).reset_index()
base["cidade_norm"] = base.NM_MUNICIPIO.map(norm)

# geografia
geo = json.load(open(D / "ma_municipios.geojson", encoding="utf-8"))
linhas = []
for f in geo["features"]:
    p = f["properties"]
    c = shape(f["geometry"]).representative_point()
    linhas.append({"cd_ibge": p["CD_MUN"], "municipio": p["NM_MUN"], "cidade_norm": norm(p["NM_MUN"]),
                   "regiao_imediata": p["NM_RGI"], "regiao_intermediaria": p["NM_RGINT"], "lat": c.y, "lon": c.x})
geo_df = pd.DataFrame(linhas)
base = geo_df.merge(base, on="cidade_norm", how="left", indicator=True)
sem_tse = base.loc[base._merge != "both", "municipio"].tolist()
base = base.drop(columns=["_merge", "NM_MUNICIPIO"])

# prefeitos
pref = pd.read_csv(D / "prefeitos_apoio_governo_2026.csv")
pref["cidade_norm"] = pref.municipio.map(norm)
sem_pref = sorted(set(pref.cidade_norm) - set(base.cidade_norm))
base = base.merge(pref[["cidade_norm", "prefeito_apoia"]], on="cidade_norm", how="left")
base["prefeito_apoia"] = base.prefeito_apoia.fillna("Neutro")

base["grande_ilha"] = base.cidade_norm.isin(GRANDE_ILHA).astype(int)
base["sao_luis"] = (base.cidade_norm == "sao luis").astype(int)
base["imperatriz"] = (base.cidade_norm == "imperatriz").astype(int)
base["eleitores_26"] = (base.comparecimento22 * 1.03).round()  # comparecimento 2022 + crescimento do eleitorado
base["peso_estado"] = base.validos22 / base.validos22.sum()
base.to_csv(D / "base_municipios.csv", index=False, encoding="utf-8")

print(f"{len(base)} municípios | sem TSE: {sem_tse} | prefeitos sem correspondência: {sem_pref}")
print(base.prefeito_apoia.value_counts().to_dict())
print(base.nlargest(6, "validos22")[["municipio", "validos22", "brandao22", "lahesio22", "weverton22",
                                     "edivaldo22", "prefeito_apoia"]].to_string(index=False))
