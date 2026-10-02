"""Página — Cenário Nacional: Lula × Flávio Bolsonaro (mesma estrutura do cenário estadual).

Dados: preparar_base_nacional.py → modelos_pesquisas_nacional.py → modelo_ufs_mc.py (pasta nacional/resultados/)
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
sys.path.insert(0, str(RAIZ.parent))
sys.path.insert(0, str(RAIZ))
from validacao_modelo import decidir
from comum import CSS, barra_navegacao, grafico, n, pct, tabela, veredito_simples  # noqa: E402

RES, DADOS = RAIZ / "resultados", RAIZ / "dados"
VERM, AZUL, CINZA, VERDE, AMAR = "#C8102E", "#1D4E89", "#8A8F98", "#1F7A4D", "#F2A900"
COR = {"Lula": VERM, "Flávio": AZUL, "Indefinido": "#B8BEC8", "Neutro": "#B8BEC8"}
if __name__ == "__main__":
    st.set_page_config(page_title="Nacional 2026 · Lula × Flávio", page_icon="🗳️", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(ttl=60)
def carregar():
    j = lambda f: json.load(open(RES / f, encoding="utf-8"))
    ufs = pd.read_csv(RES / "ufs_previsao.csv")
    pesq = pd.read_csv(RES / "pesquisas_nacionais_tratadas.csv", parse_dates=["meio", "fim"])
    ler = lambda f: pd.read_csv(DADOS / f) if (DADOS / f).exists() else pd.DataFrame()
    args = (DADOS / "midia_nacional_argumentos.md").read_text(encoding="utf-8") \
        if (DADOS / "midia_nacional_argumentos.md").exists() else ""
    geo = json.load(open(DADOS / "br_ufs.json", encoding="utf-8"))
    return (j("ensemble_nacional.json"), j("simulacao_nacional.json"), j("geo_ml_nacional.json"), ufs, pesq,
            ler("midia_nacional.csv"), args, geo, ler("erro_historico_presidente.csv"),
            ler("governadores_apoio_2026.csv"), ler("pesquisas_presidente.csv"), ler("pesquisas_presidente_regioes.csv"),
            ler("indicadores_nacionais.csv"))


ENS, SIM, GEO, UFS, PESQ, MIDIA, ARGS, GEOJ, HIST, GOV, PRAW, PREG, IND = carregar()
st.warning("Modelo experimental: validade preditiva pendente de backtest temporal. As probabilidades dependem das premissas; efeitos estaduais redistribuem o total nacional. Exterior não incluído.")
st.caption(f"Corte dos dados: {SIM.get('data_corte', 'não registrado')}")
P1, P2, FIM, ALR, HI = SIM["primeiro_turno"], SIM["segundo_turno"], SIM["resultado_final"], SIM["cenario_alerta"], \
    SIM["erro_historico"]
pl, pf = FIM["prob_lula_presidente"], FIM["prob_flavio_presidente"]
N1 = ENS["n_pesquisas_1t"]

barra_navegacao("br")
st.markdown(f"""
<div class="capa" style="background: linear-gradient(100deg, #C8102E 0%, #1B2A41 50%, #1D4E89 100%);">
  <div class="selo">ELEIÇÃO PRESIDENCIAL · BRASIL · 4 DE OUTUBRO DE 2026 · MODELO INDEPENDENTE</div>
  <div class="titulo">Lula × Flávio Bolsonaro: quem leva?</div>
  <div class="sub">{N1} pesquisas de 1º turno e {ENS['n_pesquisas_2t']} de 2º turno · {len(ENS['institutos'])} institutos ·
  6 agregadores · 5 modelos geográficos · {n(SIM['n_cenarios'])} cenários · 27 estados</div>
  <div class="placar">
    <div class="lado"><div class="nome">Lula (PT)</div><div class="prob">{pct(pl)}</div>
      <div class="leg">chance de ser eleito · 1º turno: {n(P1['lula_validos_p10_p50_p90'][1], 1)}% dos válidos</div></div>
    <div class="lado"><div class="nome">Flávio Bolsonaro (PL)</div><div class="prob">{pct(pf)}</div>
      <div class="leg">chance de ser eleito · 1º turno: {n(P1['flavio_validos_p10_p50_p90'][1], 1)}% dos válidos</div></div>
  </div>
  <div class="sub" style="margin-top:12px">⚠️ Se as pesquisas errarem exatamente como em 2022 (direita subestimada):
  <b>Lula {pct(ALR['prob_lula_presidente'])} × Flávio {pct(ALR['prob_flavio_presidente'])}</b>. Veja “Cenários”.</div>
