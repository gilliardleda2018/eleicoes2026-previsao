"""Contratos numéricos, temporais e gravação estrita para o modelo eleitoral."""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd


def data_corte():
    """Fixe MODELO_DATA_CORTE=AAAA-MM-DD para reconstruções reproduzíveis."""
    return pd.Timestamp(os.environ.get("MODELO_DATA_CORTE", pd.Timestamp.now(tz="America/Sao_Paulo").date())).normalize()


def validar_percentuais(df, cols, contexto):
    vals = df[cols].to_numpy(dtype=float)
    if not np.isfinite(vals).all() or ((vals < 0) | (vals > 100)).any():
        raise ValueError(f"{contexto}: percentuais ausentes, não finitos ou fora de [0,100]")


def filtrar_datas(df, corte, inicio="inicio", fim="fim"):
    df = df.copy()
    df[fim] = pd.to_datetime(df[fim], errors="raise")
    if df[fim].isna().any():
        raise ValueError("Data final ausente")
    if inicio in df:
        df[inicio] = pd.to_datetime(df[inicio], errors="raise").fillna(df[fim])
        if (df[inicio] > df[fim]).any():
            raise ValueError("Início da pesquisa posterior ao fim")
    # Datas de campo não garantem disponibilidade pública. Quando informada,
    # a divulgação também deve ser anterior ao corte.
    if "divulgacao" in df:
        divulgacao = pd.to_datetime(df.divulgacao, errors="raise")
        if divulgacao.isna().any():
            raise ValueError("Data de divulgação ausente")
        df = df[divulgacao <= corte]
    return df[df[fim] <= corte].copy()


def transferencia_implicita(pp):
    """Uma observação por pesquisa: duplicatas ambíguas não são independentes."""
    a, b = pp[pp.turno == 1].copy(), pp[pp.turno == 2].copy()
    chaves = ["instituto", "fim"]
    for p in (a, b):
        if p.duplicated(chaves).any():
            raise ValueError("Pares de transferência ambíguos: informe uma pesquisa por instituto/data/turno")
    par = a.drop(columns="lula_2p", errors="ignore").merge(b[chaves + ["lula_2p"]], on=chaves, validate="one_to_one")
    par["resto"] = 100 - par.lula_val - par.flavio_val
    par = par[(par.resto > 3) & (pd.to_datetime(par.fim) >= "2026-08-01")].copy()
    par["t"] = (par.lula_2p - par.lula_val) / par.resto
    if len(par):
        validar_percentuais(par, ["lula_val", "flavio_val", "lula_2p"], "Transferência")
    if not np.isfinite(par.t.to_numpy()).all() or ((par.t < 0) | (par.t > 1)).any():
        raise ValueError("Transferência implícita fora de [0,1]; não representa migração identificável")
    return par


def sortear_transferencia(valores, rng, n):
    """Distribuição empírica; evita ajuste Beta inválido e precisão artificial."""
    v = np.asarray(valores, dtype=float)
    if len(v) < 4:
        raise ValueError("São necessários ao menos quatro pares válidos para transferência")
    if not np.isfinite(v).all() or ((v < 0) | (v > 1)).any():
        raise ValueError("Transferências inválidas")
    return rng.choice(v, size=n, replace=True)


def decidir(l1, f1, l2):
    l1, f1, l2 = map(np.asarray, (l1, f1, l2))
    if not all(np.isfinite(v).all() for v in (l1, f1, l2)):
        raise ValueError("Simulação contém NaN ou infinito")
    if ((l1 < 0) | (f1 < 0) | (l1 + f1 > 100 + 1e-8)).any() or ((l2 < 0) | (l2 > 1)).any():
        raise ValueError("Simulação fora do domínio eleitoral")
    primeiro_l, primeiro_f = l1 > 50, f1 > 50
    segundo = ~primeiro_l & ~primeiro_f
    if (segundo & (l2 == .5)).any():
        raise ValueError("Empate exato: exige regra explícita de desempate")
    l = primeiro_l | (segundo & (l2 > .5))
    f = primeiro_f | (segundo & (l2 < .5))
    if not np.all(l ^ f):
        raise ValueError("Cenário sem vencedor único")
    return primeiro_l, primeiro_f, segundo, l, f


def escrever_json(path, obj):
    path = Path(path)
    texto = json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(texto, encoding="utf-8")
    tmp.replace(path)
