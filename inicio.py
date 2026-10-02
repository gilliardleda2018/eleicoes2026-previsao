"""Página inicial: marca no topo, capa, três cenários simétricos, compartilhar e créditos da Aggilli."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "apuracao"))
from comum import _logo_base64, pct  # noqa: E402

LINK = os.environ.get("LINK_PUBLICO", "https://aggillintelligence.com.br/eleicoes_2026") or \
    "https://aggillintelligence.com.br/eleicoes_2026"
BRT = timezone(timedelta(hours=-3))
INICIO_APURACAO = datetime(2026, 10, 4, 17, 0, tzinfo=BRT)


def ler(arq):
    try:
        return json.load(open(RAIZ / arq, encoding="utf-8"))["resultado_final"]
    except Exception:
        return {}


br = ler("nacional/resultados/simulacao_nacional.json")
ma = ler("resultados/simulacao.json")

# ---------------------------------------------------------------- visual da página inicial (só nesta página)
# azul mais leve que o resto do app: fundo claro e painéis em azul médio, no estilo "cartão de vidro"
st.markdown("""<style>
.stApp {background: radial-gradient(circle at 15% 0%, #F4F9FF 0%, transparent 45%),
                    linear-gradient(180deg, #EAF3FC 0%, #DCEAF8 100%) !important;}
.hm-topo, .hm-capa, [class*="st-key-hc_"], .st-key-hs_compartilhar, .hm-creditos {
    --az1: #2A63AD; --az2: #3474C2; --az3: #3C5FB5; --linha: rgba(255,255,255,.18); --suave: #D6E6FA;}
.hm-topo {display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 18px; padding: 14px 26px;
    border-radius: 18px; border: 1px solid var(--linha); color: #FFFFFF; margin: 2px 0 18px;
    background: linear-gradient(100deg, var(--az1), var(--az2)); box-shadow: 0 10px 26px rgba(33,86,160,.25);}
.hm-topo > img {height: 66px; display: block; margin: -6px 0;}
.hm-topo .hm-slogan {font: 700 1.3rem 'Montserrat'; letter-spacing: -.005em; text-align: center;}
.hm-topo .hm-slogan span, .hm-capa h1 span, .hm-creditos .cr-slogan span {color: #8FE3FF;}
.hm-contato {display: flex; flex-direction: column; align-items: flex-end; gap: 5px; font: 600 .84rem 'Montserrat';}
.hm-contato a {color: #FFFFFF !important; text-decoration: none; display: inline-flex; align-items: center; gap: 7px;}
.hm-contato b {color: #8FE3FF; letter-spacing: .08em; margin-left: 6px;}
.hm-redes {display: grid; grid-template-columns: auto auto; gap: 7px 16px; align-items: center; justify-items: start;
    font: 600 .82rem 'Montserrat';}
.hm-redes a {color: #FFFFFF !important; text-decoration: none; display: inline-flex; align-items: center; gap: 7px;
    padding: 3px 10px 3px 3px; border-radius: 999px; background: rgba(255,255,255,.10); border: 1px solid var(--linha);
    transition: background .15s;}
.hm-redes a:hover {background: rgba(255,255,255,.22);}
.hm-redes img, .hm-bola {width: 24px; height: 24px; border-radius: 50%; flex: none;}
.hm-bola {display: inline-flex; align-items: center; justify-content: center; background: #8FE3FF; color: #1E4C86;}
.hm-bola .hm-ic {width: 14px; height: 14px; color: #1E4C86 !important;}
.hm-redes b {grid-column: 1 / -1; justify-self: end; color: #8FE3FF; letter-spacing: .14em; font: 700 .74rem 'Montserrat';}
.hm-ic {width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round;
    stroke-linejoin: round; flex: none;}
.hm-topo .hm-ic {color: #8FE3FF;}
.hm-capa {position: relative; overflow: hidden; text-align: center; padding: 38px 28px 22px; border-radius: 26px;
    color: #FFFFFF; border: 1px solid var(--linha); margin-bottom: 26px; box-shadow: 0 16px 36px rgba(33,86,160,.28);
    background: linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px) 0 0 / 34px 34px,
                linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px) 0 0 / 34px 34px,
                radial-gradient(circle at 12% 0%, rgba(143,227,255,.30), transparent 45%),
                radial-gradient(circle at 95% 100%, rgba(150,120,235,.35), transparent 50%),
                linear-gradient(125deg, var(--az1), var(--az2) 55%, var(--az3));}
.hm-selo {display: inline-block; font: 700 .72rem 'Montserrat'; letter-spacing: .26em; color: #BDEFFF; padding: 8px 18px;
    border-radius: 999px; border: 1px solid rgba(189,239,255,.45); background: rgba(255,255,255,.08);}
.hm-capa h1 {font: 800 3.4rem/1.08 'Montserrat' !important; color: #FFFFFF !important; margin: 22px 0 14px !important;
    padding: 0 !important; letter-spacing: -.02em;}
.hm-capa p {font: 500 1.04rem/1.65 'Montserrat'; color: var(--suave); max-width: 700px; margin: 0 auto;}
.hm-contagem {display: inline-flex; align-items: center; gap: 10px; margin-top: 22px; padding: 11px 22px;
    border-radius: 999px; font: 600 .93rem 'Montserrat'; background: rgba(255,255,255,.12); border: 1px solid var(--linha);}
.hm-contagem i {width: 10px; height: 10px; border-radius: 50%; background: #3BE07F; animation: hmpulso 1.8s infinite;}
@keyframes hmpulso {0% {box-shadow: 0 0 0 0 rgba(59,224,127,.7);} 70% {box-shadow: 0 0 0 10px rgba(59,224,127,0);}
    100% {box-shadow: 0 0 0 0 rgba(59,224,127,0);}}
.hm-recursos {display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 30px; padding-top: 20px;
    border-top: 1px solid var(--linha);}
.hm-recursos div {display: flex; align-items: center; justify-content: center; gap: 9px; font: 600 .88rem 'Montserrat';
    color: #EAF4FF;}
.hm-recursos .hm-ic {width: 18px; height: 18px; color: #8FE3FF;}
/* cards */
[data-testid="stHorizontalBlock"]:has(.st-key-hc_br) {align-items: stretch;}
[data-testid="stColumn"]:has([class*="st-key-hc_"]) > div {height: 100%;}
[class*="st-key-hc_"] {position: relative; height: 100%; justify-content: space-between; text-align: center;
    padding: 22px 24px 18px; border-radius: 24px; color: #FFFFFF; border: 1px solid var(--linha);
    background: radial-gradient(circle at 50% 0%, rgba(255,255,255,.14), transparent 55%),
                linear-gradient(180deg, var(--az2), var(--az1));
    box-shadow: 0 14px 30px rgba(33,86,160,.25); transition: transform .18s, box-shadow .18s;}
[class*="st-key-hc_"]:hover {transform: translateY(-4px); box-shadow: 0 20px 38px rgba(33,86,160,.33);}
.st-key-hc_br {border-top: 4px solid #2BD27A !important;} .st-key-hc_ma {border-top: 4px solid #FF5A6E !important;}
.st-key-hc_ap {border-top: 4px solid #2BD27A !important;}
.hc-num {position: absolute; top: 10px; right: 18px; font: 800 2.7rem 'Montserrat'; color: rgba(255,255,255,.13);}
.hc-emblema {height: 128px; display: flex; align-items: center; justify-content: center;}
.hc-emblema .hc-bandeira {width: 150px; height: 104px; transform: rotate(-3deg); filter: drop-shadow(0 12px 16px rgba(10,30,70,.38));}
.hc-emblema .hc-icone {font-size: 5.4rem; line-height: 1; filter: drop-shadow(0 12px 14px rgba(10,30,70,.35));}
.hc-selo {font: 700 .72rem 'Montserrat'; letter-spacing: .24em; color: #8FE3FF; margin-top: 10px; display: flex;
    justify-content: center; align-items: center; gap: 8px;}
.hc-selo em {font-style: normal; font-size: .62rem; letter-spacing: .1em; color: #0B3B24; background: #3BE07F;
    border-radius: 999px; padding: 2px 9px;}
.hc-titulo {font: 800 1.7rem/1.1 'Montserrat'; letter-spacing: -.01em; margin: 6px 0 6px;}
.hc-texto {font: 500 .92rem 'Montserrat'; color: var(--suave); min-height: 2.6em;}
.hc-linhas {text-align: left; margin-top: 14px;}
.hc-linha {display: flex; justify-content: space-between; align-items: baseline; font: 600 .98rem 'Montserrat';}
.hc-linha span {display: inline-flex; align-items: center; gap: 8px;}
.hc-linha span i {width: 8px; height: 8px; border-radius: 50%;}
.hc-linha b {font: 800 1.2rem 'Montserrat';}
.hc-barra {height: 7px; border-radius: 7px; background: rgba(255,255,255,.18); margin: 6px 0 12px; overflow: hidden;}
.hc-barra i {display: block; height: 100%; border-radius: 7px;}
.hc-chips {display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 16px; min-height: 5.4rem;
    align-content: center;}
.hc-chips span {display: inline-flex; align-items: center; gap: 6px; font: 600 .84rem 'Montserrat'; color: #FFFFFF;
    background: rgba(255,255,255,.12); border: 1px solid var(--linha); border-radius: 999px; padding: 7px 14px;}
.hc-chips .hm-ic {width: 14px; height: 14px; color: #8FE3FF;}
.hc-legenda {font: 500 .78rem 'Montserrat'; color: var(--suave); margin: 4px 0 6px; letter-spacing: .04em;}
[class*="st-key-hc_"] [data-testid="stPageLink"] a {background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.35);
    border-radius: 14px; justify-content: center; padding: .6rem 1rem; transition: background .15s;}
[class*="st-key-hc_"] [data-testid="stPageLink"] a:hover {background: rgba(255,255,255,.24);}
[class*="st-key-hc_"] [data-testid="stPageLink"] a p {color: #FFFFFF !important; font: 700 .92rem 'Montserrat' !important;}
.st-key-hc_ap [data-testid="stPageLink"] a {background: linear-gradient(100deg, #1FA463, #2BD27A); border-color: transparent;}
/* compartilhar e créditos */
.st-key-hs_compartilhar {max-width: 560px; margin: 28px auto 8px; padding: 18px 18px 6px; border-radius: 24px;
    border: 1px solid var(--linha); background: linear-gradient(160deg, var(--az2), var(--az1));
    box-shadow: 0 14px 30px rgba(33,86,160,.22);}
.st-key-hs_compartilhar .cp-titulo {font: 700 1.15rem 'Montserrat'; color: #FFFFFF; text-align: center; margin-bottom: 10px;}
.hm-creditos {display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 24px; margin: 26px 0 6px;
    padding: 22px 26px; border-radius: 24px; color: #FFFFFF; border: 1px solid var(--linha);
    background: radial-gradient(circle at 0% 0%, rgba(143,227,255,.25), transparent 40%), linear-gradient(110deg, var(--az1), var(--az2));
    box-shadow: 0 14px 30px rgba(33,86,160,.22);}
.hm-creditos img {height: 80px; display: block;}
.hm-creditos .cr-selo {font: 700 .68rem 'Montserrat'; letter-spacing: .2em; color: #8FE3FF;}
.hm-creditos .cr-nome {font: 800 1.45rem 'Montserrat';}
.hm-creditos .cr-slogan {font: 600 .98rem 'Montserrat';}
.hm-creditos .cr-texto {font: 500 .84rem/1.55 'Montserrat'; color: var(--suave); margin-top: 6px;}
.hm-creditos .cr-texto b {color: #8FE3FF;}
.hm-nota {text-align: center; color: #3E5675; font: 500 .8rem 'Montserrat'; margin-top: 8px;}
@media (max-width: 900px) {
  .hm-topo {grid-template-columns: 1fr; text-align: center; gap: 8px; padding: 14px;}
  .hm-topo > img {margin: 0 auto; height: 52px;} .hm-contato {align-items: center;}
  .hm-redes {grid-template-columns: 1fr; justify-items: center;} .hm-redes b {justify-self: center;}
  .hm-capa {padding: 28px 16px 18px;} .hm-selo {font-size: .64rem; letter-spacing: .14em; padding: 7px 12px;} .hm-capa h1 {font-size: 2.05rem !important;}
  .hm-recursos {grid-template-columns: 1fr; gap: 12px;}
  .hm-creditos {grid-template-columns: 1fr; text-align: center; gap: 12px;}
  .hm-creditos img {margin: 0 auto; height: 58px;} .hm-creditos .hm-contato {align-items: center;}}
</style>""", unsafe_allow_html=True)

# ícones de traço (estilo Lucide), desenhados aqui
_IC = {"mail": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
       "fone": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
       "grafico": '<path d="M3 3v18h18"/><path d="M8 17v-6M13 17V7M18 17v-4"/>',
       "base": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/>',
       "prancheta": '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/>',
       "radio": '<circle cx="12" cy="12" r="2"/><path d="M16.2 7.8a6 6 0 0 1 0 8.5M7.8 16.2a6 6 0 0 1 0-8.5M19.1 4.9a10 10 0 0 1 0 14.2M4.9 19.1a10 10 0 0 1 0-14.2"/>',
       "globo": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>'}


def ic(nome):
    return f'<svg class="hm-ic" viewBox="0 0 24 24">{_IC[nome]}</svg>'


# bandeiras estilizadas (SVG desenhado aqui: cantos arredondados, brilho suave e sombra)
_BRILHO = """<defs><linearGradient id="{id}" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#fff" stop-opacity=".38"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/>
<stop offset="1" stop-color="#000" stop-opacity=".18"/></linearGradient>
<clipPath id="{id}c"><rect width="150" height="104" rx="16"/></clipPath></defs>"""

BANDEIRA_BR = f"""<svg viewBox="0 0 150 104" class="hc-bandeira" role="img" aria-label="Bandeira do Brasil">
{_BRILHO.format(id="gbr")}<g clip-path="url(#gbrc)">
<rect width="150" height="104" fill="#009B3A"/>
<polygon points="75,11 139,52 75,93 11,52" fill="#FEDF00"/>
<circle cx="75" cy="52" r="25" fill="#002776"/>
<path d="M51 46 Q75 38 99 55 L98 61 Q75 45 52 52 Z" fill="#FFFFFF"/>
<g fill="#fff"><circle cx="66" cy="62" r="1.6"/><circle cx="74" cy="66" r="1.8"/><circle cx="83" cy="63" r="1.5"/>
<circle cx="79" cy="70" r="1.3"/><circle cx="69" cy="70" r="1.2"/><circle cx="62" cy="57" r="1.1"/>
<circle cx="88" cy="68" r="1.1"/><circle cx="72" cy="40" r="1.4"/></g>
<rect width="150" height="104" fill="url(#gbr)"/></g></svg>"""

_listras = "".join(
    f'<rect y="{i * 104 / 9:.2f}" width="150" height="{104 / 9 + .3:.2f}" fill="{c}"/>'
    for i, c in enumerate(["#D21034", "#FFFFFF", "#111111", "#FFFFFF", "#D21034",
                           "#FFFFFF", "#111111", "#FFFFFF", "#D21034"]))
BANDEIRA_MA = f"""<svg viewBox="0 0 150 104" class="hc-bandeira" role="img" aria-label="Bandeira do Maranhão">
{_BRILHO.format(id="gma")}<g clip-path="url(#gmac)">{_listras}
<rect width="50" height="52" fill="#0B3F8C"/>
<polygon fill="#fff" points="25,13 28.5,22.5 38.5,22.8 30.6,29 33.4,38.6 25,33 16.6,38.6 19.4,29 11.5,22.8 21.5,22.5"/>
<rect width="150" height="104" fill="url(#gma)"/></g></svg>"""

ICONE_AP = '<div class="hc-icone" role="img" aria-label="Apuração ao vivo">📡</div>'

# ---------------------------------------------------------------- marca + capa
_logo = _logo_base64()
st.markdown(f"""
<div class="hm-topo">
  {f'<img src="data:image/webp;base64,{_logo}" alt="Aggilli Intelligence">' if _logo else '<b>AGGILLI</b>'}
  <div class="hm-slogan">Transformando dados em <span>inteligência</span></div>
  <div class="hm-redes">
    <a href="https://wa.me/5599991722200" target="_blank" title="WhatsApp"><img src="/app/static/icones/whatsapp.png" alt="">(99) 99172-2200</a>
    <a href="https://www.instagram.com/aggillisoftware/" target="_blank" title="Instagram"><img src="/app/static/icones/instagram.png" alt="">@aggillisoftware</a>
    <a href="https://www.aggillintelligence.com.br" target="_blank" title="Site"><span class="hm-bola">{ic("globo")}</span>aggillintelligence.com.br</a>
    <a href="mailto:adi@aggillintelligence.com.br" title="E-mail"><span class="hm-bola">{ic("mail")}</span>adi@aggillintelligence.com.br</a>
    <b>G. C. LÉDA</b>
  </div>
</div>""", unsafe_allow_html=True)

agora = datetime.now(BRT)
if agora < INICIO_APURACAO:
    dias = (INICIO_APURACAO.date() - agora.date()).days
    contagem = {0: "É hoje! Apuração a partir das 17h", 1: "Amanhã! Apuração domingo a partir das 17h"}.get(
        dias, f"Faltam {dias} dias · apuração domingo, a partir das 17h")
    selo_ap, chip_ap = "DOMINGO · 4/10 · 17H", "em breve"
else:
    contagem, selo_ap, chip_ap = "Apuração ao vivo agora · atualização a cada 90 segundos", "AO VIVO", "ao vivo"

st.markdown(f"""
<div class="hm-capa">
  <div class="hm-selo">ELEIÇÕES 2026 · 1º TURNO · 4 DE OUTUBRO</div>
  <h1>Modelo Preditivo <span>&amp;</span><br>Apuração em Tempo Real</h1>
  <p>Modelo independente com pesquisas registradas, histórico oficial do TSE e 20 mil cenários simulados — e, no
  domingo, os votos do TSE em tempo real.</p>
  <div class="hm-contagem"><i></i>{contagem}</div>
  <div class="hm-recursos">
    <div>{ic("grafico")}20 mil cenários simulados</div>
    <div>{ic("base")}Histórico oficial do TSE</div>
    <div>{ic("prancheta")}Pesquisas registradas</div>
  </div>
</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- três cenários simétricos
cards = [
    ("hc_br", "01", BANDEIRA_BR, "CENÁRIO", "BRASIL", "Presidente · Lula × Flávio Bolsonaro",
     [("Lula", br.get("prob_lula_presidente"), "#FF6B7D"), ("Flávio", br.get("prob_flavio_presidente"), "#9FD0FF")],
     "chance de ser eleito", "nacional/painel_nacional.py", "Abrir cenário Brasil →"),
    ("hc_ma", "02", BANDEIRA_MA, "CENÁRIO", "MARANHÃO", "Governador · Braide × Orleans",
     [("Braide", ma.get("prob_braide_governador"), "#9FD0FF"), ("Orleans", ma.get("prob_orleans_governador"), "#FFB15C")],
     "chance de ser eleito", "painel_governo_ma.py", "Abrir cenário Maranhão →"),
    ("hc_ap", "03", ICONE_AP, selo_ap, "APURAÇÃO AO VIVO", "Resultado do TSE × projeção, a cada 90 segundos",
     ["Presidente", "Governador", "Senado", "Deputados"],
     "Brasil · Maranhão · Tuntum", "apuracao/painel_apuracao.py", "Acompanhar a apuração →"),
]
col = st.columns(3, gap="medium")
for c, (chave, num, emblema, selo, titulo, texto, itens, legenda, pagina, botao) in zip(col, cards):
    with c, st.container(key=chave):
        if chave == "hc_ap":
            corpo = "<div class='hc-chips'>" + "".join(f"<span>{ic('radio')}{t}</span>" for t in itens) + "</div>"
        else:
            corpo = "<div class='hc-linhas'>" + "".join(
                f"<div class='hc-linha'><span><i style='background:{cor}'></i>{nome}</span>"
                f"<b style='color:{cor}'>{pct(v) if v is not None else '—'}</b></div>"
                f"<div class='hc-barra'><i style='width:{(v or 0) * 100:.0f}%;background:{cor}'></i></div>"
                for nome, v, cor in itens) + "</div>"
        st.markdown(f"""
<div class="hc-num">{num}</div>
<div class="hc-emblema">{emblema}</div>
<div class="hc-selo">{selo}{f"<em>{chip_ap}</em>" if chave == "hc_ap" else ""}</div>
<div class="hc-titulo">{titulo}</div>
<div class="hc-texto">{texto}</div>
{corpo}
<div class="hc-legenda">{legenda}</div>
""", unsafe_allow_html=True)
        try:
            st.page_link(pagina, label=botao, width="stretch")
        except Exception:  # página aberta sozinha (fora do app.py): sem navegação registrada
            pass

# ---------------------------------------------------------------- compartilhar
if agora < INICIO_APURACAO:
    quando = ("A apuração AO VIVO começa no *domingo, 4 de outubro, a partir das 17h* (horário de Brasília). "
              "Salve o link!")
else:
    quando = "A apuração está AO VIVO, com atualização a cada 90 segundos."
texto = ("🗳️ Eleições 2026 com a Aggilli Intelligence: modelo preditivo para Presidente (Lula × Flávio) e Governo do "
         "Maranhão (Braide × Orleans) e apuração em tempo real.\n\n💗 Vem torcer com a gente pela Bruna e pelo Time do Fernando! "
         + quando + "\n\n👉 Acompanhe aqui:\n" + LINK)
ARTE = "inicio_aggilli.jpg"  # miniatura da Aggilli (gerada por apuracao/arte_inicio.py)
wa = f"https://wa.me/?text={quote(texto)}"
with st.container(key="hs_compartilhar"):
    logo = _logo_base64()
    st.markdown(f"""
<div class="compartilhe">
  <div class="cp-titulo">Compartilhe com seus amigos</div>
</div>""", unsafe_allow_html=True)
    # miniatura + ícones num componente: o Instagram abre o menu de compartilhar do celular com a miniatura e o link;
    # no computador, baixa a miniatura e abre o Instagram
    components.html(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;700&display=swap');
  body {{margin: 0; font-family: Montserrat, Arial, sans-serif;}}
  .mini {{display: block; width: 100%; max-width: 440px; margin: 0 auto 12px; border-radius: 16px;
         box-shadow: 0 12px 26px rgba(10,30,70,.35); border: 1px solid rgba(255,255,255,.25);}}
  .ic {{display: flex; justify-content: center; gap: 30px; padding: 4px 0;}}
  .ic a, .ic button {{background: none; border: 0; padding: 0; cursor: pointer; text-align: center; text-decoration: none;}}
  .ic img {{width: 64px; height: 64px; transition: transform .15s; filter: drop-shadow(0 6px 12px rgba(27,42,65,.18));}}
  .ic a:hover img, .ic button:hover img {{transform: translateY(-3px) scale(1.06);}}
  .ic span {{display: block; font: 700 12px Montserrat, Arial; color: #FFFFFF; margin-top: 4px;}}
  #msg {{text-align: center; font-size: 12px; color: #EAF4FF; min-height: 16px; margin-top: 4px;}}
</style>
<a href="{wa}" target="_blank" rel="noopener"><img class="mini" src="/app/static/compartilhar/{ARTE}"
   alt="Eleições 2026 · Modelo Preditivo & Apuração em Tempo Real · Aggilli Intelligence"></a>
<div class="ic">
  <a href="{wa}" target="_blank" rel="noopener" title="Compartilhar no WhatsApp">
    <img src="/app/static/icones/whatsapp.png" alt="WhatsApp"><span>WhatsApp</span></a>
  <button id="insta" title="Compartilhar no Instagram">
    <img src="/app/static/icones/instagram.png" alt="Instagram"><span>Instagram</span></button>
</div>
<div id="msg"></div>
<script>
const URL_LINK = {json.dumps(LINK)};
const TEXTO = {json.dumps(texto)};
const ARTE = "/app/static/compartilhar/{ARTE}";
const msg = t => document.getElementById("msg").textContent = t;
async function copiar(t) {{
  try {{ await (window.parent.navigator.clipboard || navigator.clipboard).writeText(t); return true; }} catch (e) {{ return false; }}
}}
document.getElementById("insta").addEventListener("click", async () => {{
  const nav = (window.parent && window.parent.navigator && window.parent.navigator.share) ? window.parent.navigator : navigator;
  const copiado = await copiar(URL_LINK);
  try {{
    const blob = await (await fetch(ARTE)).blob();
    const arquivo = new File([blob], "{ARTE}", {{type: "image/jpeg"}});
    if (nav.canShare && nav.canShare({{files: [arquivo]}})) {{
      await nav.share({{files: [arquivo], text: TEXTO}});
      msg(copiado ? "Link copiado: no Stories, cole no adesivo Link." : "");
      return;
    }}
  }} catch (e) {{ if (e && e.name === "AbortError") return; }}
  const a = document.createElement("a"); a.href = ARTE; a.download = "{ARTE}"; document.body.appendChild(a); a.click(); a.remove();
  const celular = /Android|iPhone|iPad/i.test(navigator.userAgent);
  window.open(celular ? "instagram://story-camera" : "https://www.instagram.com/", "_blank");
  msg("Miniatura baixada" + (copiado ? " e link copiado" : "") + ": publique e cole o link.");
}});
</script>""", height=360)

# ---------------------------------------------------------------- créditos
st.markdown(f"""
<div class="hm-creditos">
  {f'<img src="data:image/webp;base64,{logo}" alt="Aggilli Intelligence">' if logo else '<b>AGGILLI</b>'}
  <div>
    <div class="cr-selo">INTELIGÊNCIA ELEITORAL POR</div>
    <div class="cr-nome">Aggilli Intelligence</div>
    <div class="cr-slogan">Transformando dados em <span>inteligência</span></div>
    <div class="cr-texto">Modelagem estatística, pesquisas, dados oficiais do TSE e painéis em tempo real.
    Desenvolvimento: <b>G. C. Léda</b>.</div>
  </div>
  <div class="hm-contato">
    <a href="mailto:adi@aggillintelligence.com.br">{ic("mail")}adi@aggillintelligence.com.br</a>
    <a href="https://wa.me/5599991722200" target="_blank">{ic("fone")}(99) 99172-2200</a>
    <a href="https://www.aggillintelligence.com.br" target="_blank">{ic("globo")}aggillintelligence.com.br</a>
  </div>
</div>
<div class="hm-nota">As probabilidades mudam a cada nova pesquisa · resultados oficiais: TSE</div>
""", unsafe_allow_html=True)