</div>
""", unsafe_allow_html=True)

st.info(
    f"**Como ler estes números:**\n\n"
    f"• **Chance de vitória:** em 100 eleições simuladas pelo modelo, Lula vence cerca de {pct(pl).replace('%', '')} "
    f"e Flávio cerca de {pct(pf).replace('%', '')}. Isso não é a porcentagem de votos nem uma garantia.\n\n"
    f"• **Projeção de votos:** no segundo turno, o centro da estimativa é Lula com "
    f"{n(P2['lula_validos_p10_p50_p90'][1], 1)}% e Flávio com "
    f"{n(100 - P2['lula_validos_p10_p50_p90'][1], 1)}% dos votos válidos "
    f"(excluem brancos e nulos). Um placar apertado pode dar chances de vitória diferentes.\n\n"
    "**Faixa de 80%:** reúne os 80% centrais dos resultados simulados; o resultado real pode ficar fora dela. "
    "As pesquisas alimentam o cálculo, que também considera erros históricos e hipóteses. "
    "Novos dados podem mudar as estimativas."
)

SECOES = ["🏁 Veredito", "📊 Pesquisas", "🧠 Modelos", "🗺️ Mapa", "🏙️ Estados", "🧭 Regiões", "📰 Mídia",
          "🎛️ Cenários", "📚 Nossa base", "ℹ️ Metodologia"]
_e = st.pills("Seção", SECOES, default=SECOES[0], selection_mode="single", label_visibility="collapsed", key="secao_br")
SECAO = SECOES.index(_e) if _e in SECOES else 0

# ====================================================================== veredito
if SECAO == 0:
    veredito_simples("Lula", "Flávio", VERM, AZUL, P1["prob_segundo_turno"], P1["prob_lula_vence_1t"],
                     P2["lula_validos_p10_p50_p90"][1], pl)
    l1, f1 = P1["lula_validos_p10_p50_p90"], P1["flavio_validos_p10_p50_p90"]
    lider = "Lula" if pl >= pf else "Flávio"
    st.markdown(f"""
<div class="cartao vermelho"><h4>O que os números dizem</h4>
Corrigido o viés de cada instituto, os seis agregadores apontam Lula com <b>{n(l1[1], 1)}%</b> dos votos válidos no
1º turno (faixa de 80%: {n(l1[0], 1)}% a {n(l1[2], 1)}%) e Flávio com <b>{n(f1[1], 1)}%</b> ({n(f1[0], 1)}% a {n(f1[2], 1)}%).
A chance de a eleição ir ao 2º turno é de <b>{pct(P1['prob_segundo_turno'])}</b>. No 2º turno, o modelo projeta Lula com
<b>{n(P2['lula_validos_p10_p50_p90'][1], 1)}%</b>. Favorito hoje: <b>{lider}</b>.</div>

<div class="cartao azul"><h4>Como o erro histórico entra no resultado</h4>
O primeiro turno usa erros observados de primeiro turno. O segundo usa erros observados de pesquisas finais
 de segundo turno, com persistência sorteada entre 0% e 100%. Essa persistência é uma hipótese ainda não calibrada
 em backtest temporal. O cenário de alerta usa o erro de 2022. Favorito neste cálculo: <b>{lider}</b>.</div>
