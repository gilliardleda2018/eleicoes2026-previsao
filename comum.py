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
# tom moderno e sóbrio: tinta azul-ardósia, grade quase invisível, barras com cantos arredondados
_lay = pio.templates["painel"].layout
_lay.font = dict(family="Manrope, Arial, sans-serif", size=13, color="#3A4458")
_lay.title = dict(font=dict(family="Archivo, Arial, sans-serif", size=16, color="#1B2A41"), x=0, xanchor="left")
for _eixo in (_lay.xaxis, _lay.yaxis):
    _eixo.gridcolor = "#E9EEF5"
    _eixo.linecolor = "#D5DCE6"
    _eixo.zeroline = False
    _eixo.tickfont = dict(color="#5B6477", size=12)
    _eixo.title = dict(font=dict(color="#5B6477", size=12))
_lay.hoverlabel = dict(bgcolor="#FFFFFF", bordercolor="#D5DCE6", font=dict(family="Manrope, Arial", color="#1B2A41"))
_lay.legend = dict(font=dict(color="#3A4458", size=12), bgcolor="rgba(0,0,0,0)")
_lay.barcornerradius = 4
_lay.bargap = 0.28
_lay.bargroupgap = 0.08
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
[class*="st-key-card_"] {background: #FFFFFF; border: 1.5px solid #C9D3E0; border-radius: 22px; padding: 22px 22px 14px;
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
/* veredito em perguntas e respostas */
.respostas {display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 14px;}
.resp {background: #FFFFFF; border: 1px solid #D9E1EC; border-top: 5px solid var(--cor, #1B2A41); border-radius: 16px;
       padding: 12px 16px;}
.resp .perg {font: 700 .9rem 'Manrope'; color: #5B6477;}
.resp .fala {font: 900 1.45rem/1.15 'Archivo'; color: var(--cor, #1B2A41); margin: 6px 0 4px;}
.resp .obs {font: 600 .85rem/1.35 'Manrope'; color: #3A4458;}
@media (max-width: 900px) {.respostas {grid-template-columns: repeat(2, 1fr);}}
@media (max-width: 520px) {.respostas {grid-template-columns: 1fr;}}
h1, h2, h3, h4 {font-family: 'Archivo', Arial, sans-serif !important; color: #1B2A41;}
.block-container {padding-top: 4.2rem; max-width: 1400px;}
/* ---- tom moderno: superfícies brancas, sombras suaves, filete em degradê ---- */
.stApp {background: radial-gradient(1200px 500px at 100% -10%, #EEF1FB 0%, rgba(238,241,251,0) 60%),
                    radial-gradient(900px 400px at -10% 0%, #F1F6F4 0%, rgba(241,246,244,0) 55%), #F6F8FB;}
[data-testid="stMetric"] {background: #FFFFFF; border: 1.5px solid #C9D3E0; border-radius: 16px; padding: 12px 16px;
    box-shadow: 0 1px 2px rgba(27,42,65,.04), 0 8px 24px rgba(27,42,65,.05); transition: box-shadow .2s, transform .2s;}
[data-testid="stMetric"]:hover {box-shadow: 0 2px 4px rgba(27,42,65,.06), 0 14px 32px rgba(27,42,65,.09); transform: translateY(-1px);}
[data-testid="stMetricLabel"] p {font: 700 .78rem 'Manrope', sans-serif !important; letter-spacing: .04em; color: #5B6477 !important;
    text-transform: uppercase;}
[data-testid="stMetricValue"] {font-family: 'Archivo', Arial, sans-serif; font-weight: 900; color: #1B2A41;}
[data-testid="stMetricDelta"] {font-weight: 700;}
/* "concha": cada gráfico e tabela dentro de uma moldura com contorno nítido + anel interno claro */
[class*="st-key-caixa_"] {background: linear-gradient(90deg, #1F6FB2, #6D5BA8 50%, #C2477F) top / 100% 3px no-repeat,
    #FFFFFF; border: 1.5px solid #C9D3E0; border-radius: 18px; padding: 16px 14px 10px; overflow: hidden;
    outline: 1px solid #E3E9F1; outline-offset: -7px;
    box-shadow: 0 1px 2px rgba(27,42,65,.05), 0 10px 28px rgba(27,42,65,.07); margin: 6px 0 14px;}
/* tabela dentro da concha: contorno próprio, cantos arredondados */
[class*="st-key-caixa_"] [data-testid="stDataFrame"] {border: 1px solid #C9D3E0; border-radius: 12px; overflow: hidden;}
/* separadores entre blocos */
hr, [data-testid="stDivider"] {border: none !important; height: 1px !important; margin: 18px 0 !important;
    background: linear-gradient(90deg, rgba(201,211,224,0), #C9D3E0 15%, #C9D3E0 85%, rgba(201,211,224,0)) !important;}
.capa {border-radius: 22px; padding: 22px 26px; color: #fff; margin-bottom: 12px;
       box-shadow: 0 14px 40px rgba(27,42,65,.18);}
.capa .selo {font: 800 .72rem 'Manrope'; letter-spacing: .12em; opacity: .9;}
.capa .titulo {font: 900 2.3rem/1.05 'Archivo'; margin: 6px 0;}
.capa .sub {font: 600 .95rem 'Manrope'; opacity: .92;}
.placar {display: flex; gap: 14px; margin-top: 14px; flex-wrap: wrap;}
.placar .lado {flex: 1; min-width: 220px; background: rgba(255,255,255,.14); border-radius: 16px; padding: 12px 16px;}
.placar .nome {font: 900 1.2rem 'Archivo';}
.placar .prob {font: 900 2.6rem/1.1 'Archivo';}
.placar .leg {font: 600 .8rem 'Manrope'; opacity: .9;}
.cartao {border-radius: 16px; padding: 14px 18px; background: #FFFFFF; border: 1.5px solid #C9D3E0;
         box-shadow: 0 1px 2px rgba(27,42,65,.04), 0 8px 24px rgba(27,42,65,.05);
         border-left: 6px solid #1B2A41; margin-bottom: 10px;}
.cartao.azul {border-left-color: #1F6FB2;} .cartao.laranja {border-left-color: #E07B1F;}
.cartao.vermelho {border-left-color: #C8102E;} .cartao.verde {border-left-color: #1F7A4D;}
.cartao.alerta {border-left-color: #C0392B; background: #FFF6F4;}
.cartao h4 {margin: 0 0 4px 0;}
.pequeno {font-size: .85rem; opacity: .75;}
/* placar da apuração de presidente: Lula (vermelho) × Flávio (azul), fotos acima dos quadros */
.placar-pres {display: flex; align-items: flex-end; justify-content: center; gap: 18px; margin: 8px 0 4px;}
.pl-lado {flex: 1; max-width: 460px; display: flex; flex-direction: column; align-items: center;}
.pl-foto {width: 132px; height: 132px; border-radius: 50%; overflow: hidden; margin-bottom: -40px; z-index: 2;
    border: 5px solid #FFFFFF; box-shadow: 0 0 0 3px var(--cor), 0 10px 24px rgba(27,42,65,.18); background: #FFFFFF;}
.pl-foto img {width: 100%; height: 100%; object-fit: cover; object-position: top;}
.pl-ini {width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: #FFFFFF;
    font: 900 2.6rem 'Archivo';}
.pl-quadro {width: 100%; border-radius: 22px; padding: 52px 18px 18px; text-align: center; color: #FFFFFF;
    box-shadow: 0 14px 34px rgba(27,42,65,.20);}
.pl-nome {font: 800 .9rem 'Manrope'; letter-spacing: .12em; opacity: .92;}
.pl-votos {font: 900 3.4rem/1.05 'Archivo'; margin: 6px 0 2px; letter-spacing: -.02em;}
.pl-pct {font: 700 1.05rem 'Manrope'; opacity: .95;}
.pl-x {align-self: center; margin-top: 70px; width: 56px; height: 56px; border-radius: 50%; background: #FFFFFF;
    border: 1.5px solid #C9D3E0; display: flex; align-items: center; justify-content: center;
    font: 900 1.6rem 'Archivo'; color: #1B2A41; box-shadow: 0 6px 16px rgba(27,42,65,.12); flex: 0 0 auto;}
.pl-dif {text-align: center; font: 800 .95rem 'Manrope'; color: #3A4458; margin: 10px 0 14px;}
.pl-legenda {text-align: center; font: 900 1.7rem/1.1 'Archivo'; letter-spacing: .08em; color: #1B2A41;
    margin: 18px 0 6px;}
.placar-tuntum {display: flex; align-items: stretch; justify-content: center; gap: 18px;}
.pt-quadro {flex: 1; max-width: 460px; border-radius: 18px; padding: 14px 18px; text-align: center; background: #FFFFFF;
    border: 1.5px solid #C9D3E0; border-top: 6px solid var(--cor); box-shadow: 0 8px 22px rgba(27,42,65,.08);}
.pt-nome {font: 800 .82rem 'Manrope'; letter-spacing: .12em; color: var(--cor);}
.pt-votos {font: 900 2.4rem/1.1 'Archivo'; color: #1B2A41; margin: 4px 0 2px;}
.pt-pct {font: 700 .9rem 'Manrope'; color: #5B6477;}
.pl-x.pequeno-x {margin-top: 0; font-size: 1.2rem;}
@media (max-width: 640px) {.pl-votos {font-size: 2.1rem;} .pl-foto {width: 96px; height: 96px; margin-bottom: -30px;}
  .pl-quadro {padding-top: 38px;} .placar-pres {gap: 8px;} .pl-x {width: 40px; height: 40px; font-size: 1.1rem;}
  .pl-legenda {font-size: 1.25rem;} .pt-votos {font-size: 1.7rem;} .placar-tuntum {gap: 8px;}}
/* cartão de Tuntum (apuração dos deputados): Bruna grande; Abigail e Eric menores, do mesmo tamanho */
.tuntum {border: 1.5px solid #C9D3E0; border-radius: 20px; padding: 16px 20px; margin: 4px 0 12px; color: #1B2A41;
    background: radial-gradient(600px 220px at 0% 0%, rgba(224,37,151,.10), rgba(224,37,151,0) 70%), #FFFFFF;
    outline: 1px solid #E3E9F1; outline-offset: -7px; box-shadow: 0 1px 2px rgba(27,42,65,.05), 0 10px 28px rgba(27,42,65,.07);}
.tuntum .tt-selo {font: 800 .74rem 'Manrope'; letter-spacing: .12em; color: #5B6477;}
.tuntum .tt-corpo {display: flex; gap: 24px 48px; align-items: center; margin-top: 8px; flex-wrap: wrap;}
.tuntum .tt-bruna {flex: 0 1 auto; min-width: 280px; border-left: 7px solid #E02597; padding: 6px 0 6px 18px;}
.tuntum .tt-nome {font: 800 1.25rem 'Manrope'; color: #E02597;}
.tuntum .tt-num {font: 900 5.6rem/1 'Archivo'; color: #1B2A41; margin: 6px 0 4px; letter-spacing: -.02em;}
.tuntum .tt-leg {font: 600 1rem 'Manrope'; color: #5B6477;}
.tuntum .tt-outros {flex: 0 0 auto; margin: 0 auto; display: flex; gap: 14px; align-items: stretch;}  /* centralizados no espaço livre */
.tuntum .tt-outro {width: 210px; border: 1px solid #E3E9F1; border-top: 4px solid var(--cor); border-radius: 14px;
    padding: 10px 12px; background: #FAFBFD;}
.tuntum .tt-nome2 {font: 800 .85rem 'Manrope'; color: var(--cor);}
.tuntum .tt-num2 {font: 900 1.6rem/1.1 'Archivo'; color: #1B2A41; margin: 4px 0 2px;}
.tuntum .tt-leg2 {font: 600 .78rem 'Manrope'; color: #5B6477;}
@media (max-width: 760px) {.tuntum .tt-num {font-size: 4rem;} .tuntum .tt-outros {margin: 0; width: 100%;}
  .tuntum .tt-outro {flex: 1; width: auto;}}
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


# ---------------------------------------------------------------- tabelas com vida (cores suaves)
# cor de cada candidato (identidade; a mesma dos gráficos) — nas tabelas entra só como tinta clara
CORES_CANDIDATOS = {"lula": "#C8102E", "flavio": "#1D4E89", "braide": "#1F6FB2", "orleans": "#E07B1F",
                    "camarao": "#B83A4B", "rocha": "#6B4FA0", "bruna": "#E02597", "abigail": "#E8702A",
                    "eric": "#3B6FB6"}
_ZEBRA = ("#FFFFFF", "#F7F9FC")
_POSITIVO, _NEGATIVO, _NEUTRO, _AZUL = "#1F9D74", "#D0546A", "#8A94A6", "#3A6FB0"
_SINAIS = ("diferença", "desvio", "saldo", "vantagem", "vs.", "variação")


def _sem_acento(txt):
    import unicodedata
    return unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode().lower()


def _mistura(cor, fundo, t):
    """Mistura cor sobre o fundo (t = 0 → só fundo; 1 → só a cor)."""
    a = [int(cor[k:k + 2], 16) for k in (1, 3, 5)]
    b = [int(fundo[k:k + 2], 16) for k in (1, 3, 5)]
    return "#" + "".join(f"{round(y + (x - y) * t):02x}" for x, y in zip(a, b))


def _candidato(txt):
    t = _sem_acento(txt)
    return next((c for c in CORES_CANDIDATOS if c in t), None)


def _estilo_tabela(df, modo="auto"):
    """Fundo de cada célula: zebra suave + tinta pelo papel da coluna (identidade, magnitude ou sinal).
    modo="identidade": linhas de unidades diferentes (ex.: placar) — só a tinta fixa do candidato em cada coluna."""
    estilos = pd.DataFrame("", index=df.index, columns=df.columns)
    zebra = [_ZEBRA[i % 2] for i in range(len(df))]
    for col in df.columns:
        nome = _sem_acento(col)
        serie = df[col]
        cand = _candidato(col)
        if modo == "identidade":
            cores = [_mistura(CORES_CANDIDATOS[cand], z, .10) if cand else None for z in zebra]
        elif pd.api.types.is_numeric_dtype(serie) and not pd.api.types.is_bool_dtype(serie):
            v = pd.to_numeric(serie, errors="coerce")
            sinal = any(k in nome for k in _SINAIS) or (v.min() < 0 < v.max())
            if sinal:  # divergente: verde-água (positivo) × rosado (negativo), intensidade pelo tamanho
                m = v.abs().max() or 1
                cores = [None if pd.isna(x) else _mistura(_POSITIVO if x >= 0 else _NEGATIVO, z, .08 + .22 * abs(x) / m)
                         for x, z in zip(v, zebra)]
            elif cand or any(k in nome for k in ("%", "prob", "chance")):  # magnitude: uma só cor, clara → média
                base = CORES_CANDIDATOS[cand] if cand else _AZUL
                lo, hi = v.min(), v.max()
                rng = (hi - lo) or 1
                cores = [None if pd.isna(x) else _mistura(base, z, .05 + .23 * (x - lo) / rng) for x, z in zip(v, zebra)]
            else:
                cores = [None] * len(v)
        else:  # texto: situação (acima/abaixo/dentro) ou nome de candidato
            cores = []
            for x, z in zip(serie, zebra):
                t = _sem_acento(x)
                if "acima" in t or t.startswith("sim"):
                    cores.append(_mistura(_POSITIVO, z, .16))
                elif "abaixo" in t:
                    cores.append(_mistura(_NEGATIVO, z, .16))
                elif any(k in t for k in ("dentro do esperado", "neutro", "empate", "indefinido")):
                    cores.append(_mistura(_NEUTRO, z, .12))
                elif _candidato(t) and len(t.split()) <= 3:  # a célula É um nome (não uma frase que cita alguém)
                    cores.append(_mistura(CORES_CANDIDATOS[_candidato(t)], z, .16))
                else:
                    cores.append(None)
        estilos[col] = [f"background-color: {c or z}; color: #1B2A41" for c, z in zip(cores, zebra)]
    return estilos


def tabela(df, modo="auto", **kw):
    """st.dataframe com números no padrão brasileiro e cores suaves: zebra, tinta do candidato nas colunas dele,
    verde-água/rosado para diferenças (+/−) e para situações acima/abaixo do esperado."""
    df = df.reset_index(drop=True)
    fmt = {c: (lambda v, c=c: "" if pd.isna(v) else n(v, 1 if any(t in str(c) for t in ("%", "Prob", "pts")) else 0))
           for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    for c in df.columns:  # probabilidade guardada de 0 a 1 aparece como porcentagem
        if "prob" in _sem_acento(c) and pd.api.types.is_numeric_dtype(df[c]) and df[c].max() <= 1:
            fmt[c] = lambda v: "" if pd.isna(v) else pct(v)
    try:
        est = df.style.format(fmt).apply(lambda _: _estilo_tabela(df, modo), axis=None)
    except Exception:  # noqa: BLE001  (nunca derruba a página por causa de cor)
        est = df.style.format(fmt).apply(
            lambda l: [f"background-color: {_ZEBRA[l.name % 2]}"] * len(l), axis=1)
    kw.setdefault("hide_index", True)
    kw.setdefault("width", "stretch")
    with caixa():
        st.dataframe(est, **kw)


def chance_amigavel(p):
    """Probabilidade sem falsa precisão: 'menos de 1%' em vez de 0%."""
    return "menos de 1%" if p < .01 else "mais de 99%" if p > .99 else pct(p)


def em_palavras(p):
    """Chance de 'sim' em linguagem de conversa."""
    for lim, txt in [(.99, "Quase certeza que sim"), (.85, "Muito provável"), (.65, "Provável"),
                     (.35, "Cara ou coroa"), (.15, "Pouco provável"), (.01, "Muito difícil")]:
        if p >= lim:
            return txt
    return "Quase impossível"


def veredito_simples(a, b, cor_a, cor_b, p2t, pa_1t, va_2t, pa):
    """Os 4 cartões do veredito em pergunta e resposta. a/b = nomes; p2t = chance de 2º turno;
    pa_1t = chance de A levar no 1º turno; va_2t = % de A nos válidos do 2º turno; pa = chance de A ser eleito."""
    fav, outro, cfav, pfav = (a, b, cor_a, pa) if pa >= .5 else (b, a, cor_b, 1 - pa)
    fala_fav = (f"{fav}, com folga" if pfav >= .9 else f"{fav}, mas nada decidido" if pfav >= .65
                else f"{fav}, por pouco" if pfav >= .55 else "Empate técnico")
    (n1, v1, c1), (n2, v2) = ((a, va_2t, cor_a), (b, 100 - va_2t)) if va_2t >= 50 else ((b, 100 - va_2t, cor_b), (a, va_2t))
    dif = v1 - v2
    clima = (f"Tá apertado: só {n(dif, 1)} pontos de diferença." if dif < 3
             else f"{n1} na frente por {n(dif, 1)} pontos." if dif < 8 else f"{n1} com folga de {n(dif, 1)} pontos.")
    x = min(max(round(100 * pfav), 1), 99)
    cartoes = [
        ("Vai ter 2º turno?", em_palavras(p2t), "#1B2A41",
         f"Chance: {chance_amigavel(p2t)}. " + ("Ninguém deve passar dos 50% no dia 4." if p2t >= .65
                                               else "Pode acabar já no dia 4.")),
        (f"{a} leva já no 1º turno?", em_palavras(pa_1t), cor_a,
         f"Chance: {chance_amigavel(pa_1t)}. Precisaria de mais da metade dos votos válidos."),
        ("E o placar do 2º turno?", f"{n1} {n(v1, 1)}% × {n2} {n(v2, 1)}%", c1,
         f"{clima} (votos válidos, no palpite mais provável)"),
        ("Quem é o favorito?", fala_fav, cfav,
         f"De cada 100 eleições simuladas, {fav} ganha {x} e {outro} ganha {100 - x}."),
    ]
    st.markdown('<div class="respostas">' + "".join(
        f'<div class="resp" style="--cor:{cor}"><div class="perg">{perg}</div><div class="fala">{fala}</div>'
        f'<div class="obs">{obs}</div></div>' for perg, fala, cor, obs in cartoes) + "</div>", unsafe_allow_html=True)


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
