"""Painel — Governo do Maranhão 2026: Braide × Orleans. Modelo independente de previsão.

Rodar:  streamlit run painel_governo_ma.py
Dados:  preparar_base.py → modelos_pesquisas.py → modelo_municipios_mc.py (pasta resultados/)
"""
import hmac
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

RAIZ = Path(__file__).resolve().parent
RES, DADOS = RAIZ / "resultados", RAIZ / "dados"
AZUL, LARANJA, VERMELHO, VERDE, CINZA, TINTA = "#1F6FB2", "#E07B1F", "#C0392B", "#2E8B57", "#8A8F98", "#1B2A41"
COR = {"Braide": AZUL, "Orleans": LARANJA, "Camarão": VERMELHO, "Rocha": "#6B4FA0", "Indefinido": "#B8BEC8",
       "Neutro": "#B8BEC8"}

pio.templates["painel"] = go.layout.Template(pio.templates["plotly_white"])
pio.templates["painel"].layout.paper_bgcolor = "rgba(0,0,0,0)"
pio.templates["painel"].layout.plot_bgcolor = "rgba(0,0,0,0)"
pio.templates.default = "painel"
px.defaults.template = "painel"

st.set_page_config(page_title="Governo MA 2026 · Braide × Orleans", page_icon="🗳️", layout="wide")


def _exigir_senha():
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