""", unsafe_allow_html=True)
    sc = SIM.get("sem_correcao_historica", {})
    st.markdown("#### Três cenários com premissas diferentes")
    tabela(pd.DataFrame([
        {"Leitura": "Pesquisas e transferência implícita (sem correção histórica)", "Chance de Lula %": 100 * sc.get("prob_lula", 0),
         "Chance de Flávio %": 100 * (1 - sc.get("prob_lula", 0))},
        {"Leitura": "Modelo principal: viés histórico com persistência incerta (0 a 100%)",
         "Chance de Lula %": 100 * pl, "Chance de Flávio %": 100 * pf},
        {"Leitura": "Alerta: repete o erro de 2022 por inteiro",
         "Chance de Lula %": 100 * ALR["prob_lula_presidente"], "Chance de Flávio %": 100 * ALR["prob_flavio_presidente"]},
    ]))
    fig = go.Figure()
    for nome, prob, cor in [("Lula", pl, VERM), ("Flávio", pf, AZUL)]:
        fig.add_bar(x=[prob * 100], y=[nome], orientation="h", marker_color=cor, text=[pct(prob, 1)],
                    textposition="inside")
    fig.update_layout(title="Chance de ser eleito presidente", height=220, showlegend=False,
                      xaxis=dict(range=[0, 100], title="%"), margin=dict(t=50, b=30, l=10, r=10))
    grafico(fig)

# ====================================================================== pesquisas
elif SECAO == 1:
    st.subheader("Pesquisas de 1º turno (votos válidos)")
    p1 = PESQ[PESQ.turno == 1]
    long = p1.melt(id_vars=["instituto", "meio", "n"], value_vars=["lula_val", "flavio_val"], var_name="c",
                   value_name="valido")
    long["c"] = long.c.map({"lula_val": "Lula", "flavio_val": "Flávio"})
    fig = px.scatter(long, x="meio", y="valido", color="c", color_discrete_map=COR, hover_data=["instituto", "n"],
                     height=460, labels={"meio": "", "valido": "% dos votos válidos", "c": ""})
    for cand, nome, cor in [("lula_1t", "Lula", VERM), ("flavio_1t", "Flávio", AZUL)]:
        e = ENS["ensemble"][cand]
        fig.add_scatter(x=[pd.Timestamp("2026-10-04")], y=[e["est"]], mode="markers",
                        marker=dict(size=16, color=cor, symbol="star"), name=f"Consenso {nome} (4/10)",
                        error_y=dict(type="data", array=[1.28 * e["dp"]], color=cor))
    fig.add_hline(y=50, line_dash="dot", line_color=CINZA, annotation_text="Mais de 50% = vence no 1º turno")
    fig.update_layout(legend=dict(orientation="h", y=-0.15))
    grafico(fig)
    p2 = PESQ[PESQ.turno == 2]
    if len(p2):
        fig = px.scatter(p2, x="meio", y="lula_2p", color="instituto", height=380,
                         labels={"meio": "", "lula_2p": "Lula no 2º turno (% dos válidos)", "instituto": ""})
        fig.add_hline(y=50, line_dash="dot", line_color=CINZA)
        fig.update_layout(title="Pesquisas de 2º turno: Lula × Flávio", legend=dict(orientation="h", y=-0.2))
        grafico(fig)
    ef = ENS["efeito_instituto"]
    dfe = pd.DataFrame({"Instituto": list(ef["lula_1t"]),
                        "Diferença pró-Lula (pts)": [ef["lula_1t"][k] - ef["flavio_1t"].get(k, 0) for k in ef["lula_1t"]]})
    dfe = dfe.sort_values("Diferença pró-Lula (pts)")
    fig = px.bar(dfe, x="Diferença pró-Lula (pts)", y="Instituto", orientation="h", height=max(320, 26 * len(dfe)),
                 color="Diferença pró-Lula (pts)", color_continuous_scale=[[0, AZUL], [0.5, "#EDEDED"], [1, VERM]],
                 color_continuous_midpoint=0)
    fig.update_layout(coloraxis_showscale=False, title="Efeito relativo de instituto (não equivale a erro frente à urna)")
    grafico(fig)

# ====================================================================== modelos
elif SECAO == 2:
    st.subheader("Seis agregadores (os mesmos do cenário estadual)")
    linhas = []
    for nome in ENS["modelos"]["lula_1t"]:
        if nome.startswith("_"):
            continue
        linha = {"Modelo": nome, "Lula 1º t %": ENS["modelos"]["lula_1t"][nome]["est"],
                 "Flávio 1º t %": ENS["modelos"]["flavio_1t"][nome]["est"]}
        if "lula_2t" in ENS["modelos"]:
            linha["Lula 2º t %"] = ENS["modelos"]["lula_2t"][nome]["est"]
        linhas.append(linha)
    df = pd.DataFrame(linhas)
    fig = go.Figure()
    fig.add_scatter(x=df["Lula 1º t %"], y=df.Modelo, mode="markers", marker=dict(size=13, color=VERM), name="Lula 1º t")
    fig.add_scatter(x=df["Flávio 1º t %"], y=df.Modelo, mode="markers", marker=dict(size=13, color=AZUL), name="Flávio 1º t")
    if "Lula 2º t %" in df:
        fig.add_scatter(x=df["Lula 2º t %"], y=df.Modelo, mode="markers", marker=dict(size=13, color=VERM, symbol="diamond"),
                        name="Lula 2º t")
    fig.add_vline(x=50, line_dash="dot", line_color=CINZA)
    fig.update_layout(height=380, xaxis_title="% dos votos válidos", legend=dict(orientation="h", y=-0.2))
    grafico(fig)
    tabela(df)
    if ENS.get("ancora"):
        a = ENS["modelos"]["lula_1t"].get("_ancora", {}).get("est")
        st.markdown(f'<div class="cartao"><h4>E se a referência forem os institutos que mais acertaram em 2022?</h4>'
                    f'Usando {", ".join(ENS["ancora"])} como referência do viés, Lula fica com <b>{n(a, 1)}%</b> dos válidos '
                    f'no 1º turno.</div>', unsafe_allow_html=True)
    st.subheader("Geografia do voto: os mesmos 5 modelos de aprendizado de máquina, por estado")
    tabela(pd.DataFrame([{"Modelo": k, "R² (validação)": v["r2_cv"], "Erro médio (pts)": v["erro_medio_pts"]}
                         for k, v in GEO.items() if not k.startswith("_")]))
    st.caption("Aprendem como o mapa de 2018 (Haddad) previu o de 2022 (Lula), estado a estado. Diferente do Maranhão, "
               "a validação deixa uma região de fora a cada rodada e não comprova desempenho em uma eleição futura.")
    c = st.columns(2)
    c[0].metric("2º turno pelas pesquisas de 2º turno", f"{n(P2['modelo_pesquisas_2t_p50'], 1)}% Lula")
    c[1].metric("Transferência implícita / fallback", f"{n(P2['modelo_transferencia_p50'], 1)}% Lula")

# ====================================================================== mapa
elif SECAO == 3:
    visao = st.radio("Mostrar", ["Lula no 2º turno (%)", "Favorito no estado", "Governador apoia", "Lula no 1º turno (%)",
                                 "Lula em 2022 (2º turno)"], horizontal=True)
    comum = dict(geojson=GEOJ, locations="uf", featureidkey="properties.uf", hover_name="uf", map_style="carto-positron",
                 zoom=2.8, center={"lat": -14.5, "lon": -52}, opacity=.8, height=640,
                 hover_data={"uf": False, "lula_2t": ":.1f", "prob_lula_vence_uf_2t": ":.0%", "governador_apoia": True})
    esc = [[0, AZUL], [0.5, "#F2F2F2"], [1, VERM]]
    if visao.startswith("Lula no 2º"):
        fig = px.choropleth_map(UFS, color="lula_2t", color_continuous_scale=esc, range_color=(25, 75), **comum)
    elif visao == "Favorito no estado":
        fig = px.choropleth_map(UFS, color="favorito_2t", color_discrete_map=COR, **comum)
    elif visao == "Governador apoia":
        g = UFS.assign(gov=UFS.governador_apoia.map(lambda s: "Lula" if "lula" in str(s).lower()
                                                    else ("Flávio" if "fl" in str(s).lower() else "Neutro")))
        fig = px.choropleth_map(g, color="gov", color_discrete_map=COR, **comum)
    elif visao.startswith("Lula no 1º"):
        fig = px.choropleth_map(UFS, color="lula_1t", color_continuous_scale=esc, range_color=(20, 75), **comum)
    else:
        fig = px.choropleth_map(UFS, color="lula22_2t", color_continuous_scale=esc, range_color=(25, 75), **comum)
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), legend_title_text="")
    grafico(fig)

# ====================================================================== estados
elif SECAO == 4:
    s = SIM["estados"]
    k = st.columns(3)
    k[0].metric("Lula favorito", s["favorito_lula"])
    k[1].metric("Flávio favorito", s["favorito_flavio"])
    k[2].metric("Indefinidos", s["indefinidos"])
    tabela(UFS.sort_values("validos_26_est", ascending=False)[[
        "uf", "regiao", "governador_apoia", "validos_26_est", "lula22_2t", "lula_1t", "flavio_1t", "lula_2t", "lula_2t_p10",
        "lula_2t_p90", "prob_lula_vence_uf_2t", "saldo_lula_2t", "favorito_2t"]].rename(columns={
        "uf": "UF", "regiao": "Região", "governador_apoia": "Governador (2º t)", "validos_26_est": "Votos válidos (est.)",
        "lula22_2t": "Lula 2022 %", "lula_1t": "Lula 1º t %", "flavio_1t": "Flávio 1º t %", "lula_2t": "Lula 2º t %",
        "lula_2t_p10": "Lula 2º t P10 %", "lula_2t_p90": "Lula 2º t P90 %", "prob_lula_vence_uf_2t": "Prob. Lula no estado",
        "saldo_lula_2t": "Saldo Lula (votos)", "favorito_2t": "Favorito"}))
    st.caption("A eleição presidencial é decidida pelo total nacional de votos; o resultado por estado mostra de onde vem cada voto.")

# ====================================================================== regiões
elif SECAO == 5:
    r = UFS.groupby("regiao").agg(vl=("votos_lula_2t", "sum"), vf=("votos_flavio_2t", "sum")).reset_index()
    r["Lula 2º t %"] = 100 * r.vl / (r.vl + r.vf)
    r["Saldo Lula"] = r.vl - r.vf
    fig = px.bar(r.sort_values("Saldo Lula"), x="Saldo Lula", y="regiao", orientation="h", color="Saldo Lula",
                 color_continuous_scale=[[0, AZUL], [0.5, "#EDEDED"], [1, VERM]], color_continuous_midpoint=0, height=360,
                 labels={"regiao": ""})
    fig.update_layout(coloraxis_showscale=False, title="Saldo projetado de votos no 2º turno, por região")
    grafico(fig)
    tabela(r.rename(columns={"regiao": "Região", "vl": "Votos Lula", "vf": "Votos Flávio"}))

# ====================================================================== mídia
elif SECAO == 6:
    st.subheader("O que a mídia nacional diz")
    if len(MIDIA):
        m = MIDIA[MIDIA.candidato_alvo.isin(["Lula", "Flávio"])]
        tons = m.groupby(["candidato_alvo", "tom"]).size().reset_index(name="itens")
        fig = px.bar(tons, x="candidato_alvo", y="itens", color="tom", barmode="group", height=360,
                     color_discrete_map={"positivo": VERDE, "negativo": VERM, "neutro": CINZA},
                     labels={"candidato_alvo": "", "itens": "Itens", "tom": ""})
        fig.update_layout(title=f"Tom de {len(MIDIA)} itens de mídia nacional (ago–set/2026)")
        grafico(fig)
        temas = m.groupby(["tema", "candidato_alvo"]).size().reset_index(name="itens")
        fig = px.bar(temas, x="itens", y="tema", color="candidato_alvo", orientation="h", color_discrete_map=COR,
                     height=400, labels={"tema": "", "candidato_alvo": ""})
        fig.update_layout(title="Temas")
        grafico(fig)
        with st.expander("Todos os itens (com links)"):
            tabela(MIDIA[["data", "veiculo", "vies_veiculo", "candidato_alvo", "tom", "tema", "resumo", "url"]],
                   column_config={"url": st.column_config.LinkColumn("Link")})
    else:
        st.info("Levantamento de mídia nacional em andamento.")
    if ARGS:
        with st.expander("Argumentos pró e contra cada candidato (com fontes)", expanded=True):
            st.markdown(ARGS)

# ====================================================================== cenários
elif SECAO == 7:
    st.subheader("E se…? Mexa nas premissas")
    el, ef_ = ENS["ensemble"]["lula_1t"], ENS["ensemble"]["flavio_1t"]
    c = st.columns(2)
    vies = c[0].slider("Erro das pesquisas a favor de Flávio (pts na margem)", -10.0, 15.0,
                       float(round(-HI["media_1t"] * 2) / 2), 0.5,
                       help="Positivo = as pesquisas subestimam Flávio (como Bolsonaro em 2018 e 2022)")
    tm = P2["transferencia_medida"]["lula"]
    if tm is None:
        st.info("Sem pares suficientes para transferência: simulador indisponível.")
        st.stop()
    t_o = c[1].slider("Eleitores dos demais candidatos que vão para Lula no 2º turno", 0.0, 1.0,
                      float(round(tm * 20) / 20), 0.05, help=f"Valor medido nas pesquisas: {pct(tm)}")
    rng = np.random.default_rng(1)
    cov = [[el["dp"]**2, -.5*el["dp"]*ef_["dp"]], [-.5*el["dp"]*ef_["dp"], ef_["dp"]**2]]
    sorteios = rng.multivariate_normal([el["est"], ef_["est"]], cov, 20000)

    def simular(v, n_=20000):
        l0, f0 = sorteios[:n_, 0], sorteios[:n_, 1]
        l1, f1 = np.clip(l0-v/2, 0, 100), np.clip(f0+v/2, 0, 100)
        resto = np.clip(100-l1-f1, 0, None)
        total = l1+f1+resto
        l1, f1 = 100*l1/total, 100*f1/total
        l2 = np.clip((l0+t_o*np.clip(100-l0-f0, 0, None))/100-v/200, 0, 1)
        return decidir(l1, f1, l2)[3].mean()

    x = np.linspace(-10, 20, 61)
    probs = [simular(vv) for vv in x]
    atual = simular(vies, 20000)
    st.metric("Chance de Lula com essas premissas", pct(atual))
    fig = go.Figure(go.Scatter(x=x, y=np.array(probs) * 100, mode="lines", line=dict(color=VERM, width=3)))
    fig.add_hline(y=50, line_dash="dot", line_color=CINZA)
    for rot, val, cor in [("média 1º turno 2006–2022", -HI["media_1t"], CINZA),
                          ("2º turno antecipado 2022", -HI["erro_2t_antecipado_2022"], AZUL)]:
        fig.add_vline(x=val, line_dash="dash", line_color=cor, annotation_text=rot, annotation_position="top")
    fig.update_layout(title="Chance de Lula conforme o erro das pesquisas", height=380,
                      xaxis_title="Erro a favor de Flávio (pts na margem Lula–Flávio)", yaxis_title="Chance de Lula (%)")
    grafico(fig)
    virada = next((xv for xv, pv in zip(x, probs) if pv < 0.5), None)
    if virada is not None:
        st.markdown(f"**Ponto de virada:** Flávio passa a favorito se as pesquisas estiverem subestimando-o em cerca de "
                    f"**{n(virada, 1)} pontos** na margem.")
    st.caption("Este simulador usa apenas transferência implícita e erro fixo; não reproduz integralmente o modelo principal. O modelo principal sorteia o erro de uma "
               "eleição presidencial real (2006–2022).")

# ====================================================================== nossa base
elif SECAO == 8:
    n_conf = ENS.get("n_conferidas", 0)
    st.subheader("Em que se apoia esta previsão")
    k = st.columns(4)
    k[0].metric("Pesquisas analisadas", N1 + ENS["n_pesquisas_2t"], f"{n_conf} conferidas em 2ª fonte", delta_color="off")
    k[1].metric("Institutos", len(ENS["institutos"]))
    k[2].metric("Pesquisas históricas × urna", HI["pesquisas"], f"eleições {', '.join(map(str, HI['eleicoes']))}",
                delta_color="off")
    k[3].metric("Cenários simulados", n(SIM["n_cenarios"]), "+ 20 mil no cenário de alerta", delta_color="off")
    ngov = GOV.apoio_1t.value_counts().to_dict() if len(GOV) else {}
    st.markdown(f"""
