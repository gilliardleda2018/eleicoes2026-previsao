"""Atualiza apuracao/deputados_previsao.csv a partir do modelo da Bruna (C:/modelo_bruna/v13_estrategia).

Copia só os números por município usados na apuração ao vivo (nada de lideranças ou estratégia).
Uso: python apuracao/atualizar_deputados.py [pasta_do_modelo_bruna]
"""
import sys
from pathlib import Path

import pandas as pd

ORIGEM = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/modelo_bruna/v13_estrategia")
DESTINO = Path(__file__).resolve().parent / "deputados_previsao.csv"

b = pd.read_csv(ORIGEM / "previsao_v13_municipios.csv")
ab = pd.read_csv(ORIGEM / "duelo_abigail_2026_municipios.csv")[["CD_MUNICIPIO", "abigail_2026"]]
d = b[["CD_MUNICIPIO", "cd_ibge", "municipio", "total_dep_est_2022", "votos_projetados", "abigail_2022",
       "eric_costa_2022"]].merge(ab, on="CD_MUNICIPIO", how="left")
d.to_csv(DESTINO, index=False, encoding="utf-8")
print(f"{DESTINO.name}: {len(d)} municípios · Bruna projetada {d.votos_projetados.sum():,.0f} votos")
