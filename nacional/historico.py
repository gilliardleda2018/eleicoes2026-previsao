"""Leitura padronizada do erro histórico das pesquisas presidenciais (2006–2022).

Critério: pesquisas finais até 10 dias antes da eleição, sem os recortes regionais. Por padrão inclui TODOS os
institutos, porque o consenso de 2026 também é a média de todos (mesma régua); incluir_pequenos=False = só os grandes. Erro = margem na urna − margem na pesquisa (PT − adversário, só os dois),
em pontos; negativo = pesquisa superestimou o PT.
"""
import unicodedata
from pathlib import Path

import pandas as pd

ELEICOES = {(2006, 1): "2006-10-01", (2006, 2): "2006-10-29", (2010, 1): "2010-10-03", (2010, 2): "2010-10-31",
            (2014, 1): "2014-10-05", (2014, 2): "2014-10-26", (2018, 1): "2018-10-07", (2018, 2): "2018-10-28",
            (2022, 1): "2022-10-02", (2022, 2): "2022-10-30"}
PEQUENOS = {"verita", "brasmarket", "gerp", "ifp"}


def sem_acento(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()


def carregar(arq: Path, incluir_pequenos=True):
    h = pd.read_csv(arq)
    for c in ("pesq_pt", "pesq_adv", "urna_pt_validos", "urna_adv_validos"):
        h[c] = pd.to_numeric(h[c], errors="coerce")
    h = h.dropna(subset=["pesq_pt", "pesq_adv", "urna_pt_validos", "urna_adv_validos"])
    h = h[~h.instituto.fillna("").str.contains(r"\[regiao", case=False)]
    if not incluir_pequenos:
        h = h[~h.instituto.map(sem_acento).isin(PEQUENOS)]
    dia = pd.Series(pd.to_datetime([ELEICOES[(a, t)] for a, t in zip(h.ano, h.turno)]), index=h.index)
    dias = (dia - pd.to_datetime(h.fim_campo, errors="coerce")).dt.days
    h = h[dias.between(0, 10)].copy()
    vals = h[["pesq_pt", "pesq_adv", "urna_pt_validos", "urna_adv_validos"]]
    if ((vals < 0) | (vals > 100)).any().any():
        raise ValueError("Histórico: percentuais fora de [0,100]")
    if ((h.pesq_pt + h.pesq_adv <= 0) | (h.urna_pt_validos + h.urna_adv_validos <= 0)).any():
        raise ValueError("Histórico: denominador nulo")
    h["erro_margem"] = 2 * (100 * h.urna_pt_validos / (h.urna_pt_validos + h.urna_adv_validos)
                            - 100 * h.pesq_pt / (h.pesq_pt + h.pesq_adv))
    return h
