"""Visual, formatação e componentes comuns aos dois cenários (nacional e estadual)."""
import base64
import hmac
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

pio.templates["painel"] = go.layout.Template(pio.templates["plotly_white"])
pio.templates["painel"].layout.paper_bgcolor = "rgba(0,0,0,0)"
pio.templates["painel"].layout.plot_bgcolor = "rgba(0,0,0,0)"
pio.templates.default = "painel"
px.defaults.template = "painel"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@700;900&family=Manrope:wght@400;600;800&display=swap');
html, body, [class*="st-"], .stMarkdown {font-family: 'Manrope', Arial, sans-serif;}
/* não sobrescrever a fonte dos ícones do Streamlit (senão aparece o nome do ícone, ex.: "double_arrow_right") */
[data-testid="stIconMaterial"], [class*="material-symbols"], [class*="material-icons"] {
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;}
/* página inicial: cards de navegação */
[class*="st-key-card_"] {background: #FFFFFF; border: 1px solid #D9E1EC; border-radius: 22px; padding: 22px 22px 14px;
    box-shadow: 0 6px 22px rgba(27,42,65,.08); height: 100%;}
[class*="st-key-card_"] .card-icone {font-size: 2.6rem; line-height: 1;}
[class*="st-key-card_"] .card-selo {font: 800 .72rem 'Manrope'; letter-spacing: .14em; color: #5B6477; margin-top: 10px;}
[class*="st-key-card_"] .card-titulo {font: 900 1.7rem/1.1 'Archivo'; color: #1B2A41; margin: 4px 0 8px;}
[class*="st-key-card_"] .card-texto {font: 600 .95rem 'Manrope'; color: #3A4458;}
[class*="st-key-card_"] .card-numero {font: 900 2rem 'Archivo'; margin-top: 10px;}
[class*="st-key-card_"] [data-testid="stPageLink"] a {background: #1B2A41; border-radius: 12px; justify-content: center;
    padding: .55rem 1rem;}
[class*="st-key-card_"] [data-testid="stPageLink"] a p {color: #FFFFFF !important; font-weight: 800;}
.st-key-card_br {border-top: 6px solid #C8102E;} .st-key-card_ma {border-top: 6px solid #1F6FB2;}
.st-key-card_ap {border-top: 6px solid #0F5132;}
.st-key-compartilhar [data-testid="stLinkButton"] a {background: #25D366 !important; border-color: #25D366 !important;
    color: #FFFFFF !important; font-weight: 800; border-radius: 14px;}
.desenvolvedor {display: flex; align-items: center; justify-content: center; gap: 14px; margin: 28px 0 8px;
                padding: 10px 18px; border-radius: 16px; background: linear-gradient(100deg, #122545, #1d3a66);}
.desenvolvedor span {color: rgba(255,255,255,.8); font: 600 .78rem 'Manrope', sans-serif; letter-spacing: .08em;}
.desenvolvedor img {height: 54px;}
@media (max-width: 760px) {.desenvolvedor {flex-direction: column; gap: 6px;} .desenvolvedor img {height: 46px;}}
[class*="st-key-barra_nav"] [data-testid="stPageLink"] a {background: #FFFFFF; border: 1px solid #D9E1EC;
    border-radius: 999px; justify-content: center; padding: .2rem .6rem;}
h1, h2, h3, h4 {font-family: 'Archivo', Arial, sans-serif !important; color: #1B2A41;}
.block-container {padding-top: 4.2rem; max-width: 1400px;}
[data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #D9E1EC; border-radius: 14px; padding: 10px 14px;}
[data-testid="stMetricValue"] {font-family: 'Archivo', Arial, sans-serif; font-weight: 900; color: #1B2A41;}
[class*="st-key-caixa_"] {background: linear-gradient(180deg, #EEF3FA 0px, #FFFFFF 180px); border: 1px solid #D9E1EC;
    border-top: 4px solid #1B2A41; border-radius: 14px; padding: 10px 10px 8px;}
.capa {border-radius: 22px; padding: 22px 26px; color: #fff; margin-bottom: 12px;}
.capa .selo {font: 800 .72rem 'Manrope'; letter-spacing: .12em; opacity: .9;}
.capa .titulo {font: 900 2.3rem/1.05 'Archivo'; margin: 6px 0;}
.capa .sub {font: 600 .95rem 'Manrope'; opacity: .92;}
.placar {display: flex; gap: 14px; margin-top: 14px; flex-wrap: wrap;}
.placar .lado {flex: 1; min-width: 220px; background: rgba(255,255,255,.14); border-radius: 16px; padding: 12px 16px;}
.placar .nome {font: 900 1.2rem 'Archivo';}
.placar .prob {font: 900 2.6rem/1.1 'Archivo';}
.placar .leg {font: 600 .8rem 'Manrope'; opacity: .9;}
.cartao {border-radius: 14px; padding: 14px 18px; background: #FFFFFF; border: 1px solid #D9E1EC;
         border-left: 6px solid #1B2A41; margin-bottom: 10px;}
.cartao.azul {border-left-color: #1F6FB2;} .cartao.laranja {border-left-color: #E07B1F;}
.cartao.vermelho {border-left-color: #C8102E;} .cartao.verde {border-left-color: #1F7A4D;}
.cartao.alerta {border-left-color: #C0392B; background: #FFF6F4;}
.cartao h4 {margin: 0 0 4px 0;}
@media (max-width: 760px) {
  .block-container {padding-left: 1rem; padding-right: 1rem;}
  .capa .titulo {font-size: 1.6rem;} .placar .prob {font-size: 2rem;}
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {flex-wrap: wrap; gap: .6rem;}
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"] {
      flex: 1 1 calc(50% - .6rem) !important; min-width: calc(50% - .6rem) !important;}
}
</style>
"""


def exigir_senha():
    """Com APP_PASSWORD (ou PAINEL_SENHA) definida, pede senha antes de mostrar qualquer página."""
    senha = os.environ.get("APP_PASSWORD") or os.environ.get("PAINEL_SENHA", "")
    if not senha or st.session_state.get("_ok"):
        return
    st.markdown("### 🔒 Painel restrito")
    with st.form("login"):
        d = st.text_input("Senha de acesso", type="password")
        if st.form_submit_button("Entrar"):
            if hmac.compare_digest(d.encode(), senha.encode()):
                st.session_state._ok = True
                st.rerun()
            st.error("Senha incorreta.")
    st.stop()


def n(x, casas=0):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, casas=0):
    return n(100 * x, casas) + "%"


_cont = [0]


def caixa():
    _cont[0] += 1
    return st.container(key=f"caixa_{_cont[0]}")


def grafico(fig, **kw):
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    with caixa():
        st.plotly_chart(fig, width="stretch", **kw)


def tabela(df, **kw):
    df = df.reset_index(drop=True)
    fmt = {c: (lambda v, c=c: "" if pd.isna(v) else n(v, 1 if any(t in str(c) for t in ("%", "Prob", "pts")) else 0))
           for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    est = df.style.format(fmt).apply(
        lambda l: [f"background-color: {'#EEF3FA' if l.name % 2 else '#FFFFFF'}"] * len(l), axis=1)
    kw.setdefault("hide_index", True)
    kw.setdefault("width", "stretch")
    with caixa():
        st.dataframe(est, **kw)


PAGINAS = {"inicio": ("inicio.py", "🏠 Início"), "br": ("nacional/painel_nacional.py", "🌎 Brasil"),
           "ma": ("painel_governo_ma.py", "🏛️ Maranhão"), "ap": ("apuracao/painel_apuracao.py", "📡 Apuração")}


def barra_navegacao(atual):
    """Atalhos entre as páginas (só quando o painel roda pelo app.py, que registra as páginas)."""
    try:
        with st.container(key="barra_nav"):
            cols = st.columns(len(PAGINAS))
            for col, (chave, (arq, rotulo)) in zip(cols, PAGINAS.items()):
                if chave != atual:
                    col.page_link(arq, label=rotulo, width="stretch")
                else:
                    col.markdown(f"<div style='text-align:center;font-weight:800;padding:.35rem'>{rotulo}</div>",
                                 unsafe_allow_html=True)
    except Exception:  # página rodando sozinha (streamlit run <página>): sem atalhos
        pass


@st.cache_data
def _logo_base64():
    arq = Path(__file__).resolve().parent / "assets" / "aggilli_logo_web.webp"
    return base64.b64encode(arq.read_bytes()).decode() if arq.exists() else ""


def rodape_desenvolvedor():
    """Faixa de créditos com a logomarca da Aggilli Intelligence (rodapé de todas as páginas)."""
    logo = _logo_base64()
    if logo:
        st.markdown(f'''<div class="desenvolvedor"><span>DESENVOLVIDO POR</span>
<img src="data:image/webp;base64,{logo}" alt="Aggilli Intelligence"></div>''', unsafe_allow_html=True)