### 1. O que o eleitor diz: as pesquisas
- **{N1} pesquisas de 1º turno** e **{ENS['n_pesquisas_2t']} de 2º turno (Lula × Flávio)**, de {len(ENS['institutos'])} institutos,
  conferidas em segunda fonte sempre que possível ({n_conf} confirmadas).
- Medimos e descontamos o **viés de cada instituto**, exatamente como no cenário estadual.

### 2. Como cada região e estado pensa
- Recortes regionais e pesquisas estaduais para presidente, comparados com o total nacional **na mesma pesquisa**.

### 3. O que as urnas já mostraram (TSE)
- Resultado oficial por estado de **2018 e 2022**, 1º e 2º turno (API oficial de resultados do TSE e tabelas do TSE).
- Em 2022, Lula venceu com **50,9%** — a eleição mais apertada da história.

### 4. Quanto as pesquisas já erraram
- **{HI['pesquisas']} pesquisas finais** comparadas com as urnas nas eleições presidenciais de {', '.join(map(str, HI['eleicoes']))}.
- Erro médio no 1º turno: **{n(HI['media_1t'], 1)} pontos** na margem PT − adversário (negativo = pesquisas
  superestimaram o PT). A direção e a persistência devem ser verificadas em backtest.
- Em 2022, as simulações de 2º turno feitas **antes** do 1º turno erraram **{n(HI['erro_2t_antecipado_2022'], 1)} pontos**
  (9 institutos).
