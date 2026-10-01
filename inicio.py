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
from comum import _logo_base64, cabecalho_marca, pct  # noqa: E402

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

# bandeiras estilizadas (SVG desenhado aqui: cantos arredondados, brilho suave e sombra)
_BRILHO = """<defs><linearGradient id="{id}" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#fff" stop-opacity=".38"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/>
<stop offset="1" stop-color="#000" stop-opacity=".18"/></linearGradient>
<clipPath id="{id}c"><rect width="150" height="104" rx="16"/></clipPath></defs>"""

BANDEIRA_BR = f"""<svg viewBox="0 0 150 104" class="bandeira" role="img" aria-label="Bandeira do Brasil">
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
BANDEIRA_MA = f"""<svg viewBox="0 0 150 104" class="bandeira" role="img" aria-label="Bandeira do Maranhão">
{_BRILHO.format(id="gma")}<g clip-path="url(#gmac)">{_listras}
<rect width="50" height="52" fill="#0B3F8C"/>
<polygon fill="#fff" points="25,13 28.5,22.5 38.5,22.8 30.6,29 33.4,38.6 25,33 16.6,38.6 19.4,29 11.5,22.8 21.5,22.5"/>
<rect width="150" height="104" fill="url(#gma)"/></g></svg>"""

ICONE_AP = '<div class="emblema-icone" role="img" aria-label="Apuração ao vivo">📡</div>'

# ---------------------------------------------------------------- marca + capa
cabecalho_marca()

agora = datetime.now(BRT)
if agora < INICIO_APURACAO:
    dias = (INICIO_APURACAO.date() - agora.date()).days
    contagem = {0: "É hoje! Apuração a partir das 17h", 1: "Amanhã! Apuração domingo a partir das 17h"}.get(
        dias, f"Faltam {dias} dias · apuração domingo, a partir das 17h")
    selo_ap, chip_ap = "DOMINGO · 4/10 · 17H", "em breve"
else:
    contagem, selo_ap, chip_ap = "Apuração ao vivo agora · atualização a cada 90 segundos", "AO VIVO", "ao vivo"

st.markdown(f"""
<div class="capa-inicio">
  <div class="ci-selo">ELEIÇÕES 2026 · 4 DE OUTUBRO</div>
  <div class="ci-titulo">Previsão <span>&amp;</span> Apuração</div>
  <div class="ci-texto">Modelo independente com pesquisas registradas, histórico oficial do TSE e 20 mil cenários
  simulados — e, no domingo, os votos do TSE em tempo real.</div>
  <div class="ci-contagem"><i></i>{contagem}</div>
