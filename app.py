"""Painel de previsão eleitoral 2026 — entrada única.

Rodar:  streamlit run app.py
Páginas: 2º turno presidencial (previsão + apuração ao vivo + Maranhão + Tuntum) e, como arquivo do 1º turno,
Cenário Nacional (Lula × Flávio Bolsonaro), Cenário Estadual MA (Braide × Orleans) e Apuração ao vivo.
"""
from pathlib import Path

import streamlit as st

from comum import CSS, exigir_senha, rodape_desenvolvedor

RAIZ = Path(__file__).resolve().parent
_ICONE = RAIZ / "assets" / "aggilli_logo.png"  # favicon da Aggilli
st.set_page_config(page_title="Eleições 2026 · Previsão", page_icon=str(_ICONE) if _ICONE.exists() else "🗳️",
                   layout="wide")


@st.cache_resource
def _previa_do_link():
    """Miniatura do link no WhatsApp: grava as tags og: no HTML do Streamlit uma vez por processo."""
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
    st.Page(RAIZ / "segundo_turno" / "painel_2t.py", title="2º turno · Lula × Flávio", icon="🗳️",
            url_path="segundo_turno"),
    st.Page(RAIZ / "nacional" / "painel_nacional.py", title="Cenário Nacional · Lula × Flávio", icon="🌎",
            url_path="nacional"),
    st.Page(RAIZ / "painel_governo_ma.py", title="Cenário Estadual MA · Braide × Orleans", icon="🏛️",
            url_path="maranhao"),
    st.Page(RAIZ / "apuracao" / "painel_apuracao.py", title="Apuração ao vivo", icon="📡", url_path="apuracao"),
]
pagina = st.navigation(paginas, position="hidden")  # navegação pelos cards e pela barra
pagina.run()
if getattr(pagina, "url_path", "") not in ("", "inicio", "segundo_turno"):  # essas páginas já têm os créditos completos
    rodape_desenvolvedor()
