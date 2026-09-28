"""Painel — Governo do Maranhão 2026: Braide × Orleans. Modelo independente de previsão.

Rodar:  streamlit run app.py  (página "Cenário Estadual MA")
Dados:  preparar_base.py → modelos_pesquisas.py → modelo_municipios_mc.py (pasta resultados/)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
from comum import CSS, barra_navegacao, caixa, grafico, n, pct, tabela  # noqa: E402,F401

RES, DADOS = RAIZ / "resultados", RAIZ / "dados"
AZUL, LARANJA, VERMELHO, VERDE, CINZA, TINTA = "#1F6FB2", "#E07B1F", "#C0392B", "#2E8B57", "#8A8F98", "#1B2A41"
COR = {"Braide": AZUL, "Orleans": LARANJA, "Camarão": VERMELHO, "Rocha": "#6B4FA0", "Indefinido": "#B8BEC8",
       "Neutro": "#B8BEC8"}
if __name__ == "__main__":  # execução isolada (streamlit run painel_governo_ma.py)
    st.set_page_config(page_title="Governo MA 2026 · Braide × Orleans", page_icon="🗳️", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


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

barra_navegacao("ma")
st.markdown(f"""
<div class="capa" style="background: linear-gradient(100deg, #1F6FB2 0%, #1B2A41 50%, #E07B1F 100%);">
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
          "🎛️ Cenários", "📚 Nossa base", "ℹ️ Metodologia"]
_e = st.pills("Seção", SECOES, default=SECOES[0], selection_mode="single", label_visibility="collapsed", key="secao_ma")
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
    sc = SIM.get("sem_correcao_historica", {})
    st.markdown("#### Três leituras, do mais otimista ao mais cauteloso para quem lidera")
    tabela(pd.DataFrame([
        {"Leitura": "Só as pesquisas (sem correção histórica)", "Chance de Braide %": 100 * sc.get("prob_braide", 0),
         "Chance de Orleans %": 100 * (1 - sc.get("prob_braide", 0))},
        {"Leitura": "Modelo principal: viés histórico com persistência incerta (0 a 100%)",
         "Chance de Braide %": 100 * pb, "Chance de Orleans %": 100 * po},
        {"Leitura": "Alerta: repete o padrão Bahia/Piauí 2022 por inteiro",
         "Chance de Braide %": 100 * CX["prob_braide_governador"], "Chance de Orleans %": 100 * CX["prob_orleans_governador"]},
    ]))
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
    t = P2["transferencia_medida"]
    st.caption(f"Transferência medida em {t['pares']} pesquisas que perguntaram 1º e 2º turno na mesma entrevista: "
               f"{pct(t['braide'])} dos eleitores de Camarão, Rocha e demais vão para Braide (±{pct(t['dp'])}). "
               "O 2º turno usa os mesmos 6 agregadores do 1º turno.")

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
    c = st.columns(2)
    vies = c[0].slider("Erro das pesquisas a favor de Orleans (pts na margem)", -10.0, 25.0,
                       float(round(HI.get("media_1t", 0.0) * 2) / 2), 0.5,
                       help="Positivo = as pesquisas subestimam Orleans (como na Bahia em 2022 com o candidato do governo). "
                            "Vale para os dois turnos.")
    tm = P2["transferencia_medida"]["braide"]
    t_o = c[1].slider("Eleitores dos demais candidatos que vão para Braide no 2º turno", 0.0, 1.0,
                      float(round(tm * 20) / 20), 0.05, help=f"Valor medido nas pesquisas: {pct(tm)}")
    rng = np.random.default_rng(1)

    def simular(v, n_=20000):
        b0 = rng.normal(eb["est"], eb["dp"], n_)
        o0 = rng.normal(eo["est"], eo["dp"], n_)
        b1, o1 = b0 - v / 2, o0 + v / 2
        b2 = (b0 + t_o * np.clip(100 - b0 - o0, 3, None)) / 100 - v / 200  # 2º turno herda o mesmo erro
        return b1, o1, b2, (b1 >= 50) | ((b1 < 50) & (o1 < 50) & (b2 > .5))

    B1, O1, B2, leva = simular(vies)
    v1 = B1 >= 50
    k = st.columns(3)
    k[0].metric("Braide vence no 1º turno", pct(v1.mean()))
    k[1].metric("Braide no 2º turno", f"{n(100 * np.median(B2), 1)}%")
    k[2].metric("Chance de Braide ser eleito", pct(leva.mean()))
    x = np.linspace(-10, 25, 71)
    probs = []
    for vv in x:
        probs.append(simular(vv, 4000)[3].mean())
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