</div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------- três cenários simétricos
cards = [
    ("card_br", BANDEIRA_BR, "CENÁRIO", "BRASIL", "Presidente · Lula × Flávio Bolsonaro",
     [("Lula", br.get("prob_lula_presidente"), "#C8102E"), ("Flávio", br.get("prob_flavio_presidente"), "#1D4E89")],
     "chance de ser eleito", "nacional/painel_nacional.py", "Abrir cenário Brasil →"),
    ("card_ma", BANDEIRA_MA, "CENÁRIO", "MARANHÃO", "Governador · Braide × Orleans",
     [("Braide", ma.get("prob_braide_governador"), "#1F6FB2"), ("Orleans", ma.get("prob_orleans_governador"), "#E07B1F")],
     "chance de ser eleito", "painel_governo_ma.py", "Abrir cenário Maranhão →"),
    ("card_ap", ICONE_AP, selo_ap, "APURAÇÃO AO VIVO", "Resultado do TSE × projeção, a cada 90 segundos",
     [("Presidente", None, "#1B2A41"), ("Governador", None, "#1B2A41"), ("Deputados", None, "#1B2A41")],
     "Brasil · Maranhão · Tuntum", "apuracao/painel_apuracao.py", "Acompanhar a apuração →"),
]
col = st.columns(3, gap="medium")
for c, (chave, emblema, selo, titulo, texto, numeros, legenda, pagina, botao) in zip(col, cards):
    with c, st.container(key=chave):
        if chave == "card_ap":
            corpo = "".join(f"<span class='card-chip'>{n}</span>" for n, _, _ in numeros)
            corpo = f"<div class='card-chips'>{corpo}</div>"
        else:
            corpo = "".join(
                f"<div class='card-prob'><b style='color:{cor}'>{pct(v) if v is not None else '—'}</b>"
                f"<span>{nome}</span><i style='background:{cor};width:{(v or 0) * 100:.0f}%'></i></div>"
                for nome, v, cor in numeros)
            corpo = f"<div class='card-probs'>{corpo}</div>"
        st.markdown(f"""
<div class="card-emblema">{emblema}</div>
<div class="card-selo">{selo}{f"<em>{chip_ap}</em>" if chave == "card_ap" else ""}</div>
<div class="card-titulo">{titulo}</div>
<div class="card-texto">{texto}</div>
{corpo}
<div class="card-legenda">{legenda}</div>
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
texto = ("🗳️ Eleições 2026 com a Aggilli Intelligence: previsão para Presidente (Lula × Flávio) e Governo do "
         "Maranhão (Braide × Orleans).\n\n💗 Vem torcer com a gente pela Bruna e pelo Time do Fernando! "
         + quando + "\n\n👉 Acompanhe aqui:\n" + LINK)
ARTE = "inicio_aggilli.jpg"  # miniatura da Aggilli (gerada por apuracao/arte_inicio.py)
wa = f"https://wa.me/?text={quote(texto)}"
with st.container(key="compartilhar_inicio"):
    logo = _logo_base64()
    st.markdown(f"""
<div class="compartilhe">
  {f'<img class="cp-logo" src="data:image/webp;base64,{logo}" alt="Aggilli Intelligence">' if logo else ''}
  <div class="cp-titulo">Compartilhe com seus amigos</div>
</div>""", unsafe_allow_html=True)
    # miniatura + ícones num componente: o Instagram abre o menu de compartilhar do celular com a miniatura e o link;
    # no computador, baixa a miniatura e abre o Instagram
    components.html(f"""
<style>
  body {{margin: 0; font-family: Manrope, Arial, sans-serif;}}
  .mini {{display: block; width: 100%; max-width: 440px; margin: 0 auto 12px; border-radius: 16px;
         box-shadow: 0 10px 24px rgba(11,22,40,.25); border: 1px solid rgba(27,42,65,.12);}}
  .ic {{display: flex; justify-content: center; gap: 30px; padding: 4px 0;}}
  .ic a, .ic button {{background: none; border: 0; padding: 0; cursor: pointer; text-align: center; text-decoration: none;}}
  .ic img {{width: 64px; height: 64px; transition: transform .15s; filter: drop-shadow(0 6px 12px rgba(27,42,65,.18));}}
  .ic a:hover img, .ic button:hover img {{transform: translateY(-3px) scale(1.06);}}
  .ic span {{display: block; font: 800 12px Manrope, Arial; color: #3A4458; margin-top: 4px;}}
  #msg {{text-align: center; font-size: 12px; color: #3A4458; min-height: 16px; margin-top: 4px;}}
</style>
<a href="{wa}" target="_blank" rel="noopener"><img class="mini" src="/app/static/compartilhar/{ARTE}"
   alt="Eleições 2026 · Previsão & Apuração · Aggilli Intelligence"></a>
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
<div class="creditos-inicio">
  <div class="cr-logo">{f'<img src="data:image/webp;base64,{logo}" alt="Aggilli Intelligence">' if logo else '<b>AGGILLI</b>'}</div>
  <div class="cr-meio">
    <div class="cr-selo">INTELIGÊNCIA ELEITORAL POR</div>
    <div class="cr-nome">Aggilli Intelligence</div>
    <div class="cr-slogan">Transformando dados em <span>inteligência</span></div>
    <div class="cr-texto">Modelagem estatística, pesquisas, dados oficiais do TSE e painéis em tempo real.
    Desenvolvimento: <b>G. C. Léda</b>.</div>
  </div>
  <div class="cr-contato">
    <a href="mailto:adi@aggillintelligence.com.br">✉️ adi@aggillintelligence.com.br</a>
    <a href="https://wa.me/5599991722200" target="_blank">💬 (99) 99172-2200</a>
    <a href="https://www.aggillintelligence.com.br" target="_blank">🌐 aggillintelligence.com.br</a>
  </div>
</div>
<div class="nota-inicio">As probabilidades mudam a cada nova pesquisa · resultados oficiais: TSE</div>
""", unsafe_allow_html=True)
