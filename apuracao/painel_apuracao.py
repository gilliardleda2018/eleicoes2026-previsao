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
    "Assembleia MA · Bruna, Abigail e Eric": dict(disputa="deputado", unidade="Município"),
}
# Deputados estaduais acompanhados (em votos): nome, cor e coluna da projeção
DEPUTADOS = {"bruna": ("Bruna Pessoa", "#E02597", "votos_projetados", "projeção do modelo"),
             "abigail": ("Abigail Cunha", "#E8702A", "abigail_2026", "referência: 2022 + 3% de eleitorado"),
             "eric": ("Eric Costa", "#3B6FB6", "eric_2026", "referência: 2022 + 3% de eleitorado")}

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
cfg = DISPUTAS[escolha]
deputados = cfg["disputa"] == "deputado"
if deputados:  # deputado estadual: só 1º turno
    turno = 1
    c[1].markdown("**Turno**<br>1º turno (único)", unsafe_allow_html=True)
else:
    turno = c[1].radio("Turno", [1, 2], format_func=lambda t: f"{t}º turno", horizontal=True, key="ap_turno")
modo = c[2].radio("Modo", ["Ao vivo (2026)", "Ensaio com a apuração de 2022"], horizontal=True, key="ap_modo")
ensaio = modo.startswith("Ensaio")
if ensaio and deputados:
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
    tabela(tab.astype({"Bruna": float, "Abigail": float, "Eric": float}))  # vazio (e não "None") onde não se aplica
    melhor = ap.assign(vant=ap.real_bruna - ap.real_abigail).sort_values("real_bruna", ascending=False).head(1)
    if len(melhor):
        m = melhor.iloc[0]
        st.caption(f"Maior votação da Bruna até agora: {m.municipio} ({n(m.real_bruna)} votos; "
                   f"{_sinal(m.real_bruna - m.real_abigail)} sobre a Abigail e {_sinal(m.real_bruna - m.real_eric)} "
                   f"sobre o Eric na cidade). Municípios com votos apurados: {len(ap)} de {len(d)}.")


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
{''.join(f'<div style="font:900 1.15rem Archivo;color:#E02597;margin-bottom:6px">{a}</div>' for a in avisos)}
<div style="font-size:1.05rem">{base}</div>
{f'<div style="margin-top:6px">{marco}</div>' if marco else ''}
<div class="pequeno" style="margin-top:8px">{difs} (votos apurados até agora)</div>
</div>""", unsafe_allow_html=True)


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
    narrador(r, geral, numeros, ensaio, apurado)

    k = st.columns(3)
    for col, (chave, (nome, cor, _, origem)) in zip(k, DEPUTADOS.items()):
        c = r["cand"][chave]
        ritmo = c["ritmo"]
        texto_ritmo = "sem votos apurados ainda" if ritmo is None or c["esperado_ate_agora"] < 1 else (
            f"{'+' if ritmo >= 1 else '−'}{n(abs(ritmo - 1) * 100, 0)}% vs. {'projeção' if chave == 'bruna' else '2022'}")
        num = numeros.get(chave, "?")
        col.markdown(f"""
<div class="cartao" style="border-left-color:{cor}"><h4 style="color:{cor}">{nome}
<span style="font-size:.8rem;opacity:.7">nº {num if str(num).isdigit() else '—'}</span></h4>
<div style="font:900 2rem Archivo">{n(c['contado'])} <span style="font-size:1rem">votos</span></div>
<div class="pequeno">{texto_ritmo} · esperado até agora {n(c['esperado_ate_agora'])}</div>
<div style="margin-top:8px"><b>Projeção do final: {mil(c['final'][1])}</b><br>
<span class="pequeno">faixa provável {mil(c['final'][0])} a {mil(c['final'][2])} · antes da apuração: {mil(c['previsto'])}
({origem})</span></div>
<div style="margin-top:6px">Chance de passar de 38,3 mil: <b>{pct(c['prob_acima']['último eleito da chapa do governo em 2022'])}</b>
· de 24,8 mil: <b>{pct(c['prob_acima']['menor eleito em 2022'])}</b></div></div>""", unsafe_allow_html=True)

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


if deputados:
    painel_deputados()
else:
    painel()
