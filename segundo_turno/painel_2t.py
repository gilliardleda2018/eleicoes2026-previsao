"""Página — 2º turno presidencial (25/10/2026): Projeto Convencimento (abstenção), apuração ao vivo, Maranhão e Tuntum.

Tudo do 2º turno fica nesta página; as páginas do 1º turno seguem como arquivo.
Dados do modelo: segundo_turno/resultados/ (gerados por segundo_turno/modelo_2t.py).
Ao vivo: segundo_turno/motor_2t.py (TSE com fallback em camadas).
"""
import base64
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(AQUI))
from comum import CSS, _logo_base64, barra_navegacao, grafico, n, tabela  # noqa: E402
import motor_2t  # noqa: E402
import convencimento as cv  # noqa: E402

if __name__ == "__main__":
    st.set_page_config(page_title="2º turno · Presidente", page_icon=str(RAIZ / "assets" / "aggilli_logo.png"),
                       layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

RES, DADOS = AQUI / "resultados", AQUI / "dados"
BRT = timezone(timedelta(hours=-3))  # horário de Brasília (sem horário de verão desde 2019), independe do fuso do servidor
INICIO = datetime(2026, 10, 25, 17, 0, tzinfo=BRT)
COR_L, COR_F = "#C8102E", "#1D4E89"
COR_L_CLARO, COR_F_CLARO = "#FF8A9A", "#8FC3FF"
ESCALA = [[0, COR_F], [0.5, "#F3F1EC"], [1, COR_L]]


# ================================================================ dados
@st.cache_data(ttl=600, show_spinner=False)
def dados():
    sim = json.loads((RES / "simulacao_2t.json").read_text(encoding="utf-8"))
    uf = pd.read_csv(RES / "ufs_2t.csv")
    mun = pd.read_csv(RES / "ma_municipios_2t.csv", dtype={"cd_tse": str})
    ref = pd.read_csv(RAIZ / "resultados" / "municipios_previsao.csv", usecols=["CD_MUNICIPIO", "cd_ibge", "municipio"])
    ref["cd_tse"] = ref.CD_MUNICIPIO.map(lambda c: f"{int(c):05d}")
    mun = mun.merge(ref[["cd_tse", "cd_ibge", "municipio"]], on="cd_tse", how="left")
    mun["cd_ibge"] = mun.cd_ibge.astype("Int64").astype(str)
    # regiões geográficas do IBGE (divisão de 2017: 5 intermediárias, 22 imediatas) e cidades-polo
    reg = pd.read_csv(DADOS / "regioes_ibge_ma.csv", dtype={"cd_ibge": str})
    mun = mun.merge(reg.drop(columns=["municipio"]), on="cd_ibge", how="left")
    sec = pd.read_csv(RES / "tuntum_secoes_2t.csv", dtype={"zona": str, "secao": str})
    loc = pd.read_csv(RES / "tuntum_locais_2t.csv")
    pes = pd.read_csv(RES / "pesquisas_2t_tratadas.csv", parse_dates=["inicio", "fim", "meio"])
    ctx = pd.read_csv(DADOS / "contexto_2t.csv", parse_dates=["data"])
    trf = pd.read_csv(DADOS / "transferencia_2t.csv")
    cen = np.load(RES / "cenarios_lula_2t.npy") if (RES / "cenarios_lula_2t.npy").exists() else None
    locais_geo = DADOS / "locais_tuntum.csv"  # local,nome,bairro,endereco,lat,lon (cadastro do TSE)
    lg = pd.read_csv(locais_geo) if locais_geo.exists() else None
    cad = DADOS / "tuntum_secoes_cadastro.csv"  # seção → local e bairro do cadastro
    sc = pd.read_csv(cad, dtype={"secao": str, "secao_principal": str}) if cad.exists() else None
    return sim, uf, mun, sec, loc, pes, ctx, trf, cen, lg, sc


def _arred(c, k=4):
    return [_arred(x, k) for x in c] if c and isinstance(c[0], list) else [round(v, k) for v in c]


@st.cache_data(show_spinner=False)
def geo(nome):
    """Malha leve: coordenadas com 4 casas (~11 m) — o mapa do MA cai de ~490 KB para ~280 KB por envio."""
    arq = {"br": RAIZ / "nacional" / "dados" / "br_ufs.json", "ma": RAIZ / "dados" / "ma_leve.geojson"}[nome]
    g = json.loads(arq.read_text(encoding="utf-8"))
    for f in g["features"]:
        f["geometry"]["coordinates"] = _arred(f["geometry"]["coordinates"])
    return g


def geo_recorte(geojson, chave_geo, ids):
    """Só as feições pedidas (cada mapa envia a malha uma vez, não duas)."""
    prop = chave_geo.split(".", 1)[1]
    ids = {str(i) for i in ids}
    return {"type": "FeatureCollection", "features": [f for f in geojson["features"] if str(f["properties"].get(prop)) in ids]}


@st.cache_data(show_spinner=False)
def foto(nome):
    arq = RAIZ / "assets" / "fotos" / nome
    return "data:image/jpeg;base64," + base64.b64encode(arq.read_bytes()).decode() if arq.exists() else ""


SIM, UF, MUN, SEC, LOC, PES, CTX, TRF, CEN, LOCAIS_GEO, SEC_CAD = dados()
R = SIM["resultado"]
P_L, P_F = R["prob_lula"], R["prob_flavio"]
L50 = R["lula_validos_p10_p50_p90"][1]


def pct(x, casas=1):
    return n(x, casas) + "%"


def chance(p):
    return "menos de 1%" if p < .01 else "mais de 99%" if p > .99 else f"{round(100 * p)}%"


def mil(x):
    return n(x / 1e6, 1) + " mi" if abs(x) >= 1e6 else n(x / 1e3, 1) + " mil" if abs(x) >= 1e3 else n(x)


# ================================================================ visual
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&display=swap');
.block-container {padding-top: 3.2rem;}
.t2-topo, .t2-hero, .t2-rodape {--linha: rgba(210,230,255,.30);}
/* barra superior com a marca e os créditos */
.t2-topo {display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 18px; padding: 12px 22px;
  border-radius: 20px; color: #FFFFFF; margin: 0 0 14px; border: 1px solid var(--linha);
  background: linear-gradient(145deg, #12233F 0%, #16304F 55%, #1B3B66 100%);
  box-shadow: 0 12px 30px rgba(11,22,40,.25), inset 1px 1px 0 rgba(255,255,255,.12);}
.t2-topo > img {height: 54px; display: block;}
.t2-topo .t2-cred {font: 600 .8rem/1.45 'Montserrat'; color: #D6E6FA; text-align: center;}
.t2-topo .t2-cred b {color: #FFFFFF; font-weight: 800;}
.t2-redes {display: flex; flex-wrap: wrap; gap: 6px 8px; justify-content: flex-end; max-width: 520px;}
.t2-redes a {display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px 3px 3px; border-radius: 999px;
  color: #FFFFFF !important; text-decoration: none; font: 600 .74rem 'Montserrat'; background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.16);}
.t2-redes a:hover {background: rgba(255,255,255,.18);}
.t2-redes img, .t2-redes .bola {width: 20px; height: 20px; border-radius: 50%;}
.t2-redes .bola {display: inline-flex; align-items: center; justify-content: center; background: #8FE3FF; color: #12233F;
  font: 800 .66rem 'Montserrat';}
/* capa: pôster de luta (foto do confronto em alta definição, servida por /app/static) */
.t2-ufc {position: relative; overflow: hidden; border-radius: 28px; aspect-ratio: 3 / 2; max-height: 640px; width: 100%;
  margin-bottom: 10px; color: #FFFFFF; background: #0B1628 url('/app/static/duelo_2t_hd.webp') center 18% / cover no-repeat;
  box-shadow: 0 22px 48px rgba(11,22,40,.38);}
.t2-ufc:before {content: ""; position: absolute; inset: 0;
  background: linear-gradient(90deg, rgba(12,40,110,.55) 0%, rgba(12,40,110,0) 38%, rgba(160,10,30,0) 62%, rgba(160,10,30,.55) 100%),
              linear-gradient(180deg, rgba(5,10,22,.70) 0%, rgba(5,10,22,0) 24%, rgba(5,10,22,0) 52%, rgba(5,10,22,.92) 100%);}
.t2-ufc > * {position: absolute; z-index: 1;}
.ufc-topo {top: 20px; left: 0; right: 0; text-align: center;}
.ufc-topo span {display: block; font: 700 .76rem 'Montserrat'; letter-spacing: .3em; color: #DCE8FF;}
.ufc-topo b {display: block; font: 400 clamp(2rem, 5vw, 3.6rem)/1 'Anton', 'Impact', sans-serif; letter-spacing: .06em;
  margin-top: 6px; text-shadow: 0 4px 18px rgba(0,0,0,.6);}
.ufc-vs {left: 50%; bottom: 42px; transform: translateX(-50%) skewX(-8deg); font: 400 clamp(2.6rem, 6vw, 4.6rem)/1 'Anton', 'Impact', sans-serif;
  background: linear-gradient(180deg, #FFFFFF 20%, #C9D2DE 55%, #8A96A8); -webkit-background-clip: text; background-clip: text;
  color: transparent; filter: drop-shadow(0 4px 10px rgba(0,0,0,.7));}
.ufc-canto {bottom: 28px; max-width: 42%;}
.ufc-azul {left: 30px;} .ufc-vermelho {right: 30px; text-align: right;}
.ufc-nome {font: 400 clamp(2.2rem, 5.6vw, 4.6rem)/.92 'Anton', 'Impact', sans-serif; letter-spacing: .02em; font-style: italic;
  text-shadow: 0 6px 22px rgba(0,0,0,.65);}
.ufc-faixa {display: inline-block; margin-top: 12px; padding: 8px 16px; font: 800 clamp(.72rem, 1.5vw, 1rem)/1.2 'Montserrat';
  letter-spacing: .12em; transform: skewX(-10deg); box-shadow: 0 10px 24px rgba(0,0,0,.4);}
.ufc-azul .ufc-faixa {background: linear-gradient(100deg, #0B3A8C, #1D4E89 60%, #2F6FD0); border-left: 5px solid #8FC3FF;}
.ufc-vermelho .ufc-faixa {background: linear-gradient(100deg, #E0213F, #C8102E 40%, #7A0A1C); border-right: 5px solid #FF8A9A;}
.t2-chips.claro {margin: 2px 0 12px;} .t2-chips.claro span {color: #1B2A41; background: #FFFFFF; border-color: #D6DEE9;}
@media (max-width: 760px) {.t2-ufc {aspect-ratio: 4 / 3; border-radius: 20px;} .ufc-topo {top: 10px;}
  .ufc-topo span {font-size: .5rem; letter-spacing: .14em;} .ufc-canto {bottom: 14px; max-width: 46%;}
  .ufc-azul {left: 12px;} .ufc-vermelho {right: 12px;} .ufc-nome {font-size: 1.5rem;}
  .ufc-faixa {font-size: .55rem; padding: 5px 8px; letter-spacing: .06em; margin-top: 6px;} .ufc-vs {bottom: 18px; font-size: 2rem;}}
[class*="st-key-t2_compartilhar"] {background: #FFFFFF; border: 1px solid #D6DEE9; border-radius: 16px; padding: 8px 12px 0;
  margin: 0 0 12px;}
[class*="st-key-t2_compartilhar"] [data-testid="stLinkButton"] a {background: #25D366 !important; border-color: #25D366 !important;
  color: #FFFFFF !important; font-weight: 800; border-radius: 12px;}
.t2-1t {display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 6px 0 4px;}
.t2-1t-l {position: relative; overflow: hidden; border-radius: 20px; padding: 16px 20px; color: #FFFFFF;
  background: linear-gradient(145deg, var(--cor), var(--escuro)); box-shadow: 0 12px 28px rgba(27,42,65,.18);}
.t2-1t-l .nm {font: 700 .78rem 'Montserrat'; letter-spacing: .14em; opacity: .92;}
.t2-1t-l .pc {font: 800 clamp(2rem, 4.4vw, 3rem)/1.05 'Montserrat'; letter-spacing: -.03em; margin: 6px 0 2px;}
.t2-1t-l .vt {font: 700 1.05rem 'Montserrat'; opacity: .95; font-variant-numeric: tabular-nums;}
.t2-1t-l .ft {position: absolute; right: -10px; bottom: -14px; width: 120px; height: 120px; border-radius: 50%;
  background-size: cover; background-position: center top; opacity: .30;}
.t2-1t-nota {font: 600 .78rem 'Montserrat'; color: #5B6477; margin: 0 0 12px;}
@media (max-width: 760px) {.t2-1t {grid-template-columns: 1fr;}}
/* capa: o duelo */
.t2-hero {position: relative; overflow: hidden; border-radius: 28px; padding: 22px 26px 18px; color: #FFFFFF;
  border: 1px solid var(--linha); margin-bottom: 12px;
  background: radial-gradient(900px 300px at 0% 0%, rgba(200,16,46,.30), transparent 60%),
              radial-gradient(900px 300px at 100% 0%, rgba(29,78,137,.55), transparent 60%),
              linear-gradient(145deg, #0B1628 0%, #12233F 50%, #16304F 100%);
  box-shadow: 0 18px 40px rgba(11,22,40,.32), inset 1px 1px 0 rgba(255,255,255,.10);}
.t2-hero .selo {text-align: center; font: 700 .74rem 'Montserrat'; letter-spacing: .26em; color: #8FE3FF;}
.t2-hero h1 {text-align: center; font: 800 clamp(1.7rem, 3.6vw, 2.7rem)/1.1 'Montserrat' !important; color: #FFFFFF !important;
  margin: 8px 0 18px !important; padding: 0 !important; letter-spacing: -.03em;}
.t2-duelo {display: grid; grid-template-columns: 1fr auto 1fr; gap: 18px; align-items: center;}
.t2-lado {display: flex; align-items: center; gap: 18px;}
.t2-lado.dir {flex-direction: row-reverse; text-align: right;}
.t2-foto {width: 128px; height: 128px; border-radius: 50%; flex: none; background-size: cover; background-position: center top;
  border: 4px solid rgba(255,255,255,.9); box-shadow: 0 0 0 4px var(--cor), 0 14px 30px rgba(0,0,0,.35);}
.t2-nome {font: 800 1.05rem 'Montserrat'; letter-spacing: .12em; color: var(--claro);}
.t2-prob {font: 800 clamp(2.6rem, 5.4vw, 4rem)/1 'Montserrat'; letter-spacing: -.04em; margin: 4px 0;}
.t2-sub {font: 500 .86rem 'Montserrat'; color: #D6E6FA;}
.t2-x {display: flex; flex-direction: column; align-items: center; gap: 8px;}
.t2-x b {width: 52px; height: 52px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font: 800 1.3rem 'Montserrat'; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.25);}
.t2-x span {font: 600 .7rem 'Montserrat'; letter-spacing: .14em; color: #8FE3FF; text-align: center;}
.t2-barra {display: flex; height: 14px; border-radius: 999px; overflow: hidden; margin: 18px 0 6px;
  box-shadow: inset 0 1px 3px rgba(0,0,0,.35);}
.t2-barra i {display: block; height: 100%;}
.t2-legenda {display: flex; justify-content: space-between; font: 600 .8rem 'Montserrat'; color: #D6E6FA;}
.t2-chips {display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 14px;}
.t2-chips span {font: 600 .8rem 'Montserrat'; padding: 6px 12px; border-radius: 999px; background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.18); color: #EAF4FF;}
.t2-chips span.vivo {background: rgba(59,224,127,.16); border-color: rgba(59,224,127,.5);}
.t2-chips span.vivo:before {content: ""; display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 7px;
  background: #3BE07F; animation: t2p 1.8s infinite;}
@keyframes t2p {0% {box-shadow: 0 0 0 0 rgba(59,224,127,.7);} 70% {box-shadow: 0 0 0 9px rgba(59,224,127,0);} 100% {box-shadow: 0 0 0 0 rgba(59,224,127,0);}}
/* cartões de número */
.t2-cards {display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 6px 0 12px;}
.t2-card {background: linear-gradient(160deg, #FFFFFF, #F4F7FB); border: 1px solid #D6DEE9; border-radius: 18px;
  padding: 14px 16px; box-shadow: 0 8px 22px rgba(27,42,65,.07); border-top: 4px solid var(--cor, #1B2A41);}
.t2-card .r {font: 700 .7rem 'Montserrat'; letter-spacing: .12em; color: #5B6477; text-transform: uppercase;}
.t2-card .v {font: 800 1.7rem/1.15 'Montserrat'; color: var(--cor, #1B2A41); margin: 4px 0 2px; letter-spacing: -.02em;}
.t2-card .s {font: 500 .8rem 'Montserrat'; color: #5B6477;}
/* abas: barra de botões em vidro azul-noite; a aba ativa ganha o degradê do duelo.
   Streamlit 1.6x desenha as abas com react-aria (role="tab", aria-selected / data-selected,
   .react-aria-SelectionIndicator e uma linha cinza em ::after); versões antigas usavam baseweb. Cobre os dois. */
[data-testid="stTabs"] [role="tablist"] {position: sticky !important; top: 3.4rem; z-index: 60 !important; display: flex !important; flex-wrap: wrap !important; justify-content: center;
  gap: 8px !important; padding: 8px !important; margin: 2px 0 18px !important; border-radius: 20px !important;
  overflow-x: auto !important; overflow-y: hidden !important; scrollbar-width: thin; scrollbar-color: #22C55E rgba(255,255,255,.12);
  -webkit-overflow-scrolling: touch; scroll-behavior: smooth; border: 0 !important;
  background: linear-gradient(145deg, rgba(18,35,63,.97), rgba(22,48,79,.97) 55%, rgba(27,59,102,.97)) !important;
  box-shadow: 0 14px 30px rgba(11,22,40,.22), inset 1px 1px 0 rgba(255,255,255,.10);}
/* rolagem lateral visível: ninguém perde as abas que não couberam */
[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar {display: block; height: 7px;}
[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar-track {background: rgba(255,255,255,.10); border-radius: 8px; margin: 0 14px;}
[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar-thumb {background: #22C55E; border-radius: 8px;}
[data-testid="stTabsScrollLeft"], [data-testid="stTabsScrollRight"] {display: flex !important;}
[data-testid="stTabs"] [role="tablist"]::after, [data-testid="stTabs"] [role="tablist"]::before {display: none !important;}
[data-testid="stTabs"] .react-aria-SelectionIndicator, [data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"], [data-testid="stTabs"] [data-testid="stTabsHighlight"] {display: none !important;}
[data-testid="stTabs"] [role="tab"] {flex: 0 0 auto !important; justify-content: center !important; height: auto !important;
  min-height: 0 !important; margin: 0 !important; padding: .62rem 1.15rem !important; border-radius: 14px !important;
  border: 1px solid rgba(255,255,255,.16) !important; background: rgba(255,255,255,.07) !important;
  color: #D6E6FA !important; transition: transform .16s, background .16s, box-shadow .16s;}
[data-testid="stTabs"] [role="tab"] p, [data-testid="stTabs"] [role="tab"] span, [data-testid="stTabs"] [role="tab"] div {
  font-family: 'Montserrat', sans-serif !important; font-weight: 700 !important; font-size: .92rem !important;
  color: inherit !important; white-space: nowrap;}
[data-testid="stTabs"] [role="tab"]:hover, [data-testid="stTabs"] [role="tab"][data-hovered] {background: rgba(255,255,255,.15) !important; color: #FFFFFF !important;
  transform: translateY(-1px);}
[data-testid="stTabs"] [role="tab"][aria-selected="true"], [data-testid="stTabs"] [role="tab"][data-selected] {color: #FFFFFF !important; border-color: transparent !important;
  background: linear-gradient(110deg, #C8102E 0%, #7A1F55 48%, #1D4E89 100%) !important;
  box-shadow: 0 8px 20px rgba(200,16,46,.30), 0 8px 20px rgba(29,78,137,.30), inset 0 1px 0 rgba(255,255,255,.25) !important;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] p, [data-testid="stTabs"] [role="tab"][data-selected] p {font-weight: 800 !important;}
[data-testid="stTabs"] [role="tab"]:focus-visible, [data-testid="stTabs"] [role="tab"][data-focus-visible] {outline: 2px solid #8FE3FF !important; outline-offset: 2px;}
/* celular: todas as abas à vista, em grade de 2 colunas (sem precisar rolar para descobrir as outras) */
@media (max-width: 760px) {[data-testid="stTabs"] [role="tablist"] {position: relative !important; top: auto;
    display: grid !important; grid-template-columns: 1fr 1fr; overflow: visible !important; border-radius: 16px !important;
    padding: 6px !important; gap: 6px !important;}
  [data-testid="stTabs"] [role="tab"] {min-width: 0 !important; width: auto !important; padding: .55rem .4rem !important;}
  [data-testid="stTabs"] [role="tab"] p {font-size: .84rem !important; white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis;}
  [data-testid="stTabsScrollLeft"], [data-testid="stTabsScrollRight"] {display: none !important;}
  [data-testid="stTabs"] [role="tab"]:nth-child(2) {grid-column: 1 / -1;}}
@media (prefers-reduced-motion: reduce) {[data-testid="stTabs"] [role="tab"] {transition: none;}}
/* contador de pessoas conectadas */
.t2-online {display: flex; width: fit-content; margin: 2px 0 10px auto; align-items: center; gap: 8px;
  padding: 6px 14px; border-radius: 999px; background: #0F1E36; color: #E6F0FF; font: 600 .86rem 'Montserrat';
  box-shadow: 0 6px 16px rgba(11,22,40,.18);}
.t2-online b {font-weight: 800; color: #FFFFFF; font-size: .98rem;}
.t2-online .pulso {width: 9px; height: 9px; border-radius: 50%; background: #2ECC71; box-shadow: 0 0 0 0 rgba(46,204,113,.6);
  animation: t2pulso 1.8s infinite;}
@keyframes t2pulso {70% {box-shadow: 0 0 0 9px rgba(46,204,113,0);} 100% {box-shadow: 0 0 0 0 rgba(46,204,113,0);}}
@media (prefers-reduced-motion: reduce) {.t2-online .pulso {animation: none;}}
/* ===== Projeto Convencimento: cards de mobilização (papel claro, vermelho, Anton) ===== */
[class*="st-key-cv_papel"] {background: #F3F0EA radial-gradient(rgba(0,0,0,.035) 1px, transparent 1px) 0 0/5px 5px;
  border-radius: 22px; padding: 26px 26px 18px; margin: 4px 0 22px; box-shadow: 0 16px 34px rgba(60,20,20,.10);
  border: 1px solid #E6DED2;}
[class*="st-key-cv_verm"] {background: #E1302A radial-gradient(rgba(255,255,255,.06) 1px, transparent 1px) 0 0/6px 6px;
  border-radius: 22px; padding: 26px 26px 18px; margin: 4px 0 22px; box-shadow: 0 18px 38px rgba(160,20,20,.28);}
.cv-tag {display: inline-block; border: 2px solid #D3252B; color: #D3252B; font: 800 .78rem 'Montserrat', sans-serif;
  letter-spacing: .24em; padding: 5px 14px; text-transform: uppercase; background: transparent;}
.cv-h {font: 400 clamp(2.1rem, 5.4vw, 3.9rem)/.98 'Anton', 'Impact', sans-serif; color: #D3252B; text-transform: uppercase;
  margin: 14px 0 6px; letter-spacing: .01em;}
.cv-h .ln {display: inline-block; width: clamp(40px, 16%, 180px); height: 3px; background: currentColor; vertical-align: middle;
  margin: 0 12px;} .cv-h .st {font-size: .45em; vertical-align: middle;}
.cv-sub {font: 800 .8rem/1.35 'Montserrat', sans-serif; letter-spacing: .05em; color: #A61E24; text-transform: uppercase;
  margin-bottom: 14px;}
.cv-fonte {font: 500 .74rem/1.4 'Manrope', sans-serif; color: #5E3B3B; margin-top: 10px;}
.cv-verm .cv-tag, [class*="st-key-cv_verm"] .cv-tag {border-color: #fff; color: #fff;}
[class*="st-key-cv_verm"] .cv-h, [class*="st-key-cv_verm"] .cv-sub, [class*="st-key-cv_verm"] .cv-fonte {color: #fff;}
.cv-mega {font: 400 clamp(4.2rem, 13vw, 9.5rem)/.86 'Anton', 'Impact', sans-serif; color: #fff; letter-spacing: -.01em;}
.cv-big {font: 400 clamp(2rem, 5.6vw, 3.9rem)/1 'Anton', 'Impact', sans-serif; color: #fff; text-transform: uppercase;}
.cv-big .ln {display: inline-block; width: clamp(40px, 26%, 300px); height: 3px; background: #fff; vertical-align: middle; margin: 0 14px;}
.cv-faixa {display: inline-block; background: #fff; color: #D3252B; padding: 2px 12px; margin: 6px 0;
  font: 400 clamp(2rem, 5.6vw, 3.9rem)/1 'Anton', 'Impact', sans-serif; text-transform: uppercase;}
.cv-amarelo {color: #FFD86B !important;}
.cv-lista .it {display: grid; grid-template-columns: 3.2rem 1fr auto; align-items: center; gap: 10px;
  border-top: 2px solid #D3252B; padding: 7px 0;}
.cv-lista .it:last-child {border-bottom: 2px solid #D3252B;}
.cv-lista .n {font: 400 2rem/1 'Anton', sans-serif; color: #D3252B;}
.cv-lista .nm {font: 400 1.32rem/1.05 'Anton', sans-serif; color: #D3252B; text-transform: uppercase;}
.cv-lista .bx {font: 500 .8rem 'Manrope', sans-serif; color: #2B2B2B;}
.cv-lista .v {font: 400 2rem/1 'Anton', sans-serif; color: #D3252B; text-align: right; white-space: nowrap;}
.cv-barras .it {display: grid; grid-template-columns: minmax(110px, 34%) 1fr 7.2rem; align-items: center; gap: 12px; margin: 7px 0;}
.cv-barras .nm {font: 400 1.35rem/1 'Anton', sans-serif; color: #fff; text-transform: uppercase; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;}
.cv-barras .tr {height: 30px; background: rgba(255,255,255,.22);} .cv-barras .fi {height: 100%; background: #fff;}
.cv-barras .v {font: 400 1.6rem/1 'Anton', sans-serif; color: #fff; text-align: right; white-space: nowrap;}
.cv-bloco {border-top: 5px solid var(--c); padding: 6px 0 10px; margin-bottom: 4px;}
.cv-bloco .r {font: 800 .74rem 'Montserrat', sans-serif; letter-spacing: .14em; color: var(--c); text-transform: uppercase;}
.cv-bloco .q {font: 400 2.5rem/1 'Anton', sans-serif; color: var(--c); margin: 2px 0;}
.cv-bloco .d {font: 600 .8rem 'Manrope', sans-serif; color: #2B2B2B;}
.cv-total .q {font: 400 2.9rem/1 'Anton', sans-serif; color: #D3252B;}
.cv-cta {font: 400 clamp(3rem, 10vw, 7rem)/.9 'Anton', 'Impact', sans-serif; color: #D3252B; text-transform: uppercase;}
.cv-cta .e {display: flex; align-items: center; gap: 14px; font-size: .45em;} .cv-cta .e:before, .cv-cta .e:after {content: "";
  flex: 1; height: 4px; background: #D3252B;}
@media (max-width: 760px) {.cv-barras .it {grid-template-columns: 34% 1fr 5.4rem;} .cv-barras .v {font-size: 1.2rem;} .cv-barras .nm {font-size: 1.05rem;}
  .cv-lista .nm {font-size: 1.05rem;} .cv-lista .v, .cv-lista .n {font-size: 1.5rem;}}
.cv-kpis {display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 14px 0 6px;}
.cv-kpis .k {background: #fff; border-top: 5px solid #D3252B; padding: 12px 14px 10px; box-shadow: 0 6px 14px rgba(120,30,30,.08);}
.cv-kpis .r {font: 800 .68rem 'Montserrat', sans-serif; letter-spacing: .14em; color: #A61E24; text-transform: uppercase;}
.cv-kpis .q {font: 400 clamp(1.45rem, 2.4vw, 2.1rem)/1.05 'Anton', 'Impact', sans-serif; color: #D3252B; margin: 4px 0 2px;}
.cv-kpis .d {font: 600 .76rem 'Manrope', sans-serif; color: #4A3A3A;}
.cv-kpis.v .k {background: rgba(255,255,255,.12); border-top-color: #fff; box-shadow: none;}
.cv-kpis.v .r, .cv-kpis.v .d {color: #FFE3E0;} .cv-kpis.v .q {color: #fff;}
.cv-nivel {font: 400 clamp(1.6rem, 3.6vw, 2.4rem)/1 'Anton', 'Impact', sans-serif; color: #1E1E1E; text-transform: uppercase;
  margin: 34px 0 12px; padding: 10px 0 10px 16px; border-left: 8px solid #D3252B; letter-spacing: .02em;}
/* selo verde piscando com o % apurado */
.t2-ap-tit {display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  margin: 22px 0 10px; font: 800 1.45rem 'Montserrat', sans-serif; color: #1B2A41;}
.t2-ap-selo {display: inline-flex; align-items: center; gap: 8px; background: #C9F7DC; color: #0B5E35;
  border-radius: 8px; padding: 4px 12px; font: 700 .95rem 'Montserrat', sans-serif; white-space: nowrap;}
.t2-ap-selo .pt {width: 10px; height: 10px; border-radius: 50%; background: #12A150;
  box-shadow: 0 0 0 0 rgba(18,161,80,.7); animation: t2piscar 1.4s ease-in-out infinite;}
@keyframes t2piscar {0% {opacity: 1; box-shadow: 0 0 0 0 rgba(18,161,80,.65);}
  50% {opacity: .35; box-shadow: 0 0 0 7px rgba(18,161,80,0);} 100% {opacity: 1; box-shadow: 0 0 0 0 rgba(18,161,80,0);}}
@media (prefers-reduced-motion: reduce) {.t2-ap-selo .pt {animation: none;}}
/* mapa por município (visão escura) */
[class*="st-key-t2_mapa_mun"] {background: #202124; border-radius: 18px; padding: 14px 14px 10px;}
.t2-leg {color: #E8EAED; font: 600 .8rem 'Montserrat', sans-serif; margin-top: 4px;}
.t2-leg .tt {display: inline-block; background: #3C4043; border-radius: 8px; padding: 5px 10px; margin-bottom: 8px;}
.t2-leg .ln {display: flex; align-items: center; gap: 6px; margin: 3px 0;}
.t2-leg .q {width: 13px; height: 13px; border-radius: 3px; display: inline-block; border: 1px solid rgba(255,255,255,.25);}
.t2-leg .ln span:last-child {margin-left: 8px;}
.t2-leg .nt, [class*="st-key-t2_mapa_mun"] .nt {color: #BDC1C6; font: 500 .74rem 'Manrope', sans-serif; margin-top: 6px;}
/* placar ao vivo */
.t2-placar {display: grid; grid-template-columns: 1fr 1fr; gap: 12px;}
.t2-pl {border-radius: 20px; padding: 16px 18px; color: #FFFFFF; position: relative; overflow: hidden;
  background: linear-gradient(145deg, var(--cor), var(--escuro)); box-shadow: 0 12px 28px rgba(27,42,65,.18);}
.t2-pl .nm {font: 700 .8rem 'Montserrat'; letter-spacing: .14em; opacity: .9;}
.t2-pl .vt {font: 800 clamp(1.8rem, 4vw, 2.8rem)/1.05 'Montserrat'; letter-spacing: -.03em; margin: 6px 0 2px;}
.t2-pl .pc {font: 600 1rem 'Montserrat'; opacity: .95;}
.t2-pl .ft {position: absolute; right: -10px; bottom: -14px; width: 110px; height: 110px; border-radius: 50%;
  background-size: cover; background-position: center top; opacity: .28;}
.t2-status {font: 600 .82rem 'Montserrat'; color: #3A4458; background: #FFFFFF; border: 1px solid #D6DEE9;
  border-radius: 14px; padding: 8px 14px; margin: 8px 0;}
.t2-status b {color: #1B2A41;}
.t2-aviso {font: 600 .82rem 'Montserrat'; color: #7A4B00; background: #FFF6E5; border: 1px solid #F3D19C;
  border-radius: 12px; padding: 7px 12px; margin: 4px 0;}
/* linha do tempo */
.t2-tl {border-left: 3px solid #D6DEE9; margin-left: 8px; padding-left: 18px;}
.t2-ev {position: relative; margin: 0 0 14px;}
.t2-ev:before {content: ""; position: absolute; left: -26px; top: 4px; width: 13px; height: 13px; border-radius: 50%;
  background: var(--cor, #5B6477); border: 3px solid #FFFFFF; box-shadow: 0 0 0 1px #D6DEE9;}
.t2-ev .d {font: 700 .72rem 'Montserrat'; letter-spacing: .1em; color: #5B6477;}
.t2-ev .t {font: 800 1rem 'Montserrat'; color: #1B2A41;}
.t2-ev .x {font: 500 .86rem 'Montserrat'; color: #3A4458;}
.t2-ev a {font: 600 .76rem 'Montserrat'; color: #1F6FB2 !important;}
/* rodapé */
.t2-rodape {display: grid; grid-template-columns: auto 1fr auto; gap: 22px; align-items: center; margin: 26px 0 6px;
  padding: 18px 24px; border-radius: 22px; color: #FFFFFF; border: 1px solid var(--linha);
  background: radial-gradient(circle at 0% 0%, rgba(143,227,255,.18), transparent 45%), linear-gradient(110deg, #12233F, #1B3B66);
  box-shadow: 0 14px 30px rgba(11,22,40,.22);}
.t2-rodape img.logo {height: 64px;}
.t2-rodape .nm {font: 800 1.1rem 'Montserrat';} .t2-rodape .tx {font: 500 .8rem/1.5 'Montserrat'; color: #D6E6FA;}
@media (max-width: 900px) {
  .t2-topo, .t2-rodape {grid-template-columns: 1fr; text-align: center;} .t2-topo > img, .t2-rodape img.logo {margin: 0 auto;}
  .t2-redes {justify-content: center; max-width: none;}
  .t2-duelo {grid-template-columns: 1fr; gap: 10px;} .t2-lado, .t2-lado.dir {flex-direction: row; text-align: left;}
  .t2-foto {width: 84px; height: 84px;} .t2-x {flex-direction: row;}
  .t2-cards {grid-template-columns: repeat(2, 1fr);} .t2-placar {grid-template-columns: 1fr;}}
</style>""", unsafe_allow_html=True)

_LOGO = _logo_base64()
LOGO_IMG = f'<img src="data:image/webp;base64,{_LOGO}" alt="Aggilli Intelligence">' if _LOGO else "<b>AGGILLI</b>"
REDES = """
<a href="https://wa.me/5599991722200" target="_blank" title="WhatsApp"><img src="/app/static/icones/whatsapp.png" alt="">(99) 99172-2200</a>
<a href="https://wa.me/5599991667990" target="_blank" title="WhatsApp"><img src="/app/static/icones/whatsapp.png" alt="">(99) 99166-7990</a>
<a href="https://www.instagram.com/aggillisoftware/" target="_blank" title="Instagram"><img src="/app/static/icones/instagram.png" alt="">@aggillisoftware</a>
<a href="mailto:adi@aggillintelligence.com.br" title="E-mail"><span class="bola">@</span>adi@aggillintelligence.com.br</a>
<a href="https://www.aggillintelligence.com.br" target="_blank" title="Site"><span class="bola">www</span>aggillintelligence.com.br</a>"""
CREDITO = "<b>Gilliard Cardoso Léda</b> · Cientista de Dados | Aggilli Intelligence"

st.markdown(f'<div class="t2-topo">{LOGO_IMG}<div class="t2-cred">{CREDITO}<br>Modelo preditivo e apuração em '
            f'tempo real · 2º turno 2026</div><div class="t2-redes">{REDES}</div></div>', unsafe_allow_html=True)
# Link "só o 2º turno": ?so2t=1 (ou SOMENTE_2T=1 no serviço) esconde a navegação para as outras páginas
def _param(nome):
    try:
        return str(st.query_params.get(nome, "") or "")
    except Exception:  # noqa: BLE001
        return ""


SOMENTE_2T = _param("so2t") == "1" or os.environ.get("SOMENTE_2T", "") == "1"
# endereço divulgado: a página de redirecionamento da Aggilli, quando configurada no serviço
LINK_2T = os.environ.get("LINK_2T") or (os.environ.get("PUBLIC_URL", "").rstrip("/") + "/?so2t=1"
                                        if os.environ.get("PUBLIC_URL") else "")
barra_navegacao("2t")  # na produção, também mostra o contador de pessoas conectadas e o modo TV
if SOMENTE_2T:
    st.markdown('<style>[class*="st-key-barra_nav"] {display: none !important;}</style>', unsafe_allow_html=True)


# pessoas conectadas agora (também no link ?so2t=1): atualiza sozinho a cada 30 s
@st.fragment(run_every="30s")
def conectados():
    try:
        import presenca
        total, origem = presenca.contar()
    except Exception:  # noqa: BLE001
        return
    rotulo = "pessoa conectada agora" if total == 1 else "pessoas conectadas agora"
    st.markdown(f'<div class="t2-online" title="Contagem por {origem}; atualiza a cada 30 s">'
                f'<span class="pulso"></span><b>{n(total)}</b> {rotulo}</div>', unsafe_allow_html=True)


conectados()

# ================================================================ capa
agora = datetime.now(BRT)
if agora < INICIO:
    d = (INICIO.date() - agora.date()).days
    quando = {0: "É hoje · apuração a partir das 17h (Brasília)", 1: "Amanhã · apuração a partir das 17h (Brasília)"}.get(
        d, f"Faltam {d} dias · domingo, 25 de outubro, apuração a partir das 17h (horário de Brasília)")
    vivo = ""
else:
    quando, vivo = "Apuração em andamento · dados oficiais do TSE", "vivo"
def foto_url(nome):
    return f"/app/static/fotos_2t/{nome}" if (RAIZ / "static" / "fotos_2t" / nome).exists() else foto(nome)


fl, ff = foto_url("lula.jpg"), foto_url("flavio.jpg")  # placar do ao vivo: URL estática, o navegador guarda em cache
# capa no estilo pôster de luta: só a foto do confronto, nomes e os slogans (sem números)
st.markdown("""
<div class="t2-ufc" role="img" aria-label="Flávio Bolsonaro e Lula frente a frente">
  <div class="ufc-topo"><span>ELEIÇÕES 2026 · 2º TURNO · PRESIDENTE DA REPÚBLICA</span><b>25 DE OUTUBRO</b></div>
  <div class="ufc-vs">VS</div>
  <div class="ufc-canto ufc-azul">
    <div class="ufc-nome">FLÁVIO<br>BOLSONARO</div>
    <div class="ufc-faixa">UMA OPORTUNIDADE DE VIDA</div>
  </div>
  <div class="ufc-canto ufc-vermelho">
    <div class="ufc-nome">LULA</div>
    <div class="ufc-faixa">A ÚLTIMA DANÇA DO VELHO ESTADISTA</div>
  </div>
</div>""", unsafe_allow_html=True)
st.markdown(f'<div class="t2-chips claro"><span class="{vivo}">{quando}</span></div>', unsafe_allow_html=True)


def compartilhar_2t(chave="t2_compartilhar"):
    """Compartilhar só esta página: WhatsApp com mensagem pronta e o link para copiar."""
    link = LINK_2T
    if not link:
        return
    from urllib.parse import quote
    texto = ("🗳️ Mais de 14 milhões de eleitores de Lula não foram votar no 1º turno. Veja onde eles estão no Brasil, "
             "no Maranhão e em Tuntum — e acompanhe a apuração ao vivo no domingo, 25/10.\n\n"
             "Cada um leva um! 👉 " + link)
    with st.container(key=chave):
        c1, c2 = st.columns([1, 2.2], vertical_alignment="center")
        c1.link_button("📲 Compartilhar no WhatsApp", f"https://wa.me/?text={quote(texto)}", width="stretch")
        c2.code(link, language=None)


compartilhar_2t()


def cards(itens):
    st.markdown('<div class="t2-cards">' + "".join(
        f'<div class="t2-card" style="--cor:{c}"><div class="r">{r}</div><div class="v">{v}</div><div class="s">{s}</div></div>'
        for r, v, s, c in itens) + "</div>", unsafe_allow_html=True)


OUTROS_1T = ["cury", "renan", "caiado", "zema", "outros"]


# Astolfo Seabra e Vila Luizão são o mesmo bairro (o cadastro do TSE só usa "Residencial Astolfo Seabra de Carvalho").
# A escola "Astolfo Seabra de Carvalho" do Povoado Belém é outra coisa (zona rural) e fica no povoado.
BAIRRO_UNIFICADO = "Astolfo Seabra / Vila Luizão"


def bairro_tuntum(nome):
    """Nome de bairro/povoado para exibição: sem o sufixo de zona e com bairros iguais unificados."""
    if not isinstance(nome, str) or not nome.strip():
        return "Sem bairro no cadastro"
    up = nome.upper()
    if ("ASTOLFO SEABRA" in up and "POVOADO" not in up) or "LUIZÃO" in up or "LUIZAO" in up:
        return BAIRRO_UNIFICADO
    limpo = re.sub(r"\s*-\s*ZONA\s+(URBANA|RURAL)\s*$", "", nome.strip(), flags=re.I).title()
    limpo = re.sub(r"\b(Da|De|Do|Das|Dos|E)\b", lambda m: m.group(1).lower(), limpo)
    return re.sub(r"\bSao\b", "São", limpo).replace("Belem", "Belém")


def zona_tuntum(nome):
    up = str(nome).upper()
    return "Zona rural" if "RURAL" in up or up.startswith("POVOADO") else "Zona urbana"


def _br(x, casas=1):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


HOVER_CARD = dict(bgcolor="#0F1E36", bordercolor="#C8102E", align="left",
                  font=dict(family="Montserrat, Manrope, Arial, sans-serif", size=12, color="#EAF1FB"))
_LINHA = '<span style="color:#3A5277">──────────────────────────</span>'


def _barra(pct_lula):
    k = int(round(max(0.0, min(100.0, pct_lula)) / 5))
    return f'<span style="color:#E3243B">{"█" * k}</span><span style="color:#3C7DD9">{"█" * (20 - k)}</span>'


def _rot(txt):
    return f'<span style="color:#9FB7D9">{txt}</span>'


def _lider(pct_lula):
    return ("<span style='color:#FF6B7D'><b>Lula na frente</b></span>" if pct_lula >= 50
            else "<span style='color:#7FB2FF'><b>Flávio na frente</b></span>")


def cartao_municipio(r, ao_vivo=False):
    """Cartão do município no mapa do Maranhão (mesmo estilo do cartão dos locais de Tuntum)."""
    nome = escape(str(r.municipio))
    polo = ""
    if getattr(r, "polo_intermediaria", 0) == 1:
        polo = ' <span style="color:#F5C04A;font-size:11px">★ POLO REGIONAL</span>'
    elif getattr(r, "polo_imediata", 0) == 1:
        polo = ' <span style="color:#F5C04A;font-size:11px">★ CIDADE-POLO</span>'
    reg = escape(f"{getattr(r, 'regiao_imediata', '')} · {getattr(r, 'regiao_intermediaria', '')}".upper())
    cab = (f'<span style="font-size:15px"><b>{nome}</b></span>{polo}<br>'
           f'<span style="color:#9FB7D9;font-size:11px">📍 REGIÃO {reg}</span><br>{_LINHA}<br>')
    l1, l2 = float(r.lula_1t_pct) if hasattr(r, "lula_1t_pct") else np.nan, float(r.lula_2t)
    vl, vf = int(round(r.votos_lula_2t)), int(round(r.votos_flavio_2t))
    if ao_vivo:
        a_l, a_f, pst = float(r.v_13 or 0), float(r.v_22 or 0), float(r.pst or 0)
        agora = 100 * a_l / (a_l + a_f) if a_l + a_f else np.nan
        dif = agora - l2
        sinal = "+" if dif >= 0 else "−"
        cor_d = "#FF6B7D" if dif >= 0 else "#7FB2FF"
        return (cab + f'{_rot("Apurado")}  <b>{_br(pst)}%</b> das seções<br>{_LINHA}<br>'
                f'<span style="color:#FF6B7D"><b>● Lula</b></span>     <span style="font-size:14px"><b>{_br(a_l, 0)}</b></span>'
                f'  votos · <b>{_br(agora)}%</b><br>'
                f'<span style="color:#7FB2FF"><b>● Flávio</b></span>  <span style="font-size:14px"><b>{_br(a_f, 0)}</b></span>'
                f'  votos · <b>{_br(100 - agora)}%</b><br>{_barra(agora)}<br>'
                f'{_rot("Previsto Lula")}  <b>{_br(l2)}%</b>  · <span style="color:{cor_d}"><b>{sinal}{_br(abs(dif))} pts</b></span>'
                f'  · {_lider(agora)}<br>'
                f'<span style="color:#6F86A8;font-size:10px">% entre Lula e Flávio · apuração do TSE × modelo Aggilli</span>')
    linhas = f'{_rot("Eleitores")}  <b>{_br(r.eleitorado, 0)}</b>   {_rot("Válidos no 1º t")}  <b>{_br(r.validos, 0)}</b><br>{_LINHA}<br>'
    return (cab + linhas +
            f'<span style="color:#FF6B7D"><b>● Lula</b></span>     1º t {_br(l1)}%  →  '
            f'<span style="font-size:14px"><b>{_br(l2)}%</b></span> {_rot("proj.")}<br>'
            f'<span style="color:#7FB2FF"><b>● Flávio</b></span>  1º t {_br(r.flavio_1t_pct)}%  →  '
            f'<span style="font-size:14px"><b>{_br(100 - l2)}%</b></span> {_rot("proj.")}<br>'
            f'{_barra(l2)}<br>'
            f'{_rot("Votos projetados")}  <b>{_br(vl, 0)} × {_br(vf, 0)}</b>  · {_lider(l2)}<br>'
            f'<span style="color:#6F86A8;font-size:10px">1º turno em % dos válidos · 2º turno: projeção do modelo Aggilli</span>')


def cartao_local(r):
    """Cartão do local de votação no mapa de Tuntum (HTML do hover do Plotly)."""
    nome = re.sub(r"\b(Da|De|Do|Das|Dos|E)\b", lambda m: m.group(1).lower(), str(r.nome).title())
    nome = escape(re.sub(r"\s+", " ", nome).strip())
    bairro = escape(bairro_tuntum(r.bairro))
    zona = zona_tuntum(r.bairro).replace("Zona ", "zona ")
    secs = [s for s in str(r.secoes).split(", ") if s]
    l1, l2 = float(r.lula_1t), float(r.lula_2t)
    vl, vf = int(round(r.votos_lula_2t)), int(round(r.votos_flavio_2t))
    k = int(round(l2 / 5))  # barra de 20 blocos
    barra = (f'<span style="color:#E3243B">{"█" * k}</span>'
             f'<span style="color:#3C7DD9">{"█" * (20 - k)}</span>')
    lider = ("<span style='color:#FF6B7D'><b>Lula na frente</b></span>" if l2 >= 50
             else "<span style='color:#7FB2FF'><b>Flávio na frente</b></span>")
    linha = '<span style="color:#3A5277">──────────────────────────</span>'
    return (f'<span style="font-size:15px"><b>{nome}</b></span><br>'
            f'<span style="color:#9FB7D9;font-size:11px">📍 {bairro.upper()} · {zona.upper()}</span><br>{linha}<br>'
            f'<span style="color:#9FB7D9">Seções</span>  <b>{" · ".join(secs)}</b> ({len(secs)})<br>'
            f'<span style="color:#9FB7D9">Eleitores aptos</span>  <b>{_br(r.aptos, 0)}</b><br>{linha}<br>'
            f'<span style="color:#FF6B7D"><b>● Lula</b></span>     1º t {_br(l1)}%  →  '
            f'<span style="font-size:14px"><b>{_br(l2)}%</b></span> <span style="color:#9FB7D9">proj.</span><br>'
            f'<span style="color:#7FB2FF"><b>● Flávio</b></span>  1º t {_br(100 - l1)}%  →  '
            f'<span style="font-size:14px"><b>{_br(100 - l2)}%</b></span> <span style="color:#9FB7D9">proj.</span><br>'
            f'{barra}<br>'
            f'<span style="color:#9FB7D9">Votos projetados</span>  <b>{_br(vl, 0)} × {_br(vf, 0)}</b>  · {lider}<br>'
            f'<span style="color:#6F86A8;font-size:10px">% entre Lula e Flávio · projeção do modelo Aggilli</span>')


def base_tuntum():
    """Seções de Tuntum (1º turno + projeção) com bairro, local do cadastro do TSE e zona urbana/rural."""
    nomes = LOCAIS_GEO.set_index("local").nome.str.title().to_dict() if LOCAIS_GEO is not None else {}
    bairros = LOCAIS_GEO.set_index("local").bairro.str.title().to_dict() if LOCAIS_GEO is not None else {}
    s = SEC.copy()
    if SEC_CAD is not None:
        s = s.merge(SEC_CAD[["secao", "local_cadastro", "bairro"]], on="secao", how="left")
        s["bairro"] = s.bairro.str.title()
    else:
        s["local_cadastro"], s["bairro"] = s.local, s.local.map(bairros)
    s["Local"] = s.local_cadastro.map(lambda x: nomes.get(x, f"Local {x}"))
    s["zona_tipo"] = s.bairro.map(zona_tuntum)
    s["bairro"] = s.bairro.map(bairro_tuntum)
    s["faltosos"] = s.aptos - s.comparecimento
    s["margem_1t"] = s.lula - s.flavio
    s["em_disputa"] = s[OUTROS_1T].sum(axis=1)
    return s, nomes


def destino_em_disputa(df):
    """Para onde tendem os votos de Cury, Renan, Caiado, Zema e demais (transferência medida no modelo)."""
    trf = SIM["componentes"]["estrutural"]["transferencia"]
    lula = sum(df[c] * trf[c]["decide"] * trf[c]["lula_entre"] for c in OUTROS_1T)
    flavio = sum(df[c] * trf[c]["decide"] * (1 - trf[c]["lula_entre"]) for c in OUTROS_1T)
    return lula, flavio


ao_vivo_agora = agora >= INICIO - timedelta(hours=1)
if ao_vivo_agora:  # bolinha verde piscando na aba "Ao vivo · agora" (no lugar do emoji vermelho)
    st.markdown("""<style>
[data-testid="stTabs"] [role="tab"]:nth-child(2) p::before {content: ""; display: inline-block; width: 10px; height: 10px;
  margin-right: 8px; vertical-align: middle; border-radius: 50%; background: #22C55E;
  animation: t2piscar 1.4s ease-in-out infinite;}
/* o botão inteiro solta ondas verdes, como um sinal ao vivo */
[data-testid="stTabs"] [role="tab"]:nth-child(2) {position: relative !important; overflow: visible !important;
  border-color: rgba(34,197,94,.85) !important; animation: t2vibra 1.1s ease-in-out infinite;}
[data-testid="stTabs"] [role="tab"]:nth-child(2)::after {content: ""; position: absolute; inset: 0; border-radius: 14px;
  pointer-events: none; animation: t2onda 1.1s ease-out infinite;}
@keyframes t2onda {0% {box-shadow: 0 0 0 0 rgba(34,197,94,.95), 0 0 0 0 rgba(34,197,94,.6);}
  50% {box-shadow: 0 0 0 4px rgba(34,197,94,.45), 0 0 0 1px rgba(34,197,94,.7);}
  100% {box-shadow: 0 0 0 8px rgba(34,197,94,0), 0 0 0 5px rgba(34,197,94,0);}}
@keyframes t2vibra {0%, 100% {transform: scale(1);} 25% {transform: scale(1.035);} 50% {transform: scale(.99);}
  75% {transform: scale(1.02);}}
@media (prefers-reduced-motion: reduce) {[data-testid="stTabs"] [role="tab"]:nth-child(2),
  [data-testid="stTabs"] [role="tab"]:nth-child(2)::after {animation: none;}}
</style>""", unsafe_allow_html=True)
aba = st.tabs(["📣 Convencimento", "APURAÇÃO - AO VIVO AQUI" if ao_vivo_agora else "📡 Ao vivo", "🗺️ Maranhão", "📍 Tuntum",
               "📰 Pesquisas e contexto", "🧪 Metodologia"])


# ================================================================ 1) previsão
def mapa_br(df, cor, titulo, rng=(20, 80), escala=ESCALA, hover=None):
    fig = px.choropleth_map(df, geojson=geo_recorte(geo("br"), "properties.uf", df["uf"]), locations="uf", featureidkey="properties.uf", color=cor,
                            color_continuous_scale=escala, range_color=rng, map_style="carto-positron", zoom=2.7,
                            center={"lat": -14.5, "lon": -52}, opacity=.85, hover_name="uf", hover_data=hover)
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=36, b=0), title=titulo,
                      coloraxis_colorbar=dict(title="", ticksuffix="%"))
    return fig


def sem_votos(fig, geojson, chave_geo, locais, nomes):
    """Unidades ainda sem voto apurado: camada cinza por baixo (senão o mapa as deixa em branco)."""
    if not len(locais):
        return fig
    base = go.Choroplethmap(geojson=geo_recorte(geojson, chave_geo, locais), locations=list(locais), z=[0] * len(locais), featureidkey=chave_geo,
                            colorscale=[[0, "#C7CED9"], [1, "#C7CED9"]], showscale=False, marker_opacity=.75,
                            marker_line_color="#FFFFFF", marker_line_width=.6,
                            text=[x if "<" in str(x) else f'<span style="font-size:15px"><b>{escape(str(x))}</b></span><br>'
                                  f'<span style="color:#9FB7D9">⏳ aguardando os primeiros votos</span>' for x in nomes],
                            hovertemplate="%{text}<extra></extra>", hoverlabel=HOVER_CARD)
    fig.add_trace(base)
    fig.data = (fig.data[-1],) + fig.data[:-1]  # cinza por baixo das unidades já apuradas
    return fig


CORES_REG = {"São Luís": "#B3141B", "Santa Inês - Bacabal": "#E8892B", "Imperatriz": "#2E8B3E",
             "Caxias": "#D8B226", "Presidente Dutra": "#1E1E1E",
             "Nordeste": "#B3141B", "Sudeste": "#E8892B", "Sul": "#2E8B3E", "Norte": "#D8B226", "Centro-Oeste": "#1E1E1E",
             "Zona urbana": "#B3141B", "Zona rural": "#E8892B"}


def _cab(tag, titulo, sub, estrela=True):
    st.markdown(f'<span class="cv-tag">{tag}</span><div class="cv-h">{titulo}'
                + ('<span class="ln"></span><span class="st">★</span>' if estrela else "") + f'</div>'
                + (f'<div class="cv-sub">{sub}</div>' if sub else ""), unsafe_allow_html=True)


def _lista(itens):
    """itens: (nome, detalhe, valor) — lista numerada no estilo do card 'os 10 locais'."""
    st.markdown('<div class="cv-lista">' + "".join(
        f'<div class="it"><div class="n">{k}</div><div><div class="nm">{escape(nm)}</div><div class="bx">{escape(dt)}</div></div>'
        f'<div class="v">{cv.fmt_qtd(v)}</div></div>' for k, (nm, dt, v) in enumerate(itens, 1)) + "</div>",
        unsafe_allow_html=True)


def _barras(itens):
    """itens: (nome, valor) — barras brancas no card vermelho."""
    mx = max(v for _, v in itens) or 1
    st.markdown('<div class="cv-barras">' + "".join(
        f'<div class="it"><div class="nm">{escape(nm)}</div><div class="tr"><div class="fi" style="width:{100 * v / mx:.1f}%">'
        f'</div></div><div class="v">{cv.fmt_qtd(v)}</div></div>' for nm, v in itens) + "</div>", unsafe_allow_html=True)


def _blocos(grupos, total_rotulo, total):
    """grupos: (rótulo, cor, valor, detalhe) — blocos coloridos no estilo 'Recife por RPA'."""
    st.markdown("".join(
        f'<div class="cv-bloco" style="--c:{c}"><div class="r">{escape(r)}</div><div class="q">{cv.fmt_qtd(v)}</div>'
        f'<div class="d">{escape(d)}</div></div>' for r, c, v, d in grupos)
        + f'<div class="cv-bloco cv-total" style="--c:#D3252B"><div class="r">{escape(total_rotulo)}</div>'
          f'<div class="q">{cv.fmt_qtd(total)}</div></div>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _contorno(nome, cd=None, passo=3):
    """Linhas finas dos limites (estados do Brasil, municípios do MA ou só Tuntum) para dar contexto às bolhas."""
    xs, ys = [], []
    for f in geo(nome)["features"]:
        if cd and f["properties"].get("CD_MUN") != cd:
            continue
        g = f["geometry"]
        for pol in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            anel = pol[0][::passo] + [pol[0][0]]
            xs += [c[0] for c in anel] + [None]
            ys += [c[1] for c in anel] + [None]
    return xs, ys


def _bolhas(df, lat, lon, grupo, valor, nome, rotulos=None, altura=520, tam_max=38, contorno=None):
    """Mapa de bolhas sem fundo (papel): cada ponto é um lugar; maior = mais eleitores de Lula em casa."""
    fig = go.Figure()
    if contorno:
        xs, ys = contorno
        fig.add_scatter(x=xs, y=ys, mode="lines", line=dict(color="rgba(120,90,80,.35)", width=.8),
                        hoverinfo="skip", showlegend=False)
    mx = float(df[valor].max()) or 1
    for g, d in df.groupby(grupo, sort=False):
        fig.add_scatter(x=d[lon], y=d[lat], mode="markers", name=str(g),
                        marker=dict(size=np.clip(tam_max * np.sqrt(d[valor] / mx), 5, tam_max),
                                    color=CORES_REG.get(str(g), "#B3141B"), opacity=.82,
                                    line=dict(width=1.2, color="rgba(255,255,255,.9)")),
                        text=[f'<span style="font-size:14px"><b>{escape(str(a))}</b></span><br>'
                              f'<span style="color:#9FB7D9">{escape(str(g))}</span><br>{_LINHA}<br>'
                              f'{_rot("Eleitores de Lula que ficaram em casa")}  <b>{cv.fmt_qtd(b)}</b><br>'
                              f'{_rot("Lula no 1º turno")}  <b>{_br(c)}%</b> dos válidos'
                              for a, b, c in zip(d[nome], d[valor], d["lula_pct"])],
                        hovertemplate="%{text}<extra></extra>", hoverlabel=HOVER_CARD)
    for (rx, ry, rt) in (rotulos or []):
        fig.add_annotation(x=rx, y=ry, text=f"<b>{escape(rt.upper())}</b>", showarrow=False,
                           font=dict(family="Montserrat, sans-serif", size=10, color="#3A2A2A"),
                           bgcolor="rgba(243,240,234,.85)")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(height=altura, margin=dict(l=0, r=0, t=6, b=0), showlegend=True, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-.02, font=dict(size=11)))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _kpis(itens, verm=False):
    """itens: (rótulo, valor, detalhe) — fileira de KPIs no estilo dos cards."""
    st.markdown('<div class="cv-kpis' + (' v' if verm else '') + '">' + "".join(
        f'<div class="k"><div class="r">{escape(r)}</div><div class="q">{q}</div><div class="d">{escape(d)}</div></div>'
        for r, q, d in itens) + "</div>", unsafe_allow_html=True)


def _graf(fig, altura=420):
    fig.update_layout(height=altura, margin=dict(l=8, r=8, t=46, b=8), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Montserrat, Manrope, sans-serif", color="#3A2A2A"),
                      title_font=dict(family="Anton, Impact, sans-serif", size=20, color="#D3252B"),
                      hoverlabel=HOVER_CARD, legend=dict(orientation="h", y=-.18))
    fig.update_xaxes(gridcolor="rgba(160,120,110,.18)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(160,120,110,.18)", zeroline=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _dispersao(df, nome, grupo, titulo, rotular=8, tam_col="lula_casa", altura=460):
    """Abstenção × voto em Lula: no alto à direita estão os lugares que mais rendem na mobilização."""
    fig = go.Figure()
    mx = float(df[tam_col].max()) or 1
    for g, d in df.groupby(grupo, sort=False):
        fig.add_scatter(x=d.lula_pct, y=d.abstencao_pct, mode="markers", name=str(g),
                        marker=dict(size=np.clip(44 * np.sqrt(d[tam_col] / mx), 6, 44), color=CORES_REG.get(str(g), "#B3141B"),
                                    opacity=.8, line=dict(width=1, color="#fff")),
                        text=[f'<span style="font-size:14px"><b>{escape(str(a))}</b></span><br>{_LINHA}<br>'
                              f'{_rot("Abstenção")}  <b>{_br(b)}%</b><br>{_rot("Lula no 1º turno")}  <b>{_br(c)}%</b><br>'
                              f'{_rot("Eleitores de Lula em casa")}  <b>{cv.fmt_qtd(e)}</b>'
                              for a, b, c, e in zip(d[nome], d.abstencao_pct, d.lula_pct, d[tam_col])],
                        hovertemplate="%{text}<extra></extra>")
    for r in df.nlargest(rotular, tam_col).itertuples():
        fig.add_annotation(x=r.lula_pct, y=r.abstencao_pct, text=f"<b>{escape(str(getattr(r, nome)))}</b>", showarrow=False,
                           yshift=14, font=dict(size=10, color="#3A2A2A"))
    fig.add_vline(x=50, line_dash="dot", line_color="#D3252B")
    fig.update_layout(title=titulo, xaxis_title="Lula no 1º turno (% dos válidos)", yaxis_title="Abstenção no 1º turno (%)")
    _graf(fig, altura)


def _barras_pct(nomes, valores, titulo, ref=None, ref_txt="", altura=420, cor="#D3252B"):
    fig = go.Figure(go.Bar(x=valores, y=nomes, orientation="h", marker_color=cor,
                           text=[f"{_br(v)}%" for v in valores], textposition="outside",
                           hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
    if ref is not None:
        fig.add_vline(x=ref, line_dash="dash", line_color="#1E1E1E", annotation_text=ref_txt, annotation_position="top")
    fig.update_layout(title=titulo, yaxis=dict(autorange="reversed"), xaxis=dict(ticksuffix="%"), showlegend=False)
    _graf(fig, altura)


with aba[0]:
    est, BR_T = cv.brasil()
    vezes = int(1 / BR_T["fracao_para_virar"]) if BR_T["fracao_para_virar"] > 0 else 0
    MA_C = cv.maranhao(MUN)
    base_c, _ = base_tuntum()
    TU = cv.tuntum(base_c)
    ma_uf = est[est.uf == "MA"].iloc[0]

    # ================= capa
    with st.container(key="cv_verm_capa"):
        st.markdown(f"""<span class="cv-tag">Brasil · 2º turno · 25 de outubro</span>
<div class="cv-big" style="margin-top:16px">Mais de<span class="ln"></span>★</div>
<div class="cv-mega">{cv.fmt_qtd(BR_T["lula_casa"]).upper()}</div>
<div class="cv-big">de eleitores de Lula<span class="ln"></span>★</div>
<div class="cv-faixa">não foram votar no 1º turno</div>
<div class="cv-big">A diferença foi de {cv.fmt_qtd(BR_T["diferenca"])} de votos<span class="ln"></span>★</div>
<div class="cv-big cv-amarelo">Basta que 1 em cada {vezes} volte às urnas</div>""", unsafe_allow_html=True)
        _kpis([("Faltaram no Brasil", cv.fmt_qtd(BR_T["faltaram"]), f"{pct(BR_T['abstencao_pct'])} do eleitorado"),
               ("Eleitores de Lula em casa", cv.fmt_qtd(BR_T["lula_casa"]), "estimativa pela votação em cada estado"),
               ("Diferença no 1º turno", cv.fmt_qtd(BR_T["diferenca"]), "Flávio à frente de Lula"),
               ("Precisam voltar", pct(100 * BR_T["fracao_para_virar"]), f"1 em cada {vezes} eleitores de Lula que ficaram em casa"),
               ("No Maranhão", cv.fmt_qtd(ma_uf.lula_casa), f"cobrem {pct(100 * ma_uf.lula_casa / BR_T['diferenca'], 0)} da diferença"),
               ("Em Tuntum", cv.fmt_qtd(TU.lula_casa.sum()), f"{n(TU.faltaram.sum())} eleitores faltaram")], verm=True)
        st.markdown(f'<div class="cv-fonte">Fonte: TSE, resultado oficial do 1º turno (4/10/2026): Flávio {n(BR_T["flavio_1t"])} × '
                    f'Lula {n(BR_T["lula_1t"])} votos. Eleitores de Lula estimados pela votação do local onde cada pessoa vota '
                    '(voto no exterior fora da conta).</div>', unsafe_allow_html=True)

    # ================= calculadora da virada
    with st.container(key="cv_papel_calc"):
        _cab("Calculadora da virada", "Quantos precisam voltar?",
             "Arraste: que parte dos eleitores de Lula que ficaram em casa volta a votar no domingo?")
        volta = st.slider("Eleitores de Lula que voltam a votar (%)", 1, 40, 20, 1, format="%d%%", key="cv_volta")
        ganho = BR_T["lula_casa"] * volta / 100
        saldo = ganho - BR_T["diferenca"]
        c1, c2 = st.columns([1, 1.3], gap="large")
        with c1:
            _kpis([("Votos que voltam", cv.fmt_qtd(ganho), f"{volta}% de {cv.fmt_qtd(BR_T['lula_casa'])}"),
                   ("Diferença do 1º turno", cv.fmt_qtd(BR_T["diferenca"]), "o que é preciso superar"),
                   ("Saldo", ("+" if saldo >= 0 else "−") + cv.fmt_qtd(abs(saldo)),
                    "a diferença é superada" if saldo >= 0 else "ainda faltam votos")])
        with c2:
            fig = go.Figure()
            fig.add_bar(y=["Diferença do 1º turno"], x=[BR_T["diferenca"]], orientation="h", marker_color="#1E1E1E",
                        text=[cv.fmt_qtd(BR_T["diferenca"])], textposition="inside", name="Diferença")
            fig.add_bar(y=["Eleitores de Lula que voltam"], x=[ganho], orientation="h",
                        marker_color="#D3252B" if saldo >= 0 else "#E8892B", text=[cv.fmt_qtd(ganho)],
                        textposition="inside", name="Voltam")
            fig.update_layout(title="Votos que voltam × diferença a cobrir", showlegend=False,
                              xaxis=dict(range=[0, max(BR_T["diferenca"], ganho) * 1.08]))
            _graf(fig, 260)
        st.markdown('<div class="cv-fonte">A conta considera só a volta dos eleitores de Lula que faltaram, sobre a diferença '
                    'oficial do 1º turno.</div>', unsafe_allow_html=True)

    # ================= FEDERAL
    st.markdown('<div class="cv-nivel">🇧🇷 Federal · Brasil por estado</div>', unsafe_allow_html=True)
    with st.container(key="cv_papel_br"):
        _cab("Brasil por estado", "Onde eles estão",
             "Eleitores de Lula que não votaram no 1º turno, por estado. Quanto maior a bolha, mais gente de Lula ficou em casa.")
        c1, c2 = st.columns([1.5, 1], gap="large")
        with c1:
            cen = cv.centroides_uf()
            b = est.assign(lat=est.uf.map(lambda u: cen.get(u, (np.nan, np.nan))[0]),
                           lon=est.uf.map(lambda u: cen.get(u, (np.nan, np.nan))[1])).dropna(subset=["lat"])
            _bolhas(b, "lat", "lon", "regiao", "lula_casa", "nome",
                    rotulos=[(r.lon, r.lat - 1.6, r.uf) for r in b.head(8).itertuples()], altura=600, tam_max=60,
                    contorno=_contorno("br", passo=4))
        with c2:
            rg = est.groupby("regiao")
            blocos = []
            for nome_r, v in rg.lula_casa.sum().sort_values(ascending=False).items():
                top = rg.get_group(nome_r).sort_values("lula_casa", ascending=False).head(2)
                blocos.append((nome_r, CORES_REG[nome_r], v,
                               " · ".join(f"{x.nome} {cv.fmt_qtd(x.lula_casa)}" for x in top.itertuples())))
            _blocos(blocos, "Brasil", BR_T["lula_casa"])
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(key="cv_verm_br"):
            _cab("Os 10 estados", "Votos a recuperar por estado", "Eleitores de Lula que não votaram no 1º turno")
            _barras([(x.nome, x.lula_casa) for x in est.head(10).itertuples()])
            st.markdown(f'<div class="cv-fonte">Só esses 10 estados somam {cv.fmt_qtd(est.head(10).lula_casa.sum())}. '
                        'Fonte: TSE, 1º turno de 2026.</div>', unsafe_allow_html=True)
    with c2:
        with st.container(key="cv_papel_brfortes"):
            fortes = est[est.lula_pct >= 60].head(10)
            _cab("Onde Lula vence", "Onde Lula vence e mais gente ficou em casa",
                 "Estados onde Lula teve 60% ou mais dos votos válidos", estrela=False)
            _lista([(x.nome, f"{x.regiao} · Lula {_br(x.lula_pct)}% · abstenção {_br(x.abstencao_pct)}%", x.lula_casa)
                    for x in fortes.itertuples()])
    with st.container(key="cv_papel_brgraf"):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            _dispersao(est, "uf", "regiao", "Abstenção × voto em Lula, por estado")
        with c2:
            r_ = est.groupby("regiao").agg(faltaram=("faltaram", "sum"), eleitorado=("eleitorado", "sum"),
                                           lula_casa=("lula_casa", "sum")).reset_index()
            r_["abst"] = 100 * r_.faltaram / r_.eleitorado
            r_ = r_.sort_values("lula_casa", ascending=False)
            fig = go.Figure(go.Bar(x=r_.regiao, y=r_.lula_casa, marker_color=[CORES_REG[x] for x in r_.regiao],
                                   text=[f"<b>{cv.fmt_qtd(v)}</b><br>abstenção {_br(a_)}%" for v, a_ in zip(r_.lula_casa, r_.abst)],
                                   textposition="outside", hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
            fig.update_layout(title="Eleitores de Lula em casa, por região", showlegend=False,
                              yaxis=dict(range=[0, r_.lula_casa.max() * 1.25], tickformat=".2s"))
            _graf(fig, 460)
        st.markdown('<div class="cv-fonte">No alto à direita do gráfico de dispersão ficam os estados onde a abstenção foi alta '
                    'e Lula venceu: é onde cada conversa rende mais.</div>', unsafe_allow_html=True)

    # ================= ESTADUAL · MARANHÃO
    st.markdown('<div class="cv-nivel">🏛️ Estadual · Maranhão por região e município</div>', unsafe_allow_html=True)
    ma_falt, ma_elei = MA_C.faltaram.sum(), MA_C.eleitorado.sum()
    with st.container(key="cv_verm_makpi"):
        _cab("Maranhão", f"{cv.fmt_qtd(MA_C.lula_casa.sum())} eleitores de Lula em casa",
             "Eleitores de Lula que não votaram no 1º turno no Maranhão")
        _kpis([("Faltaram no MA", cv.fmt_qtd(ma_falt), f"{pct(100 * ma_falt / ma_elei)} do eleitorado"),
               ("Eleitores de Lula em casa", cv.fmt_qtd(MA_C.lula_casa.sum()), "soma dos 217 municípios"),
               ("Parte da diferença nacional", pct(100 * MA_C.lula_casa.sum() / BR_T["diferenca"], 0),
                f"de {cv.fmt_qtd(BR_T['diferenca'])}"),
               ("Lula no MA (1º turno)", pct(100 * MA_C.lula.sum() / MA_C.validos.sum()), "dos votos válidos"),
               ("Municípios com Lula ≥ 60%", str(int((MA_C.lula_pct >= 60).sum())), "de 217"),
               ("Abstenção acima de 25%", str(int((MA_C.abstencao_pct > 25).sum())), "municípios")], verm=True)
    with st.container(key="cv_papel_ma"):
        _cab("Maranhão por região", "Onde eles estão no Maranhão",
             "Cada ponto é um município: quanto maior, mais gente de Lula ficou em casa. Cores: regiões do IBGE.")
        c1, c2 = st.columns([1.5, 1], gap="large")
        with c1:
            polos = MA_C[MA_C.polo_intermediaria == 1]
            _bolhas(MA_C, "lat", "lon", "regiao_intermediaria", "lula_casa", "municipio",
                    rotulos=[(r.lon, r.lat - .28, r.municipio) for r in polos.itertuples()], altura=640, tam_max=46,
                    contorno=_contorno("ma", passo=3))
        with c2:
            rg = MA_C.groupby("regiao_intermediaria")
            blocos = []
            for nome_r, v in rg.lula_casa.sum().sort_values(ascending=False).items():
                top = rg.get_group(nome_r).head(2)
                blocos.append((f"Região de {nome_r}", CORES_REG.get(nome_r, "#B3141B"), v,
                               " · ".join(f"{x.municipio} {cv.fmt_qtd(x.lula_casa)}" for x in top.itertuples())))
            _blocos(blocos, "Maranhão", MA_C.lula_casa.sum())
        st.markdown('<div class="cv-fonte">Fonte: TSE, 1º turno de 2026; regiões geográficas do IBGE (2017). Eleitores de Lula '
                    'estimados pela votação de Lula no município.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(key="cv_verm_ma"):
            _cab("Os 10 municípios", "Votos a recuperar no MA", "Eleitores de Lula que não votaram no 1º turno")
            _barras([(x.municipio, x.lula_casa) for x in MA_C.head(10).itertuples()])
            st.markdown('<div class="cv-fonte">Fonte: TSE, 1º turno de 2026.</div>', unsafe_allow_html=True)
    with c2:
        with st.container(key="cv_papel_ma10"):
            fortes = MA_C[MA_C.lula_pct >= 60].head(10)
            _cab("Os 10 municípios", "Onde Lula vence e mais gente ficou em casa",
                 "Municípios onde Lula teve 60% ou mais dos votos válidos", estrela=False)
            _lista([(x.municipio, f"Região {x.regiao_imediata} · Lula {_br(x.lula_pct)}%", x.lula_casa)
                    for x in fortes.itertuples()])
    with st.container(key="cv_papel_magraf"):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            _dispersao(MA_C, "municipio", "regiao_intermediaria", "Abstenção × voto em Lula, por município", rotular=8)
        with c2:
            ri = MA_C.groupby("regiao_imediata").agg(faltaram=("faltaram", "sum"), eleitorado=("eleitorado", "sum"),
                                                      lula_casa=("lula_casa", "sum")).reset_index()
            ri = ri.sort_values("lula_casa", ascending=False)
            fig = go.Figure(go.Bar(x=ri.lula_casa, y=ri.regiao_imediata, orientation="h", marker_color="#D3252B",
                                   text=[cv.fmt_qtd(v) for v in ri.lula_casa], textposition="outside",
                                   customdata=100 * ri.faltaram / ri.eleitorado,
                                   hovertemplate="%{y}: %{x:,.0f} · abstenção %{customdata:.1f}%<extra></extra>"))
            fig.update_layout(title="As 22 regiões imediatas", yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
                              showlegend=False)
            _graf(fig, 640)
    # ---- seu município
    with st.container(key="cv_papel_mun"):
        _cab("Seu município", "Quanto o seu município pode ajudar", "Escolha um dos 217 municípios do Maranhão",
             estrela=False)
        nomes_m = MA_C.sort_values("municipio").municipio.tolist()
        esc = st.selectbox("Município", nomes_m, index=nomes_m.index("Tuntum") if "Tuntum" in nomes_m else 0,
                           key="cv_mun")
        x = MA_C[MA_C.municipio == esc].iloc[0]
        rank = int((MA_C.lula_casa > x.lula_casa).sum()) + 1
        _kpis([("Eleitorado", n(x.eleitorado), f"região de {x.regiao_imediata}"),
               ("Faltaram", n(x.faltaram), f"{pct(x.abstencao_pct)} de abstenção"),
               ("Eleitores de Lula em casa", cv.fmt_qtd(x.lula_casa), f"{rank}º do Maranhão"),
               ("Lula no 1º turno", pct(x.lula_pct), "dos votos válidos"),
               ("Meta: 1 em cada " + str(vezes), cv.fmt_qtd(x.lula_casa / vezes), "votos a trazer de volta")])

    # ================= MUNICIPAL · TUNTUM
    st.markdown('<div class="cv-nivel">📍 Municipal · Tuntum por bairro, povoado e local</div>', unsafe_allow_html=True)
    loc = TU.groupby("local_cadastro", as_index=False).agg(
        lula_casa=("lula_casa", "sum"), faltaram=("faltaram", "sum"), aptos=("aptos", "sum"), lula=("lula", "sum"),
        validos=("validos", "sum"), Local=("Local", "first"), bairro=("bairro", "first"), zona_tipo=("zona_tipo", "first"))
    loc["lula_pct"] = 100 * loc.lula / loc.validos.replace(0, np.nan)
    loc["abstencao_pct"] = 100 * loc.faltaram / loc.aptos.replace(0, np.nan)
    loc = loc.sort_values("lula_casa", ascending=False)
    bb = TU.groupby(["bairro", "zona_tipo"], as_index=False).agg(
        lula_casa=("lula_casa", "sum"), faltaram=("faltaram", "sum"), aptos=("aptos", "sum"), lula=("lula", "sum"),
        validos=("validos", "sum"))
    bb["abstencao_pct"] = 100 * bb.faltaram / bb.aptos
    bb["lula_pct"] = 100 * bb.lula / bb.validos
    with st.container(key="cv_verm_tunkpi"):
        _cab("Tuntum", f"{cv.fmt_qtd(TU.lula_casa.sum())} eleitores de Lula em casa",
             "Eleitores de Lula que não votaram no 1º turno em Tuntum")
        zt = TU.groupby("zona_tipo").agg(f=("faltaram", "sum"), a=("aptos", "sum"))
        _kpis([("Aptos", n(TU.aptos.sum()), f"{len(TU)} seções · {TU.local_cadastro.nunique()} locais"),
               ("Faltaram", n(TU.faltaram.sum()), f"{pct(100 * TU.faltaram.sum() / TU.aptos.sum())} de abstenção"),
               ("Eleitores de Lula em casa", cv.fmt_qtd(TU.lula_casa.sum()), "seção por seção"),
               ("Lula no 1º turno", pct(100 * TU.lula.sum() / TU.validos.sum()), "dos votos válidos"),
               ("Abstenção na zona urbana", pct(100 * zt.loc["Zona urbana"].f / zt.loc["Zona urbana"].a)
                if "Zona urbana" in zt.index else "–", "cidade"),
               ("Abstenção na zona rural", pct(100 * zt.loc["Zona rural"].f / zt.loc["Zona rural"].a)
                if "Zona rural" in zt.index else "–", "povoados")], verm=True)
    with st.container(key="cv_papel_tun"):
        _cab("Tuntum por bairro e povoado", "Onde eles estão em Tuntum",
             "Cada ponto é um local de votação: quanto maior, mais gente de Lula ficou em casa.")
        c1, c2 = st.columns([1.5, 1], gap="large")
        with c1:
            if LOCAIS_GEO is not None:
                pts = loc.merge(LOCAIS_GEO[["local", "lat", "lon"]].rename(columns={"local": "local_cadastro"}),
                                on="local_cadastro").dropna(subset=["lat", "lon"])
                cd_tun = str(MUN.loc[MUN.cd_tse == motor_2t.TUNTUM, "cd_ibge"].iloc[0])
                _bolhas(pts, "lat", "lon", "zona_tipo", "lula_casa", "Local", altura=640, tam_max=44,
                        contorno=_contorno("ma", cd=cd_tun, passo=1))
        with c2:
            zg = TU.groupby("zona_tipo")
            blocos = []
            for z, v in zg.lula_casa.sum().sort_values(ascending=False).items():
                top = zg.get_group(z).groupby("bairro").lula_casa.sum().sort_values(ascending=False).head(2)
                blocos.append((z, CORES_REG[z], v, " · ".join(f"{b_} {cv.fmt_qtd(x_)}" for b_, x_ in top.items())))
            _blocos(blocos, "Tuntum", TU.lula_casa.sum())
        st.markdown('<div class="cv-fonte">Fonte: TSE, boletins de urna do 1º turno de 2026. Eleitores de Lula estimados pela '
                    'votação de Lula na própria seção. Bairro conforme o cadastro do local de votação no TSE.</div>',
                    unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(key="cv_verm_tun"):
            por_b = bb.sort_values("lula_casa", ascending=False).head(10)
            _cab("Os 10 bairros e povoados", "Votos a recuperar por bairro", "Eleitores de Lula que não votaram no 1º turno")
            _barras([(x.bairro, x.lula_casa) for x in por_b.itertuples()])
            st.markdown('<div class="cv-fonte">Astolfo Seabra e Vila Luizão contam como um bairro só. Fonte: TSE, '
                        'boletins de urna do 1º turno de 2026.</div>', unsafe_allow_html=True)
    with c2:
        with st.container(key="cv_papel_tun10"):
            fortes = loc[loc.lula_pct >= 60].head(10)
            _cab("Os 10 locais de votação", "Onde Lula vence e mais gente ficou em casa",
                 "Locais onde Lula teve 60% ou mais dos votos válidos", estrela=False)
            _lista([(x.Local, f"{x.bairro} · Lula {_br(x.lula_pct)}%", x.lula_casa) for x in fortes.itertuples()])
    with st.container(key="cv_papel_tungraf"):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            ba = bb.sort_values("abstencao_pct", ascending=False)
            _barras_pct(ba.bairro, ba.abstencao_pct, "Abstenção por bairro e povoado",
                        ref=100 * TU.faltaram.sum() / TU.aptos.sum(), ref_txt="média de Tuntum",
                        altura=max(460, 26 * len(ba) + 120))
        with c2:
            _dispersao(loc, "Local", "zona_tipo", "Abstenção × voto em Lula, por local de votação", rotular=6,
                       altura=max(460, 26 * len(ba) + 120))

    # ================= chamada final
    with st.container(key="cv_papel_cta"):
        st.markdown(f"""<span class="cv-tag">Domingo · 25 de outubro</span>
<div class="cv-h" style="font-size:clamp(3.4rem,11vw,8rem);margin-top:14px">{cv.fmt_qtd(BR_T["lula_casa"]).upper()}</div>
<div class="cv-faixa" style="background:#D3252B;color:#fff">eleitores de Lula</div>
<div class="cv-h">não foram às urnas<span class="ln"></span><span class="st">★</span></div>
<div class="cv-cta">É hora de<br>conversar<div class="e">e</div>convencer!</div>
<div class="cv-sub" style="margin-top:12px">Cada um leva um. Compartilhe com quem vota no seu bairro.</div>""",
                    unsafe_allow_html=True)
        compartilhar_2t("t2_compartilhar_cta")


# ================================================================ 2) ao vivo
@st.cache_data(ttl=60, show_spinner="Consultando o TSE…")
def vivo_nacional():
    return motor_2t.apuracao_nacional()


@st.cache_data(ttl=60, show_spinner="Consultando os municípios do Maranhão…")
def vivo_ma():
    return motor_2t.apuracao_ma()


@st.cache_data(ttl=60, show_spinner="Lendo os boletins de urna de Tuntum…")
def vivo_secoes(cd):
    return motor_2t.apuracao_secoes(cdmun=cd)


NIVEIS_REG = {"Regiões intermediárias (5)": "regiao_intermediaria", "Regiões imediatas (22)": "regiao_imediata"}


def por_regiao(m, chave, ao_vivo=True):
    """Soma por região do IBGE. m: municípios com regiões, previsão e (ao vivo) v_13, v_22, vv, pst."""
    d = m.copy()
    if ao_vivo:
        for c in ("v_13", "v_22", "vv", "pst"):
            d[c] = d[c].fillna(0) if c in d else 0
        d["apurado_pond"] = d.pst / 100 * d.validos_2t_est
    g = d.groupby(chave).agg(
        municipios=("cd_ibge", "count"), esperado=("validos_2t_est", "sum"), prev_l=("votos_lula_2t", "sum"),
        prev_f=("votos_flavio_2t", "sum"), l1=("lula", "sum"), v1=("validos", "sum"),
        **({"lula": ("v_13", "sum"), "flavio": ("v_22", "sum"), "apurado_pond": ("apurado_pond", "sum")} if ao_vivo else {}))
    g["previsto"] = 100 * g.prev_l / (g.prev_l + g.prev_f)
    g["primeiro"] = 100 * g.l1 / g.v1  # % dos válidos, como no resto da página
    if ao_vivo:
        g["apurado"] = 100 * g.apurado_pond / g.esperado
        g["lula_pct"] = 100 * g.lula / (g.lula + g.flavio).replace(0, np.nan)
        g["dif"] = g.lula_pct - g.previsto
        g["saldo"] = g.lula - g.flavio
    return g.reset_index()


def tabela_regioes(m, ao_vivo, key):
    st.markdown("##### Por região geográfica do IBGE")
    nivel = st.segmented_control("Agrupar por", list(NIVEIS_REG), default=list(NIVEIS_REG)[0], key=key) \
        or list(NIVEIS_REG)[0]
    chave = NIVEIS_REG[nivel]
    g = por_regiao(m, chave, ao_vivo)
    nome = "Região intermediária" if chave == "regiao_intermediaria" else "Região imediata"
    if ao_vivo:
        g = g.sort_values("saldo", ascending=False)
        tabela(g[[chave, "municipios", "apurado", "lula", "flavio", "lula_pct", "previsto", "dif", "saldo"]].rename(
            columns={chave: nome, "municipios": "Municípios", "apurado": "% apurado", "lula": "Lula", "flavio": "Flávio",
                     "lula_pct": "Lula %", "previsto": "Previsto %", "dif": "Diferença (pts)", "saldo": "Saldo Lula"}),
            height=min(60 + 36 * len(g), 560))
    else:
        g["saldo_prev"] = g.prev_l - g.prev_f
        g = g.sort_values("saldo_prev", ascending=False)
        tabela(g[[chave, "municipios", "esperado", "primeiro", "previsto", "prev_l", "prev_f", "saldo_prev"]].rename(
            columns={chave: nome, "municipios": "Municípios", "esperado": "Válidos esperados",
                     "primeiro": "Lula 1º turno %", "previsto": "Lula 2º turno % (proj.)", "prev_l": "Votos Lula (proj.)",
                     "prev_f": "Votos Flávio (proj.)", "saldo_prev": "Saldo Lula (proj.)"}),
            height=min(60 + 36 * len(g), 560))
    st.caption("Divisão regional do IBGE (2017). Cada região leva o nome da sua cidade-polo.")


def tabela_polos(m, ao_vivo):
    st.markdown("##### Cidades-polo das regiões")
    d = m[m.polo_imediata == 1].copy()
    d["Polo de"] = np.where(d.polo_intermediaria == 1, "intermediária e imediata", "região imediata")
    if ao_vivo:
        for c in ("v_13", "v_22", "pst"):
            d[c] = d[c].fillna(0) if c in d else 0
        d["lula_pct"] = 100 * d.v_13 / (d.v_13 + d.v_22).replace(0, np.nan)
        d["dif"] = d.lula_pct - d.lula_2t
        d = d.sort_values("validos_2t_est", ascending=False)
        tabela(d[["municipio", "regiao_intermediaria", "Polo de", "pst", "v_13", "v_22", "lula_pct", "lula_2t", "dif"]].rename(
            columns={"municipio": "Cidade-polo", "regiao_intermediaria": "Região intermediária", "pst": "% apurado",
                     "v_13": "Lula", "v_22": "Flávio", "lula_pct": "Lula %", "lula_2t": "Previsto %",
                     "dif": "Diferença (pts)"}), height=min(60 + 36 * len(d), 600))
    else:
        d = d.sort_values("validos_2t_est", ascending=False)
        tabela(d[["municipio", "regiao_intermediaria", "Polo de", "validos", "lula_1t_pct", "lula_2t", "votos_lula_2t",
                  "votos_flavio_2t"]].rename(
            columns={"municipio": "Cidade-polo", "regiao_intermediaria": "Região intermediária",
                     "validos": "Válidos 1º turno", "lula_1t_pct": "Lula 1º turno %", "lula_2t": "Lula 2º turno % (proj.)",
                     "votos_lula_2t": "Votos Lula (proj.)", "votos_flavio_2t": "Votos Flávio (proj.)"}),
            height=min(60 + 36 * len(d), 600))
    st.caption(f"{len(d)} cidades-polo: as que dão nome às 22 regiões imediatas (Tutóia e Araioses dividem uma). "
               "As 6 que também nomeiam regiões intermediárias estão marcadas.")


def apuracao_por_bairro(base_t, sec_v):
    """Ao vivo em Tuntum: um resumo por bairro/povoado e uma tabela de seções para cada um."""
    st.markdown("##### Apuração por bairro e povoado")
    s = base_t[["secao", "bairro", "zona_tipo", "Local", "aptos", "lula", "flavio", "lula_2t"]].rename(
        columns={"lula": "lula_1t", "flavio": "flavio_1t"})
    if len(sec_v):
        v = sec_v.assign(secao=sec_v.secao.astype(str).str.zfill(4))[["secao", "lula", "flavio", "comparecimento",
                                                                      "brancos", "nulos"]]
        s = s.merge(v, on="secao", how="left")
    else:
        s = s.assign(lula=np.nan, flavio=np.nan, comparecimento=np.nan, brancos=np.nan, nulos=np.nan)
    s["apurada"] = s.lula.notna()
    ap = s[s.apurada]
    g = s.groupby(["zona_tipo", "bairro"], as_index=False).agg(secoes=("secao", "count"), apuradas=("apurada", "sum"),
                                                               aptos=("aptos", "sum"))
    a = ap.groupby("bairro", as_index=False).agg(lula=("lula", "sum"), flavio=("flavio", "sum"),
                                                 l1=("lula_1t", "sum"), f1=("flavio_1t", "sum"))
    g = g.merge(a, on="bairro", how="left").fillna({"lula": 0, "flavio": 0, "l1": 0, "f1": 0})
    g["lula_pct"] = 100 * g.lula / (g.lula + g.flavio).replace(0, np.nan)
    g["lula_1t_pct"] = 100 * g.l1 / (g.l1 + g.f1).replace(0, np.nan)
    g["saldo"] = g.lula - g.flavio
    g = g.sort_values(["zona_tipo", "aptos"], ascending=[False, False])  # zona urbana primeiro, maiores primeiro
    tabela(g[["bairro", "zona_tipo", "apuradas", "secoes", "lula", "flavio", "lula_pct", "lula_1t_pct", "saldo"]].rename(
        columns={"bairro": "Bairro/povoado", "zona_tipo": "Zona", "apuradas": "Seções apuradas", "secoes": "Seções",
                 "lula": "Lula", "flavio": "Flávio", "lula_pct": "Lula %", "lula_1t_pct": "Lula % no 1º t (mesmas seções)",
                 "saldo": "Saldo Lula"}), height=min(60 + 36 * len(g), 640))
    st.caption("Lula % = Lula ÷ (Lula + Flávio). O 1º turno é comparado nas mesmas seções já apuradas. "
               f"{BAIRRO_UNIFICADO} são um bairro só.")
    for _, b in g.iterrows():
        d = s[s.bairro == b.bairro].sort_values("secao")
        rot = (f"{b.bairro} · {int(b.apuradas)}/{int(b.secoes)} seções · Lula {n(b.lula)} × Flávio {n(b.flavio)}"
               if b.apuradas else f"{b.bairro} · {int(b.secoes)} seções · aguardando boletins")
        with st.expander(rot):
            d = d.assign(lula_pct=100 * d.lula / (d.lula + d.flavio).replace(0, np.nan),
                         situacao=np.where(d.apurada, "apurada", "aguardando"))
            tabela(d[["secao", "Local", "situacao", "aptos", "comparecimento", "lula", "flavio", "lula_pct", "lula_1t",
                      "flavio_1t", "lula_2t"]].rename(columns={
                "secao": "Seção", "situacao": "Situação", "aptos": "Aptos", "comparecimento": "Votaram", "lula": "Lula",
                "flavio": "Flávio", "lula_pct": "Lula %", "lula_1t": "Lula 1º t", "flavio_1t": "Flávio 1º t",
                "lula_2t": "Previsto Lula %"}), height=min(60 + 36 * len(d), 520))


@st.cache_data(ttl=60, show_spinner=False)
def proj_vivo(nivel):
    """Projeção do final a partir da leitura ao vivo — uma vez por minuto por servidor (não por pessoa)."""
    if nivel == "uf":
        uf_v, br_v, _ = vivo_nacional()
        return motor_2t.projetar(uf_v, UF, "uf")[1] if br_v is not None else {"sem_dados": True}
    mun_v, ma_v, _ = vivo_ma()
    return motor_2t.projetar(mun_v, MUN, "cd_tse")[1] if ma_v is not None else {"sem_dados": True}


import mapa_br as mapa_br_mod  # noqa: E402


@st.cache_resource(show_spinner=False)
def iniciar_mapa_br():
    mapa_br_mod.iniciar(motor_2t)
    return True


@st.cache_data(show_spinner=False, max_entries=20)
def mapa_mun_ensaio(fracao, semente, _uf_v):
    return mapa_br_mod.desenhar(mapa_br_mod.ensaio(_uf_v))


def _leg(cores):
    return "".join(f'<span class="q" style="background:{c}"></span>' for c in cores)


LEGENDA_MAPA_MUN = (
    '<div class="t2-leg"><div class="tt">Como ler o mapa?</div>'
    + "".join(f'<div class="ln"><span class="q" style="background:{f}"></span><span class="q" style="background:{l}"></span>'
              f'<span>{r}</span></div>' for f, l, r in zip(mapa_br_mod.TONS_F, mapa_br_mod.TONS_L,
                                                             ("0 a 5 p.p.", "5 a 20 p.p.", "acima de 20 p.p.")))
    + '<div class="nt"><b style="color:#7C84C6">Azul: Flávio</b> · <b style="color:#E0607A">Vermelho: Lula</b> · '
      'cinza: ainda sem votos. Quanto mais escuro, maior a vantagem do 1º colocado.</div></div>')


def titulo_apurado(texto, pst):
    """Título da seção com o selo verde piscando: % apurado."""
    v = f"{float(pst or 0):.2f}".replace(".", ",")
    st.markdown(f'<div class="t2-ap-tit"><span>{texto}</span><span class="t2-ap-selo"><span class="pt"></span>{v} %</span>'
                '</div>', unsafe_allow_html=True)


def placar(nome_l, votos_l, nome_f, votos_f, total, rotulo=""):
    pl_, pf_ = (100 * votos_l / total, 100 * votos_f / total) if total else (0, 0)
    st.markdown(f"""<div class="t2-placar">
<div class="t2-pl" style="--cor:{COR_L};--escuro:#7A0A1C"><div class="ft" style="background-image:url('{fl}')"></div>
<div class="nm">{nome_l}{rotulo}</div><div class="vt">{n(votos_l)}</div><div class="pc">{pct(pl_, 2)} dos válidos</div></div>
<div class="t2-pl" style="--cor:{COR_F};--escuro:#0B2648"><div class="ft" style="background-image:url('{ff}')"></div>
<div class="nm">{nome_f}{rotulo}</div><div class="vt">{n(votos_f)}</div><div class="pc">{pct(pf_, 2)} dos válidos</div></div>
</div>""", unsafe_allow_html=True)


def bloco_projecao(r_, apurado, votos_l=0, votos_f=0):
    if r_.get("sem_dados"):
        st.markdown('<div class="t2-status">Projeção do final aparece quando ao menos 3 unidades tiverem votos.</div>',
                    unsafe_allow_html=True)
        return
    a10, a50, a90 = r_["final_a"]
    frente = "Lula" if votos_l >= votos_f else "Flávio"
    cards([("Apurado", pct(apurado, 2), "das seções/votos", "#1B2A41"),
           ("Diferença agora", n(abs(votos_l - votos_f)) + " votos", f"{frente} à frente na apuração",
            COR_L if frente == "Lula" else COR_F),
           ("Projeção do final · Lula", pct(a50, 2), f"faixa: {pct(a10, 2)} a {pct(a90, 2)}", COR_L),
           ("Projeção do final · Flávio", pct(100 - a50, 2), f"faixa: {pct(100 - a90, 2)} a {pct(100 - a10, 2)}", COR_F)])


def status(info, ensaio):
    hora = datetime.fromtimestamp(info.get("consultado", time.time()), BRT).strftime("%H:%M:%S")
    fonte = "🧪 Ensaio (cenário simulado do modelo)" if ensaio else f"📡 TSE · eleição {info.get('eleicao', '?')}"
    st.markdown(f'<div class="t2-status"><b>{fonte}</b> · consulta às {hora} (Brasília)'
                + (" · <b>leitura anterior (TSE sem resposta)</b>" if info.get("desatualizado") else "") + "</div>",
                unsafe_allow_html=True)
    for a in info.get("avisos", [])[:4]:
        st.markdown(f'<div class="t2-aviso">⚠️ {escape(str(a))}</div>', unsafe_allow_html=True)


with aba[1]:
    c = st.columns([1.3, 1, 1])
    # ?modo=vivo abre direto no ao vivo (link de divulgação no domingo e teste de carga antes dele)
    abre_vivo = _param("modo").lower() != "ensaio"
    modo = c[0].segmented_control("Modo", ["Ao vivo", "Ensaio"], default="Ao vivo" if abre_vivo else "Ensaio",
                                  key="t2_modo", selection_mode="single") or "Ensaio"
    ensaio = modo == "Ensaio"
    fracao = c[1].slider("Ensaio: quanto apurar", 2, 100, 35, 1, format="%d%%", disabled=not ensaio, key="t2_frac") / 100
    semente = c[2].number_input("Ensaio: cenário nº", 1, 99, 7, disabled=not ensaio, key="t2_sem")
    if ensaio:
        st.caption("Ensaio: um cenário sorteado do próprio modelo vira uma apuração parcial, para testar a página antes "
                   "de domingo. Não é previsão nem resultado.")
    elif agora < INICIO:
        st.info("A apuração do 2º turno começa no domingo, 25 de outubro, às 17h (Brasília). Até lá, o modo ao vivo "
                "mostra 0% apurado; use o **Ensaio** para ver a página funcionando.")

    @st.fragment(run_every=None if ensaio else "60s")
    def ao_vivo():
        if ensaio:
            uf_v, br_v, mun_v, ma_v, sec_v = motor_2t.ensaio(fracao, semente=int(semente))
            info = info_ma = {"consultado": time.time(), "avisos": []}
            info_sec = {"publicadas": len(sec_v), "lidas": len(sec_v)}
        else:
            uf_v, br_v, info = vivo_nacional()
            mun_v, ma_v, info_ma = vivo_ma()
            sec_v, info_sec = vivo_secoes(motor_2t.TUNTUM)
        status(info, ensaio)
        if br_v is None:
            st.error(info.get("erro", "Sem dados do TSE no momento."))
            with st.expander("Diagnóstico da conexão com o TSE"):
                if st.button("Testar agora", key="t2_diag"):
                    for etapa, ok, det in motor_2t.diagnostico():
                        st.write(("✅ " if ok else "❌ ") + f"**{etapa}** · {det}")
        else:
            vl, vf = br_v["votos"].get("13", 0), br_v["votos"].get("22", 0)
            titulo_apurado("🇧🇷 Brasil", br_v.get("pst", 0))
            placar("LULA", vl, "FLÁVIO BOLSONARO", vf, vl + vf)
            r_ = motor_2t.projetar(uf_v, UF, "uf")[1] if ensaio else proj_vivo("uf")
            bloco_projecao(r_, br_v.get("pst", 0), vl, vf)
            # histórico desta sessão
            h = st.session_state.setdefault("t2_hist_" + modo, [])
            if vl + vf and (not h or h[-1][1] != br_v.get("pst")):
                h.append((datetime.now(BRT).strftime("%H:%M:%S"), br_v.get("pst", 0), 100 * vl / (vl + vf),
                          r_.get("final_a", [None, None, None])[1]))
            c1, c2 = st.columns([1.4, 1], gap="large")
            with c1:
                u = uf_v.copy()
                u["uf"] = u.unidade.astype(str)
                u["lula_agora"] = np.where(u.vv > 0, 100 * u.get("v_13", 0) / u.vv.replace(0, np.nan), np.nan)
                u = u[u.uf != "ZZ"]
                todas = sorted(set(UF.uf) - {"ZZ"})
                faltam = [x for x in todas if x not in set(u.loc[u.lula_agora.notna(), "uf"])]
                try:  # mapa por município (vermelho Lula, azul Flávio); se falhar, volta o mapa por estado
                    if ensaio:
                        png, n_mun = mapa_mun_ensaio(fracao, int(semente), uf_v), None
                    else:
                        iniciar_mapa_br()
                        png, n_mun, _ = mapa_br_mod.imagem_atual()
                    with st.container(key="t2_mapa_mun"):
                        st.image(png, width="stretch")
                        st.markdown(LEGENDA_MAPA_MUN + (f'<div class="nt">{n(n_mun)} municípios com votos nesta leitura · '
                                    'atualiza a cada ~4 min</div>' if n_mun is not None else ""), unsafe_allow_html=True)
                except Exception:  # noqa: BLE001
                    fig = mapa_br(u[u.lula_agora.notna()], "lula_agora", "Apuração por estado · Lula (% dos válidos apurados)",
                                  hover={"pst": ":.1f", "lula_agora": ":.1f"})
                    grafico(sem_votos(fig, geo("br"), "properties.uf", faltam, faltam))
                    if faltam:
                        st.caption(f"Em cinza: {len(faltam)} estado(s) ainda sem votos apurados.")
            with c2:
                if len(h) >= 2:
                    hh = pd.DataFrame(h, columns=["hora", "apurado", "lula_agora", "lula_proj"])
                    fig = go.Figure()
                    fig.add_scatter(x=hh.apurado, y=hh.lula_agora, name="Lula apurado", line=dict(color=COR_L))
                    fig.add_scatter(x=hh.apurado, y=hh.lula_proj, name="Lula projetado", line=dict(color=COR_L, dash="dot"))
                    fig.add_hline(y=50, line_dash="dash", line_color="#5B6477")
                    fig.update_layout(title="Evolução nesta sessão", height=520, xaxis_title="% apurado",
                                      yaxis_title="Lula (% dos válidos)", legend=dict(orientation="h", y=-.15))
                    grafico(fig)
                else:
                    t = uf_v.assign(Lula=uf_v.get("v_13", 0), Flávio=uf_v.get("v_22", 0))
                    t = t.assign(saldo=t.Lula - t.Flávio).sort_values("saldo")
                    tabela(t[["unidade", "pst", "Lula", "Flávio", "saldo"]].rename(
                        columns={"unidade": "UF", "pst": "% apurado", "saldo": "Saldo Lula"}), height=500)

        # ---- Maranhão
        # mesma tela na simulação e no ao vivo; antes de começar, tudo aparece zerado/cinza
        comecou = ma_v is not None and bool(ma_v.get("validos"))
        titulo_apurado("🏛️ Maranhão", ma_v.get("pst", 0) if ma_v is not None else 0)
        if not comecou:
            st.markdown('<div class="t2-status">O Maranhão ainda não começou a apurar: as tabelas abaixo se preenchem '
                        'sozinhas assim que o TSE publicar os primeiros votos.</div>', unsafe_allow_html=True)
            mun_v = pd.DataFrame({"unidade": MUN.cd_tse, "pst": 0.0, "vv": 0.0, "v_13": 0.0, "v_22": 0.0})
        ml, mf = (ma_v["votos"].get("13", 0), ma_v["votos"].get("22", 0)) if comecou else (0, 0)
        placar("LULA · MA", ml, "FLÁVIO · MA", mf, ml + mf)
        if comecou:
            rm = motor_2t.projetar(mun_v, MUN, "cd_tse")[1] if ensaio else proj_vivo("ma")
            bloco_projecao(rm, ma_v.get("pst", 0), ml, mf)
        m = MUN[["cd_tse", "cd_ibge", "municipio", "lula_2t", "lula", "flavio", "validos", "validos_2t_est",
                 "votos_lula_2t", "votos_flavio_2t", "regiao_imediata", "regiao_intermediaria", "polo_imediata",
                 "polo_intermediaria"]].merge(mun_v.assign(cd_tse=mun_v.unidade.astype(str)), on="cd_tse", how="left")
        for c_ in ("vv", "pst", "v_13", "v_22"):
            m[c_] = m[c_].fillna(0) if c_ in m else 0.0
        m["lula_agora"] = np.where(m.vv > 0, 100 * m.v_13 / m.vv.replace(0, np.nan), np.nan)
        m["desvio"] = m.lula_agora - m.lula_2t
        c1, c2 = st.columns([1.3, 1], gap="large")
        with c1:
            m_ok = m[m.lula_agora.notna()]
            if len(m_ok):
                fig = px.choropleth_map(m_ok, geojson=geo_recorte(geo("ma"), "properties.CD_MUN", m_ok.cd_ibge),
                                        locations="cd_ibge", featureidkey="properties.CD_MUN",
                                        color="lula_agora", color_continuous_scale=ESCALA, range_color=(20, 80),
                                        map_style="carto-positron", zoom=5.3, center={"lat": -5.2, "lon": -45.2},
                                        opacity=.85, hover_name="municipio",
                                        hover_data={"pst": ":.1f", "lula_agora": ":.1f", "lula_2t": ":.1f", "cd_ibge": False})
                fig.update_traces(text=[cartao_municipio(r, ao_vivo=True) for r in m_ok.itertuples()],
                                  hovertemplate="%{text}<extra></extra>", hoverlabel=HOVER_CARD)
            else:
                fig = go.Figure()
                fig.update_layout(map=dict(style="carto-positron", zoom=5.3, center={"lat": -5.2, "lon": -45.2}))
            fig.update_layout(height=560, margin=dict(l=0, r=0, t=36, b=0), title="Municípios · Lula apurado (%)",
                              coloraxis_colorbar=dict(title="", ticksuffix="%"))
            falt = m[m.lula_agora.isna()]
            nomes_falt = [f'<span style="font-size:15px"><b>{escape(str(r.municipio))}</b></span><br>'
                          f'<span style="color:#9FB7D9;font-size:11px">📍 REGIÃO {escape(str(r.regiao_imediata).upper())}</span><br>'
                          f'{_LINHA}<br><span style="color:#9FB7D9">⏳ aguardando os primeiros votos</span><br>'
                          f'{_rot("Previsto Lula")}  <b>{_br(r.lula_2t)}%</b>  ·  {_rot("Flávio")}  <b>{_br(100 - r.lula_2t)}%</b><br>'
                          f'{_barra(r.lula_2t)}' for r in falt.itertuples()]
            grafico(sem_votos(fig, geo("ma"), "properties.CD_MUN", falt.cd_ibge, nomes_falt))
            if len(falt):
                st.caption(f"Em cinza: {len(falt)} município(s) ainda sem votos apurados.")
        with c2:
            t = m[m.vv > 0].sort_values("desvio") if (m.vv > 0).any() else m.sort_values("validos_2t_est", ascending=False)
            tabela(t[["municipio", "pst", "lula_agora", "lula_2t", "desvio"]].rename(columns={
                "municipio": "Município", "pst": "% apurado", "lula_agora": "Lula agora %",
                "lula_2t": "Lula previsto %", "desvio": "Diferença (pts)"}), height=540)
        c1, c2 = st.columns([1, 1.15], gap="large")
        with c1:
            tabela_regioes(m, True, "t2_reg_vivo")
        with c2:
            tabela_polos(m, True)

        # ---- Tuntum
        tun = mun_v[mun_v.unidade.astype(str) == motor_2t.TUNTUM] if len(mun_v) else pd.DataFrame()
        titulo_apurado("📍 Tuntum · boletins de urna por seção",
                       float(tun.pst.iloc[0]) if len(tun) and "pst" in tun else 0)
        if len(tun) and tun.vv.iloc[0] > 0:
            placar("LULA · TUNTUM", tun.get("v_13", pd.Series([0])).iloc[0], "FLÁVIO · TUNTUM",
                   tun.get("v_22", pd.Series([0])).iloc[0], tun.vv.iloc[0], "")
        st.caption(f"Boletins publicados: {info_sec.get('publicadas', 0)} · lidos: {info_sec.get('lidas', 0)} de "
                   f"{len(SEC)} seções.")
        base_t, _ = base_tuntum()
        lidas = set(sec_v.secao.astype(str).str.zfill(4)) if len(sec_v) else set()
        prog = base_t.assign(apurada=base_t.secao.isin(lidas)).groupby("bairro", as_index=False).agg(
            secoes=("secao", "count"), apuradas=("apurada", "sum"), aptos=("aptos", "sum"),
            aptos_apurados=("aptos", lambda a: a[base_t.loc[a.index, "secao"].isin(lidas)].sum()))
        faltam = int(base_t.loc[~base_t.secao.isin(lidas), "aptos"].sum())
        cards([("Seções de Tuntum apuradas", f"{len(lidas)} de {len(base_t)}", "boletins de urna lidos", "#1B2A41"),
               ("Eleitores aptos ainda não apurados", n(faltam), f"de {n(base_t.aptos.sum())} aptos", "#6D5BA8")])
        prog = prog.sort_values("aptos", ascending=False)
        fig = go.Figure()
        fig.add_bar(y=prog.bairro, x=prog.apuradas, orientation="h", name="apuradas", marker_color="#2E7D5B")
        fig.add_bar(y=prog.bairro, x=prog.secoes - prog.apuradas, orientation="h", name="faltam",
                    marker_color="#D6DEE9")
        fig.update_layout(barmode="stack", title="Seções apuradas por bairro/povoado",
                          height=max(380, 22 * len(prog) + 110), yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
                          legend=dict(orientation="h", y=-.06))
        grafico(fig)
        apuracao_por_bairro(base_t, sec_v)
        if len(sec_v):
            ganho = base_t[["secao", "bairro", "Local", "lula", "flavio", "comparecimento"]].rename(
                columns={"lula": "lula_1t", "flavio": "flavio_1t", "comparecimento": "comp_1t"}).merge(
                sec_v.assign(secao=sec_v.secao.astype(str).str.zfill(4))[["secao", "lula", "flavio", "comparecimento"]],
                on="secao")
            ganho["Lula ganhou"] = ganho.lula - ganho.lula_1t
            ganho["Flávio ganhou"] = ganho.flavio - ganho.flavio_1t
            ganho["Comparecimento (dif.)"] = ganho.comparecimento - ganho.comp_1t
            cards([("Lula · votos a mais que no 1º turno", f"{int(ganho['Lula ganhou'].sum()):+,}".replace(",", "."),
                    "nas seções já apuradas", COR_L),
                   ("Flávio · votos a mais que no 1º turno", f"{int(ganho['Flávio ganhou'].sum()):+,}".replace(",", "."),
                    "nas seções já apuradas", COR_F),
                   ("Comparecimento × 1º turno", f"{int(ganho['Comparecimento (dif.)'].sum()):+,}".replace(",", "."),
                    "eleitores nas seções já apuradas", "#1B2A41")])
            tabela(ganho.sort_values("Lula ganhou")[["secao", "bairro", "Local", "lula_1t", "lula", "Lula ganhou",
                                                     "flavio_1t", "flavio", "Flávio ganhou", "Comparecimento (dif.)"]].rename(
                columns={"secao": "Seção", "bairro": "Bairro/povoado", "lula_1t": "Lula 1º t", "lula": "Lula 2º t",
                         "flavio_1t": "Flávio 1º t", "flavio": "Flávio 2º t"}), height=360)
            s_ = SEC[["secao", "local", "lula_2t"]].merge(sec_v.assign(secao=sec_v.secao.astype(str).str.zfill(4))
                                                          .drop(columns=["local"], errors="ignore"), on="secao")
            s_["lula_agora"] = 100 * s_.lula / (s_.lula + s_.flavio).replace(0, np.nan)
            s_["desvio"] = s_.lula_agora - s_.lula_2t
            c1, c2 = st.columns([1.2, 1], gap="large")
            with c1:
                fig = go.Figure()
                s_ = s_.sort_values("secao")
                fig.add_bar(x=s_.secao, y=s_.lula, name="Lula", marker_color=COR_L)
                fig.add_bar(x=s_.secao, y=s_.flavio, name="Flávio", marker_color=COR_F)
                fig.update_layout(barmode="stack", title="Votos por seção apurada", height=420, xaxis_title="Seção",
                                  legend=dict(orientation="h", y=-.2))
                grafico(fig)
            with c2:
                tabela(s_[["secao", "local", "lula", "flavio", "lula_agora", "lula_2t", "desvio"]].rename(columns={
                    "secao": "Seção", "local": "Local", "lula": "Lula", "flavio": "Flávio", "lula_agora": "Lula %",
                    "lula_2t": "Previsto %", "desvio": "Diferença (pts)"}), height=400)

    ao_vivo()


# ================================================================ 3) Maranhão
with aba[2]:
    ma = SIM["maranhao"]
    i_ma = UF[UF.uf == "MA"].iloc[0]
    cards([("Lula no MA (projeção)", pct(ma["lula_p10_p50_p90"][1]),
            f"faixa: {pct(ma['lula_p10_p50_p90'][0])} a {pct(ma['lula_p10_p50_p90'][2])}", COR_L),
           ("1º turno no MA", f"{pct(i_ma.lula_1t_pct)} × {pct(i_ma.flavio_1t_pct)}", "Lula × Flávio, válidos", "#1B2A41"),
           ("Saldo projetado de Lula", "+" + mil(i_ma.saldo_lula_2t) + " votos", "no estado", COR_L),
           ("Municípios", f"{ma['municipios_favorito_lula']} · {ma['municipios_favorito_flavio']}",
            f"favoritos Lula · Flávio ({ma['municipios_indefinidos']} indefinidos)", "#6D5BA8")])
    opcoes = {"Projeção do 2º turno · Lula %": ("lula_2t", (20, 85)),
              "1º turno · Lula %": ("lula_1t_pct", (20, 85)),
              "Variação projetada (pts)": ("variacao", (-6, 6))}
    vis = st.segmented_control("Mapa", list(opcoes), default=list(opcoes)[0], key="t2_ma_mapa") or list(opcoes)[0]
    m = MUN.assign(variacao=MUN.lula_2t - MUN.lula_1t_pct, prob_lula_pct=100 * MUN.prob_lula)
    col_, faixa = opcoes[vis]
    c1, c2 = st.columns([1.35, 1], gap="large")
    with c1:
        fig = px.choropleth_map(m, geojson=geo("ma"), locations="cd_ibge", featureidkey="properties.CD_MUN", color=col_,
                                color_continuous_scale=ESCALA, range_color=faixa, map_style="carto-positron", zoom=5.3,
                                center={"lat": -5.2, "lon": -45.2}, opacity=.85, hover_name="municipio",
                                hover_data={"lula_1t_pct": ":.1f", "lula_2t": ":.1f", "votos_lula_2t": ":,.0f",
                                            "votos_flavio_2t": ":,.0f", "cd_ibge": False})
        fig.update_traces(text=[cartao_municipio(r) for r in m.itertuples()], hovertemplate="%{text}<extra></extra>",
                          hoverlabel=HOVER_CARD, selector=dict(type="choroplethmap"))
        fig.update_layout(height=640, margin=dict(l=0, r=0, t=36, b=0), title=vis,
                          coloraxis_colorbar=dict(title="", ticksuffix="%" if col_ != "variacao" else " pts"))
        grafico(fig)
    with c2:
        busca = st.text_input("Buscar município", key="t2_busca_ma", placeholder="ex.: Imperatriz")
        t = m.copy()
        if busca:
            alvo = busca.strip().lower()
            t = t[t.municipio.str.lower().str.contains(alvo, na=False)]
        t = t.sort_values("validos", ascending=False)
        tabela(t[["municipio", "validos", "lula_1t_pct", "lula_2t", "votos_lula_2t", "votos_flavio_2t",
                  "saldo_lula_2t"]].rename(columns={
            "municipio": "Município", "validos": "Válidos 1º turno", "lula_1t_pct": "Lula 1º turno %",
            "lula_2t": "Lula 2º turno %", "votos_lula_2t": "Votos Lula (proj.)", "votos_flavio_2t": "Votos Flávio (proj.)",
            "saldo_lula_2t": "Saldo Lula"}), height=560)
    c1, c2 = st.columns([1, 1.15], gap="large")
    with c1:
        tabela_regioes(MUN, False, "t2_reg_prev")
    with c2:
        tabela_polos(MUN, False)
    st.markdown("##### Seções de um município (boletins de urna do TSE)")
    nomes = MUN.sort_values("municipio").set_index("cd_tse").municipio
    cd_esc = st.selectbox("Município", list(nomes.index), format_func=lambda c: nomes[c],
                          index=list(nomes.index).index(motor_2t.TUNTUM), key="t2_mun_sec")
    turno_sec = st.segmented_control("Turno", ["1º turno (4/10)", "2º turno (25/10)"], default="1º turno (4/10)",
                                     key="t2_turno_sec") or "1º turno (4/10)"
    if st.button("Ler boletins por seção", key="t2_ler_sec"):
        cod = motor_2t.codigos()
        if turno_sec.startswith("1º"):
            cod = dict(cod, eleicao=cod.get("eleicao_1t", "6257"), pleito=cod.get("pleito_1t", "3220"))
        with st.spinner("Lendo os boletins de urna…"):
            tab_s, inf = motor_2t.apuracao_secoes(cod, cd_esc)
        if len(tab_s):
            tab_s["Lula %"] = 100 * tab_s.lula / (tab_s.lula + tab_s.flavio).replace(0, np.nan)
            st.caption(f"{inf['lidas']} boletins lidos de {inf['publicadas']} publicados.")
            tabela(tab_s.drop(columns=["hora"]).rename(columns={"zona": "Zona", "secao": "Seção", "local": "Local",
                                                                 "aptos": "Aptos", "comparecimento": "Comparecimento",
                                                                 "lula": "Lula", "flavio": "Flávio", "brancos": "Brancos",
                                                                 "nulos": "Nulos"}), height=420)
        else:
            st.warning("Nenhum boletim disponível agora (antes da apuração, ou o TSE não respondeu).")


# ================================================================ 4) Tuntum
with aba[3]:
    tun = MUN[MUN.cd_tse == motor_2t.TUNTUM].iloc[0]
    tt = SIM["tuntum"]
    cards([("Lula em Tuntum (projeção)", pct(tt["lula_p10_p50_p90"][1]),
            f"faixa: {pct(tt['lula_p10_p50_p90'][0])} a {pct(tt['lula_p10_p50_p90'][2])}", COR_L),
           ("1º turno em Tuntum", f"{n(tun.lula)} × {n(tun.flavio)}",
            f"Lula {pct(tun.lula_1t_pct)} × Flávio {pct(tun.flavio_1t_pct)}", "#1B2A41"),
           ("Votos projetados", f"{n(tt['votos_lula_p50'])} × {n(tt['votos_flavio_p50'])}", "Lula × Flávio", COR_F),
           ("Seções · locais", f"{tt['secoes']} · {tt['locais']}", f"{n(SEC.aptos.sum())} eleitores aptos · zona 79",
            "#6D5BA8")])
    s_, nomes_loc = base_tuntum()
    c1, c2 = st.columns([1.1, 1], gap="large")
    with c1:
        g_tun = {"type": "FeatureCollection", "features": [f for f in geo("ma")["features"]
                                                           if f["properties"]["CD_MUN"] == str(tun.cd_ibge)]}
        fig = go.Figure()
        fig.add_choroplethmap(geojson=g_tun, locations=[str(tun.cd_ibge)], z=[1], featureidkey="properties.CD_MUN",
                              colorscale=[[0, "rgba(27,42,65,.06)"], [1, "rgba(27,42,65,.06)"]], showscale=False,
                              marker_line_width=3, marker_line_color="#1B2A41", hoverinfo="skip")
        centro = {"lat": -5.46, "lon": -44.72}
        if LOCAIS_GEO is not None:
            por_local = s_.groupby("local_cadastro", as_index=False).agg(
                aptos=("aptos", "sum"), lula=("lula", "sum"), flavio=("flavio", "sum"),
                votos_lula_2t=("votos_lula_2t", "sum"), votos_flavio_2t=("votos_flavio_2t", "sum"),
                secoes=("secao", lambda x: ", ".join(sorted(x))))
            pts = por_local.merge(LOCAIS_GEO.rename(columns={"local": "local_cadastro"}), on="local_cadastro").dropna(
                subset=["lat", "lon"])
            pts["lula_2t"] = 100 * pts.votos_lula_2t / (pts.votos_lula_2t + pts.votos_flavio_2t)
            pts["lula_1t"] = 100 * pts.lula / (pts.lula + pts.flavio)
            pts["card"] = [cartao_local(r) for r in pts.itertuples()]
            tam = np.clip(np.sqrt(pts.aptos) / 1.6, 9, 34)
            # halo branco por baixo: destaca cada bolinha sobre o mapa
            fig.add_scattermap(lat=pts.lat, lon=pts.lon, mode="markers", hoverinfo="skip", showlegend=False,
                               marker=dict(size=tam + 6, color="rgba(255,255,255,.95)"))
            fig.add_scattermap(lat=pts.lat, lon=pts.lon, mode="markers",
                               marker=dict(size=tam, color=pts.lula_2t, colorscale=ESCALA, cmin=20, cmax=85, opacity=.95,
                                           colorbar=dict(title="", ticksuffix="%", len=.6, thickness=12)),
                               text=pts.card, hovertemplate="%{text}<extra></extra>", name="Locais de votação",
                               hoverlabel=HOVER_CARD)
            centro = {"lat": float(pts.lat.median()), "lon": float(pts.lon.median())}
        fig.update_layout(height=620, margin=dict(l=0, r=0, t=36, b=0), map_style="carto-positron",
                          map=dict(center=centro, zoom=8.2), title="Locais de votação · projeção Lula (%)",
                          showlegend=False)
        grafico(fig)
        if LOCAIS_GEO is not None:
            st.caption("Coordenadas do cadastro do TSE (não auditadas em campo); 35 dos 36 locais têm ponto. Tamanho = "
                       "eleitores aptos. As seções 64 a 67 (Ipu Iru) seguem o local do cadastro; o boletim indica outro.")
    with c2:
        grupo = st.segmented_control("Agrupar por", ["Bairro/povoado", "Local de votação"], default="Bairro/povoado",
                                     key="t2_tun_grupo") or "Bairro/povoado"
        chave = "bairro" if grupo.startswith("Bairro") else "Local"
        g = s_.groupby(chave, as_index=False).agg(aptos=("aptos", "sum"), lula=("lula", "sum"),
                                                  votos_lula_2t=("votos_lula_2t", "sum"),
                                                  votos_flavio_2t=("votos_flavio_2t", "sum")).sort_values(
            "aptos", ascending=False)
        fig = go.Figure()
        fig.add_bar(y=g[chave], x=g.votos_lula_2t, orientation="h", name="Lula (proj.)", marker_color=COR_L)
        fig.add_bar(y=g[chave], x=g.votos_flavio_2t, orientation="h", name="Flávio (proj.)", marker_color=COR_F)
        fig.add_scatter(y=g[chave], x=g.lula, mode="markers", name="Lula no 1º turno",
                        marker=dict(symbol="line-ns", size=14, line=dict(width=2, color="#1B2A41")))
        fig.update_layout(barmode="stack", height=max(420, 26 * len(g) + 120),
                          title=f"{grupo} · votos projetados no 2º turno", yaxis=dict(autorange="reversed"),
                          legend=dict(orientation="h", y=-.04))
        grafico(fig)
    # ================= indicadores (1º turno oficial + projeção)
    st.markdown("### 📊 Indicadores de Tuntum")
    tot = s_[["aptos", "comparecimento", "lula", "flavio", "validos", "brancos", "nulos", "em_disputa"]].sum()

    # 1) urbano × rural
    zt = s_.groupby("zona_tipo").agg(secoes=("secao", "count"), aptos=("aptos", "sum"),
                                     comparecimento=("comparecimento", "sum"), lula=("lula", "sum"),
                                     flavio=("flavio", "sum"), validos=("validos", "sum"), brancos=("brancos", "sum"),
                                     nulos=("nulos", "sum"), v2l=("votos_lula_2t", "sum"), v2f=("votos_flavio_2t", "sum"))
    st.markdown("##### Zona urbana × zona rural · 1º turno")
    itens = []
    for nome in ("Zona urbana", "Zona rural"):
        if nome not in zt.index:
            continue
        z = zt.loc[nome]
        itens += [(f"{nome} · Lula", pct(100 * z.lula / z.validos),
                   f"{n(z.lula)} votos · Flávio {pct(100 * z.flavio / z.validos)} ({n(z.flavio)}) · "
                   f"2º turno proj.: Lula {pct(100 * z.v2l / (z.v2l + z.v2f))}", COR_L),
                  (f"{nome} · comparecimento", pct(100 * z.comparecimento / z.aptos),
                   f"{n(z.aptos - z.comparecimento)} faltaram · {int(z.secoes)} seções · brancos e nulos "
                   f"{pct(100 * (z.brancos + z.nulos) / z.comparecimento)}", "#1B2A41")]
    cards(itens)

    # 6) Tuntum × Maranhão × Brasil
    st.markdown("##### Tuntum comparado ao Maranhão e ao Brasil · 1º turno")
    uf1 = pd.read_csv(DADOS / "tse_1t_2026" / "presidente_1t_uf.csv").set_index("abrangencia")
    linhas = [("Tuntum", tot.aptos, tot.comparecimento, tot.lula, tot.flavio, tot.validos, tot.brancos + tot.nulos)]
    for nome, k in (("Maranhão", "ma"), ("Brasil", "br")):
        r_ = uf1.loc[k]
        linhas.append((nome, r_.eleitorado, r_.comparecimento, r_.lula, r_.flavio, r_.validos, r_.brancos + r_.nulos))
    bench = pd.DataFrame([{"Onde": a_, "Lula %": 100 * l_ / v_, "Flávio %": 100 * f_ / v_,
                           "Demais candidatos %": 100 * (v_ - l_ - f_) / v_, "Comparecimento %": 100 * c_ / e_,
                           "Abstenção %": 100 - 100 * c_ / e_, "Brancos e nulos %": 100 * bn / c_}
                          for a_, e_, c_, l_, f_, v_, bn in linhas])
    tabela(bench, modo="identidade", height=160)

    # 2) comparecimento e abstenção · 3) brancos e nulos
    c1, c2 = st.columns(2, gap="large")
    with c1:
        lo = s_.groupby("Local", as_index=False).agg(aptos=("aptos", "sum"), comp=("comparecimento", "sum"))
        lo["abst"] = 100 - 100 * lo.comp / lo.aptos
        lo = lo.sort_values("abst", ascending=False)
        fig = go.Figure(go.Bar(y=lo.Local, x=lo.abst, orientation="h", marker=dict(color=lo.abst, colorscale="Oranges"),
                               text=[f"{pct(v)} · {n(a - c)}" for v, a, c in zip(lo.abst, lo.aptos, lo.comp)],
                               textposition="outside", hovertemplate="%{y}<br>abstenção %{x:.1f}%<extra></extra>"))
        fig.update_layout(title=f"Abstenção por local de votação (Tuntum: {pct(100 - 100 * tot.comparecimento / tot.aptos)}, "
                                f"{n(tot.aptos - tot.comparecimento)} eleitores)", height=max(420, 22 * len(lo) + 120),
                          yaxis=dict(autorange="reversed", tickfont=dict(size=10)), xaxis=dict(ticksuffix="%"))
        grafico(fig)
    with c2:
        bb = s_.groupby("bairro", as_index=False).agg(comp=("comparecimento", "sum"), brancos=("brancos", "sum"),
                                                     nulos=("nulos", "sum"))
        bb["bn"] = 100 * (bb.brancos + bb.nulos) / bb.comp
        bb = bb.sort_values("bn", ascending=False)
        fig = go.Figure()
        fig.add_bar(y=bb.bairro, x=100 * bb.brancos / bb.comp, orientation="h", name="Brancos", marker_color="#B8C2D1")
        fig.add_bar(y=bb.bairro, x=100 * bb.nulos / bb.comp, orientation="h", name="Nulos", marker_color="#6B7A90")
        fig.update_layout(barmode="stack", title=f"Brancos e nulos por bairro/povoado (Tuntum: "
                                                 f"{pct(100 * (tot.brancos + tot.nulos) / tot.comparecimento)})",
                          height=max(420, 22 * len(bb) + 120), yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
                          xaxis=dict(ticksuffix="%"), legend=dict(orientation="h", y=-.06))
        grafico(fig)
    st.markdown("###### Seções com mais eleitores que não votaram")
    tabela(s_.sort_values("faltosos", ascending=False).head(10)[["secao", "bairro", "Local", "aptos", "comparecimento",
                                                                 "faltosos"]].rename(columns={
        "secao": "Seção", "bairro": "Bairro/povoado", "aptos": "Aptos", "comparecimento": "Votaram",
        "faltosos": "Não votaram"}), height=390)

    # 4) margem e redutos
    st.markdown("##### Margem e redutos · 1º turno")
    ml = s_.groupby("Local", as_index=False).agg(bairro=("bairro", "first"), lula=("lula", "sum"),
                                                 flavio=("flavio", "sum"), validos=("validos", "sum"))
    ml["margem"] = ml.lula - ml.flavio
    ml["Lula %"] = 100 * ml.lula / ml.validos
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**Maiores vantagens de Lula**")
        tabela(ml.sort_values("margem", ascending=False).head(5)[["Local", "bairro", "lula", "flavio", "margem"]].rename(
            columns={"bairro": "Bairro/povoado", "lula": "Lula", "flavio": "Flávio", "margem": "Vantagem (votos)"}),
            height=230)
    with c2:
        st.markdown("**Locais em que Flávio foi melhor**")
        tabela(ml.sort_values("margem").head(5)[["Local", "bairro", "lula", "flavio", "margem"]].rename(
            columns={"bairro": "Bairro/povoado", "lula": "Lula", "flavio": "Flávio", "margem": "Vantagem de Lula (votos)"}),
            height=230)
    ap = s_[s_.margem_1t.abs() < 20].sort_values("margem_1t")
    st.markdown(f"**Seções apertadas** (diferença menor que 20 votos): {len(ap)} · Flávio venceu em "
                f"{int((s_.margem_1t < 0).sum())} seção(ões) no 1º turno")
    tabela(ap[["secao", "bairro", "Local", "lula", "flavio", "margem_1t", "em_disputa"]].rename(columns={
        "secao": "Seção", "bairro": "Bairro/povoado", "lula": "Lula", "flavio": "Flávio",
        "margem_1t": "Vantagem de Lula (votos)", "em_disputa": "Votos em disputa"}), height=380)

    # 5) votos em disputa
    st.markdown(f"##### Votos em disputa · {n(tot.em_disputa)} votos de Cury, Renan, Caiado, Zema e demais")
    vd = s_.groupby("bairro", as_index=False)[OUTROS_1T + ["em_disputa"]].sum().sort_values("em_disputa",
                                                                                            ascending=False)
    vd["para_lula"], vd["para_flavio"] = destino_em_disputa(vd)
    vd["indefinido"] = vd.em_disputa - vd.para_lula - vd.para_flavio
    fig = go.Figure()
    fig.add_bar(y=vd.bairro, x=vd.para_lula, orientation="h", name="tendem a Lula", marker_color=COR_L)
    fig.add_bar(y=vd.bairro, x=vd.para_flavio, orientation="h", name="tendem a Flávio", marker_color=COR_F)
    fig.add_bar(y=vd.bairro, x=vd.indefinido, orientation="h", name="branco, nulo ou não vota", marker_color="#C7CED9")
    tl, tf = destino_em_disputa(s_[OUTROS_1T].sum().to_frame().T)
    fig.update_layout(barmode="stack", height=max(420, 22 * len(vd) + 120),
                      title=f"Onde estão e para onde tendem (estimativa: ~{n(float(tl.iloc[0]))} para Lula, "
                            f"~{n(float(tf.iloc[0]))} para Flávio)",
                      yaxis=dict(autorange="reversed", tickfont=dict(size=10)), legend=dict(orientation="h", y=-.06))
    grafico(fig)
    st.caption("Estimativa com a transferência medida nas pesquisas (AtlasIntel e Quaest) para os eleitores de cada "
               "candidato; é uma tendência média, não o voto de cada pessoa.")

    st.markdown("##### As 97 seções")
    tabela(s_[["secao", "bairro", "Local", "aptos", "comparecimento", "lula", "flavio", "lula_1t_pct", "lula_2t",
               "lula_2t_p10", "lula_2t_p90", "votos_lula_2t", "votos_flavio_2t"]].rename(columns={
        "secao": "Seção", "bairro": "Bairro/povoado", "aptos": "Aptos", "comparecimento": "Compareceram (1º t)",
        "lula": "Lula 1º t", "flavio": "Flávio 1º t", "lula_1t_pct": "Lula 1º t %", "lula_2t": "Lula 2º t %",
        "lula_2t_p10": "P10 %", "lula_2t_p90": "P90 %", "votos_lula_2t": "Lula (proj.)",
        "votos_flavio_2t": "Flávio (proj.)"}), height=520)
    st.caption("1º turno: boletins de urna oficiais do TSE (as 97 seções somam exatamente o total do município). "
               "2º turno: projeção do modelo; no domingo, a aba Ao vivo lê os boletins de cada seção assim que o TSE publica.")


# ================================================================ 5) pesquisas e contexto
with aba[4]:
    fig = go.Figure()
    for inst, g in PES.groupby("instituto"):
        fig.add_scatter(x=g.meio, y=g.lula_2p, mode="markers+lines", name=inst, marker=dict(size=9),
                        line=dict(width=1), hovertemplate=f"{inst}<br>%{{x|%d/%m}} · Lula %{{y:.1f}}%<extra></extra>")
    fig.add_hline(y=50, line_dash="dash", line_color="#5B6477")
    fig.update_layout(title="Pesquisas registradas do 2º turno · Lula nos votos válidos", height=460, yaxis_title="Lula (%)",
                      legend=dict(orientation="h", y=-.2, font=dict(size=10)))
    grafico(fig)
    st.caption("Pesquisas medem intenção de quem diz que vai votar. O resultado depende de quem comparece: veja na aba "
               "📣 Convencimento onde estão os eleitores de Lula que faltaram no 1º turno.")
    st.markdown("##### Para onde vão os eleitores de quem ficou de fora")
    tr = TRF.assign(Lula=TRF.lula, Flávio=TRF.flavio, Outros=TRF.branco_nulo_indeciso)
    tabela(tr[["instituto", "eleitor_1t", "Flávio", "Lula", "Outros", "observacao"]].rename(columns={
        "instituto": "Instituto", "eleitor_1t": "Eleitor no 1º turno", "Outros": "Branco/nulo/indeciso",
        "observacao": "Obs."}), height=300)
    st.markdown("##### Linha do tempo do 2º turno")
    cor_lado = {"lula": COR_L, "flavio": COR_F}
    evs = CTX.sort_values("data", ascending=False)
    st.markdown('<div class="t2-tl">' + "".join(
        f'<div class="t2-ev" style="--cor:{cor_lado.get(str(e.lado), "#5B6477")}"><div class="d">'
        f'{e.data.strftime("%d/%m")} · {escape(str(e.tipo)).upper()}</div><div class="t">{escape(str(e.titulo))}</div>'
        f'<div class="x">{escape(str(e.detalhe))}</div><a href="{escape(str(e.fonte))}" target="_blank">fonte</a></div>'
        for e in evs.itertuples()) + "</div>", unsafe_allow_html=True)
    st.markdown("##### Todas as pesquisas usadas")
    tabela(PES.sort_values("fim", ascending=False)[["instituto", "contratante", "inicio", "fim", "amostra",
                                                    "registro_tse", "lula_validos", "flavio_validos"]].assign(
        inicio=lambda d: d.inicio.dt.strftime("%d/%m"), fim=lambda d: d.fim.dt.strftime("%d/%m")).rename(columns={
        "instituto": "Instituto", "contratante": "Contratante", "inicio": "Início", "fim": "Fim", "amostra": "Amostra",
        "registro_tse": "Registro TSE", "lula_validos": "Lula %", "flavio_validos": "Flávio %"}), height=480)


# ================================================================ 6) metodologia
with aba[5]:
    st.markdown(f"""
**📣 Projeto Convencimento: como os números são calculados**

1. **Quem faltou.** Para cada lugar, faltosos = eleitores aptos − quem compareceu no 1º turno (4/10/2026), pelos
   resultados oficiais do TSE: por estado no Brasil, por município no Maranhão e por seção (boletim de urna) em Tuntum.
2. **Eleitor de Lula estimado.** Os faltosos de cada lugar são contados como eleitores de Lula na mesma proporção dos
   votos válidos de Lula naquele lugar (é o método usado pelas campanhas de mobilização). Quanto menor o lugar, melhor a
   estimativa: em Tuntum a conta é seção por seção.
3. **A diferença a virar.** No 1º turno, Flávio teve {n(BR_T["flavio_1t"])} votos e Lula {n(BR_T["lula_1t"])}: diferença de
   {n(BR_T["diferenca"])}. Trazer de volta {pct(100 * BR_T["fracao_para_virar"], 1)} dos eleitores de Lula que ficaram em
   casa ({cv.fmt_qtd(BR_T["lula_casa"])}) cobre essa diferença.
4. **Regiões.** Estados agrupados nas 5 regiões do Brasil; municípios do Maranhão nas regiões geográficas do IBGE (2017);
   em Tuntum, bairro e povoado conforme o cadastro do local de votação (Astolfo Seabra e Vila Luizão como um só bairro).

**Limites.** É uma estimativa: quem faltou não vota necessariamente como os vizinhos. Os eleitores de Flávio que faltaram
também existem (estimativa: {cv.fmt_qtd(BR_T["flavio_casa"])}); a conta mostra o efeito de trazer de volta os de Lula.
O voto no exterior fica fora da conta.

**Apuração ao vivo.** No domingo, a partir das 17h (Brasília), a aba Ao vivo lê os arquivos oficiais do TSE a cada minuto
(Brasil, estados, os 217 municípios do Maranhão e os boletins de urna de cada seção de Tuntum). As abas Maranhão e
Tuntum mostram o resultado do 1º turno e a estimativa do modelo para o 2º turno nesses lugares.
""")


# ================================================================ rodapé com créditos
st.markdown(f"""<div class="t2-rodape">{LOGO_IMG.replace('<img', '<img class="logo"')}
<div><div class="nm">Aggilli Intelligence · Transformando dados em inteligência</div>
<div class="tx">{CREDITO}.
Projeto Convencimento: estimativas a partir dos resultados oficiais do TSE do 1º turno; apuração com dados públicos do TSE.<br><span style="opacity:.6">Versão do painel: 2º turno · 25/10 (mapa por município)</span></div></div>
<div class="t2-redes">{REDES}</div></div>""", unsafe_allow_html=True)
