"""Verifica pré-requisitos sem executar modelos ou baixar dados."""
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def verificar():
    faltas = []
    for mod in ("numpy", "pandas", "scipy", "sklearn", "plotly", "streamlit"):
        if importlib.util.find_spec(mod) is None:
            faltas.append(f"Dependência Python: {mod}")
    for arquivo in ("agregadores.py", "comum.py"):
        if not any((p/arquivo).is_file() for p in (RAIZ, RAIZ.parent)):
            faltas.append(f"Módulo do projeto: {arquivo}")
    for arquivo in ("base_ufs.csv", "centroides_ufs.json", "pesquisas_presidente.csv",
                    "erro_historico_presidente.csv", "erro_2t_antecipado_2022.csv", "br_ufs.json"):
        if not (RAIZ/"dados"/arquivo).is_file():
            faltas.append(f"Base: dados/{arquivo}")
    return faltas


if __name__ == "__main__":
    faltas = verificar()
    print("\n".join(faltas) if faltas else "Pré-requisitos presentes; isso não valida sua procedência.")
    raise SystemExit(bool(faltas))
