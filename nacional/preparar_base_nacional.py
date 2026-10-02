"""Base por estado (27 UFs) para o cenário nacional: Lula × Flávio Bolsonaro.

- 2022: API oficial de divulgação do TSE (resultados.tse.jus.br), 1º turno (eleição 544) e 2º turno (545).
- 2018: tabela por estado da Wikipédia (en) "2018 Brazilian general election" (fonte: TSE), salva em dados/tse/presidente_2018_uf.csv.

Saída: dados/base_ufs.csv
"""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd
from validacao_modelo import validar_percentuais

D = Path(__file__).resolve().parent / "dados"
UFS = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
       "DF": "Federal District", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso",
       "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
       "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
       "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo (state)",
       "SE": "Sergipe", "TO": "Tocantins"}
REGIAO = {"AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
          "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste", "PE": "Nordeste",
          "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste", "DF": "Centro-Oeste", "GO": "Centro-Oeste",
          "MT": "Centro-Oeste", "MS": "Centro-Oeste", "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste",
          "SP": "Sudeste", "PR": "Sul", "RS": "Sul", "SC": "Sul"}
CACHE = D / "tse" / "api_2022"
CACHE.mkdir(parents=True, exist_ok=True)


def tse_uf(uf, eleicao):
    arq = CACHE / f"{uf}_{eleicao}.json"
    if not arq.exists():
        url = (f"https://resultados.tse.jus.br/oficial/ele2022/{eleicao}/dados-simplificados/{uf.lower()}/"
               f"{uf.lower()}-c0001-e000{eleicao}-r.json")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        arq.write_bytes(urllib.request.urlopen(req, timeout=30).read())
        time.sleep(0.2)
    t = json.loads(arq.read_text(encoding="utf-8"))
    if float(str(t.get("pst", "0")).replace(",", ".")) != 100:
        raise ValueError(f"Apuração incompleta ou sem marcador de conclusão: {uf}/{eleicao}")
    votos = {c["nm"]: int(c["vap"]) for c in t["cand"]}
    if int(t["vv"]) <= 0 or sum(votos.values()) != int(t["vv"]):
        raise ValueError(f"Contagem de votos inconsistente: {uf}/{eleicao}")
    obrigatorios = {"LULA", "JAIR BOLSONARO"}
    if eleicao == 544:
        obrigatorios |= {"SIMONE TEBET", "CIRO GOMES"}
    if not obrigatorios.issubset(votos):
        raise ValueError(f"Candidato obrigatório ausente: {uf}/{eleicao}")
    return votos, int(t["vv"]), int(t["e"]), int(t["c"])  # válidos, eleitorado, comparecimento


linhas = []
for uf in UFS:
    v1, val1, eleit, comp = tse_uf(uf, 544)
    v2, val2, _, comp2 = tse_uf(uf, 545)
    linhas.append({"uf": uf, "regiao": REGIAO[uf], "eleitorado22": eleit, "comparecimento22_2t": comp2,
                   "validos22_1t": val1, "validos22_2t": val2,
                   "lula22_1t": round(100 * v1.get("LULA", 0) / val1, 2),
                   "bolsonaro22_1t": round(100 * v1.get("JAIR BOLSONARO", 0) / val1, 2),
                   "tebet22_1t": round(100 * v1.get("SIMONE TEBET", 0) / val1, 2),
                   "ciro22_1t": round(100 * v1.get("CIRO GOMES", 0) / val1, 2),
                   "lula22_2t": round(100 * v2.get("LULA", 0) / val2, 2),
                   "bolsonaro22_2t": round(100 * v2.get("JAIR BOLSONARO", 0) / val2, 2)})
b = pd.DataFrame(linhas)

r18 = pd.read_csv(D / "tse" / "presidente_2018_uf.csv")
r18["uf"] = r18.estado.map({v: k for k, v in UFS.items()})
if r18.uf.isna().any() or r18.uf.duplicated().any() or set(r18.uf) != set(UFS):
    raise ValueError("Base de 2018 incompleta, duplicada ou com nomes de estados desconhecidos")
b = b.merge(r18.drop(columns="estado"), on="uf", how="left", validate="one_to_one")
validar_percentuais(b, ["haddad18_2t", "haddad18_1t", "ciro18_1t", "bolsonaro18_2t"], "Base de 2018")
b["peso"] = b.validos22_2t / b.validos22_2t.sum()
b.to_csv(D / "base_ufs.csv", index=False, encoding="utf-8")

tot = b[["validos22_1t", "validos22_2t"]].sum()
lula2 = (b.lula22_2t * b.validos22_2t).sum() / tot.validos22_2t
print(f"{len(b)} UFs | Lula 2º t 2022 (soma das UFs, sem exterior): {lula2:.2f}% | faltando 2018: "
      f"{b.bolsonaro18_2t.isna().sum()}")
print(b[["uf", "lula22_1t", "bolsonaro22_1t", "lula22_2t", "haddad18_2t", "validos22_2t"]].to_string(index=False))
