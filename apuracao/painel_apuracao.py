"""Página — Apuração ao vivo (domingo): apuração parcial do TSE × projeção do modelo, e para onde aponta o final."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "apuracao"))
import motor  # noqa: E402
from comum import CSS, barra_navegacao, grafico, n, pct, tabela  # noqa: E402

if __name__ == "__main__":
    st.set_page_config(page_title="Apuração ao vivo", page_icon="🗳️", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

DISPUTAS = {
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
}

barra_navegacao("ap")
st.markdown("""
<div class="capa" style="background: linear-gradient(100deg, #0F5132 0%, #1B2A41 55%, #6D2E8F 100%);">
  <div class="selo">DOMINGO, 4 DE OUTUBRO · APURAÇÃO OFICIAL DO TSE · ATUALIZA A CADA 90 SEGUNDOS</div>
  <div class="titulo">Apuração ao vivo</div>
  <div class="sub">Compara cada estado e município apurado com a projeção do modelo e estima para onde vai o resultado final.</div>
</div>
""", unsafe_allow_html=True)

c = st.columns([2, 1, 2])
escolha = c[0].radio("Disputa", list(DISPUTAS), horizontal=True, key="ap_disputa")
turno = c[1].radio("Turno", [1, 2], format_func=lambda t: f"{t}º turno", horizontal=True, key="ap_turno")
modo = c[2].radio("Modo", ["Ao vivo (2026)", "Ensaio com a apuração de 2022"], horizontal=True, key="ap_modo")
cfg = DISPUTAS[escolha]
ensaio = modo.startswith("Ensaio")
if ensaio:
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


painel()