_exigir_senha()
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@700;900&family=Manrope:wght@400;600;800&display=swap');
html, body, [class*="st-"], .stMarkdown {font-family: 'Manrope', Arial, sans-serif;}
h1, h2, h3, h4 {font-family: 'Archivo', Arial, sans-serif !important; color: #1B2A41;}
.block-container {padding-top: 3.4rem; max-width: 1400px;}
[data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #D9E1EC; border-radius: 14px; padding: 10px 14px;}
[data-testid="stMetricValue"] {font-family: 'Archivo', Arial, sans-serif; font-weight: 900; color: #1B2A41;}
[class*="st-key-caixa_"] {background: linear-gradient(180deg, #EEF3FA 0px, #FFFFFF 180px); border: 1px solid #D9E1EC;
    border-top: 4px solid #1B2A41; border-radius: 14px; padding: 10px 10px 8px;}
.capa {border-radius: 22px; padding: 22px 26px; color: #fff; margin-bottom: 12px;
       background: linear-gradient(100deg, #1F6FB2 0%, #1B2A41 50%, #E07B1F 100%);}
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
""", unsafe_allow_html=True)


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


@st.cache_data
def carregar():
    j = lambda f: json.load(open(RES / f, encoding="utf-8"))
    mun = pd.read_csv(RES / "municipios_previsao.csv")
    mun["cd_ibge"] = mun.cd_ibge.astype(str)
    pesq = pd.read_csv(RES / "pesquisas_tratadas.csv", parse_dates=["meio", "fim"])
    midia = pd.read_csv(DADOS / "midia_itens.csv") if (DADOS / "midia_itens.csv").exists() else pd.DataFrame()
    args = (DADOS / "midia_argumentos.md").read_text(encoding="utf-8") if (DADOS / "midia_argumentos.md").exists() else ""
    geo = json.load(open(DADOS / "ma_leve.geojson", encoding="utf-8"))
    hist = pd.read_csv(DADOS / "erro_historico_pesquisas.csv") if (DADOS / "erro_historico_pesquisas.csv").exists() else None
    return j("ensemble_pesquisas.json"), j("simulacao.json"), j("geo_ml.json"), mun, pesq, midia, args, geo, hist


ENS, SIM, GEO, MUN, PESQ, MIDIA, ARGS, GEOJ, HIST = carregar()
P1, P2, FIM = SIM["primeiro_turno"], SIM["segundo_turno"], SIM["resultado_final"]
pb, po = FIM["prob_braide_governador"], FIM["prob_orleans_governador"]
CX = SIM.get("cenario_ex_prefeito")
HI = SIM.get("erro_historico") or {}

st.markdown(f"""
<div class="capa">
  <div class="selo">ELEIÇÃO PARA GOVERNADOR · MARANHÃO · 4 DE OUTUBRO DE 2026 · MODELO INDEPENDENTE</div>
  <div class="titulo">Braide × Orleans: quem leva?</div>
  <div class="sub">{ENS['n_pesquisas']} pesquisas de {len(ENS['institutos'])} institutos · 6 agregadores · 5 modelos
  geográficos · {n(SIM['n_cenarios'])} cenários simulados · 217 municípios</div>
  <div class="placar">
    <div class="lado"><div class="nome">Eduardo Braide (PSD)</div><div class="prob">{pct(pb)}</div>
      <div class="leg">chance de ser eleito · 1º turno: {n(P1['braide_validos_p10_p50_p90'][1], 1)}% dos válidos</div></div>
    <div class="lado"><div class="nome">Orleans Brandão (MDB)</div><div class="prob">{pct(po)}</div>
      <div class="leg">chance de ser eleito · 1º turno: {n(P1['orleans_validos_p10_p50_p90'][1], 1)}% dos válidos</div></div>
  </div>
  {f'<div class="sub" style="margin-top:12px">⚠️ Se as pesquisas errarem como na Bahia e no Piauí em 2022 (ex-prefeito da '
   f'capital na oposição): <b>Braide {pct(CX["prob_braide_governador"])} × Orleans {pct(CX["prob_orleans_governador"])}</b>. '
   f'Veja “Cenários”.</div>' if CX else ''}
</div>
""", unsafe_allow_html=True)

SECOES = ["🏁 Veredito", "📊 Pesquisas", "🧠 Modelos", "🗺️ Mapa", "🏙️ Cidades", "🧭 Regiões", "📰 Mídia",
          "🎛️ Cenários", "ℹ️ Metodologia"]
_e = st.pills("Seção", SECOES, default=SECOES[0], selection_mode="single", label_visibility="collapsed", key="secao")
SECAO = SECOES.index(_e) if _e in SECOES else 0

# ====================================================================== 1. veredito
if SECAO == 0:
    k = st.columns(4)
    k[0].metric("Chance de 2º turno", pct(P1["prob_segundo_turno"]))
    k[1].metric("Braide liquida no 1º turno", pct(P1["prob_braide_vence_1t"]))
    k[2].metric("Braide no 2º turno (válidos)", f"{n(P2['braide_validos_p10_p50_p90'][1], 1)}%")
    k[3].metric("Braide vence se houver 2º turno", pct(P2["prob_braide_vence_se_2t"]))
    b1 = P1["braide_validos_p10_p50_p90"]
    risco = SIM.get("cenario_historico")
    st.markdown(f"""
<div class="cartao azul"><h4>O que os números dizem</h4>
Corrigido o viés de cada instituto, os seis agregadores concordam: <b>Braide tem entre {n(b1[0], 1)}% e {n(b1[2], 1)}% dos
votos válidos</b> (faixa de 80%), com centro em {n(b1[1], 1)}%. Ele está <b>no limite dos 50%</b>: a eleição pode acabar
no 1º turno, mas o mais provável é o 2º turno ({pct(P1['prob_segundo_turno'])}). No 2º turno, a rejeição de Orleans
(38% × 21%, Quaest) e a transferência dos votos de Rocha e parte de Camarão favorecem Braide.</div>

<div class="cartao laranja"><h4>A força de Orleans não aparece nas pesquisas nacionais</h4>
Orleans tem <b>174 dos 217 prefeitos</b>, mais tempo de TV, o governo com aprovação majoritária e os institutos locais
(IPSensus, Véritas, INOP, Qualitativa) mostrando-o à frente ou empatado. Os grupos que hoje o apoiam somaram
<b>72% dos votos para governador em 2022</b> (Brandão + Weverton). O modelo trata essa divergência como incerteza,
não como ruído.</div>
""", unsafe_allow_html=True)
    if risco:
        st.markdown(f"""<div class="cartao alerta"><h4>⚠️ O risco "Bahia 2022"</h4>{risco['texto']}</div>""",
                    unsafe_allow_html=True)
    fig = go.Figure()
    for nome, prob, cor in [("Braide", pb, AZUL), ("Orleans", po, LARANJA)]:
        fig.add_bar(x=[prob * 100], y=[nome], orientation="h", marker_color=cor, text=[pct(prob, 1)],
                    textposition="inside", name=nome)
    fig.update_layout(title="Chance de ser eleito governador", height=220, showlegend=False,
                      xaxis=dict(range=[0, 100], title="%"), margin=dict(t=50, b=30, l=10, r=10))
    grafico(fig)

# ====================================================================== 2. pesquisas
elif SECAO == 1:
    st.subheader("Todas as pesquisas de 1º turno (votos válidos)")
    long = PESQ.melt(id_vars=["instituto", "meio", "n"], value_vars=["braide_val", "orleans_val", "camarao_val"],
                     var_name="candidato", value_name="valido")
    long["candidato"] = long.candidato.map({"braide_val": "Braide", "orleans_val": "Orleans", "camarao_val": "Camarão"})
    fig = px.scatter(long, x="meio", y="valido", color="candidato", color_discrete_map=COR, hover_data=["instituto", "n"],
                     height=460, labels={"meio": "", "valido": "% dos votos válidos", "candidato": ""})
    for cand, cor in [("braide", AZUL), ("orleans", LARANJA)]:
        e = ENS["ensemble"][cand]
        fig.add_scatter(x=[pd.Timestamp("2026-10-04")], y=[e["est"]], mode="markers", marker=dict(size=16, color=cor,
                        symbol="star"), name=f"Consenso {cand.title()} (4/10)",
                        error_y=dict(type="data", array=[1.28 * e["dp"]], color=cor))
    fig.add_hline(y=50, line_dash="dot", line_color=CINZA, annotation_text="50% = vence no 1º turno")
    fig.update_layout(legend=dict(orientation="h", y=-0.15))
    grafico(fig)
    st.markdown("**Efeito-instituto:** quanto cada casa desvia da média das demais, em pontos de votos válidos. "
                "Positivo para Braide = a casa dá mais Braide do que o conjunto.")
    ef = pd.DataFrame({"Instituto": list(ENS["efeito_instituto"]["braide"]),
                       "Braide (pts)": list(ENS["efeito_instituto"]["braide"].values()),
                       "Orleans (pts)": [ENS["efeito_instituto"]["orleans"][k] for k in ENS["efeito_instituto"]["braide"]]})
    ef["Diferença pró-Braide (pts)"] = ef["Braide (pts)"] - ef["Orleans (pts)"]
    ef = ef.sort_values("Diferença pró-Braide (pts)")
    fig = px.bar(ef, x="Diferença pró-Braide (pts)", y="Instituto", orientation="h", height=420,
                 color="Diferença pró-Braide (pts)", color_continuous_scale=[[0, LARANJA], [0.5, "#EDEDED"], [1, AZUL]],
                 color_continuous_midpoint=0)
    fig.update_layout(coloraxis_showscale=False, title="Viés de cada instituto (corrigido no modelo)")
    grafico(fig)
    tabela(PESQ[["instituto", "fim", "n", "braide", "orleans", "camarao", "rocha", "braide_val", "orleans_val"]]
           .sort_values("fim", ascending=False).rename(columns={
               "instituto": "Instituto", "fim": "Fim do campo", "n": "Amostra", "braide": "Braide %", "orleans": "Orleans %",
               "camarao": "Camarão %", "rocha": "Rocha %", "braide_val": "Braide % válidos",
               "orleans_val": "Orleans % válidos"}).assign(**{"Fim do campo": lambda d: d["Fim do campo"].dt.strftime("%d/%m")}))

# ====================================================================== 3. modelos
elif SECAO == 2:
    st.subheader("Seis agregadores, uma pergunta: quanto cada um terá dos votos válidos em 4/10?")
    linhas = []
    for nome in ENS["modelos"]["braide"]:
        if nome.startswith("_"):
            continue
        linhas.append({"Modelo": nome, "Braide %": ENS["modelos"]["braide"][nome]["est"],
                       "± Braide": ENS["modelos"]["braide"][nome]["dp"], "Orleans %": ENS["modelos"]["orleans"][nome]["est"],
                       "± Orleans": ENS["modelos"]["orleans"][nome]["dp"]})
    df = pd.DataFrame(linhas)
    fig = go.Figure()
    fig.add_scatter(x=df["Braide %"], y=df.Modelo, mode="markers", marker=dict(size=13, color=AZUL), name="Braide",
                    error_x=dict(type="data", array=df["± Braide"], color=AZUL))
    fig.add_scatter(x=df["Orleans %"], y=df.Modelo, mode="markers", marker=dict(size=13, color=LARANJA), name="Orleans",
                    error_x=dict(type="data", array=df["± Orleans"], color=LARANJA))
    fig.add_vline(x=50, line_dash="dot", line_color=CINZA)
    fig.update_layout(height=380, xaxis_title="% dos votos válidos (1º turno)", legend=dict(orientation="h", y=-0.2))
    grafico(fig)
    tabela(df)
    a = ENS["modelos"]["braide"]["_ancora_nacionais"]["est"]
    st.markdown(f"""
<div class="cartao"><h4>Quem é a "verdade"?</h4>
Por padrão, o modelo supõe que a média dos institutos está certa. Se, em vez disso, a referência forem os institutos
nacionais (Quaest, AtlasIntel, Paraná Pesquisas, Real Time Big Data), Braide vai a <b>{n(a, 1)}%</b> dos válidos.
Se a referência fossem os institutos locais pró-Orleans, o quadro se aproximaria do empate.</div>
""", unsafe_allow_html=True)
    st.subheader("Geografia do voto: 5 modelos de aprendizado de máquina")
    g = pd.DataFrame([{"Modelo": k, "R² (validação)": v["r2_cv"], "Erro médio (pts)": v["erro_medio_pts"]}
                      for k, v in GEO.items() if not k.startswith("_")])
    tabela(g)
    st.caption("Os modelos aprendem como o mapa de 2018 (Dino) previu o de 2022 (Brandão). O R² baixo é um achado: "
               "o mapa governista se reembaralha muito entre eleições — por isso a previsão por cidade tem faixa larga.")
    st.subheader("2º turno: dois caminhos")
    c = st.columns(2)
    c[0].metric("Pelas pesquisas de 2º turno (corrigidas)", f"{n(P2['modelo_pesquisas_2t_p50'], 1)}% Braide")
    c[1].metric("Pela transferência de votos do 1º turno", f"{n(P2['modelo_transferencia_p50'], 1)}% Braide")
    t = P2["premissas_transferencia"]
    st.caption(f"Transferência: {pct(t['camarao_para_braide'])} dos eleitores de Camarão, {pct(t['rocha_para_braide'])} "
               f"dos de Rocha e {pct(t['outros_para_braide'])} dos demais iriam para Braide (com incerteza).")

# ====================================================================== 4. mapa
elif SECAO == 3:
    visao = st.radio("Mostrar", ["Braide no 2º turno (%)", "Favorito na cidade", "Apoio do prefeito",
                                 "Braide no 1º turno (%)", "Governista em 2022 (Brandão+Weverton)"], horizontal=True)
    comum = dict(geojson=GEOJ, locations="cd_ibge", featureidkey="properties.CD_MUN", hover_name="municipio",
                 map_style="carto-positron", zoom=5.3, center={"lat": -5.2, "lon": -45.2}, opacity=.8, height=640,
                 hover_data={"cd_ibge": False, "braide_2t": ":.1f", "prob_braide_vence_cidade_2t": ":.0%",
                             "prefeito_apoia": True})
    escala = [[0, LARANJA], [0.5, "#F2F2F2"], [1, AZUL]]
    if visao.startswith("Braide no 2º"):
        fig = px.choropleth_map(MUN, color="braide_2t", color_continuous_scale=escala, range_color=(30, 70), **comum)
    elif visao == "Favorito na cidade":
        fig = px.choropleth_map(MUN, color="favorito_2t", color_discrete_map=COR, **comum)
    elif visao == "Apoio do prefeito":
        fig = px.choropleth_map(MUN, color="prefeito_apoia", color_discrete_map=COR, **comum)
    elif visao.startswith("Braide no 1º"):
        fig = px.choropleth_map(MUN, color="braide_1t", color_continuous_scale=escala, range_color=(25, 70), **comum)
    else:
        MUN["gov22"] = MUN.brandao22 + MUN.weverton22
        fig = px.choropleth_map(MUN, color="gov22", color_continuous_scale=[[0, "#FFF"], [1, LARANJA]], **comum)
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), legend_title_text="")
    grafico(fig)

# ====================================================================== 5. cidades
elif SECAO == 4:
    st.subheader("Previsão para os 217 municípios")
    busca = st.text_input("Buscar município")
    d = MUN.copy()
    if busca:
        d = d[d.municipio.str.contains(busca, case=False)]
    k = st.columns(3)
    s = SIM["municipios"]
    k[0].metric("Braide favorito", s["favorito_braide"])
    k[1].metric("Orleans favorito", s["favorito_orleans"])
    k[2].metric("Indefinidos", s["indefinidos"])
    tabela(d.sort_values("validos_26_est", ascending=False)[[
        "municipio", "regiao_intermediaria", "prefeito_apoia", "validos_26_est", "braide_1t", "orleans_1t", "braide_2t",
        "braide_2t_p10", "braide_2t_p90", "prob_braide_vence_cidade_2t", "saldo_2t", "favorito_2t"]].rename(columns={
        "municipio": "Município", "regiao_intermediaria": "Região", "prefeito_apoia": "Prefeito apoia",
        "validos_26_est": "Votos válidos (est.)", "braide_1t": "Braide 1º t %", "orleans_1t": "Orleans 1º t %",
        "braide_2t": "Braide 2º t %", "braide_2t_p10": "Braide 2º t mín %", "braide_2t_p90": "Braide 2º t máx %",
        "prob_braide_vence_cidade_2t": "Prob. Braide vencer na cidade", "saldo_2t": "Saldo Braide (votos)",
        "favorito_2t": "Favorito"}))
    st.caption("Faixa mínimo–máximo = 80% dos cenários. Com R² geográfico baixo, a previsão por cidade é bem mais incerta "
               "do que a estadual: use para priorizar, não como resultado.")

# ====================================================================== 6. regiões
elif SECAO == 5:
    r = (MUN.groupby("regiao_intermediaria").agg(vb=("votos_braide_2t", "sum"), vo=("votos_orleans_2t", "sum"),
                                                 mun=("municipio", "count"),
                                                 pref_orleans=("prefeito_apoia", lambda s: (s == "Orleans").sum()))
         .reset_index())
    r["Braide 2º t %"] = 100 * r.vb / (r.vb + r.vo)
    r["Saldo Braide"] = r.vb - r.vo
    fig = px.bar(r.sort_values("Saldo Braide"), x="Saldo Braide", y="regiao_intermediaria", orientation="h",
                 color="Saldo Braide", color_continuous_scale=[[0, LARANJA], [0.5, "#EDEDED"], [1, AZUL]],
                 color_continuous_midpoint=0, height=380, labels={"regiao_intermediaria": ""})
    fig.update_layout(coloraxis_showscale=False, title="Saldo projetado de votos no 2º turno, por região")
    grafico(fig)
    tabela(r.rename(columns={"regiao_intermediaria": "Região", "vb": "Votos Braide", "vo": "Votos Orleans",
                             "mun": "Municípios", "pref_orleans": "Prefeitos com Orleans"}))

# ====================================================================== 7. mídia
elif SECAO == 6:
    st.subheader("O que a mídia e os comentários públicos dizem")
    st.markdown('<div class="cartao alerta"><h4>Leia com cuidado</h4>A blogosfera política do Maranhão é majoritariamente '
                'governista. O saldo de tom mede <b>quem escreve</b>, não necessariamente o eleitor.</div>',
                unsafe_allow_html=True)
    if len(MIDIA):
        m = MIDIA[MIDIA.candidato_alvo.isin(["Braide", "Orleans"])]
        tons = m.groupby(["candidato_alvo", "tom"]).size().reset_index(name="itens")
        fig = px.bar(tons, x="candidato_alvo", y="itens", color="tom", barmode="group", height=360,
                     color_discrete_map={"positivo": VERDE, "negativo": VERMELHO, "neutro": CINZA},
                     labels={"candidato_alvo": "", "itens": "Itens", "tom": ""})
        fig.update_layout(title=f"Tom de {len(MIDIA)} itens de mídia (ago–set/2026)")
        grafico(fig)
        temas = m.groupby(["tema", "candidato_alvo"]).size().reset_index(name="itens")
        fig = px.bar(temas, x="itens", y="tema", color="candidato_alvo", orientation="h", color_discrete_map=COR,
                     height=380, labels={"tema": "", "candidato_alvo": ""})
        fig.update_layout(title="Temas")
        grafico(fig)
        with st.expander("Todos os itens (com links)"):
            tabela(MIDIA[["data", "veiculo", "vies_veiculo", "candidato_alvo", "tom", "tema", "resumo", "url"]],
                   column_config={"url": st.column_config.LinkColumn("Link")})
    if ARGS:
        with st.expander("Argumentos pró e contra cada candidato (com fontes)", expanded=True):
            st.markdown(ARGS)

# ====================================================================== 8. cenários
elif SECAO == 7:
    st.subheader("E se…? Mexa nas premissas")
    eb, eo = ENS["ensemble"]["braide"], ENS["ensemble"]["orleans"]
    c = st.columns(3)
    vies = c[0].slider("Erro das pesquisas a favor de Orleans (pts na margem)", -10.0, 25.0,
                       float(round(HI.get("media_1t", 0.0) * 2) / 2), 0.5,
                       help="Positivo = as pesquisas subestimam Orleans (como na Bahia em 2022 com o candidato do governo)")
    t_c = c[1].slider("Eleitores de Camarão que vão para Braide no 2º turno", 0.0, 1.0, 0.5, 0.05)
    t_r = c[2].slider("Eleitores de Rocha que vão para Braide", 0.0, 1.0, 0.72, 0.05)
    rng = np.random.default_rng(1)
    N = 20000
    B1 = rng.normal(eb["est"], eb["dp"], N) - vies / 2
    O1 = rng.normal(eo["est"], eo["dp"], N) + vies / 2
    resto = np.clip(100 - B1 - O1, 3, None)
    C1, R1, X1 = resto * .55, resto * .27, resto * .18
    B2 = (B1 + t_c * C1 + t_r * R1 + .55 * X1) / (B1 + O1 + resto)
    v1 = B1 >= 50
    leva = v1 | (~v1 & (O1 < 50) & (B2 > .5))
    k = st.columns(3)
    k[0].metric("Braide vence no 1º turno", pct(v1.mean()))
    k[1].metric("Braide no 2º turno", f"{n(100 * np.median(B2), 1)}%")
    k[2].metric("Chance de Braide ser eleito", pct(leva.mean()))
    x = np.linspace(-10, 25, 71)
    probs = []
    for vv in x:
        b1 = rng.normal(eb["est"], eb["dp"], 4000) - vv / 2
        o1 = rng.normal(eo["est"], eo["dp"], 4000) + vv / 2
        rs = np.clip(100 - b1 - o1, 3, None)
        b2 = (b1 + t_c * rs * .55 + t_r * rs * .27 + .55 * rs * .18) / (b1 + o1 + rs)
        probs.append(((b1 >= 50) | ((b1 < 50) & (o1 < 50) & (b2 > .5))).mean())
    fig = go.Figure(go.Scatter(x=x, y=np.array(probs) * 100, mode="lines", line=dict(color=AZUL, width=3)))
    fig.add_hline(y=50, line_dash="dot", line_color=CINZA)
    if HI:
        for rot, val, cor in [("média Nordeste", HI["media_1t"], CINZA), ("Bahia/Piauí 2022", HI["ex_prefeito_media"], VERMELHO)]:
            fig.add_vline(x=val, line_dash="dash", line_color=cor, annotation_text=rot, annotation_position="top")
    fig.update_layout(title="Chance de Braide conforme o tamanho do erro das pesquisas", height=380,
                      xaxis_title="Erro a favor de Orleans (pts na margem Braide–Orleans)",
                      yaxis_title="Chance de Braide (%)")
    grafico(fig)
    st.caption("Aqui o erro das pesquisas é um valor fixo, escolhido por você. O número principal do painel é menor porque "
               "sorteia, em cada cenário, o erro de uma disputa real do Nordeste — inclusive os erros grandes, como Bahia 2022.")
    virada = next((xv for xv, pv in zip(x, probs) if pv < 0.5), None)
    if virada is not None:
        st.markdown(f"**Ponto de virada:** Orleans passa a favorito se as pesquisas estiverem subestimando-o em cerca de "
                    f"**{n(virada, 1)} pontos** na margem, com essas premissas de transferência.")

# ====================================================================== 9. metodologia
elif SECAO == 8:
    st.subheader("Como o modelo funciona")
    st.markdown(f"""
**Dados.** {ENS['n_pesquisas']} pesquisas de 1º turno registradas (fonte: compilação pública, conferida em portais);
resultados do TSE para governador em 2018 e 2022 por município; posicionamento público dos 217 prefeitos
(levantamento de 18/09/2026); 63 itens de mídia classificados.

**1. Agregadores de pesquisas (6).** Média ponderada; mediana robusta; regressão com efeito-instituto; filtro de Kalman;
processo gaussiano; bayesiano hierárquico (Gibbs). Todos em votos válidos, com indecisos distribuídos proporcionalmente.
O efeito-instituto mede e remove o viés sistemático de cada casa.

**2. Geografia (5 modelos de ML).** Regressão linear, Ridge, Random Forest, Gradient Boosting e KNN geográfico aprendem a
relação entre o mapa de 2018 e o de 2022, e a aplicam de 2022 para 2026.

**3. Efeitos locais.** Apoio do prefeito (efeito sorteado entre ~0,5 e 7 pontos, maior em cidades pequenas — hipótese,
não medido); São Luís calibrada pela pesquisa da capital.

**4. Monte Carlo.** {n(SIM['n_cenarios'])} cenários com incerteza das pesquisas, erro sistemático do setor, transferência de
votos no 2º turno (50% a 50% entre modelo de transferência e pesquisas de 2º turno) e ruído municipal.

**5. Erro histórico das pesquisas.** O erro sistemático não é chutado: vem de {HI.get('pesquisas', '—')} pesquisas finais em
{HI.get('corridas_1t', '—')} disputas de 1º turno e {HI.get('corridas_2t', '—')} de 2º turno para governador no Nordeste
(2014–2022). Cada cenário sorteia o erro de uma disputa real. Média no 1º turno: {n(HI.get('media_1t', 0), 1)} pts a favor do
governo (±{n(HI.get('dp_1t', 0), 0)}); no 2º turno: {n(HI.get('media_2t', 0), 1)} (±{n(HI.get('dp_2t', 0), 1)}). O cenário
"ex-prefeito da capital" usa só Bahia e Piauí 2022 ({n(HI.get('ex_prefeito_media', 0), 0)} pts).

**Limites.**
- Pesquisas locais e nacionais discordam muito; o modelo supõe que a média dos institutos está certa.
- O efeito dos prefeitos não foi medido em eleições anteriores; é uma hipótese com faixa larga.
- A geografia de uma eleição prevê mal a seguinte (R² baixo): a previsão por cidade é orientativa.
- O cenário "ex-prefeito da capital" se apoia em só 2 disputas: indica um risco real, mas não é uma regra.
- Pesquisas conferidas: {ENS.get('n_conferidas', '—')} de {ENS['n_pesquisas']}; as demais vêm de compilação pública.
""")
