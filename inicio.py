"""Página inicial: escolha do cenário por cards (funciona bem no celular)."""
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

import streamlit as st

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
from comum import pct  # noqa: E402


def ler(arq):
    try:
        return json.load(open(RAIZ / arq, encoding="utf-8"))["resultado_final"]
    except Exception:
        return {}


br = ler("nacional/resultados/simulacao_nacional.json")
ma = ler("resultados/simulacao.json")

st.markdown("""
<div style="text-align:center; margin: 1.2rem 0 1.6rem;">
  <div style="font: 800 .8rem 'Manrope'; letter-spacing: .16em; color:#5B6477;">ELEIÇÕES 2026 · 4 DE OUTUBRO</div>
  <div style="font: 900 2.4rem/1.1 'Montserrat'; color:#1B2A41; margin:.4rem 0;">Previsão eleitoral</div>
  <div style="font: 600 1rem 'Manrope'; color:#3A4458;">Modelo independente · pesquisas, histórico oficial do TSE e
  simulação de 20 mil cenários. Escolha um cenário.</div>
</div>
""", unsafe_allow_html=True)

col = st.columns(3, gap="medium")
cards = [
    ("card_br", "🌎", "CENÁRIO", "BRASIL", "Presidente · Lula × Flávio Bolsonaro",
     [("Lula", br.get("prob_lula_presidente"), "#C8102E"), ("Flávio", br.get("prob_flavio_presidente"), "#1D4E89")],
     "nacional/painel_nacional.py", "Abrir cenário Brasil →"),
    ("card_ma", "🏛️", "CENÁRIO", "MARANHÃO", "Governador · Braide × Orleans",
     [("Braide", ma.get("prob_braide_governador"), "#1F6FB2"), ("Orleans", ma.get("prob_orleans_governador"), "#E07B1F")],
     "painel_governo_ma.py", "Abrir cenário Maranhão →"),
    ("card_ap", "📡", "DOMINGO", "APURAÇÃO AO VIVO", "Resultado do TSE × projeção, a cada 90 segundos", [],
     "apuracao/painel_apuracao.py", "Acompanhar a apuração →"),
]
for c, (chave, icone, selo, titulo, texto, numeros, pagina, botao) in zip(col, cards):
    with c, st.container(key=chave):
        linhas = "".join(
            f"<div class='card-numero' style='color:{cor}'>{nome} {pct(v)}</div>" for nome, v, cor in numeros if v is not None)
        if numeros:
            linhas += "<div class='card-texto' style='opacity:.7'>chance de ser eleito</div>"
        st.markdown(f"""
<div class="card-icone">{icone}</div>
<div class="card-selo">{selo}</div>
<div class="card-titulo">{titulo}</div>
<div class="card-texto">{texto}</div>
{linhas}
""", unsafe_allow_html=True)
        try:
            st.page_link(pagina, label=botao, width="stretch")
        except Exception:  # página aberta sozinha (fora do app.py): sem navegação registrada
            pass

# compartilhar no WhatsApp (o link mostra a miniatura com título e créditos)
# link público (redireciona para o Render); LINK_PUBLICO="" usa o endereço do próprio servidor
url = os.environ.get("LINK_PUBLICO", "https://aggillintelligence.com.br/eleicoes_2026")
if not url:
    url = os.environ.get("RENDER_EXTERNAL_URL") or getattr(st.context, "url", "") or ""
    if url:
        u = urlparse(url)
        url = f"{u.scheme}://{u.netloc}"
if url:
    texto = ("📊 Previsão eleitoral 2026 — Brasil (Lula × Flávio) e Maranhão (Braide × Orleans), "
             f"com apuração ao vivo no domingo: {url}")
    c = st.columns([1, 2, 1])
    with c[1], st.container(key="compartilhar"):
        st.link_button("📲 Compartilhar no WhatsApp", f"https://wa.me/?text={quote(texto)}", width="stretch",
                       type="primary")

st.markdown("<div style='text-align:center; margin-top:1.4rem; color:#5B6477; font: 600 .85rem Manrope;'>"
            "Painel de uso interno · as probabilidades mudam a cada nova pesquisa</div>", unsafe_allow_html=True)