- **1º turno:** usa o erro de todas as eleições (2006–2022), que inclui o voto útil de última hora. **2º turno:** usa erros de pesquisas finais do próprio segundo turno. O erro antecipado de 2022 permanece no cenário de alerta.
- Como hipótese ainda não calibrada, o modelo supõe que o viés se repete **entre 0% e 100%** (incerto).

### 5. Quem está com quem: os governadores
- Posição dos **27 governadores** (setembro de 2026): {', '.join(f'{v} {k}' for k, v in ngov.items())}.
  Redistribui votos entre UFs; não altera a chance nacional. É hipótese com faixa larga.

### 6. O que a mídia diz
- **{len(MIDIA)} notícias e comentários** de veículos nacionais de linhas editoriais variadas, com link. Não entra no cálculo.

### 7. Os modelos (os mesmos do cenário estadual)
- **6 agregadores** de pesquisas, **5 modelos de aprendizado de máquina** para a geografia e **{n(SIM['n_cenarios'])} simulações**
  de 1º e 2º turno, mais o cenário de alerta.
""")
    link = {"Fonte": st.column_config.LinkColumn("Fonte")}
    if len(PRAW):
        with st.expander("📋 Pesquisas (instituto, datas, quem pagou, método, situação)"):
            cols = [c for c in ["turno", "instituto", "fim", "amostra", "contratante", "metodo", "lula", "flavio", "status",
                                "fonte_url"] if c in PRAW.columns]
            tabela(PRAW[cols].sort_values("fim", ascending=False).rename(columns={"fonte_url": "Fonte"}), column_config=link)
    if len(PREG):
        with st.expander("📋 Recortes regionais e estaduais"):
            tabela(PREG.rename(columns={"fonte_url": "Fonte"}), column_config=link)
    if len(HIST):
        with st.expander("📋 Histórico: pesquisas finais × urnas (presidente)"):
            tabela(HIST.rename(columns={"fonte_url": "Fonte"}), column_config=link)
    if len(GOV):
        with st.expander("📋 Governadores"):
            tabela(GOV.rename(columns={"fonte_url": "Fonte"}), column_config=link)
    if len(IND):
        with st.expander("📋 Aprovação do governo e rejeição"):
            tabela(IND.rename(columns={"fonte_url": "Fonte"}), column_config=link)

# ====================================================================== metodologia
elif SECAO == 9:
    st.subheader("Como o modelo funciona")
    st.markdown(f"""
