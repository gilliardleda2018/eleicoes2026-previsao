"""Página — Apuração ao vivo (domingo): apuração parcial do TSE × projeção do modelo, e para onde aponta o final."""
import json
import os
import sys
from urllib.parse import quote
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "apuracao"))
import momento  # noqa: E402
import motor  # noqa: E402
from comum import CSS, _logo_base64, barra_navegacao, cabecalho_marca, grafico, n, pct, tabela  # noqa: E402

if __name__ == "__main__":
    st.set_page_config(page_title="Apuração ao vivo", page_icon="🗳️", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

st.markdown("""
<style>
.dep-card{--accent:#3B6FB6;background:linear-gradient(145deg,#fffdf5 0%,#f1efe4 48%,#e6e4da 100%);border:1px solid #d8d5c6;border-radius:22px;padding:24px;
box-shadow:8px 12px 24px rgba(74,69,49,.16),-4px -4px 14px rgba(255,255,255,.85),inset 1px 1px 0 rgba(255,255,255,.95),inset -1px -1px 0 rgba(154,147,120,.2);position:relative;overflow:hidden;min-height:390px}
.dep-card:before{content:"";position:absolute;top:0;left:24px;right:24px;height:3px;background:var(--accent);border-radius:0 0 6px 6px}
.dep-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:26px}
.dep-name{font-size:1.15rem;font-weight:750;color:#1B2A41;line-height:1.3}
.dep-badge{font-size:.74rem;font-weight:650;color:var(--accent);background:color-mix(in srgb,var(--accent) 9%,white);
padding:5px 9px;border-radius:8px;white-space:nowrap}
.dep-label{font-size:.68rem;font-weight:650;letter-spacing:.09em;text-transform:uppercase;color:#64748b}
.dep-votes{font-size:2.7rem;font-weight:800;letter-spacing:-.06em;line-height:1.15;color:#17263d;margin:6px 0}
.dep-votes small{font-size:.85rem;font-weight:500;letter-spacing:0;color:#64748b;margin-left:8px}
.dep-status{font-size:.77rem;line-height:1.6;color:#64748b;margin:8px 0 20px}
.dep-projection{border-top:1px solid #d9d6c7;padding-top:18px}
.dep-projection strong{display:block;font-size:1.65rem;letter-spacing:-.04em;color:#17263d;margin:4px 0}
.dep-range{font-size:.8rem;color:#64748b;line-height:1.65}
.dep-reference{font-size:.72rem;color:#64748b;margin-top:10px;line-height:1.6}
.dep-chances{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:20px}
.dep-chance{background:linear-gradient(145deg,#fffdf5,#ebe8dc);border:1px solid #dcd8c9;border-radius:12px;padding:12px;box-shadow:3px 4px 9px rgba(74,69,49,.1),inset 1px 1px 0 #fffef9}
.dep-chance span{display:block;font-size:.7rem;color:#64748b;line-height:1.5}
.dep-chance b{display:block;font-size:1.2rem;color:#17263d;margin-top:3px}
.tuntum{background:linear-gradient(145deg,#fffdf5,#f1efe4 48%,#e6e4da)!important;border:1px solid #d8d5c6!important;
border-radius:22px!important;box-shadow:8px 12px 24px rgba(74,69,49,.16),-4px -4px 14px rgba(255,255,255,.85),inset 1px 1px 0 #fffef9!important;padding:24px!important}
.tuntum .tt-bruna{border-left-width:3px!important;padding-left:20px!important}
.tuntum .tt-num{font-size:clamp(3rem,7vw,5rem)!important;letter-spacing:-.06em}
.tuntum .tt-outro{background:linear-gradient(145deg,#fffdf5,#eae7dc)!important;border:1px solid #d8d5c6!important;box-shadow:4px 6px 12px rgba(74,69,49,.12),inset 1px 1px 0 #fffef9!important;
border-top:3px solid var(--cor)!important;border-radius:16px!important;padding:16px!important}
@media(max-width:640px){.dep-card{padding:20px;min-height:0}.dep-head{margin-bottom:20px}
.dep-name{font-size:1.05rem}.tuntum{padding:18px!important}.tuntum .tt-outros{gap:10px!important}}

.st-key-placar_stats [data-testid="stMetric"]{
background:linear-gradient(145deg,#fffdf5 0%,#f1efe4 48%,#e6e4da 100%)!important;
border:1px solid #d8d5c6;border-radius:20px;padding:20px;
box-shadow:8px 12px 24px rgba(74,69,49,.16),-4px -4px 14px rgba(255,255,255,.85),
inset 1px 1px 0 rgba(255,255,255,.95),inset -1px -1px 0 rgba(154,147,120,.2)}
.st-key-placar_stats [data-testid="stMetric"]:hover{
box-shadow:8px 14px 28px rgba(74,69,49,.19),-4px -4px 14px rgba(255,255,255,.85),inset 1px 1px 0 #fffef9}
.st-key-placar_stats [class*="st-key-caixa_"]{
background:linear-gradient(145deg,#fffdf5,#f1efe4 48%,#e6e4da)!important;border-color:#d8d5c6!important;
box-shadow:8px 12px 24px rgba(74,69,49,.16),inset 1px 1px 0 #fffef9!important}

.st-key-apuracao_deputados .cartao,
.st-key-apuracao_deputados [class*="st-key-caixa_"]{
background:linear-gradient(145deg,#fffdf5 0%,#f1efe4 48%,#e6e4da 100%)!important;
border:1px solid #d8d5c6!important;border-radius:22px;padding:22px;
box-shadow:8px 12px 24px rgba(74,69,49,.16),-4px -4px 14px rgba(255,255,255,.85),
inset 1px 1px 0 rgba(255,255,255,.95),inset -1px -1px 0 rgba(154,147,120,.2)!important}
.st-key-apuracao_deputados [data-testid="stDataFrame"]{
border-color:#d8d5c6!important;border-radius:14px}
@media(max-width:640px){.st-key-apuracao_deputados .cartao,
.st-key-apuracao_deputados [class*="st-key-caixa_"]{padding:16px}}
</style>
""", unsafe_allow_html=True)

# a Assembleia MA (Bruna Pessoa) vem primeiro e em destaque
DISPUTAS = {
    "Assembleia MA · Bruna, Abigail e Eric": dict(disputa="deputado", unidade="Município"),
    "Presidente · Lula × Flávio": dict(disputa="presidente", a="lula", b="flavio", nome_a="Lula", nome_b="Flávio",
                                      cor_a="#C8102E", cor_b="#1D4E89", unidade="Estado", chave="uf",
                                      previsao=RAIZ / "nacional" / "resultados" / "ufs_previsao.csv",
                                      geo=RAIZ / "nacional" / "dados" / "br_ufs.json", feat="properties.uf",
                                      loc="uf", zoom=2.8, centro={"lat": -14.5, "lon": -52}),
    "Governador MA · Braide × Orleans": dict(disputa="governador", a="braide", b="orleans", nome_a="Braide",
                                             nome_b="Orleans", cor_a="#1F6FB2", cor_b="#E07B1F", unidade="Município",
                                             chave="CD_MUNICIPIO", previsao=RAIZ / "resultados" / "municipios_previsao.csv",
                                             geo=RAIZ / "dados" / "ma_leve.geojson", feat="properties.CD_MUN",
                                             loc="cd_ibge", zoom=5.3, centro={"lat": -5.2, "lon": -45.2}),
    "Senado MA": dict(disputa="senador", unidade="Município"),
    "Câmara Federal MA": dict(disputa="federal", unidade="Município"),
}
# Deputados estaduais acompanhados (em votos): nome, cor e coluna da projeção
DEPUTADOS = {"bruna": ("Bruna Pessoa", "#E02597", "votos_projetados", "projeção do modelo"),
             "abigail": ("Abigail Cunha", "#E8702A", "abigail_2026", "referência: 2022 + 3% de eleitorado"),
             "eric": ("Eric Costa", "#3B6FB6", "eric_2026", "referência: 2022 + 3% de eleitorado")}

cabecalho_marca()
barra_navegacao("ap")
st.markdown("""
<div class="capa" style="background: linear-gradient(100deg, #0E5A73 0%, #12233F 55%, #3B2A6B 100%);">
  <div class="selo">DOMINGO, 4 DE OUTUBRO · APURAÇÃO OFICIAL DO TSE · ATUALIZA A CADA 90 SEGUNDOS</div>
  <div class="titulo">Apuração ao vivo</div>
  <div class="sub">Compara cada estado e município apurado com a projeção do modelo e estima para onde vai o resultado final.</div>
</div>
""", unsafe_allow_html=True)

# ---- seletor moderno (botões segmentados); clicar de novo no selecionado não deixa a página sem escolha
ROTULO_DISPUTA = {"Presidente · Lula × Flávio": "🇧🇷 Presidente", "Governador MA · Braide × Orleans": "🏛️ Governador MA",
                  "Assembleia MA · Bruna, Abigail e Eric": "💗 Assembleia MA", "Senado MA": "⭐ Senado MA",
                  "Câmara Federal MA": "🏢 Dep. Federal MA"}
UMA_RODADA = ("deputado", "senador", "federal")  # sem 2º turno
MODOS = ["Ao vivo (2026)", "Ensaio com a apuração de 2022"]


def _segmentado(rotulo, opcoes, chave, formato=str, padrao=None):
    padrao = opcoes[0] if padrao is None else padrao
    if st.session_state.get(chave) not in opcoes:  # desmarcado ou inválido: volta ao último válido
        st.session_state[chave] = st.session_state.get(f"_{chave}_ok", padrao)
    v = st.segmented_control(rotulo, opcoes, format_func=formato, key=chave, selection_mode="single")
    v = v if v in opcoes else st.session_state.get(f"_{chave}_ok", padrao)
    st.session_state[f"_{chave}_ok"] = v
    return v


with st.container(key="seletor_apuracao"):
    c = st.columns([3.6, 1, 1.4], gap="large")
    with c[0]:
        escolha = _segmentado("Disputa", list(DISPUTAS), "ap_disputa", lambda d: ROTULO_DISPUTA.get(d, d))
    cfg = DISPUTAS[escolha]
    deputados = cfg["disputa"] == "deputado"
    rodada_unica = cfg["disputa"] in UMA_RODADA
    with c[1]:
        if rodada_unica:  # deputados e senado: só 1º turno
            turno = 1
            st.segmented_control("Turno", ["1º turno"], default="1º turno", key="ap_turno_dep", disabled=True)
        else:
            turno = _segmentado("Turno", [1, 2], "ap_turno", lambda t: f"{t}º turno")
    with c[2]:
        modo = _segmentado("Modo", MODOS, "ap_modo", lambda m: "🔴 Ao vivo" if m.startswith("Ao vivo") else "🧪 Ensaio 2022")
ensaio = modo.startswith("Ensaio")


def link_apuracao():
    """Link divulgado: o endereço da Aggilli (LINK_APURACAO no Render pode trocar)."""
    return os.environ.get("LINK_APURACAO", "https://aggillintelligence.com.br/eleicoes_2026")


def compartilhar(disputa):
    """Botões de compartilhar só a apuração: WhatsApp (mensagem pronta) e Instagram (arte para o Stories + link)."""
    url = link_apuracao()
    # chamada única (contratantes: Bruna Pessoa e o time do Fernando); só convida a acompanhar, sem pedir voto
    # antes de domingo 17h: convite com data e hora; depois: "está ao vivo"
    from datetime import datetime, timedelta, timezone
    agora = datetime.now(timezone(timedelta(hours=-3)))
    inicio = datetime(2026, 10, 4, 17, 0, tzinfo=timezone(timedelta(hours=-3)))
    if agora < inicio:
        quando = ("A apuração AO VIVO começa no *domingo, 4 de outubro, a partir das 17h* (horário de Brasília), "
                  "quando as urnas fecham. Salve o link! A Aggilli Intelligence vai acompanhar voto a voto")
    else:
        quando = "A apuração está AO VIVO e a Aggilli Intelligence acompanha voto a voto"
    texto = ("💗 Vem torcer com a gente pela Bruna e pelo Time do Fernando! 🗳️\n\n" + quando +
             ": Bruna Pessoa na Assembleia, a disputa pelo Governo do Maranhão e a corrida presidencial, "
             "com Tuntum em destaque e atualização a cada 90 segundos.\n\n👉 Acompanhe aqui:")
    nome_arte = "apuracao_brasil_stories.jpg" if disputa == "presidente" else "apuracao_maranhao_stories.jpg"
    wa = f"https://wa.me/?text={quote(texto + chr(10) + url)}"
    with st.container(key="compartilhar_apuracao"):
        st.markdown(f"""
<div class="compartilhe">
  {f'<img class="cp-logo" src="data:image/webp;base64,{_logo_base64()}" alt="Aggilli Intelligence">' if _logo_base64() else ''}
  <div class="cp-titulo">Compartilhe com seus amigos</div>
</div>""", unsafe_allow_html=True)
        # ícones num componente: o do Instagram abre o menu de compartilhar do celular (com a arte + o link),
        # onde aparece o app do Instagram (Stories, Feed ou Direct); no computador, baixa a arte e abre o Instagram
        components.html(f"""
<style>
  body {{margin: 0; font-family: Manrope, Arial, sans-serif;}}
  .ic {{display: flex; justify-content: center; gap: 28px; padding: 6px 0;}}
  .ic a, .ic button {{background: none; border: 0; padding: 0; cursor: pointer;}}
  .ic img {{width: 64px; height: 64px; transition: transform .15s; filter: drop-shadow(0 6px 12px rgba(27,42,65,.18));}}
  .ic a:hover img, .ic button:hover img {{transform: translateY(-3px) scale(1.06);}}
  #msg {{text-align: center; font-size: 12px; color: #3A4458; min-height: 16px;}}
</style>
<div class="ic">
  <a href="{wa}" target="_blank" rel="noopener" title="Compartilhar no WhatsApp">
    <img src="/app/static/icones/whatsapp.png" alt="WhatsApp"></a>
  <button id="insta" title="Compartilhar no Instagram"><img src="/app/static/icones/instagram.png" alt="Instagram"></button>
</div>
<div id="msg"></div>
<script>
const URL_LINK = {json.dumps(url)};
const TEXTO = {json.dumps(texto + chr(10) + url)};
const ARTE = "/app/static/compartilhar/{nome_arte}";
const msg = t => document.getElementById("msg").textContent = t;
async function copiar(t) {{
  try {{ await (window.parent.navigator.clipboard || navigator.clipboard).writeText(t); return true; }} catch (e) {{ return false; }}
}}
document.getElementById("insta").addEventListener("click", async () => {{
  const nav = (window.parent && window.parent.navigator && window.parent.navigator.share) ? window.parent.navigator : navigator;
  const copiado = await copiar(URL_LINK);
  try {{
    const blob = await (await fetch(ARTE)).blob();
    const arquivo = new File([blob], "{nome_arte}", {{type: "image/jpeg"}});
    if (nav.canShare && nav.canShare({{files: [arquivo]}})) {{
      await nav.share({{files: [arquivo], text: TEXTO}});
      msg(copiado ? "Link copiado: no Stories, cole no adesivo Link." : "");
      return;
    }}
  }} catch (e) {{ if (e && e.name === "AbortError") return; }}
  // sem menu de compartilhar (computador): baixa a arte e abre o Instagram
  const a = document.createElement("a"); a.href = ARTE; a.download = "{nome_arte}"; document.body.appendChild(a); a.click(); a.remove();
  const celular = /Android|iPhone|iPad/i.test(navigator.userAgent);
  window.open(celular ? "instagram://story-camera" : "https://www.instagram.com/", "_blank");
  msg("Arte baixada" + (copiado ? " e link copiado" : "") + ": publique no Stories e cole o link no adesivo Link.");
}});
</script>""", height=100)
        st.code(url, language=None)  # tem botão de copiar
        st.caption("Instagram: no celular, toque no ícone e escolha **Instagram** (Stories, Feed ou Direct); o link já fica "
                   "copiado para colar no adesivo **Link**.")


compartilhar(cfg["disputa"])
if ensaio and cfg["disputa"] in ("senador", "federal"):
    fracao = st.slider("Ensaio: quanto da apuração simular", 2, 100, 25, 1, format="%d%%") / 100
    st.info("🧪 **Ensaio:** usa os votos reais de 2022 no Maranhão "
            f"({'Senado: 1 vaga em 2022' if cfg['disputa'] == 'senador' else 'Câmara Federal'}). Serve para testar a "
            "página; os nomes e números são de 2022.")
elif ensaio and deputados:
    fracao = st.slider("Ensaio: quanto da apuração simular", 2, 100, 25, 1, format="%d%%") / 100
    st.info("🧪 **Ensaio:** Abigail Cunha e Eric Costa com os votos reais de 2022 por município; a Bruna não disputou em "
            "2022, então os votos dela são sorteados em torno da projeção do modelo. Serve para testar a página; os "
            "números não são previsão.")
elif ensaio:
    fracao = st.slider("Ensaio: quanto da apuração simular", 2, 100, 25, 1, format="%d%%") / 100
    st.info("🧪 **Ensaio:** usa a apuração real de 2022 como se fossem os candidatos de 2026 "
            f"({'Lula × Bolsonaro' if cfg['disputa'] == 'presidente' else 'Lahésio no lugar de Braide e Brandão no lugar de Orleans'})."
            " Serve para testar a página; os números não são previsão.")


@st.cache_data(ttl=90, show_spinner="Baixando a apuração do TSE…")
def baixar(disputa, turno_, ensaio_):
    return motor.baixar(disputa, turno_, ensaio=ensaio_)


def carregar_previsao():
    p = pd.read_csv(cfg["previsao"])
    if cfg["disputa"] == "presidente":
        p["prev_a_2t"], p["prev_b_2t"] = p.lula_2t, 100 - p.lula_2t
        p["prev_a_1t"], p["prev_b_1t"] = p.lula_1t, p.flavio_1t
    else:
        p["prev_a_2t"], p["prev_b_2t"] = p.braide_2t, 100 - p.braide_2t
        p["prev_a_1t"], p["prev_b_1t"] = p.braide_1t, p.orleans_1t
        p["cd_ibge"] = p.cd_ibge.astype(str)
    return p


def previsao_deputados():
    """Projeção por município: Bruna (modelo V13), Abigail (2022 + 3%, do duelo) e Eric (2022 + 3%).
    Só os números da apuração; o painel estratégico da Bruna fica no app próprio."""
    p = pd.read_csv(RAIZ / "apuracao" / "deputados_previsao.csv")
    p["abigail_2026"] = p.abigail_2026.fillna(p.abigail_2022 * 1.03)
    p["eric_2026"] = p.eric_costa_2022 * 1.03
    p["total_esperado"] = p.total_dep_est_2022 * 1.03
    p["cd_ibge"] = p.cd_ibge.astype(str)
    return p


def mil(x):
    return f"{x / 1000:.1f} mil".replace(".", ",")


# ---------------------------------------------------------------- narrador da apuração (textos bem-humorados)
FRASES = {
    "frente_dos_dois": [
        "🏎️ Bruna na pole position! Abigail e Eric estão vendo só a poeira do 15800.",
        "👑 A mesa da Assembleia já está arrastando uma cadeira: Bruna na frente dos dois.",
        "📈 Gráfico da Bruna subindo mais que preço de passagem em feriado.",
        "💗 Liderando o trio. Se continuar assim, vai ter que aprender o caminho do Palácio Manuel Beckman.",
    ],
    "atras_dos_dois": [
        "⏳ Calma, coordenação: urna do interior demora, mas chega. Bebe uma água.",
        "🧘 Respira… a apuração é maratona, não é 100 metros rasos.",
        "📦 Ainda tem muita urna na caixa. Ninguém tira o sapato antes da festa acabar.",
    ],
    "no_meio": [
        "🥪 Bruna no recheio do sanduíche: um na frente, um atrás. Bora virar esse pão.",
        "🎯 Uma já foi, falta a outra. Missão pela metade, café pela metade também.",
    ],
    "foto_de_chegada": [
        "📸 Foto de chegada! Diferença de {dif} votos com {quem} — dá pra contar no dedo (de uma cidade pequena).",
        "😬 {dif} votos separando Bruna e {quem}. É o tipo de placar que faz tio desligar a TV e ligar de novo.",
    ],
    "ultrapassou": [
        "🚀 ULTRAPASSOU! Bruna passou {quem} — alguém segura o foguetório de Tuntum!",
        "🏁 Virada! {quem} ficou pra trás. Pode soltar o primeiro grito (o segundo só depois dos 100%).",
        "🔄 Tabela virou: Bruna na frente de {quem}. O 15800 pediu passagem e já buzinou.",
    ],
    "perdeu_posicao": [
        "😮‍💨 {quem} passou à frente por enquanto. Relaxa: é só o GPS recalculando a rota.",
        "🎢 Montanha-russa: {quem} passou. Segura na barra que ainda tem looping.",
    ],
}
MARCOS = [(10000, "🎉 10 mil votos! Já dá pra lotar um ginásio só de eleitor da Bruna."),
          (20000, "🎺 20 mil! Isso já é bloco de carnaval saindo em Tuntum."),
          (24800, "🪑 Passou de 24,8 mil — em 2022, isso já tinha dado cadeira ao menor eleito."),
          (38329, "🏛️ Passou de 38,3 mil, a votação do último eleito da chapa do governo em 2022. O cheiro de posse ficou forte."),
          (50000, "🔥 50 mil votos! Isso não é eleitorado, é torcida organizada."),
          (60000, "🌋 60 mil! Alguém avisa o TSE que o 15800 não é erro de digitação.")]


def _frase(tipo, semente, **kw):
    lista = FRASES[tipo]
    return lista[semente % len(lista)].format(**kw)


def _vezes(a, b):
    """Quantas vezes a é de b, no formato 1,35×."""
    return "—" if b <= 0 else f"{a / b:.2f}×".replace(".", ",")


def _sinal(x):
    return f"{'+' if x >= 0 else '−'}{n(abs(x))}"


def estatisticas(d, r, apurado):
    """Placar em números: hoje × 2022, quantas vezes, diferenças e municípios vencidos."""
    c = r["cand"]
    vb, va, ve = c["bruna"]["contado"], c["abigail"]["contado"], c["eric"]["contado"]
    a22, e22 = float(d.abigail_2022.sum()), float(d.eric_costa_2022.sum())
    fb, fa, fe = c["bruna"]["final"][1], c["abigail"]["final"][1], c["eric"]["final"][1]
    st.subheader("📊 Placar em números")
    k = st.columns(4)
    k[0].metric("Bruna hoje", f"{n(vb)} votos", f"projeção do final {mil(fb)}", delta_color="off")
    k[1].metric("Abigail hoje", f"{n(va)} votos", f"em 2022 teve {n(a22)}", delta_color="off")
    k[2].metric("Eric hoje", f"{n(ve)} votos", f"em 2022 teve {n(e22)}", delta_color="off")
    k[3].metric("Seções que faltam", f"{n(max(100 - apurado, 0), 1)}%")
    k = st.columns(4)
    k[0].metric("Bruna ÷ Abigail (hoje)", _vezes(vb, va), f"{_sinal(vb - va)} votos", delta_color="off",
                help="Quantas vezes os votos da Bruna são os da Abigail, no que já foi apurado")
    k[1].metric("Bruna ÷ Eric (hoje)", _vezes(vb, ve), f"{_sinal(vb - ve)} votos", delta_color="off",
                help="Quantas vezes os votos da Bruna são os do Eric, no que já foi apurado")
    k[2].metric("Bruna hoje ÷ Abigail em 2022", _vezes(vb, a22), f"{_sinal(vb - a22)} votos", delta_color="off",
                help=f"A Abigail teve {n(a22)} votos em 2022")
    k[3].metric("Bruna hoje ÷ Eric em 2022", _vezes(vb, e22), f"{_sinal(vb - e22)} votos", delta_color="off",
                help=f"O Eric teve {n(e22)} votos em 2022")

    ap = d[d.pst > 0]
    ganha_a, ganha_e = int((ap.real_bruna > ap.real_abigail).sum()), int((ap.real_bruna > ap.real_eric).sum())
    tab = pd.DataFrame([
        {"Indicador": "Votos apurados até agora", "Bruna": vb, "Abigail": va, "Eric": ve},
        {"Indicador": "Votação em 2022", "Bruna": None, "Abigail": a22, "Eric": e22},
        {"Indicador": "% da própria votação de 2022 já alcançada", "Bruna": None,
         "Abigail": 100 * va / a22 if a22 else None, "Eric": 100 * ve / e22 if e22 else None},
        {"Indicador": "Projeção do final (votos)", "Bruna": fb, "Abigail": fa, "Eric": fe},
        {"Indicador": "Diferença da Bruna hoje (votos)", "Bruna": None, "Abigail": vb - va, "Eric": vb - ve},
        {"Indicador": "Diferença da Bruna na projeção (votos)", "Bruna": None, "Abigail": fb - fa, "Eric": fb - fe},
        {"Indicador": "Municípios em que a Bruna está à frente", "Bruna": None, "Abigail": ganha_a, "Eric": ganha_e},
    ])
    tabela(tab.astype({"Bruna": float, "Abigail": float, "Eric": float}), modo="identidade")  # vazio (e não "None") onde não se aplica
    melhor = ap.assign(vant=ap.real_bruna - ap.real_abigail).sort_values("real_bruna", ascending=False).head(1)
    if len(melhor):
        m = melhor.iloc[0]
        st.caption(f"Maior votação da Bruna até agora: {m.municipio} ({n(m.real_bruna)} votos; "
                   f"{_sinal(m.real_bruna - m.real_abigail)} sobre a Abigail e {_sinal(m.real_bruna - m.real_eric)} "
                   f"sobre o Eric na cidade). Municípios com votos apurados: {len(ap)} de {len(d)}.")


def cartao_tuntum(d):
    """Cartão de Tuntum: Bruna em destaque (grande); Abigail e Eric menores, do mesmo tamanho."""
    t = d[d.municipio.astype(str).str.lower() == "tuntum"]
    if t.empty:
        return
    t = t.iloc[0]
    vb, va, ve, pst = (float(t.get(c, 0) or 0) for c in ("real_bruna", "real_abigail", "real_eric", "pst"))
    situacao = "sem urnas apuradas ainda" if pst <= 0 else (
        "apuração encerrada" if pst >= 100 else f"{n(pst, 1)}% das seções apuradas")
    st.markdown(f"""
<div class="tuntum">
  <div class="tt-selo">🏠 TUNTUM · {situacao.upper()}</div>
  <div class="tt-corpo">
    <div class="tt-bruna"><div class="tt-nome">Bruna Pessoa</div>
      <div class="tt-num">{n(vb)}</div><div class="tt-leg">votos em Tuntum</div></div>
    <div class="tt-outros">
      <div class="tt-outro" style="--cor:#E8702A"><div class="tt-nome2">Abigail Cunha</div>
        <div class="tt-num2">{n(va)}</div><div class="tt-leg2">votos · Bruna {_sinal(vb - va)}</div></div>
      <div class="tt-outro" style="--cor:#3B6FB6"><div class="tt-nome2">Eric Costa</div>
        <div class="tt-num2">{n(ve)}</div><div class="tt-leg2">votos · Bruna {_sinal(vb - ve)}</div></div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)


def narrador(r, geral, numeros, ensaio, apurado):
    """Comentários bem-humorados conforme a apuração avança; homenagem quando a Bruna é eleita."""
    c = r["cand"]
    vb, va, ve = c["bruna"]["contado"], c["abigail"]["contado"], c["eric"]["contado"]
    if vb + va + ve < 1:
        return
    semente = int(apurado // 5)  # troca a frase a cada ~5% apurados (não fica piscando a cada atualização)
    # ---- eleita? (situação oficial do TSE; no ensaio, simulada com a linha de 38,3 mil ao fim da apuração)
    num_b = numeros.get("bruna")
    if ensaio:
        eleita = apurado >= 99.9 and vb >= 38329
        situacao = "eleita (simulação do ensaio)" if eleita else ""
    else:
        eleita = bool(geral.get("eleito", {}).get(num_b))
        situacao = geral.get("situacao", {}).get(num_b, "")
    if eleita:
        chave = "festa_ensaio" if ensaio else "festa"
        if not st.session_state.get(chave):
            st.session_state[chave] = True
            st.balloons()
        st.markdown(f"""
<div class="capa" style="background: radial-gradient(circle at 85% 20%, rgba(224,37,151,.8), transparent 55%),
     linear-gradient(160deg, #122545 25%, #5a2a6e); text-align:center;">
  <div class="selo">DEPUTADA ESTADUAL ELEITA · MARANHÃO 2026{' · ' + situacao.upper() if situacao else ''}</div>
  <div class="titulo">💗 Bruna Pessoa · 15800 · ELEITA!</div>
  <div class="sub">A filha de Tuntum agora tem cadeira na Assembleia. Cada voto dessa noite virou voz do interior
  no Palácio Manuel Beckman. Parabéns, Bruna — e parabéns a cada liderança, cabo eleitoral e eleitor que acreditou.</div>
  <div class="placar" style="justify-content:center">
    <div class="lado"><div class="nome">Bruna</div><div class="prob">{n(vb)}</div><div class="leg">votos</div></div>
    <div class="lado"><div class="nome">× Abigail</div><div class="prob">{'+' if vb >= va else '−'}{n(abs(vb - va))}</div>
      <div class="leg">diferença · Abigail {n(va)}</div></div>
    <div class="lado"><div class="nome">× Eric</div><div class="prob">{'+' if vb >= ve else '−'}{n(abs(vb - ve))}</div>
      <div class="leg">diferença · Eric {n(ve)}</div></div>
  </div>
</div>""", unsafe_allow_html=True)
        frase = ("A filha de Tuntum agora tem cadeira na Assembleia. Obrigado a cada liderança, cabo eleitoral "
                 "e eleitor que acreditou!")
        texto = (f"💗 BRUNA PESSOA ELEITA DEPUTADA ESTADUAL! 🎉\n\n{frase}\n\nBruna: {n(vb)} votos · "
                 f"Abigail: {n(va)} · Eric: {n(ve)}\n\nAcompanhamos tudo com a Aggilli Intelligence 👉 {momento.LINK}")
        momento.botoes(texto, momento.arte("Bruna Pessoa eleita!", frase, vb, va, ve, apurado, eleita=True, fmt=n),
                       "bruna_eleita.jpg")
        return

    # ---- ultrapassagens (compara com a atualização anterior desta sessão)
    anterior = st.session_state.get("narrador_posicao", {})
    atual = {"abigail": vb > va, "eric": vb > ve}
    avisos = []
    for k, nome in (("abigail", "a Abigail"), ("eric", "o Eric")):
        if k in anterior and anterior[k] != atual[k]:
            tipo = "ultrapassou" if atual[k] else "perdeu_posicao"
            txt = _frase(tipo, semente, quem=nome)
            avisos.append(txt)
            st.toast(txt, icon="🚀" if atual[k] else "🎢")
    st.session_state["narrador_posicao"] = atual

    # ---- situação atual
    if atual["abigail"] and atual["eric"]:
        base = _frase("frente_dos_dois", semente)
    elif not atual["abigail"] and not atual["eric"]:
        base = _frase("atras_dos_dois", semente)
    else:
        base = _frase("no_meio", semente)
    perto = min(((abs(vb - va), "Abigail"), (abs(vb - ve), "Eric")))
    if perto[0] <= max(300, 0.01 * (vb + va + ve)) and apurado >= 3:
        base = _frase("foto_de_chegada", semente, dif=n(perto[0]), quem=perto[1])
    marco = next((t for v, t in reversed(MARCOS) if vb >= v), "")

    difs = (f"<b>Bruna × Abigail:</b> {'+' if vb >= va else '−'}{n(abs(vb - va))} votos &nbsp;·&nbsp; "
            f"<b>Bruna × Eric:</b> {'+' if vb >= ve else '−'}{n(abs(vb - ve))} votos")
    st.markdown(f"""
<div class="cartao" style="border-left-color:#E02597; background:#FDF1F8">
<h4>🎙️ Narrador da apuração</h4>
{''.join(f'<div style="font:800 1.15rem Montserrat;color:#E02597;margin-bottom:6px">{a}</div>' for a in avisos)}
<div style="font-size:1.05rem">{base}</div>
{f'<div style="margin-top:6px">{marco}</div>' if marco else ''}
<div class="pequeno" style="margin-top:8px">{difs} (votos apurados até agora)</div>
</div>""", unsafe_allow_html=True)
    destaque = avisos[0] if avisos else base
    frase = destaque + (f" {marco}" if marco and not avisos else "")
    texto = (f"📡 Apuração ao vivo · {n(apurado, 1)}% apurado\n\n{destaque}\n\n"
             f"Bruna: {n(vb)} votos · Abigail: {n(va)} · Eric: {n(ve)}\n\n"
             f"💗 Vem torcer com a gente pela Bruna e pelo Time do Fernando! 👉 {momento.LINK}")
    momento.botoes(texto, momento.arte("Bruna Pessoa ao vivo", frase, vb, va, ve, apurado, fmt=n),
                   f"apuracao_{int(apurado)}pct.jpg")


@st.fragment(run_every=None if ensaio else "90s")
def painel_deputados():
    try:
        unidades, geral, numeros, info = baixar("deputado", 1, ensaio)
    except Exception as e:  # noqa: BLE001
        st.error(f"Não foi possível acessar o TSE agora ({e}). A página tenta de novo sozinha.")
        return
    if unidades is None:
        st.warning(f"⏳ {info['erro']} A página verifica sozinha a cada 90 segundos; no domingo, a apuração começa às 17h "
                   "(horário de Brasília). Enquanto isso, use o **modo ensaio**.")
        return
    faltando = [DEPUTADOS[k][0] for k in DEPUTADOS if k not in numeros]
    if faltando:
        st.warning(f"Não encontrei na lista do TSE: {', '.join(faltando)}. Confira o nome de urna "
                   "(apuracao/motor.py → NOMES_2026['deputado']).")
    if ensaio:
        unidades = unidades if fracao >= 1 else motor.simular_parcial(unidades, fracao, semente=int(fracao * 1000))
    prev = previsao_deputados()
    d, r = motor.projetar_votos(unidades, prev, numeros, {k: v[2] for k, v in DEPUTADOS.items()})
    apurado = r["apurado_pct"] if ensaio else geral["pst"]
    st.caption(f"Fonte: TSE · deputado estadual MA · eleição {info['eleicao']} ({info['ciclo']}) · "
               f"{r['unidades_com_votos']} de {r['unidades']} municípios com votos · atualizado agora")
    st.metric("Seções apuradas no Maranhão", f"{n(apurado, 1)}%")
    cartao_tuntum(d)
    narrador(r, geral, numeros, ensaio, apurado)

    k = st.columns(3)
    for col, (chave, (nome, cor, _, origem)) in zip(k, DEPUTADOS.items()):
        c = r["cand"][chave]
        ritmo = c["ritmo"]
        texto_ritmo = "sem votos apurados ainda" if ritmo is None or c["esperado_ate_agora"] < 1 else (
            f"{'+' if ritmo >= 1 else '−'}{n(abs(ritmo - 1) * 100, 0)}% vs. {'projeção' if chave == 'bruna' else '2022'}")
        num = numeros.get(chave, "?")
        col.markdown(f"""
<div class="dep-card" style="--accent:{cor}">
<div class="dep-head"><div class="dep-name">{nome}</div>
<span class="dep-badge">nº {num if str(num).isdigit() else '—'}</span></div>
<div class="dep-label">Votos apurados</div>
<div class="dep-votes">{n(c['contado'])}<small>votos</small></div>
<div class="dep-status">{texto_ritmo}<br>Esperado até agora: {n(c['esperado_ate_agora'])} votos</div>
<div class="dep-projection"><div class="dep-label">Projeção do resultado final</div>
<strong>{mil(c['final'][1])} votos</strong>
<div class="dep-range">Faixa provável: {mil(c['final'][0])} a {mil(c['final'][2])}</div>
<div class="dep-reference">Antes da apuração: {mil(c['previsto'])} votos<br>{origem}</div></div>
<div class="dep-chances">
<div class="dep-chance"><span>Acima de 38,3 mil votos</span><b>{pct(c['prob_acima']['último eleito da chapa do governo em 2022'])}</b></div>
<div class="dep-chance"><span>Acima de 24,8 mil votos</span><b>{pct(c['prob_acima']['menor eleito em 2022'])}</b></div>
</div></div>""", unsafe_allow_html=True)

    with st.container(key="placar_stats"):
        estatisticas(d, r, apurado)

    if r["apurado_pct"] < 5:
        st.info("Ainda há poucas seções apuradas: as projeções do final ficam largas até uns 10–15% da apuração.")

    fb, fa = r["cand"]["bruna"]["_amostras"], r["cand"]["abigail"]["_amostras"]
    fe = r["cand"]["eric"]["_amostras"]
    st.markdown(f"""
<div class="cartao verde"><h4>Quem termina à frente</h4>
Bruna à frente da Abigail em <b>{pct((fb > fa).mean())}</b> das projeções · Bruna à frente do Eric em
<b>{pct((fb > fe).mean())}</b> · Abigail à frente do Eric em <b>{pct((fa > fe).mean())}</b>.<br>
<span class="pequeno">Referências de 2022 (não são a linha de corte de 2026, que depende do quociente de cada partido):
menor eleito 24,8 mil · último eleito da chapa do governo 38,3 mil · mediana dos 42 eleitos 44,1 mil.</span></div>
""", unsafe_allow_html=True)

    fig = go.Figure()
    for chave, (nome, cor, _, _) in DEPUTADOS.items():
        c = r["cand"][chave]
        vals = [c["previsto"], c["contado"], c["final"][1]]
        fig.add_bar(name=nome, x=["Antes da apuração", "Apurado até agora", "Projeção do final"], y=vals,
                    marker_color=cor, text=[mil(v) for v in vals], textposition="outside",
                    error_y=dict(type="data", symmetric=False, array=[0, 0, c["final"][2] - c["final"][1]],
                                 arrayminus=[0, 0, c["final"][1] - c["final"][0]]))
    for corte, rotulo in [(24800, "menor eleito 2022"), (38329, "último eleito chapa gov. 2022")]:
        fig.add_hline(y=corte, line_dash="dot", line_color="#5B6477", annotation_text=rotulo,
                      annotation_position="top right", annotation_font_size=11,
                      annotation_bgcolor="rgba(255,255,255,.85)")
    fig.update_layout(barmode="group", height=420, yaxis_title="votos", legend=dict(orientation="h", y=-0.15),
                      title="Deputados estaduais: previsão × apuração × projeção final")
    grafico(fig)

    geo = json.load(open(RAIZ / "dados" / "ma_leve.geojson", encoding="utf-8"))
    mapa = d.assign(ritmo=(100 * (d.ritmo_bruna - 1)).clip(-100, 100))
    fig = px.choropleth_map(mapa, geojson=geo, locations="cd_ibge", featureidkey="properties.CD_MUN", color="ritmo",
                            color_continuous_scale=[[0, "#122545"], [0.5, "#F2F2F2"], [1, "#E02597"]],
                            range_color=(-60, 60), map_style="carto-positron", zoom=5.3,
                            center={"lat": -5.2, "lon": -45.2}, opacity=.8, height=560, hover_name="municipio",
                            hover_data={"cd_ibge": False, "real_bruna": ":,.0f", "esp_bruna": ":,.0f", "pst": ":.0f"},
                            labels={"ritmo": "Bruna vs. projeção (%)", "real_bruna": "Bruna apurado",
                                    "esp_bruna": "Bruna esperado até agora", "pst": "% apurado"})
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
    st.markdown("**Onde a Bruna está acima (rosa) ou abaixo (azul) da projeção** — cinza = sem votos ou sem "
                "projeção relevante ainda")
    grafico(fig)

    ap = d[d.pst > 0].copy()
    ap["situacao"] = np.select([ap.ritmo_bruna > 1.15, ap.ritmo_bruna < 0.85], ["Bruna acima do esperado",
                               "Bruna abaixo do esperado"], "Dentro do esperado")
    ap["ordem"] = ap[["prev_bruna", "real_bruna", "real_abigail", "real_eric"]].max(axis=1)
    tabela(ap.sort_values("ordem", ascending=False)[[
        "municipio", "pst", "real_bruna", "esp_bruna", "real_abigail", "esp_abigail", "real_eric", "esp_eric",
        "situacao"]].rename(columns={
        "municipio": "Município", "pst": "% apurado", "real_bruna": "Bruna apurado", "esp_bruna": "Bruna esperado",
        "real_abigail": "Abigail apurado", "esp_abigail": "Abigail esperado", "real_eric": "Eric apurado",
        "esp_eric": "Eric esperado", "situacao": "Situação"}))
    st.caption("Como a projeção é feita: em cada município, \"esperado até agora\" = projeção × % de seções apuradas. "
               "O ritmo de cada candidato (apurado ÷ esperado nos municípios já abertos) corrige os votos que faltam; "
               "município com metade ou mais apurada usa o próprio ritmo. Abigail e Eric não têm modelo próprio: a "
               "referência é a votação de 2022 ajustada em +3% de eleitorado, então o ritmo deles mostra quanto estão "
               "acima ou abaixo de 2022.")


FOTOS = RAIZ / "assets" / "fotos"  # coloque aqui lula.jpg / flavio.jpg (fotos de campanha) para usar no placar


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def foto_base64(chave, ciclo, ele, sqcand, abr="br"):
    """Foto do placar: arquivo em assets/fotos/<chave>.(jpg|png|webp) → foto oficial do TSE → vazio (iniciais)."""
    import base64
    for ext, mime in (("jpg", "jpeg"), ("jpeg", "jpeg"), ("png", "png"), ("webp", "webp")):
        arq = FOTOS / f"{chave}.{ext}"
        if arq.exists():
            return f"data:image/{mime};base64," + base64.b64encode(arq.read_bytes()).decode()
    if sqcand:
        try:
            return "data:image/jpeg;base64," + base64.b64encode(motor.foto_tse(ciclo, ele, abr, sqcand)).decode()
        except Exception:  # noqa: BLE001
            pass
    return ""


def _cd_tuntum():
    mun = pd.read_csv(RAIZ / "apuracao" / "deputados_previsao.csv")
    return int(mun.loc[mun.municipio.astype(str).str.lower() == "tuntum", "CD_MUNICIPIO"].iloc[0])


@st.cache_data(ttl=90, show_spinner=False)
def tuntum_presidente(ciclo, ele):
    """Votação para presidente em Tuntum (arquivo do município no TSE)."""
    return motor.ler_municipio(ciclo, ele, "ma", f"{_cd_tuntum():05d}", 1)


# placar grande de cada disputa: (chave da foto, nome, nome curto, cor, cor escura)
PLACAR = {"presidente": dict(a=("lula", "Lula", "Lula", "#C8102E", "#8E0B20"),
                             b=("flavio", "Flávio Bolsonaro", "Flávio", "#1D4E89", "#123563"),
                             legenda="🇧🇷 VOTAÇÃO BRASIL", abr="br"),
          "governador": dict(a=("braide", "Eduardo Braide", "Braide", "#1F6FB2", "#14507F"),
                             b=("orleans", "Orleans Brandão", "Orleans", "#E07B1F", "#A8560F"),
                             legenda="🏛️ VOTAÇÃO MARANHÃO", abr="ma")}


def placar_duelo(disputa, unidades, geral, numeros, info):
    """Placar grande do duelo (cores e fotos de cada candidato) + quadros de Tuntum, com legendas."""
    pc = PLACAR[disputa]
    (ka, nome_a, curto_a, cor_a, esc_a), (kb, nome_b, curto_b, cor_b, esc_b) = pc["a"], pc["b"]
    na, nb = numeros.get(ka), numeros.get(kb)
    if geral.get("votos"):
        va, vb, vv = geral["votos"].get(na, 0), geral["votos"].get(nb, 0), geral.get("vv", 0)
    else:  # ensaio: soma das unidades
        va, vb = (float(unidades[f"v_{x}"].sum()) if f"v_{x}" in unidades else 0.0 for x in (na, nb))
        vv = float(unidades.vv.sum())
    pa, pb = (100 * va / vv, 100 * vb / vv) if vv else (0, 0)
    sq = geral.get("sqcand", {})
    lados = []
    for chave, nome, num, votos, p, cor, escuro in ((ka, nome_a, na, va, pa, cor_a, esc_a),
                                                    (kb, nome_b, nb, vb, pb, cor_b, esc_b)):
        foto = foto_base64(chave, info.get("ciclo"), info.get("eleicao"), sq.get(num, ""), pc["abr"])
        img = (f'<img src="{foto}" alt="{nome}">' if foto
               else f'<div class="pl-ini" style="background:{cor}">{"".join(w[0] for w in nome.split()[:2])}</div>')
        lados.append(f"""
<div class="pl-lado">
  <div class="pl-foto" style="--cor:{cor}">{img}</div>
  <div class="pl-quadro" style="background: linear-gradient(160deg, {cor}, {escuro});">
    <div class="pl-nome">{nome.upper()} · {num if str(num).isdigit() else '—'}</div>
    <div class="pl-votos">{n(votos)}</div>
    <div class="pl-pct">{n(p, 2)}% dos votos válidos</div>
  </div>
</div>""")

    def diferenca(a, b):
        lider = curto_a if a > b else curto_b if b > a else ""
        return f"{lider} à frente por {n(abs(a - b))} votos" if lider else "empate"

    # ---- Tuntum: governador vem da própria tabela de municípios; presidente, do arquivo de Tuntum no TSE
    tun = None
    if disputa == "governador":
        linha = unidades[unidades.unidade.astype(int) == _cd_tuntum()]
        if len(linha) and float(linha.vv.iloc[0]) > 0:
            l0 = linha.iloc[0]
            tun = {"pst": float(l0.pst), "vv": float(l0.vv),
                   "votos": {x: float(l0.get(f"v_{x}", 0) or 0) for x in (na, nb)}}
    elif not info.get("ensaio"):
        try:
            tun = tuntum_presidente(info.get("ciclo"), info.get("eleicao"))
        except Exception:  # noqa: BLE001
            tun = None
    quadros_t = []
    for nome, num, cor in ((nome_a, na, cor_a), (nome_b, nb, cor_b)):
        if tun:
            v = tun["votos"].get(num, 0)
            corpo = (f'<div class="pt-votos">{n(v)}</div>'
                     f'<div class="pt-pct">{n(100 * v / tun["vv"], 2) if tun["vv"] else "0"}% dos válidos em Tuntum</div>')
        else:
            corpo = ('<div class="pt-votos">—</div><div class="pt-pct">'
                     + ("no ensaio não há dados de Tuntum" if info.get("ensaio") else "aguardando o TSE") + "</div>")
        quadros_t.append(f'<div class="pt-quadro" style="--cor:{cor}"><div class="pt-nome">{nome.upper()}</div>{corpo}</div>')
    sub_t = (f"{n(tun['pst'], 1)}% das seções apuradas em Tuntum · " + diferenca(
        tun["votos"].get(na, 0), tun["votos"].get(nb, 0))) if tun else ""
    quadro_dif = diferenca_tuntum(tun, na, nb, curto_a, curto_b, cor_a, cor_b)
    st.markdown(f"""
<div class="pl-legenda">{pc['legenda']}</div>
<div class="placar-pres">
  {lados[0]}
  <div class="pl-x">✕</div>
  {lados[1]}
</div>
<div class="pl-dif">{diferenca(va, vb)}</div>
<div class="pl-legenda">🏠 VOTAÇÃO TUNTUM</div>
<div class="placar-tuntum">
  {quadros_t[0]}
  <div class="pl-x pequeno-x">✕</div>
  {quadros_t[1]}
</div>
<div class="pl-dif">{sub_t}</div>
{quadro_dif}""", unsafe_allow_html=True)


# piadinhas para quando a diferença em Tuntum fica grande (sem pedir voto e sem desmerecer ninguém)
PIADAS_TUNTUM = [
    "Em Tuntum isso já não é disputa, é goleada: o outro lado vai pedir prorrogação! ⚽",
    "Com essa vantagem, {lider} já dá pra ser visto de satélite em Tuntum 🛰️",
    "Nem a calculadora mais otimista chama isso de disputa apertada 😅",
    "Tuntum falou alto: diferença tão grande que já tem gente pedindo recontagem só por curiosidade 🧮",
    "Se fosse corrida, {lider} já estaria tomando café na linha de chegada ☕",
]


def diferenca_tuntum(tun, na, nb, curto_a, curto_b, cor_a, cor_b):
    """Quadro central abaixo dos dois de Tuntum: diferença em votos; se for grande, uma piadinha."""
    if not tun:
        return ('<div class="pt-dif"><div class="pd-rot">DIFERENÇA EM TUNTUM</div><div class="pd-num">—</div>'
                '<div class="pd-frase">A contagem de Tuntum aparece aqui assim que o TSE divulgar.</div></div>')
    va, vb, vv = tun["votos"].get(na, 0), tun["votos"].get(nb, 0), tun.get("vv", 0) or 0
    dif = abs(va - vb)
    if va == vb:
        frase = ("Zero a zero por enquanto: Tuntum ainda está aquecendo. 🔥" if va == 0
                 else "Empate cravado em Tuntum! Cada voto agora vale ouro. 🥇")
        return (f'<div class="pt-dif"><div class="pd-rot">DIFERENÇA EM TUNTUM</div><div class="pd-num">0 votos</div>'
                f'<div class="pd-frase">{frase}</div></div>')
    lider, cor = (curto_a, cor_a) if va > vb else (curto_b, cor_b)
    pts = 100 * dif / vv if vv else 0
    if pts >= 20 and dif >= 300:
        frase = PIADAS_TUNTUM[int(dif) % len(PIADAS_TUNTUM)].format(lider=lider)
    elif pts < 2:
        frase = "Disputa voto a voto em Tuntum: ninguém pisca! 👀"
    else:
        frase = f"{lider} abre vantagem em Tuntum, mas a apuração continua."
    return (f'<div class="pt-dif" style="--cor:{cor}"><div class="pd-rot">DIFERENÇA EM TUNTUM</div>'
            f'<div class="pd-num">{n(dif)} {"voto" if dif == 1 else "votos"}</div>'
            f'<div class="pd-lider">{lider} na frente · {n(pts, 1)} pontos dos válidos</div>'
            f'<div class="pd-frase">{frase}</div></div>')


CARGO_TXT = {"presidente": ("presidente do Brasil", "O Brasil"), "governador": ("governador do Maranhão", "O Maranhão")}


def resultado_turno(disputa, turno, unidades, geral, numeros, info, ensaio_):
    """Fim do turno: parabeniza o eleito; se houver 2º turno, recado bem-humorado. Com imagem para compartilhar."""
    pc = PLACAR[disputa]
    (ka, nome_a, curto_a, cor_a, _), (kb, nome_b, curto_b, cor_b, _) = pc["a"], pc["b"]
    na, nb = numeros.get(ka), numeros.get(kb)
    if geral.get("votos"):
        va, vb, vv = geral["votos"].get(na, 0), geral["votos"].get(nb, 0), geral.get("vv", 0)
    else:
        va, vb = (float(unidades[f"v_{x}"].sum()) if f"v_{x}" in unidades else 0.0 for x in (na, nb))
        vv = float(unidades.vv.sum())
    pa, pb = (100 * va / vv, 100 * vb / vv) if vv else (0, 0)
    vencedor, segundo = None, False
    if ensaio_:  # no ensaio, decide pelo resultado de 2022 quando a barra chega a 100%
        if globals().get("fracao", 0) < 1:
            return
        if turno == 2 or max(pa, pb) > 50:
            vencedor = 0 if pa >= pb else 1
        else:
            segundo = True
    else:
        sit = geral.get("situacao", {})
        eleitos = [k for k, v in sit.items() if str(v).lower().startswith("eleit")]
        no_2t = [k for k, v in sit.items() if "turno" in str(v).lower()]
        if eleitos:
            vencedor = 0 if eleitos[0] == na else 1 if eleitos[0] == nb else eleitos[0]
        elif no_2t and turno == 1:
            segundo = True
        else:
            return
    cargo, lugar = CARGO_TXT[disputa]
    foto = lambda k: str(RAIZ / "assets" / "fotos" / f"{k}.jpg")  # noqa: E731
    A = (nome_a, va, pa, cor_a, foto(ka))
    B = (nome_b, vb, pb, cor_b, foto(kb))
    if segundo:
        selo = f"1º TURNO ENCERRADO{' · ENSAIO' if ensaio_ else ''}"
        titulo = "Ainda não foi dessa vez!"
        frase = (f"{lugar} pediu prorrogação: {curto_a} e {curto_b} voltam a campo no 2º turno, em 25 de outubro. "
                 + ("Pega a pipoca que tem mais um capítulo! 🍿" if disputa == "presidente"
                    else "Segura o coração que tem mais emoção! 💓"))
        destaque, cor_capa = None, "#3B2A6B"
    else:
        if isinstance(vencedor, int):
            nome_v, destaque, cor_capa = (nome_a, 0, cor_a) if vencedor == 0 else (nome_b, 1, cor_b)
        else:
            nome_v, destaque, cor_capa = geral.get("nomes", {}).get(vencedor, "Candidato"), None, "#1F7A4D"
        selo = f"{turno}º TURNO · RESULTADO{' · ENSAIO' if ensaio_ else ''}"
        titulo = f"{nome_v} eleito {cargo}!"
        frase = (f"Parabéns a {nome_v}, eleito {cargo}" + (" já no 1º turno" if turno == 1 else "")
                 + ". Que venha um mandato à altura da confiança de cada eleitor! 🎉")
    st.markdown(f"""
<div class="capa" style="text-align:center; background: radial-gradient(circle at 85% 15%, {cor_capa}cc, transparent 60%),
     linear-gradient(160deg, #0E1B33 20%, #12233F 60%, #3B2A6B);">
  <div class="selo">{selo}</div>
  <div class="titulo">{'🍿 ' if segundo else '🎉 '}{titulo}</div>
  <div class="sub">{frase}</div>
</div>""", unsafe_allow_html=True)
    imagem = momento.arte_duelo(selo, titulo, frase, A, B, destaque=destaque, fmt=n)
    c = st.columns([1, 2, 1])
    c[1].image(imagem, width="stretch")
    texto = (f"{'🍿' if segundo else '🎉'} {titulo}\n\n{frase}\n\n{curto_a}: {n(va)} votos ({n(pa, 2)}%) · "
             f"{curto_b}: {n(vb)} votos ({n(pb, 2)}%)\n\nAcompanhe com a Aggilli Intelligence 👉 {momento.LINK}")
    momento.botoes(texto, imagem, f"resultado_{disputa}_{turno}turno.jpg")


@st.fragment(run_every=None if ensaio else "90s")
def painel():
    if ensaio and cfg["disputa"] == "governador" and turno == 2:
        st.warning("O Maranhão não teve 2º turno para governador em 2022: não há ensaio possível.")
        return
    try:
        unidades, geral, numeros, info = baixar(cfg["disputa"], turno, ensaio)
    except Exception as e:  # noqa: BLE001
        st.error(f"Não foi possível acessar o TSE agora ({e}). A página tenta de novo sozinha.")
        return
    if unidades is None:
        st.warning(f"⏳ {info['erro']} A página verifica sozinha a cada 90 segundos; no domingo, a apuração começa às 17h "
                   "(horário de Brasília). Enquanto isso, use o **modo ensaio**.")
        return
    if len(numeros) < 2:
        st.error(f"Não identifiquei os dois candidatos na lista do TSE ({numeros}).")
        return
    if ensaio:
        unidades = unidades if fracao >= 1 else motor.simular_parcial(unidades, fracao, semente=int(fracao * 1000))
    prev = carregar_previsao()
    d, r = motor.projetar(unidades, prev, numeros, cfg["a"], cfg["b"], f"prev_a_{turno}t", f"prev_b_{turno}t",
                          "validos_26_est", cfg["chave"], turno=turno)
    na, nb = cfg["nome_a"], cfg["nome_b"]
    apurado = geral["pst"] if not ensaio else r["apurado_pct_votos"]
    st.caption(f"Fonte: TSE · eleição {info['eleicao']} ({info['ciclo']}) · {r['unidades_com_votos']} de "
               f"{r['unidades']} {cfg['unidade'].lower()}s com votos · atualizado agora")
    placar_duelo(cfg["disputa"], unidades, geral, numeros, info)
    resultado_turno(cfg["disputa"], turno, unidades, geral, numeros, info, ensaio)
    if r.get("sem_dados"):
        st.metric("Seções apuradas", f"{n(apurado, 1)}%")
        st.info("Ainda há poucos votos apurados para comparar com a projeção. Aguarde os primeiros resultados.")
        return

    k = st.columns(4)
    k[0].metric("Seções apuradas", f"{n(apurado, 1)}%")
    k[1].metric(f"{na} agora", f"{n(r['atual_a'], 1)}%", f"{n(r['desvio_medio_a'], 1)} pts vs. projeção", delta_color="off")
    k[2].metric(f"{nb} agora", f"{n(r['atual_b'], 1)}%", f"{n(r['desvio_medio_b'], 1)} pts vs. projeção", delta_color="off")
    k[3].metric(f"Chance de {na} terminar à frente", pct(r["prob_a_na_frente"]))

    fa, fb = r["final_a"], r["final_b"]
    lider, prob = (na, r["prob_a_na_frente"]) if r["prob_a_na_frente"] >= .5 else (nb, 1 - r["prob_a_na_frente"])
    texto_1t = ""
    if turno == 1:
        texto_1t = (f" Chance de alguém vencer já no 1º turno: {na} {pct(r['prob_a_50'])} · {nb} {pct(r['prob_b_50'])}.")
    aviso = (" <b>Atenção:</b> com menos de 10% apurado a estimativa ainda é pouco confiável."
             if r["apurado_pct_votos"] < 10 else "")
    st.markdown(f"""
<div class="cartao verde"><h4>Para onde aponta o resultado final</h4>
<b>{na}: {n(fa[1], 1)}%</b> (faixa provável {n(fa[0], 1)}% a {n(fa[2], 1)}%) &nbsp;×&nbsp;
<b>{nb}: {n(fb[1], 1)}%</b> ({n(fb[0], 1)}% a {n(fb[2], 1)}%) dos votos válidos.
Hoje, <b>{lider}</b> termina à frente em <b>{pct(prob)}</b> das projeções.{texto_1t}{aviso}<br>
<span style="opacity:.75">Antes da apuração, o modelo previa {na} {n(r['previsto_a'], 1)}% × {nb} {n(r['previsto_b'], 1)}%.</span>
</div>""", unsafe_allow_html=True)

    fig = go.Figure()
    for nome, vals, cor in [(na, [r["previsto_a"], r["atual_a"], fa[1]], cfg["cor_a"]),
                            (nb, [r["previsto_b"], r["atual_b"], fb[1]], cfg["cor_b"])]:
        fig.add_bar(name=nome, x=["Previsão antes da apuração", "Apurado até agora", "Projeção do final"], y=vals,
                    marker_color=cor, text=[f"{n(v, 1)}%" for v in vals], textposition="outside")
    fig.update_layout(barmode="group", height=360, yaxis_title="% dos votos válidos", legend=dict(orientation="h", y=-0.15),
                      title="Previsão × apuração × projeção final")
    grafico(fig)

    ap = d[d.contado_vv > 0].copy()
    ap["situacao"] = np.select([ap.desvio_a > 2, ap.desvio_a < -2], [f"{na} acima do esperado", f"{na} abaixo do esperado"],
                               "Dentro do esperado")
    geo = json.load(open(cfg["geo"], encoding="utf-8"))
    loc = cfg["loc"]
    mapa = d.assign(desvio=d.desvio_a.where(d.contado_vv > 0))
    fig = px.choropleth_map(mapa, geojson=geo, locations=loc, featureidkey=cfg["feat"], color="desvio",
                            color_continuous_scale=[[0, cfg["cor_b"]], [0.5, "#F2F2F2"], [1, cfg["cor_a"]]],
                            range_color=(-10, 10), map_style="carto-positron", zoom=cfg["zoom"], center=cfg["centro"],
                            opacity=.8, height=560, hover_name="municipio" if "municipio" in d else loc,
                            hover_data={loc: False, "real_a": ":.1f", "prev_a": ":.1f", "pst": ":.0f"},
                            labels={"desvio": f"{na} − projeção (pts)", "real_a": f"{na} apurado %",
                                    "prev_a": f"{na} projetado %", "pst": "% apurado"})
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
    st.markdown(f"**Onde {na} está acima (cor de {na}) ou abaixo (cor de {nb}) da projeção** — cinza = sem votos ainda")
    grafico(fig)

    nome_col = "municipio" if "municipio" in ap else cfg["chave"]
    tabela(ap.sort_values("contado_vv", ascending=False)[[nome_col, "pst", "contado_vv", "real_a", "prev_a", "desvio_a",
                                                          "real_b", "prev_b", "desvio_b", "situacao"]].rename(columns={
        nome_col: cfg["unidade"], "pst": "% apurado", "contado_vv": "Válidos apurados",
        "real_a": f"{na} apurado %", "prev_a": f"{na} projetado %", "desvio_a": f"{na} diferença (pts)",
        "real_b": f"{nb} apurado %", "prev_b": f"{nb} projetado %", "desvio_b": f"{nb} diferença (pts)",
        "situacao": "Situação"}))
    st.caption("Como a projeção final é feita: nas unidades já apuradas mede-se quanto cada candidato está acima ou abaixo "
               "do modelo; esse desvio é aplicado aos votos que ainda faltam em cada unidade. A faixa foi calibrada em "
               "apurações simuladas de 2022 (com 15% ou mais apurado, contém o resultado real em mais de 80% das vezes).")


# ------------------------------------------------------------------ Senado e Câmara Federal (MA)
@st.cache_data(ttl=90, show_spinner="Baixando a apuração do TSE…")
def baixar_ranking(disputa, ensaio_, fracao_):
    return motor.ranking(disputa, ensaio_, fracao_)


@st.cache_data(ttl=None, show_spinner=False)
def foto_candidato(ciclo, ele, sqcand):
    import base64
    try:
        return "data:image/jpeg;base64," + base64.b64encode(motor.foto_tse(ciclo, ele, "ma", sqcand)).decode()
    except Exception:  # noqa: BLE001
        return ""


def _ir_assembleia():
    alvo = next(k for k, v in DISPUTAS.items() if v["disputa"] == "deputado")
    st.session_state["ap_disputa"] = alvo
    st.session_state["_ap_disputa_ok"] = alvo


def destaque_assembleia():
    """Chamada fixa para a Assembleia MA nas páginas de Senado e Câmara Federal."""
    with st.container(key="destaque_assembleia"):
        c = st.columns([3, 1.2], vertical_alignment="center")
        c[0].markdown("""<div class="da-selo">💗 DESTAQUE DA APURAÇÃO</div>
<div class="da-titulo">Assembleia Legislativa do Maranhão</div>
<div class="da-texto">Bruna Pessoa, Abigail Cunha e Eric Costa voto a voto, com Tuntum em destaque e projeção do final.</div>""",
                      unsafe_allow_html=True)
        c[1].button("Ver a Assembleia MA →", key="ir_assembleia", on_click=_ir_assembleia, width="stretch",
                    type="primary")


def _nome_bonito(nm):
    nm = str(nm)
    if not nm.isupper():
        return nm
    t = " " + nm.title() + " "
    for p in ("De", "Da", "Do", "Dos", "Das", "E"):
        t = t.replace(f" {p} ", f" {p.lower()} ")
    return t.strip()


def _iniciais(nm):
    p = [x for x in str(nm).split() if len(x) > 2] or [str(nm)]
    return (p[0][0] + (p[-1][0] if len(p) > 1 else "")).upper()


def painel_ranking(disputa):
    vagas = motor.VAGAS[disputa]
    titulo = "Senado · Maranhão" if disputa == "senador" else "Câmara dos Deputados · Maranhão"
    destaque_assembleia()
    try:
        df, info = baixar_ranking(disputa, ensaio, fracao if ensaio else 1.0)
    except Exception as e:  # noqa: BLE001
        st.error(f"Não foi possível acessar o TSE agora ({e}). A página tenta de novo sozinha.")
        return
    if df is None:
        st.warning(f"⏳ {info['erro']}")
        return
    if not ensaio and info["pst"] <= 0:
        st.warning(f"⏳ A apuração para {'o Senado' if disputa == 'senador' else 'deputado federal'} "
                   f"começa no domingo, 4 de outubro, a partir das 17h (horário de Brasília). O TSE já publicou "
                   f"{len(df)} candidaturas; a página atualiza sozinha a cada 90 segundos. Enquanto isso, use o "
                   "**modo ensaio**.")
        return
    st.caption(f"Fonte: TSE · {titulo} · eleição {info['eleicao']} ({info['ciclo']}) · atualizado agora")
    k = st.columns(3)
    k[0].metric("Seções apuradas no Maranhão", f"{n(info['pst'], 1)}%")
    k[1].metric("Votos válidos apurados", n(info["vv"]))
    k[2].metric("Seções apuradas em Tuntum", f"{n(info['pst_tuntum'], 1)}%")

    mostrar = 6 if disputa == "senador" else 30
    vv = max(info["vv"], 1)
    topo = df.head(mostrar)
    linhas = []
    for i, r in topo.iterrows():
        foto = foto_candidato(info["ciclo"], info["eleicao"], r.sqcand) if r.sqcand and not ensaio else ""
        avatar = f'<img src="{foto}" alt="">' if foto else f"<span>{_iniciais(r.nome)}</span>"
        p_ = 100 * r.votos / vv
        larg = 100 * r.votos / max(topo.votos.max(), 1)
        st_ = str(r.situacao or "")
        eleito = st_.lower().startswith("eleit")
        chip = (f'<em class="rk-st eleito">{st_}</em>' if eleito else f'<em class="rk-st">{st_}</em>' if st_ else
                ('<em class="rk-st dentro">nas vagas</em>' if i < vagas else '<em class="rk-st vazio"></em>'))
        linhas.append(f"""<div class="rk-linha{' dentro' if i < vagas else ''}{' eleito' if eleito else ''}">
<span class="rk-pos">{i + 1}º</span><span class="rk-foto">{avatar}</span>
<div class="rk-info"><b>{_nome_bonito(r.nome)}</b><small>{r.partido or 'partido'} · nº {r.numero}</small>
<div class="rk-barra"><i style="width:{larg:.1f}%"></i></div></div>
<div class="rk-num"><b>{n(r.votos)}</b><small>{n(p_, 1)}%</small></div>
<div class="rk-num rk-tun"><b>{n(r.tuntum)}</b><small>Tuntum</small></div>{chip}</div>""")
        if i == vagas - 1 and len(topo) > vagas:
            corte = ("linha das 2 vagas de 2026" if disputa == "senador" else
                     "18 primeiros · as cadeiras dependem do quociente partidário")
            linhas.append(f'<div class="rk-corte"><span>{corte}</span></div>')
    st.markdown(f"""<div class="rk {disputa}"><div class="rk-cab">{'⭐' if disputa == 'senador' else '🏢'} {titulo.upper()}
<span>{vagas} {'vagas' if vagas > 1 else 'vaga'}</span></div>{''.join(linhas)}</div>""", unsafe_allow_html=True)
    if disputa == "federal":
        st.caption("Na Câmara, as 18 cadeiras do Maranhão são distribuídas entre partidos e federações pelo quociente "
                   "eleitoral; por isso a ordem por votos é indicativa até a totalização do TSE (a coluna situação "
                   "mostra eleito por QP, por média ou suplente quando o TSE divulgar).")
    else:
        st.caption("Em 2026 o Maranhão elege 2 senadores (cada eleitor vota em dois): os dois mais votados ficam com as "
                   "vagas.")
    with st.expander(f"Todos os {len(df)} candidatos" + (" · procurar por nome" if disputa == "federal" else "")):
        busca = st.text_input("Procurar candidato", key=f"busca_{disputa}", placeholder="nome, partido ou número")
        t = df.assign(pos=range(1, len(df) + 1), pct=100 * df.votos / vv, nome=df.nome.map(_nome_bonito))
        if busca:
            b = motor._sem_acento(busca)
            t = t[t.apply(lambda r: b in motor._sem_acento(f"{r.nome} {r.partido} {r.numero}"), axis=1)]
        tabela(t[["pos", "nome", "partido", "numero", "votos", "pct", "tuntum", "situacao"]].rename(columns={
            "pos": "Posição", "nome": "Candidato", "partido": "Partido", "numero": "Número", "votos": "Votos",
            "pct": "% válidos", "tuntum": "Votos em Tuntum", "situacao": "Situação"}))


@st.fragment(run_every=None if ensaio else "90s")
def painel_ranking_vivo():
    painel_ranking(cfg["disputa"])


if deputados:
    with st.container(key="apuracao_deputados"):
        painel_deputados()
elif cfg["disputa"] in ("senador", "federal"):
    painel_ranking_vivo()
else:
    painel()

with st.expander("🔧 Verificar conexão com o TSE (diagnóstico)"):
    st.caption("Testa, a partir deste servidor, se o site de resultados do TSE responde e se os arquivos de presidente, "
               "governador, deputados e do município de Tuntum são lidos. Antes das 17h do domingo é normal aparecer "
               "0% apurado; o que importa é cada etapa estar ✅.")
    if st.button("Rodar diagnóstico agora", key="diag_tse"):
        with st.spinner("Consultando o TSE…"):
            res = motor.diagnostico()
        for etapa, ok, detalhe in res:
            st.markdown(f"{'✅' if ok else '❌'} **{etapa}** — {detalhe}")
        if all(ok for _, ok, _ in res):
            st.success("Tudo certo: a apuração ao vivo consegue ler o TSE a partir deste servidor.")
        else:
            st.error("Há etapas com falha. Se o erro for de acesso (403/timeout), o TSE pode estar bloqueando este "
                     "servidor: no domingo, rode o painel num computador no Brasil (streamlit run app.py).")
