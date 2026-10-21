"""Página — 2º turno presidencial (25/10/2026): previsão, apuração ao vivo, Maranhão e Tuntum.

Tudo do 2º turno fica nesta página; as páginas do 1º turno seguem como arquivo.
Dados do modelo: segundo_turno/resultados/ (gerados por segundo_turno/modelo_2t.py).
Ao vivo: segundo_turno/motor_2t.py (TSE com fallback em camadas).
"""
import base64
import json
import os
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
.st-key-t2_compartilhar {background: #FFFFFF; border: 1px solid #D6DEE9; border-radius: 16px; padding: 8px 12px 0;
  margin: 0 0 12px;}
.st-key-t2_compartilhar [data-testid="stLinkButton"] a {background: #25D366 !important; border-color: #25D366 !important;
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
[data-testid="stTabs"] [role="tablist"] {position: sticky !important; top: 3.4rem; z-index: 60 !important; display: flex !important;
  gap: 8px !important; padding: 8px !important; margin: 2px 0 18px !important; border-radius: 20px !important;
  overflow-x: auto; scrollbar-width: none; border: 0 !important;
  background: linear-gradient(145deg, rgba(18,35,63,.97), rgba(22,48,79,.97) 55%, rgba(27,59,102,.97)) !important;
  box-shadow: 0 14px 30px rgba(11,22,40,.22), inset 1px 1px 0 rgba(255,255,255,.10);}
[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar {display: none;}
[data-testid="stTabs"] [role="tablist"]::after, [data-testid="stTabs"] [role="tablist"]::before {display: none !important;}
[data-testid="stTabs"] .react-aria-SelectionIndicator, [data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"], [data-testid="stTabs"] [data-testid="stTabsHighlight"] {display: none !important;}
[data-testid="stTabs"] [role="tab"] {flex: 1 0 auto !important; justify-content: center !important; height: auto !important;
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
@media (max-width: 760px) {[data-testid="stTabs"] [role="tablist"] {top: 3rem; border-radius: 16px !important; padding: 6px !important;}
  [data-testid="stTabs"] [role="tab"] {flex: 0 0 auto !important; padding: .5rem .85rem !important;}
  [data-testid="stTabs"] [role="tab"] p {font-size: .82rem !important;}}
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
LINK_2T = os.environ.get("LINK_2T") or (os.environ.get("PUBLIC_URL", "").rstrip("/") + "/segundo_turno?so2t=1"
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


def compartilhar_2t():
    """Compartilhar só esta página: WhatsApp com mensagem pronta e o link para copiar."""
    link = LINK_2T
    if not link:
        return
    from urllib.parse import quote
    texto = ("🗳️ 2º turno · Lula × Flávio, com a Aggilli Intelligence: previsão, apuração ao vivo do TSE, Maranhão "
             "município a município e Tuntum seção a seção.\n\n👉 Acompanhe aqui: " + link)
    with st.container(key="t2_compartilhar"):
        c1, c2 = st.columns([1, 2.2], vertical_alignment="center")
        c1.link_button("📲 Compartilhar no WhatsApp", f"https://wa.me/?text={quote(texto)}", width="stretch")
        c2.code(link, language=None)


compartilhar_2t()


def cards(itens):
    st.markdown('<div class="t2-cards">' + "".join(
        f'<div class="t2-card" style="--cor:{c}"><div class="r">{r}</div><div class="v">{v}</div><div class="s">{s}</div></div>'
        for r, v, s, c in itens) + "</div>", unsafe_allow_html=True)


OUTROS_1T = ["cury", "renan", "caiado", "zema", "outros"]


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
    s["zona_tipo"] = np.where(s.bairro.fillna("").str.contains("Rural", case=False), "Zona rural", "Zona urbana")
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
aba = st.tabs(["🔮 Previsão", "🔴 Ao vivo · agora" if ao_vivo_agora else "📡 Ao vivo", "🗺️ Maranhão", "📍 Tuntum",
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
                            marker_line_color="#FFFFFF", marker_line_width=.6, text=list(nomes),
                            hovertemplate="<b>%{text}</b><br>ainda sem votos apurados<extra></extra>")
    fig.add_trace(base)
    fig.data = (fig.data[-1],) + fig.data[:-1]  # cinza por baixo das unidades já apuradas
    return fig


with aba[0]:
    r = SIM["resultado"]
    # votação oficial de cada um no 1º turno (TSE), em percentual dos válidos e em votos
    br1 = pd.read_csv(DADOS / "tse_1t_2026" / "presidente_1t_uf.csv").set_index("abrangencia").loc["br"]
    st.markdown(f"""<div class="t2-1t">
<div class="t2-1t-l" style="--cor:{COR_L};--escuro:#7A0A1C"><div class="ft" style="background-image:url('{fl}')"></div>
<div class="nm">LULA · PT · 1º TURNO</div><div class="pc">{pct(100 * br1.lula / br1.validos, 2)}</div>
<div class="vt">{n(br1.lula)} votos</div></div>
<div class="t2-1t-l" style="--cor:{COR_F};--escuro:#0B2648"><div class="ft" style="background-image:url('{ff}')"></div>
<div class="nm">FLÁVIO BOLSONARO · PL · 1º TURNO</div><div class="pc">{pct(100 * br1.flavio / br1.validos, 2)}</div>
<div class="vt">{n(br1.flavio)} votos</div></div></div>
<div class="t2-1t-nota">Resultado oficial do 1º turno (TSE, 4/10), em % dos votos válidos · {n(br1.validos)} válidos</div>""",
                unsafe_allow_html=True)
    if CEN is not None:
        v = 100 * CEN
        fig = go.Figure()
        bins = np.linspace(42, 56, 57)
        h, e = np.histogram(v, bins=bins)
        centros = (e[:-1] + e[1:]) / 2
        fig.add_bar(x=centros, y=100 * h / len(v), marker_color=[COR_L if x > 50 else COR_F for x in centros],
                    hovertemplate="Lula %{x:.1f}% · %{y:.1f}% dos cenários<extra></extra>")
        fig.add_vline(x=50, line_dash="dash", line_color="#1B2A41")
        fig.add_annotation(x=50.2, y=max(100 * h / len(v)) * .95, text="Lula acima de 50% →", showarrow=False, xanchor="left",
                           font=dict(color=COR_L, size=12))
        fig.add_annotation(x=49.8, y=max(100 * h / len(v)) * .95, text="← Flávio acima de 50%", showarrow=False,
                           xanchor="right", font=dict(color=COR_F, size=12))
        fig.update_layout(title="Os cenários simulados: Lula nos votos válidos", height=380, bargap=.05,
                          xaxis_title="Lula (% dos válidos)", yaxis_title="% dos cenários", showlegend=False)
        grafico(fig)
    c1, c2 = st.columns([1.4, 1], gap="large")
    with c1:
        fig = mapa_br(UF[UF.uf != "ZZ"], "lula_2t", "Projeção por estado · Lula (% dos válidos)",
                      hover={"lula_1t_pct": ":.1f", "lula_2t": ":.1f"})
        grafico(fig)
    with c2:
        reg = SIM["regioes"]
        fig = go.Figure()
        ordem = ["Nordeste", "Norte", "Sudeste", "Centro-Oeste", "Sul", "Exterior"]
        fig.add_bar(y=ordem, x=[reg[r_] for r_ in ordem], orientation="h", marker_color=COR_L, name="Lula",
                    text=[pct(reg[r_]) for r_ in ordem], textposition="inside")
        fig.add_bar(y=ordem, x=[100 - reg[r_] for r_ in ordem], orientation="h", marker_color=COR_F, name="Flávio",
                    text=[pct(100 - reg[r_]) for r_ in ordem], textposition="inside")
        fig.update_layout(barmode="stack", height=520, title="Por região (projeção)", yaxis=dict(autorange="reversed"),
                          xaxis=dict(range=[0, 100], ticksuffix="%"), legend=dict(orientation="h", y=-.08))
        grafico(fig)
    t = UF[UF.uf != "ZZ"].sort_values("saldo_lula_2t", ascending=False)
    tabela(t[["uf", "regiao", "lula_1t_pct", "lula_2t", "lula_2t_p10", "lula_2t_p90", "saldo_lula_2t"]].rename(columns={
        "uf": "UF", "regiao": "Região", "lula_1t_pct": "Lula 1º turno %", "lula_2t": "Lula 2º turno %",
        "lula_2t_p10": "Lula P10 %", "lula_2t_p90": "Lula P90 %", "saldo_lula_2t": "Saldo Lula (votos)"}), height=420)


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


@st.cache_data(ttl=60, show_spinner=False)
def proj_vivo(nivel):
    """Projeção do final a partir da leitura ao vivo — uma vez por minuto por servidor (não por pessoa)."""
    if nivel == "uf":
        uf_v, br_v, _ = vivo_nacional()
        return motor_2t.projetar(uf_v, UF, "uf")[1] if br_v is not None else {"sem_dados": True}
    mun_v, ma_v, _ = vivo_ma()
    return motor_2t.projetar(mun_v, MUN, "cd_tse")[1] if ma_v is not None else {"sem_dados": True}


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
    abre_vivo = agora >= INICIO - timedelta(hours=1) or _param("modo").lower() in ("vivo", "aovivo", "ao-vivo")
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
            return
        vl, vf = br_v["votos"].get("13", 0), br_v["votos"].get("22", 0)
        st.subheader("🇧🇷 Brasil")
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
        st.subheader("🏛️ Maranhão")
        if ma_v is not None and ma_v.get("validos"):
            ml, mf = ma_v["votos"].get("13", 0), ma_v["votos"].get("22", 0)
            placar("LULA · MA", ml, "FLÁVIO · MA", mf, ml + mf)
            rm = motor_2t.projetar(mun_v, MUN, "cd_tse")[1] if ensaio else proj_vivo("ma")
            bloco_projecao(rm, ma_v.get("pst", 0), ml, mf)
            m = MUN[["cd_tse", "cd_ibge", "municipio", "lula_2t"]].merge(
                mun_v.assign(cd_tse=mun_v.unidade.astype(str)), on="cd_tse", how="left")
            m["lula_agora"] = np.where(m.vv > 0, 100 * m.get("v_13", 0) / m.vv.replace(0, np.nan), np.nan)
            m["desvio"] = m.lula_agora - m.lula_2t
            c1, c2 = st.columns([1.3, 1], gap="large")
            with c1:
                m_ok = m[m.lula_agora.notna()]
                fig = px.choropleth_map(m_ok, geojson=geo_recorte(geo("ma"), "properties.CD_MUN", m_ok.cd_ibge),
                                        locations="cd_ibge",
                                        featureidkey="properties.CD_MUN",
                                        color="lula_agora", color_continuous_scale=ESCALA, range_color=(20, 80),
                                        map_style="carto-positron", zoom=5.3, center={"lat": -5.2, "lon": -45.2},
                                        opacity=.85, hover_name="municipio", hover_data={"pst": ":.1f",
                                                                                        "lula_agora": ":.1f",
                                                                                        "lula_2t": ":.1f",
                                                                                        "cd_ibge": False})
                fig.update_layout(height=560, margin=dict(l=0, r=0, t=36, b=0), title="Municípios · Lula apurado (%)")
                falt = m[m.lula_agora.isna()]
                grafico(sem_votos(fig, geo("ma"), "properties.CD_MUN", falt.cd_ibge, falt.municipio))
                if len(falt):
                    st.caption(f"Em cinza: {len(falt)} município(s) ainda sem votos apurados.")
            with c2:
                t = m[m.vv > 0].sort_values("desvio")
                tabela(t[["municipio", "pst", "lula_agora", "lula_2t", "desvio"]].rename(columns={
                    "municipio": "Município", "pst": "% apurado", "lula_agora": "Lula agora %",
                    "lula_2t": "Lula previsto %", "desvio": "Diferença (pts)"}), height=540)
        else:
            st.markdown('<div class="t2-status">O Maranhão ainda não começou a apurar.</div>', unsafe_allow_html=True)

        # ---- Tuntum
        st.subheader("📍 Tuntum · boletins de urna por seção")
        tun = mun_v[mun_v.unidade.astype(str) == motor_2t.TUNTUM] if len(mun_v) else pd.DataFrame()
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
        fig.update_layout(height=640, margin=dict(l=0, r=0, t=36, b=0), title=vis)
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
            fig.add_scattermap(lat=pts.lat, lon=pts.lon, mode="markers",
                               marker=dict(size=np.clip(np.sqrt(pts.aptos) / 1.6, 9, 34), color=pts.lula_2t,
                                           colorscale=ESCALA, cmin=20, cmax=85, opacity=.9,
                                           colorbar=dict(title="", ticksuffix="%", len=.6, thickness=12)),
                               customdata=np.column_stack([pts.nome.str.title(), pts.bairro.str.title(), pts.secoes,
                                                           pts.aptos, pts.lula_1t, pts.lula_2t]),
                               hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Seções: %{customdata[2]}"
                                             "<br>%{customdata[3]} aptos<br>Lula 1º turno: %{customdata[4]:.1f}%"
                                             "<br>Lula 2º turno (proj.): %{customdata[5]:.1f}%<extra></extra>",
                               name="Locais de votação")
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
    ens = SIM["componentes"]["pesquisas"]["ensemble"]
    c1, c2 = st.columns([1.5, 1], gap="large")
    with c1:
        fig = go.Figure()
        for inst, g in PES.groupby("instituto"):
            fig.add_scatter(x=g.meio, y=g.lula_2p, mode="markers+lines", name=inst, marker=dict(size=9),
                            line=dict(width=1), hovertemplate=f"{inst}<br>%{{x|%d/%m}} · Lula %{{y:.1f}}%<extra></extra>")
        dia = pd.Timestamp("2026-10-25")
        fig.add_scatter(x=[dia], y=[ens["est"]], mode="markers", name="Média dos 6 agregadores",
                        marker=dict(size=16, color=COR_L, symbol="diamond"),
                        error_y=dict(type="data", array=[1.28 * ens["dp"]], color=COR_L))
        fig.add_hline(y=50, line_dash="dash", line_color="#5B6477")
        fig.update_layout(title="Pesquisas do 2º turno · Lula nos votos válidos", height=480, yaxis_title="Lula (%)",
                          legend=dict(orientation="h", y=-.2, font=dict(size=10)))
        grafico(fig)
    with c2:
        mods = SIM["componentes"]["pesquisas"]["modelos"]
        t = pd.DataFrame([{"Agregador": k, "Lula %": v["est"], "Desvio (pts)": v["dp"]} for k, v in mods.items()])
        tabela(t, height=260)
        ef = SIM["componentes"]["pesquisas"]["efeito_instituto"]
        fig = go.Figure(go.Bar(x=list(ef.values()), y=list(ef.keys()), orientation="h",
                               marker_color=[COR_L if v > 0 else COR_F for v in ef.values()]))
        fig.update_layout(title="Efeito de cada instituto (pts para Lula)", height=420, yaxis=dict(autorange="reversed"))
        grafico(fig)
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
    comp = SIM["componentes"]
    e = comp["erro"]
    st.markdown(f"""
**Como o modelo projeta o 2º turno**

1. **Pesquisas do 2º turno** ({comp['pesquisas']['n']} pesquisas registradas, {comp['pesquisas']['primeira'][8:10]}/10 a
   {comp['pesquisas']['ultima'][8:10]}/10) passam pelos mesmos **6 agregadores** do modelo do 1º turno (média ponderada,
   mediana, efeito-instituto, Kalman, processo gaussiano e bayesiano hierárquico). Resultado: Lula com
   **{pct(ens['est'])}** dos válidos (desvio {n(ens['dp'], 1)} ponto).
2. **Erro das pesquisas.** No 1º turno de 2026, quase todos os institutos superestimaram Lula na disputa direta (erro
   médio de {n(abs(e['erro_1t_2026_medio']), 1)} pontos na margem). Nos 2º turnos de 2006 a 2022, o erro foi pequeno. Em
   cada cenário sorteamos um desses erros (metade das vezes de cada grupo) e uma **persistência de 0% a 100%**.
3. **Base estrutural.** Votos oficiais do 1º turno + transferência medida dos eleitores de Cury, Renan, Caiado, Zema e
   demais (cruzamentos AtlasIntel e Quaest) + pequena troca entre as bases e efeito do comparecimento. Resultado: Lula com
   **{pct(comp['estrutural']['lula_p10_p50_p90'][1])}**.
4. **Mistura:** {round(100 * comp['peso_pesquisas'])}% dos cenários partem das pesquisas e o resto da base estrutural.
5. **Geografia:** cada estado, município do MA e seção de Tuntum parte do próprio 1º turno com a mesma transferência,
   recebe o padrão medido de 2022 (o 2º turno acentua levemente a geografia do 1º), o recorte regional do Datafolha (meio
   caminho) e um ruído do tamanho medido; depois é calibrado para somar o nível de cima (Brasil → UF → município → seção).
""")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        tabela(pd.DataFrame([{"Instituto": k, "Erro no 1º turno 2026 (margem, pts)": v}
                             for k, v in e["erro_1t_2026_por_instituto"].items()]).sort_values(
            "Erro no 1º turno 2026 (margem, pts)"), height=420)
    with c2:
        tabela(pd.DataFrame([{"Eleição": k, "Erro das pesquisas finais de 2º turno (margem, pts)": v}
                             for k, v in e["historico_2t_por_eleicao"].items()]), height=220)
        trf = comp["estrutural"]["transferencia"]
        tabela(pd.DataFrame([{"Eleitor de": k, "Lula entre os que escolhem %": 100 * v["lula_entre"],
                              "Escolhe Lula ou Flávio %": 100 * v["decide"]} for k, v in trf.items()]), height=220)
    st.caption("Erro na margem = (Lula − Flávio na urna) − (Lula − Flávio na pesquisa), só os dois. Negativo = a pesquisa "
               "superestimou Lula. " + " ".join(SIM["limites"]) + f" Modelo gerado em {SIM['gerado_em'][:16].replace('T', ' ')}.")

# ================================================================ rodapé com créditos
st.markdown(f"""<div class="t2-rodape">{LOGO_IMG.replace('<img', '<img class="logo"')}
<div><div class="nm">Aggilli Intelligence · Transformando dados em inteligência</div>
<div class="tx">{CREDITO}. Modelo estatístico com pesquisas registradas no TSE e resultados oficiais do 1º turno;
apuração com dados públicos do TSE. Projeções não são certeza nem recomendação de voto.<br><span style="opacity:.6">Versão do painel: 2º turno · 21/10 20h30 (escala 1.000+)</span></div></div>
<div class="t2-redes">{REDES}</div></div>""", unsafe_allow_html=True)
