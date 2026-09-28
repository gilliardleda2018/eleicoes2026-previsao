"""Painel de previsão eleitoral 2026 — entrada única.

Rodar:  streamlit run app.py
Páginas: Cenário Nacional (Lula × Flávio Bolsonaro) e Cenário Estadual MA (Braide × Orleans).
"""
from pathlib import Path

import streamlit as st

from comum import CSS, exigir_senha, rodape_desenvolvedor

RAIZ = Path(__file__).resolve().parent
st.set_page_config(page_title="Eleições 2026 · Previsão", page_icon="🗳️", layout="wide")


@st.cache_resource
def _previa_do_link():
    """Miniatura do link no WhatsApp: grava as tags og: no HTML do Streamlit uma vez por processo (só no Render)."""
    try:
        from preparar_render import gravar_open_graph
        return gravar_open_graph()
    except Exception as e:  # nunca derruba o painel por causa da prévia
        return f"prévia do link não gravada: {e}"


_previa_do_link()
exigir_senha()
st.markdown(CSS, unsafe_allow_html=True)
paginas = [
    st.Page(RAIZ / "inicio.py", title="Início", icon="🏠", url_path="inicio", default=True),
    st.Page(RAIZ / "nacional" / "painel_nacional.py", title="Cenário Nacional · Lula × Flávio", icon="🌎",
            url_path="nacional"),
    st.Page(RAIZ / "painel_governo_ma.py", title="Cenário Estadual MA · Braide × Orleans", icon="🏛️",
            url_path="maranhao"),
    st.Page(RAIZ / "apuracao" / "painel_apuracao.py", title="Apuração ao vivo", icon="📡", url_path="apuracao"),
]
st.navigation(paginas, position="hidden").run()  # navegação pelos cards e pela barra
rodape_desenvolvedor()  # créditos em todas as páginas
