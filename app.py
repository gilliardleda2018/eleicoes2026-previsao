"""Painel de previsão eleitoral 2026 — entrada única.

Rodar:  streamlit run app.py
Páginas: Cenário Nacional (Lula × Flávio Bolsonaro) e Cenário Estadual MA (Braide × Orleans).
"""
from pathlib import Path

import streamlit as st

from comum import CSS, exigir_senha

RAIZ = Path(__file__).resolve().parent
st.set_page_config(page_title="Eleições 2026 · Previsão", page_icon="🗳️", layout="wide")
exigir_senha()
st.markdown(CSS, unsafe_allow_html=True)
paginas = [
    st.Page(RAIZ / "nacional" / "painel_nacional.py", title="Cenário Nacional · Lula × Flávio", icon="🇧🇷",
            url_path="nacional", default=True),
    st.Page(RAIZ / "painel_governo_ma.py", title="Cenário Estadual MA · Braide × Orleans", icon="🏛️",
            url_path="maranhao"),
    st.Page(RAIZ / "apuracao" / "painel_apuracao.py", title="Apuração ao vivo", icon="📡", url_path="apuracao"),
]
st.navigation(paginas, position="top").run()