O cenário nacional usa **a mesma metodologia do cenário estadual**, com o mesmo código dos agregadores.

**1. Agregadores (6):** média ponderada, mediana robusta, regressão com efeito-instituto, filtro de Kalman, processo
gaussiano e bayesiano hierárquico — aplicados ao 1º turno (Lula e Flávio) e às pesquisas de 2º turno.

**2. Geografia (5 modelos de ML):** regressão linear, Ridge, Random Forest, Gradient Boosting e KNN geográfico,
treinados em 2018 → 2022 por estado e aplicados de 2022 para 2026.

**3. Ajustes:** recortes regionais das pesquisas de 2026 (em relação ao país, na mesma pesquisa) e apoio dos governadores.

**4. Erro histórico:** cada um dos {n(SIM['n_cenarios'])} cenários sorteia o erro real de uma eleição presidencial
({', '.join(map(str, HI['eleicoes']))}), multiplicado por uma persistência incerta (0 a 100%), mais o ruído normal das
pesquisas. No 2º turno, o erro vem das pesquisas finais do próprio segundo turno; sua aplicação às simulações antecipadas ainda requer validação temporal. Cenário de alerta: o erro de
2022 se repete por inteiro, inclusive o das simulações antecipadas de 2º turno ({n(HI['erro_2t_antecipado_2022'], 1)} pts).

**5. Monte Carlo:** 1º turno (alguém passa de 50%?) e 2º turno (mistura de cenários das pesquisas de 2º turno e de transferência, com pesos iguais quando ambas estão disponíveis; sem pares suficientes, usa apenas pesquisas. A
transferência de votos **implícita estimada** em {P2['transferencia_medida']['pares']} pesquisas: {pct(P2['transferencia_medida']['lula']) if P2['transferencia_medida']['lula'] is not None else 'indisponível'}
é a estimativa implícita destinada a Lula; não é acompanhamento individual dos eleitores).

**Limites:** o efeito dos governadores é hipótese; parte das posições dos governadores não foi reconfirmada em setembro;
a eleição é decidida no total nacional — o mapa por estado é informativo.
""")