# ====================================================================== 9. nossa base (linguagem simples)
elif SECAO == 8:
    ver = pd.read_csv(DADOS / "pesquisas_verificadas.csv")
    rec = pd.read_csv(DADOS / "pesquisas_recortes_regionais.csv")
    pref = pd.read_csv(DADOS / "prefeitos_apoio_governo_2026.csv")
    n_conf = int((PESQ.origem == "conferida").sum())
    n_futuras = int((ver.status == "nao_confirmada").sum())
    n_disputas = HI.get("corridas_1t", 0) + HI.get("corridas_2t", 0)
    st.subheader("Em que se apoia esta previsão")
    st.markdown("Tudo aqui é público e verificável. Abaixo, cada fonte em poucas frases, com números e links.")

    k = st.columns(4)
    k[0].metric("Pesquisas analisadas", len(PESQ), f"{n_conf} conferidas em 2ª fonte", delta_color="off")
    k[1].metric("Institutos", PESQ.instituto.nunique())
    k[2].metric("Pesquisas históricas × urna", HI.get("pesquisas", 0), f"{n_disputas} disputas no Nordeste",
                delta_color="off")
    k[3].metric("Cenários simulados", n(SIM["n_cenarios"]), "+ 20 mil no cenário de alerta", delta_color="off")

    st.markdown(f"""
### 1. O que o eleitor diz: as pesquisas
- Reunimos **{len(PESQ)} pesquisas de 1º turno** de **{PESQ.instituto.nunique()} institutos**, de março a setembro de 2026.
- **{n_conf} foram conferidas** em uma segunda fonte (jornais, relatórios dos institutos e registro no TSE/PesqEle).
  Na conferência achamos e corrigimos **números errados** que circulavam: por exemplo, brancos, nulos e indecisos da
  Quaest de setembro somam 12%, e não 1%.
- Os institutos **discordam muito**: alguns dão Braide 20 pontos à frente, outros dão Orleans na frente. Em vez de escolher
  um lado, **medimos o viés de cada instituto** (quanto cada um costuma puxar para um candidato) e o descontamos.
- Olhamos também **quem pagou e como foi feita** cada pesquisa: os levantamentos que põem Orleans à frente vêm dos mesmos
  poucos contratantes; a Quaest usa sorteio de domicílios, o método mais rigoroso.
- Há ainda **{n_futuras} pesquisas registradas** que não foram divulgadas ou sairão até 3/10. O modelo será atualizado
  quando saírem.

### 2. Como cada região pensa
- Recortes por região da pesquisa **IPPI** (Norte, Oeste, Leste, Centro, Sul) e pesquisas só de **São Luís** (800
  entrevistas) e **Imperatriz** (350), do IPSensus.
- Comparamos cada região **com o estado na mesma pesquisa**, o que anula o viés do instituto. Resultado: Braide vence pela
  Grande Ilha; no interior o jogo é equilibrado ou favorável a Orleans.

### 3. O que as urnas já mostraram: histórico oficial do TSE
- Votação para governador de **2018 e 2022 em todos os 217 municípios** (dados oficiais do Tribunal Superior Eleitoral).
- Em 2022, os grupos que hoje apoiam Orleans (Brandão + Weverton) somaram **72% dos votos válidos**. Isso mostra o tamanho
  da máquina política, e por que a liderança de Braide nas pesquisas chama a atenção.

### 4. Quanto as pesquisas já erraram no Nordeste
- Comparamos **{HI.get('pesquisas', 0)} pesquisas finais** com o resultado das urnas em **{HI.get('corridas_1t', 0)} disputas
  de 1º turno e {HI.get('corridas_2t', 0)} de 2º turno** para governador (2014, 2018 e 2022, nos 9 estados do Nordeste).
- Em média, as pesquisas **subestimaram o candidato do governo em {n(HI.get('media_1t', 0), 1)} pontos** na diferença
  entre os dois.
- Nos casos parecidos com o nosso, com a oposição liderada por um **ex-prefeito da capital** (Bahia e Piauí 2022), o erro
  foi de **{n(HI.get('ex_prefeito_media', 0), 0)} pontos**. Por isso mostramos sempre os dois cenários.
- **Cada um dos {n(SIM['n_cenarios'])} cenários sorteia o erro de uma disputa real.** Não é chute: é o que já aconteceu.

### 5. Quem está com quem: os prefeitos
- Levantamento público do posicionamento dos **217 prefeitos** (18/09/2026):
  **{int((pref.prefeito_apoia == 'Orleans').sum())} com Orleans**, **{int((pref.prefeito_apoia == 'Braide').sum())} com Braide**
  e {int((pref.prefeito_apoia == 'Neutro').sum())} sem posição.
- Entra no modelo como vantagem para o candidato do prefeito, maior nas cidades pequenas.

### 6. O que a mídia e os comentários públicos dizem
- **{len(MIDIA)} notícias e comentários** de **{MIDIA.veiculo.nunique() if len(MIDIA) else 0} veículos** (agosto e setembro),
  cada um classificado como positivo, negativo ou neutro, com link. Serve para entender os argumentos de cada lado e
  **não entra no cálculo** da chance, porque a maior parte da blogosfera local é governista e distorceria o resultado.

### 7. Os modelos: uma "segunda opinião" de cada método
- **6 formas diferentes de ler as pesquisas** (média ponderada, mediana, regressão com viés de instituto, filtro de Kalman,
  processo gaussiano e modelo bayesiano). Todas chegam a números próximos: Braide entre
  {n(ENS['ensemble']['braide']['min_modelos'], 1)}% e {n(ENS['ensemble']['braide']['max_modelos'], 1)}% dos votos válidos.
- **5 modelos de aprendizado de máquina** para a geografia do voto (regressão linear, Ridge, Random Forest, Gradient
  Boosting e vizinhos mais próximos).
- **{n(SIM['n_cenarios'])} simulações** da eleição inteira, 1º e 2º turno, mais {n(4000 * len(MUN))} resultados municipais.
""")

    st.markdown("### Por que esta análise é confiável")
    st.markdown(f"""
<div class="cartao azul"><h4>✔ Não depende de um único instituto</h4>Usa todos os que divulgaram e corrige o viés de cada um.</div>
<div class="cartao azul"><h4>✔ Números conferidos</h4>{n_conf} pesquisas checadas em segunda fonte, com erros corrigidos.</div>
<div class="cartao azul"><h4>✔ Aprende com os erros do passado</h4>Usa quanto as pesquisas realmente erraram em {n_disputas} eleições do Nordeste.</div>
<div class="cartao azul"><h4>✔ Vários métodos concordam</h4>Seis agregadores independentes chegam a resultados com menos de 1,5 ponto de diferença.</div>
<div class="cartao laranja"><h4>✔ Mostra o risco, não esconde</h4>Traz lado a lado o cenário principal e o de alerta (padrão Bahia/Piauí), e diz em que ponto o favorito muda.</div>
""", unsafe_allow_html=True)

    st.markdown("### O que ainda não sabemos")
    st.markdown("""
- **Pesquisas que ainda vão sair** até 3/10 (Quaest, AtlasIntel, Econométrica e outras).
- **O último debate** (TV Mirante, 29/09).
- **O peso real do apoio dos prefeitos**, que nunca foi medido em eleições anteriores: é uma estimativa com faixa larga.
- **A previsão por cidade** é orientativa: o voto de cada município muda muito de uma eleição para outra.
""")

    link = {"Fonte": st.column_config.LinkColumn("Fonte")}
    with st.expander("📋 Lista de pesquisas (instituto, datas, quem pagou, método e situação)"):
        cols = [c for c in ["instituto", "fim", "amostra", "contratante", "metodo", "braide", "orleans", "status",
                            "fonte_url"] if c in ver.columns]
        tabela(ver[ver.turno == 1][cols].sort_values("fim", ascending=False).rename(columns={
            "instituto": "Instituto", "fim": "Fim do campo", "amostra": "Entrevistas", "contratante": "Quem pagou",
            "metodo": "Método", "braide": "Braide %", "orleans": "Orleans %", "status": "Situação",
            "fonte_url": "Fonte"}), column_config=link)
    with st.expander("📋 Recortes regionais"):
        tabela(rec[["instituto", "fim", "recorte", "braide", "orleans", "base", "fonte_url"]].rename(columns={
            "instituto": "Instituto", "fim": "Fim", "recorte": "Recorte", "braide": "Braide %", "orleans": "Orleans %",
            "base": "Base", "fonte_url": "Fonte"}), column_config=link)
    if HIST is not None:
        with st.expander("📋 Histórico: pesquisas finais × urnas no Nordeste (2014–2022)"):
            tabela(HIST[["ano", "uf", "turno", "candidato_governo", "candidato_oposicao", "instituto", "pesq_governo",
                         "pesq_oposicao", "urna_governo_validos", "urna_oposicao_validos", "fonte_url"]].rename(columns={
                "ano": "Ano", "uf": "UF", "turno": "Turno", "candidato_governo": "Candidato do governo",
                "candidato_oposicao": "Oposição", "instituto": "Instituto", "pesq_governo": "Pesquisa governo %",
                "pesq_oposicao": "Pesquisa oposição %", "urna_governo_validos": "Urna governo %",
                "urna_oposicao_validos": "Urna oposição %", "fonte_url": "Fonte"}), column_config=link)
    with st.expander("📋 Prefeitos: posição de cada um"):
        tabela(pref[["municipio", "prefeito_apoia"]].sort_values(["prefeito_apoia", "municipio"]).rename(
            columns={"municipio": "Município", "prefeito_apoia": "Apoia"}))
    st.caption("Dados oficiais do TSE (votação por município). Demais fontes com link em cada tabela. "
               "Arquivos completos na pasta dados/ do projeto.")

# ====================================================================== 10. metodologia
elif SECAO == 9:
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

**4. Monte Carlo.** O erro histórico sorteado é multiplicado por uma persistência incerta (0 a 100%) e vale para os
dois turnos; a transferência de votos para o 2º turno é **medida** nas pesquisas que perguntaram os dois turnos.
Detalhes: {n(SIM['n_cenarios'])} cenários com incerteza das pesquisas, erro sistemático do setor, transferência de
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
