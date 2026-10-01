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
_lay.title = dict(font=dict(family="Montserrat, Arial, sans-serif", size=16, color="#1B2A41"), x=0, xanchor="left")
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
/* fontes modernas servidas pelo próprio app (static/fonts, licença OFL), com o Google Fonts como reserva */
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;500;600;700;800;900&family=Manrope:wght@400;600;800&display=swap');
@font-face {font-family: 'Montserrat'; src: url('/app/static/fonts/Montserrat.ttf') format('truetype'); font-weight: 100 900; font-display: swap;}
@font-face {font-family: 'Manrope'; src: url('/app/static/fonts/Manrope.ttf') format('truetype'); font-weight: 200 800; font-display: swap;}
html, body, [class*="st-"], .stMarkdown {font-family: 'Manrope', Arial, sans-serif;}
/* não sobrescrever a fonte dos ícones do Streamlit (senão aparece o nome do ícone, ex.: "double_arrow_right") */
[data-testid="stIconMaterial"], [class*="material-symbols"], [class*="material-icons"] {
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;}
/* página inicial: cards de navegação */
/* página inicial: capa */
.capa-inicio {position: relative; overflow: hidden; text-align: center; margin: 4px 0 22px; padding: 34px 22px 28px;
    border-radius: 26px; color: #FFFFFF; box-shadow: 0 14px 34px rgba(11,22,40,.22);
    background: radial-gradient(circle at 12% 0%, rgba(34,211,238,.28), transparent 42%),
                radial-gradient(circle at 92% 100%, rgba(200,16,46,.30), transparent 45%),
                linear-gradient(120deg, #0B1628, #16304F 55%, #1B2A41);}
.capa-inicio .ci-selo {font: 800 .78rem 'Manrope'; letter-spacing: .22em; color: #67E8F9;}
.capa-inicio .ci-titulo {font: 900 2.9rem/1.05 'Montserrat'; margin: 8px 0 10px; letter-spacing: -.01em;}
.capa-inicio .ci-titulo span {background: linear-gradient(90deg, #22D3EE, #FEDF00); -webkit-background-clip: text;
    background-clip: text; color: transparent;}
.capa-inicio .ci-texto {font: 600 1.02rem/1.5 'Manrope'; color: rgba(230,246,251,.88); max-width: 720px; margin: 0 auto;}
.capa-inicio .ci-contagem {display: inline-flex; align-items: center; gap: 10px; margin-top: 18px; padding: 9px 18px;
    border-radius: 999px; font: 800 .92rem 'Manrope'; background: rgba(255,255,255,.10);
    border: 1px solid rgba(255,255,255,.22); backdrop-filter: blur(6px);}
.capa-inicio .ci-contagem i {width: 10px; height: 10px; border-radius: 50%; background: #22C55E;
    box-shadow: 0 0 0 0 rgba(34,197,94,.7); animation: pulso 1.8s infinite;}
@keyframes pulso {70% {box-shadow: 0 0 0 10px rgba(34,197,94,0);} 100% {box-shadow: 0 0 0 0 rgba(34,197,94,0);}}
/* página inicial: cards simétricos */
[data-testid="stHorizontalBlock"]:has(.st-key-card_br) {align-items: stretch;}
[data-testid="stColumn"]:has([class*="st-key-card_"]) > div {height: 100%;}
[class*="st-key-card_"] {background: linear-gradient(180deg, #FFFFFF, #F6F9FC); border: 1.5px solid #D6DEE9;
    border-radius: 24px; padding: 22px 22px 16px; box-shadow: 0 10px 26px rgba(27,42,65,.09); height: 100%;
    text-align: center; transition: transform .18s, box-shadow .18s; justify-content: space-between;}
[class*="st-key-card_"]:hover {transform: translateY(-4px); box-shadow: 0 16px 34px rgba(27,42,65,.15);}
[class*="st-key-card_"] .card-emblema {height: 118px; display: flex; align-items: center; justify-content: center;}
[class*="st-key-card_"] .bandeira {width: 152px; height: 106px; filter: drop-shadow(0 10px 14px rgba(27,42,65,.25));
    transform: rotate(-3deg);}
[class*="st-key-card_"] .emblema-icone {font-size: 5.6rem; line-height: 1; filter: drop-shadow(0 10px 14px rgba(27,42,65,.25));}
[class*="st-key-card_"] .card-selo {font: 800 .72rem 'Manrope'; letter-spacing: .16em; color: #5B6477; margin-top: 12px;
    display: flex; justify-content: center; align-items: center; gap: 8px;}
[class*="st-key-card_"] .card-selo em {font-style: normal; text-transform: uppercase; color: #FFFFFF; background: #0F5132;
    padding: 2px 9px; border-radius: 999px; font-size: .64rem;}
[class*="st-key-card_"] .card-titulo {font: 900 1.65rem/1.1 'Montserrat'; color: #1B2A41; margin: 6px 0 6px;}
[class*="st-key-card_"] .card-texto {font: 600 .93rem 'Manrope'; color: #3A4458; min-height: 2.6em;}
[class*="st-key-card_"] .card-probs {display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px;}
[class*="st-key-card_"] .card-prob {position: relative; overflow: hidden; padding: 10px 6px 12px; border-radius: 16px;
    background: #FFFFFF; border: 1px solid #E2E8F0;}
[class*="st-key-card_"] .card-prob b {display: block; font: 900 1.9rem/1 'Montserrat';}
[class*="st-key-card_"] .card-prob span {font: 800 .8rem 'Manrope'; color: #3A4458; letter-spacing: .04em;}
[class*="st-key-card_"] .card-prob i {position: absolute; left: 0; bottom: 0; height: 4px; border-radius: 0 4px 4px 0;}
[class*="st-key-card_"] .card-chips {display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 14px;
    min-height: 4.3rem; align-content: center;}
[class*="st-key-card_"] .card-chip {font: 800 .85rem 'Manrope'; color: #0F5132; background: #E0F2E9;
    border: 1px solid #B7DFC9; border-radius: 999px; padding: 6px 13px;}
[class*="st-key-card_"] .card-legenda {font: 700 .8rem 'Manrope'; color: #5B6477; margin: 8px 0 4px; letter-spacing: .03em;}
[class*="st-key-card_"] [data-testid="stPageLink"] a {background: #1B2A41; border-radius: 14px; justify-content: center;
    padding: .6rem 1rem; transition: background .15s;}
[class*="st-key-card_"] [data-testid="stPageLink"] a:hover {background: #16304F;}
[class*="st-key-card_"] [data-testid="stPageLink"] a p {color: #FFFFFF !important; font-weight: 800;}
.st-key-card_br {border-top: 6px solid #009B3A !important;} .st-key-card_ma {border-top: 6px solid #D21034 !important;}
.st-key-card_ap {border-top: 6px solid #0F5132 !important;}
.st-key-card_ap [data-testid="stPageLink"] a {background: linear-gradient(100deg, #0F5132, #157A4C);}
@media (max-width: 760px) {.capa-inicio .ci-titulo {font-size: 2.1rem;} .capa-inicio {padding: 26px 16px 22px;}}
/* página inicial: compartilhar e créditos */
.st-key-compartilhar_inicio {max-width: 560px; margin: 26px auto 8px; padding: 16px 18px 8px; border-radius: 22px;
    border: 1.5px solid #C9D3E0; background: linear-gradient(160deg, #E0F2E9, #E6F6FB 55%, #FBE9DC);
    box-shadow: 0 8px 22px rgba(27,42,65,.07);}
.creditos-inicio {display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 24px; margin: 26px 0 6px;
    padding: 22px 26px; border-radius: 24px; color: #FFFFFF; box-shadow: 0 14px 30px rgba(11,22,40,.22);
    background: radial-gradient(circle at 0% 0%, rgba(34,211,238,.22), transparent 40%), linear-gradient(110deg, #0B1628, #16304F);}
.creditos-inicio .cr-logo img {height: 86px; display: block;}
.creditos-inicio .cr-selo {font: 800 .7rem 'Manrope'; letter-spacing: .2em; color: #67E8F9;}
.creditos-inicio .cr-nome {font: 900 1.5rem 'Montserrat';}
.creditos-inicio .cr-slogan {font: 700 1rem 'Montserrat'; color: rgba(230,246,251,.92);}
.creditos-inicio .cr-slogan span {background: linear-gradient(90deg, #22D3EE, #67E8F9); -webkit-background-clip: text;
    background-clip: text; color: transparent;}
.creditos-inicio .cr-texto {font: 600 .85rem/1.5 'Manrope'; color: rgba(230,246,251,.78); margin-top: 6px;}
.creditos-inicio .cr-texto b {color: #67E8F9;}
.creditos-inicio .cr-contato {display: flex; flex-direction: column; gap: 6px; align-items: flex-end; font: 700 .88rem 'Manrope';}
.creditos-inicio .cr-contato a {color: #E6F6FB !important; text-decoration: none; opacity: .92;}
.creditos-inicio .cr-contato a:hover {opacity: 1; text-decoration: underline;}
.nota-inicio {text-align: center; color: #5B6477; font: 600 .82rem 'Manrope'; margin-top: 8px;}
@media (max-width: 900px) {.creditos-inicio {grid-template-columns: 1fr; text-align: center; gap: 12px;}
  .creditos-inicio .cr-logo img {margin: 0 auto; height: 60px;} .creditos-inicio .cr-contato {align-items: center;}}
.st-key-compartilhar [data-testid="stLinkButton"] a {background: #25D366 !important; border-color: #25D366 !important;
    color: #FFFFFF !important; font-weight: 800; border-radius: 14px;}
.desenvolvedor {display: flex; align-items: center; justify-content: center; gap: 14px; margin: 28px 0 8px;
                padding: 10px 18px; border-radius: 16px; background: linear-gradient(100deg, #122545, #1d3a66);}
.desenvolvedor span {color: rgba(255,255,255,.8); font: 600 .78rem 'Manrope', sans-serif; letter-spacing: .08em;}
.desenvolvedor img {height: 54px;}
@media (max-width: 760px) {.desenvolvedor {flex-direction: column; gap: 6px;} .desenvolvedor img {height: 46px;}}
[class*="st-key-barra_nav"] [data-testid="stPageLink"] a {border: 1.5px solid #C9D3E0; border-radius: 999px;
    justify-content: center; padding: .25rem .7rem; box-shadow: 0 4px 12px rgba(27,42,65,.06); transition: transform .15s;}
[class*="st-key-barra_nav"] [data-testid="stPageLink"] a:hover {transform: translateY(-1px); box-shadow: 0 8px 18px rgba(27,42,65,.10);}
[class*="st-key-barra_nav"] [data-testid="stColumn"]:nth-child(4n+1) a {background: linear-gradient(160deg, #E3EDFB, #FFFFFF);}
[class*="st-key-barra_nav"] [data-testid="stColumn"]:nth-child(4n+2) a {background: linear-gradient(160deg, #E0F2E9, #FFFFFF);}
[class*="st-key-barra_nav"] [data-testid="stColumn"]:nth-child(4n+3) a {background: linear-gradient(160deg, #EBE6F9, #FFFFFF);}
[class*="st-key-barra_nav"] [data-testid="stColumn"]:nth-child(4n+4) a {background: linear-gradient(160deg, #FBE9DC, #FFFFFF);}
/* menu do topo: espaço até o bloco seguinte; no celular, uma linha só com rolagem lateral */
[class*="st-key-barra_nav"] {margin-bottom: 16px !important;}
@media (max-width: 760px) {
  [class*="st-key-barra_nav"] [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; overflow-x: auto;
      gap: 8px !important; padding: 4px 2px 8px; scrollbar-width: none;}
  [class*="st-key-barra_nav"] [data-testid="stColumn"] {flex: 0 0 auto !important; width: auto !important;
      min-width: 0 !important;}
  [class*="st-key-barra_nav"] [data-testid="stPageLink"] a, .nav-ativa {padding: .3rem .85rem !important;
      font-size: .85rem !important; white-space: nowrap;}
}
.nav-ativa {text-align: center; font: 800 .95rem 'Manrope'; padding: .42rem .7rem; border-radius: 999px; color: #FFFFFF;
    background: linear-gradient(110deg, #0E5A73, #12233F); box-shadow: 0 6px 16px rgba(18,35,63,.25);}
/* veredito em perguntas e respostas */
.respostas {display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 14px;}
.resp {background: #FFFFFF; border: 1px solid #D9E1EC; border-top: 5px solid var(--cor, #1B2A41); border-radius: 16px;
       padding: 12px 16px;}
.resp .perg {font: 700 .9rem 'Manrope'; color: #5B6477;}
.resp .fala {font: 900 1.45rem/1.15 'Montserrat'; color: var(--cor, #1B2A41); margin: 6px 0 4px;}
.resp .obs {font: 600 .85rem/1.35 'Manrope'; color: #3A4458;}
@media (max-width: 900px) {.respostas {grid-template-columns: repeat(2, 1fr);}}
@media (max-width: 520px) {.respostas {grid-template-columns: 1fr;}}
h1, h2, h3, h4 {font-family: 'Montserrat', Arial, sans-serif !important; color: #1B2A41;}
.block-container {padding-top: 4.2rem; max-width: 1400px;}
/* ---- tom moderno: superfícies brancas, sombras suaves, filete em degradê ---- */
.stApp {background: radial-gradient(1200px 500px at 100% -10%, #EEF1FB 0%, rgba(238,241,251,0) 60%),
                    radial-gradient(900px 400px at -10% 0%, #F1F6F4 0%, rgba(241,246,244,0) 55%), #F6F8FB;}
[data-testid="stMetric"] {background: #FFFFFF; border: 1.5px solid #C9D3E0; border-radius: 16px; padding: 12px 16px;
    box-shadow: 0 1px 2px rgba(27,42,65,.04), 0 8px 24px rgba(27,42,65,.05); transition: box-shadow .2s, transform .2s;}
[data-testid="stMetric"]:hover {box-shadow: 0 2px 4px rgba(27,42,65,.06), 0 14px 32px rgba(27,42,65,.09); transform: translateY(-1px);}
[data-testid="stMetricLabel"] p {font: 700 .78rem 'Manrope', sans-serif !important; letter-spacing: .04em; color: #5B6477 !important;
    text-transform: uppercase;}
[data-testid="stMetricValue"] {font-family: 'Montserrat', Arial, sans-serif; font-weight: 900; color: #1B2A41;}
[data-testid="stMetricDelta"] {font-weight: 700;}
/* "concha": cada gráfico e tabela dentro de uma moldura com contorno nítido + anel interno claro */
[class*="st-key-caixa_"] {background: linear-gradient(90deg, #1F6FB2, #6D5BA8 50%, #C2477F) top / 100% 3px no-repeat,
    #FFFFFF; border: 1.5px solid #C9D3E0; border-radius: 18px; padding: 16px 14px 10px; overflow: hidden;
    outline: 1px solid #E3E9F1; outline-offset: -7px;
    box-shadow: 0 1px 2px rgba(27,42,65,.05), 0 10px 28px rgba(27,42,65,.07); margin: 6px 0 14px;}
/* tons suaves por caixa (degradê do tom para o branco), alternando */
[class*="st-key-caixa_azul"] {background: linear-gradient(90deg, #1F6FB2, #6D5BA8 50%, #C2477F) top / 100% 3px no-repeat,
    linear-gradient(180deg, #E3EDFB 0%, #F1F6FD 100%);}
[class*="st-key-caixa_menta"] {background: linear-gradient(90deg, #1F6FB2, #6D5BA8 50%, #C2477F) top / 100% 3px no-repeat,
    linear-gradient(180deg, #E0F2E9 0%, #EFF8F3 100%);}
[class*="st-key-caixa_lilas"] {background: linear-gradient(90deg, #1F6FB2, #6D5BA8 50%, #C2477F) top / 100% 3px no-repeat,
    linear-gradient(180deg, #EBE6F9 0%, #F5F2FC 100%);}
[class*="st-key-caixa_pessego"] {background: linear-gradient(90deg, #1F6FB2, #6D5BA8 50%, #C2477F) top / 100% 3px no-repeat,
    linear-gradient(180deg, #FBE9DC 0%, #FDF4EE 100%);}
[class*="st-key-caixa_areia"] {background: linear-gradient(90deg, #1F6FB2, #6D5BA8 50%, #C2477F) top / 100% 3px no-repeat,
    linear-gradient(180deg, #F4EDDC 0%, #FAF6EC 100%);}
/* métricas: cada coluna com um tom suave */
[data-testid="stColumn"]:nth-child(5n+1) [data-testid="stMetric"] {background: linear-gradient(160deg, #E3EDFB, #FFFFFF);}
[data-testid="stColumn"]:nth-child(5n+2) [data-testid="stMetric"] {background: linear-gradient(160deg, #E0F2E9, #FFFFFF);}
[data-testid="stColumn"]:nth-child(5n+3) [data-testid="stMetric"] {background: linear-gradient(160deg, #EBE6F9, #FFFFFF);}
[data-testid="stColumn"]:nth-child(5n+4) [data-testid="stMetric"] {background: linear-gradient(160deg, #FBE9DC, #FFFFFF);}
[data-testid="stColumn"]:nth-child(5n+5) [data-testid="stMetric"] {background: linear-gradient(160deg, #F4EDDC, #FFFFFF);}
/* tabela dentro da concha: contorno próprio, cantos arredondados */
[class*="st-key-caixa_"] [data-testid="stDataFrame"] {border: 1px solid #C9D3E0; border-radius: 12px; overflow: hidden;}
/* separadores entre blocos */
hr, [data-testid="stDivider"] {border: none !important; height: 1px !important; margin: 18px 0 !important;
    background: linear-gradient(90deg, rgba(201,211,224,0), #C9D3E0 15%, #C9D3E0 85%, rgba(201,211,224,0)) !important;}
.capa {border-radius: 22px; padding: 22px 26px; color: #fff; margin: 8px 0 12px;
       box-shadow: 0 14px 40px rgba(27,42,65,.18);}
.capa .selo {font: 800 .72rem 'Manrope'; letter-spacing: .12em; opacity: .9;}
.capa .titulo {font: 900 2.3rem/1.05 'Montserrat'; margin: 6px 0;}
.capa .sub {font: 600 .95rem 'Manrope'; opacity: .92;}
.placar {display: flex; gap: 14px; margin-top: 14px; flex-wrap: wrap;}
.placar .lado {flex: 1; min-width: 220px; background: rgba(255,255,255,.14); border-radius: 16px; padding: 12px 16px;}
.placar .nome {font: 900 1.2rem 'Montserrat';}
.placar .prob {font: 900 2.6rem/1.1 'Montserrat';}
.placar .leg {font: 600 .8rem 'Manrope'; opacity: .9;}
.cartao {border-radius: 16px; padding: 14px 18px; background: linear-gradient(160deg, #EAF0F8, #FFFFFF); border: 1.5px solid #C9D3E0;
         box-shadow: 0 1px 2px rgba(27,42,65,.04), 0 8px 24px rgba(27,42,65,.05);
         border-left: 6px solid #1B2A41; margin-bottom: 10px;}
.cartao.azul {border-left-color: #1F6FB2;} .cartao.laranja {border-left-color: #E07B1F;}
.cartao.vermelho {border-left-color: #C8102E;} .cartao.verde {border-left-color: #1F7A4D;}
.cartao.alerta {border-left-color: #C0392B; background: #FFF6F4;}
.cartao.azul {background: linear-gradient(160deg, #E3EDFB, #FFFFFF);} .cartao.laranja {background: linear-gradient(160deg, #FBE9DC, #FFFFFF);}
.cartao.vermelho {background: linear-gradient(160deg, #FAE4E8, #FFFFFF);} .cartao.verde {background: linear-gradient(160deg, #E0F2E9, #FFFFFF);}
.cartao h4 {margin: 0 0 4px 0;}
.pequeno {font-size: .85rem; opacity: .75;}
/* cabeçalho da marca (apuração) */
.marca-topo {display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 22px;
    padding: 18px 26px; margin: 0 0 14px; border-radius: 22px; color: #FFFFFF;
    background: radial-gradient(700px 220px at 85% 0%, rgba(34,211,238,.22), rgba(34,211,238,0) 70%),
                linear-gradient(110deg, #0B1628 0%, #12233F 55%, #16304F 100%);
    border: 1.5px solid #22324D; box-shadow: 0 16px 40px rgba(11,22,40,.28);}
.marca-topo .mt-logo img {height: 92px; display: block; margin: -8px 0;}
.marca-topo .mt-slogan {font: 700 2rem/1.15 'Montserrat'; letter-spacing: .01em; text-align: center;}
.marca-topo .mt-slogan span {background: linear-gradient(90deg, #22D3EE, #67E8F9); -webkit-background-clip: text;
    background-clip: text; color: transparent;}
.marca-topo .mt-contato {display: flex; flex-direction: column; align-items: flex-end; gap: 4px;
    font: 600 .88rem 'Manrope';}
.marca-topo .mt-contato a {color: #E6F6FB !important; text-decoration: none; opacity: .92;}
.marca-topo .mt-contato a:hover {opacity: 1; text-decoration: underline;}
.marca-topo .mt-nome {font: 800 .8rem 'Manrope'; letter-spacing: .14em; color: #67E8F9; text-transform: uppercase;}
@media (max-width: 900px) {.marca-topo {grid-template-columns: 1fr; text-align: center; gap: 10px;}
  .marca-topo .mt-logo img {margin: 0 auto; height: 52px;} .marca-topo .mt-slogan {font-size: 1.45rem;}
  .marca-topo .mt-contato {align-items: center;}}
/* apuração: Assembleia MA em destaque no seletor (1º botão) */
.st-key-seletor_apuracao [data-testid="stColumn"]:first-child [data-testid="stButtonGroup"] button:first-of-type {
    border: 1.5px solid #E02597 !important; background: linear-gradient(120deg, #FDE7F3, #FFFFFF) !important;
    box-shadow: 0 4px 14px rgba(224,37,151,.18);}
.st-key-seletor_apuracao [data-testid="stColumn"]:first-child [data-testid="stButtonGroup"] button:first-of-type p {
    color: #B0127A !important; font-weight: 800 !important;}
.st-key-seletor_apuracao [data-testid="stColumn"]:first-child [data-testid="stButtonGroup"] button:first-of-type[kind*="Active"],
.st-key-seletor_apuracao [data-testid="stColumn"]:first-child [data-testid="stButtonGroup"] button:first-of-type[aria-checked="true"] {
    background: linear-gradient(120deg, #E02597, #8E1B7A) !important; border-color: #E02597 !important;}
.st-key-seletor_apuracao [data-testid="stColumn"]:first-child [data-testid="stButtonGroup"] button:first-of-type[kind*="Active"] p,
.st-key-seletor_apuracao [data-testid="stColumn"]:first-child [data-testid="stButtonGroup"] button:first-of-type[aria-checked="true"] p {
    color: #FFFFFF !important;}
.st-key-seletor_apuracao [data-testid="stColumn"]:first-child [data-testid="stButtonGroup"] button:first-of-type::after {
    content: "DESTAQUE"; font: 800 .56rem 'Manrope'; letter-spacing: .1em; color: #FFFFFF; background: #E02597;
    border-radius: 999px; padding: 2px 7px; margin-left: 6px;}
/* apuração: chamada da Assembleia nas páginas de Senado e Câmara */
.st-key-destaque_assembleia {padding: 16px 20px; border-radius: 20px; margin: 4px 0 14px; color: #FFFFFF;
    background: radial-gradient(circle at 100% 0%, rgba(255,255,255,.18), transparent 45%), linear-gradient(110deg, #B0127A, #E02597 55%, #8E1B7A);
    box-shadow: 0 10px 26px rgba(176,18,122,.28);}
.st-key-destaque_assembleia .da-selo {font: 800 .72rem 'Manrope'; letter-spacing: .16em; opacity: .9;}
.st-key-destaque_assembleia .da-titulo {font: 900 1.45rem/1.15 'Montserrat'; margin: 2px 0 4px;}
.st-key-destaque_assembleia .da-texto {font: 600 .92rem 'Manrope'; opacity: .92;}
.st-key-destaque_assembleia [data-testid="stBaseButton-primary"] {background: #FFFFFF !important; border: 0 !important;
    border-radius: 14px !important;}
.st-key-destaque_assembleia [data-testid="stBaseButton-primary"] p {color: #B0127A !important; font-weight: 800 !important;}
/* apuração: ranking de Senado e Câmara Federal */
.rk {border: 1.5px solid #D6DEE9; border-radius: 22px; overflow: hidden; background: #FFFFFF;
    box-shadow: 0 8px 22px rgba(27,42,65,.07); margin: 10px 0 8px;}
.rk-cab {display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; color: #FFFFFF;
    font: 900 1.05rem 'Montserrat'; letter-spacing: .04em; background: linear-gradient(110deg, #0B1628, #16304F);}
.rk.senador .rk-cab {background: linear-gradient(110deg, #0B3F8C, #12233F);}
.rk-cab span {font: 800 .75rem 'Manrope'; letter-spacing: .12em; background: rgba(255,255,255,.15);
    border-radius: 999px; padding: 4px 12px;}
.rk-linha {display: grid; grid-template-columns: 44px 48px 1fr 110px 90px 112px; align-items: center; gap: 12px;
    padding: 10px 18px; border-top: 1px solid #EDF1F6;}
.rk-linha:nth-child(even) {background: #FAFBFD;}
.rk-linha.dentro {background: linear-gradient(90deg, #EAF6EF, #FFFFFF 60%);}
.rk-linha.eleito {background: linear-gradient(90deg, #DDF3E6, #FFFFFF 70%);}
.rk-pos {font: 900 1.05rem 'Montserrat'; color: #5B6477; text-align: center;}
.rk-linha.dentro .rk-pos {color: #0F5132;}
.rk-foto img, .rk-foto span {width: 46px; height: 46px; border-radius: 50%; object-fit: cover; display: flex;
    align-items: center; justify-content: center; background: linear-gradient(135deg, #DCE5F2, #F4F7FB);
    font: 800 .9rem 'Montserrat'; color: #1B2A41; border: 2px solid #FFFFFF; box-shadow: 0 3px 8px rgba(27,42,65,.15);}
.rk-info b {display: block; font: 800 .98rem 'Montserrat'; color: #1B2A41;}
.rk-info small {font: 700 .76rem 'Manrope'; color: #5B6477; letter-spacing: .03em;}
.rk-barra {height: 6px; border-radius: 6px; background: #EDF1F6; margin-top: 6px; overflow: hidden;}
.rk-barra i {display: block; height: 100%; border-radius: 6px; background: linear-gradient(90deg, #22D3EE, #1F6FB2);}
.rk.senador .rk-barra i {background: linear-gradient(90deg, #3B82F6, #0B3F8C);}
.rk-num {text-align: right;} .rk-num b {display: block; font: 900 1.02rem 'Montserrat'; color: #1B2A41;}
.rk-num small {font: 700 .75rem 'Manrope'; color: #5B6477;}
.rk-tun b {color: #B0127A;}
.rk-st {font-style: normal; font: 800 .66rem 'Manrope'; letter-spacing: .08em; text-transform: uppercase; color: #3A4458;
    background: #EDF1F6; border-radius: 999px; padding: 4px 10px; white-space: nowrap;}
.rk-st {justify-self: end;} .rk-st.vazio {visibility: hidden;} .rk-st.dentro {color: #0F5132; background: #E0F2E9;} .rk-st.eleito {color: #FFFFFF; background: #0F5132;}
.rk-corte {position: relative; text-align: center; padding: 6px 0; border-top: 2px dashed #0F5132;
    background: #F4FAF6;}
.rk-corte span {font: 800 .7rem 'Manrope'; letter-spacing: .1em; color: #0F5132; text-transform: uppercase;}
@media (max-width: 760px) {.rk-linha {grid-template-columns: 28px 38px 1fr 76px 58px; gap: 7px; padding: 9px 10px;}
  .rk-foto img, .rk-foto span {width: 36px; height: 36px;} .rk-st {display: none;} .rk-info b {font-size: .86rem;}}
/* seletor da apuração: cartão com botões segmentados */
.st-key-seletor_apuracao {background: linear-gradient(160deg, #E3EDFB, #F1F6FD); border: 1.5px solid #C9D3E0; border-radius: 18px; padding: 14px 20px 6px;
    margin: 4px 0 14px; box-shadow: 0 1px 2px rgba(27,42,65,.05), 0 10px 28px rgba(27,42,65,.06);}
.st-key-seletor_apuracao [data-testid="stWidgetLabel"] p {font: 800 .72rem 'Manrope' !important; letter-spacing: .14em;
    text-transform: uppercase; color: #5B6477 !important;}
.st-key-seletor_apuracao [data-testid="stButtonGroup"] button {border-radius: 999px !important; padding: .35rem .95rem;
    font-weight: 700; border: 1.5px solid #D5DCE6;}
.st-key-seletor_apuracao [data-testid="stButtonGroup"] button[kind*="Active"],
.st-key-seletor_apuracao [data-testid="stButtonGroup"] button[aria-checked="true"] {
    background: linear-gradient(110deg, #0E5A73, #12233F) !important; color: #FFFFFF !important; border-color: #12233F !important;
    box-shadow: 0 6px 16px rgba(18,35,63,.25);}
.st-key-seletor_apuracao [data-testid="stButtonGroup"] button[kind*="Active"] p,
.st-key-seletor_apuracao [data-testid="stButtonGroup"] button[aria-checked="true"] p {color: #FFFFFF !important;}
/* compartilhar com ícones */
.compartilhe {text-align: center; margin: 4px 0 6px;}
.compartilhe .cp-logo {height: 58px; display: block; margin: 0 auto 10px; padding: 4px 16px; border-radius: 14px;
    background: linear-gradient(110deg, #0B1628, #16304F); box-shadow: 0 6px 16px rgba(11,22,40,.25);}
.compartilhe .cp-titulo {font: 800 1.15rem 'Montserrat'; color: #1B2A41; letter-spacing: .02em; margin-bottom: 10px;}
.compartilhe .cp-icones {display: flex; justify-content: center; gap: 26px;}
.compartilhe .cp-icones img {width: 64px; height: 64px; transition: transform .15s; filter: drop-shadow(0 6px 12px rgba(27,42,65,.18));}
.compartilhe .cp-icones a:hover img {transform: translateY(-3px) scale(1.06);}
.st-key-compartilhar_apuracao {max-width: 560px; margin: 0 auto 12px; padding: 14px 18px; border-radius: 18px;
    border: 1.5px solid #C9D3E0; background: linear-gradient(160deg, #E0F2E9, #FBE9DC);}
/* compartilhar a apuração: WhatsApp verde, Instagram em degradê */
.st-key-compartilhar_apuracao [data-testid="stLinkButton"] a {background: #25D366 !important; border-color: #25D366 !important;
    color: #FFFFFF !important; font-weight: 800; border-radius: 14px;}
.st-key-compartilhar_apuracao [data-testid="stDownloadButton"] button {border: none !important; border-radius: 14px;
    color: #FFFFFF !important; font-weight: 800;
    background: linear-gradient(45deg, #F58529, #DD2A7B 45%, #8134AF 75%, #515BD4) !important;}
.st-key-compartilhar_apuracao [data-testid="stDownloadButton"] button p {color: #FFFFFF !important; font-weight: 800;}
/* placar da apuração de presidente: Lula (vermelho) × Flávio (azul), fotos acima dos quadros */
.placar-pres {display: flex; align-items: flex-end; justify-content: center; gap: 18px; margin: 8px 0 4px;}
.pl-lado {flex: 1; max-width: 460px; display: flex; flex-direction: column; align-items: center;}
.pl-foto {width: 132px; height: 132px; border-radius: 50%; overflow: hidden; margin-bottom: -40px; z-index: 2;
    border: 5px solid #FFFFFF; box-shadow: 0 0 0 3px var(--cor), 0 10px 24px rgba(27,42,65,.18); background: #FFFFFF;}
.pl-foto img {width: 100%; height: 100%; object-fit: cover; object-position: top;}
.pl-ini {width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: #FFFFFF;
    font: 900 2.6rem 'Montserrat';}
.pl-quadro {width: 100%; border-radius: 22px; padding: 52px 18px 18px; text-align: center; color: #FFFFFF;
    box-shadow: 0 14px 34px rgba(27,42,65,.20);}
.pl-nome {font: 800 .9rem 'Manrope'; letter-spacing: .12em; opacity: .92;}
.pl-votos {font: 900 3.4rem/1.05 'Montserrat'; margin: 6px 0 2px; letter-spacing: -.02em;}
.pl-pct {font: 700 1.05rem 'Manrope'; opacity: .95;}
.pl-x {align-self: center; margin-top: 70px; width: 56px; height: 56px; border-radius: 50%; background: #FFFFFF;
    border: 1.5px solid #C9D3E0; display: flex; align-items: center; justify-content: center;
    font: 900 1.6rem 'Montserrat'; color: #1B2A41; box-shadow: 0 6px 16px rgba(27,42,65,.12); flex: 0 0 auto;}
.pl-dif {text-align: center; font: 800 .95rem 'Manrope'; color: #3A4458; margin: 10px 0 14px;}
.pl-legenda {text-align: center; font: 900 1.7rem/1.1 'Montserrat'; letter-spacing: .08em; color: #1B2A41;
    margin: 18px 0 6px;}
.placar-tuntum {display: flex; align-items: stretch; justify-content: center; gap: 18px;}
.pt-quadro {flex: 1; max-width: 460px; border-radius: 18px; padding: 14px 18px; text-align: center;
    background: linear-gradient(160deg, color-mix(in srgb, var(--cor) 14%, #FFFFFF), #FFFFFF);
    border: 1.5px solid #C9D3E0; border-top: 6px solid var(--cor); box-shadow: 0 8px 22px rgba(27,42,65,.08);}
.pt-nome {font: 800 .82rem 'Manrope'; letter-spacing: .12em; color: var(--cor);}
.pt-votos {font: 900 2.4rem/1.1 'Montserrat'; color: #1B2A41; margin: 4px 0 2px;}
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
.tuntum .tt-num {font: 900 5.6rem/1 'Montserrat'; color: #1B2A41; margin: 6px 0 4px; letter-spacing: -.02em;}
.tuntum .tt-leg {font: 600 1rem 'Manrope'; color: #5B6477;}
.tuntum .tt-outros {flex: 0 0 auto; margin: 0 auto; display: flex; gap: 14px; align-items: stretch;}  /* centralizados no espaço livre */
.tuntum .tt-outro {width: 210px; border: 1px solid #E3E9F1; border-top: 4px solid var(--cor); border-radius: 14px;
    padding: 10px 12px; background: linear-gradient(160deg, color-mix(in srgb, var(--cor) 14%, #FFFFFF), #FFFFFF);}
.tuntum .tt-nome2 {font: 800 .85rem 'Manrope'; color: var(--cor);}
.tuntum .tt-num2 {font: 900 1.6rem/1.1 'Montserrat'; color: #1B2A41; margin: 4px 0 2px;}
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


TONS_CAIXA = ("azul", "menta", "lilas", "pessego", "areia")  # tons suaves que se alternam entre as caixas


def caixa():
    _cont[0] += 1
    return st.container(key=f"caixa_{TONS_CAIXA[(_cont[0] - 1) % len(TONS_CAIXA)]}_{_cont[0]}")


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
                    col.markdown(f"<div class='nav-ativa'>{rotulo}</div>",
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


def cabecalho_marca():
    """Faixa da marca no topo das páginas: logo, slogan e contato da Aggilli Intelligence."""
    _logo = _logo_base64()
    st.markdown(f"""
<div class="marca-topo">
  <div class="mt-logo">{f'<img src="data:image/webp;base64,{_logo}" alt="Aggilli Intelligence">' if _logo else '<b>AGGILLI</b>'}</div>
  <div class="mt-slogan">Transformando dados em <span>inteligência</span></div>
  <div class="mt-contato">
    <a href="mailto:adi@aggillintelligence.com.br">✉️ adi@aggillintelligence.com.br</a>
    <a href="https://wa.me/5599991722200" target="_blank">💬 (99) 99172-2200</a>
    <span class="mt-nome">G. C. Léda</span>
  </div>
</div>""", unsafe_allow_html=True)
