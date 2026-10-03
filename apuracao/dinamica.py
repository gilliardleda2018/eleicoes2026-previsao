"""Apresentação da apuração; histórico limitado à sessão, sem modificar modelos."""
from datetime import datetime, timezone, timedelta
from html import escape
import math
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go


def registrar(estado, votos, percentual, consultado, projecoes=None):
    """Não duplica consultas em cache; correções negativas são preservadas."""
    votos = {str(k): float(v) for k, v in votos.items() if math.isfinite(float(v))}
    p = max(0.0, min(100.0, float(percentual)))
    anterior = estado.get('ultimo')
    atual = dict(votos=votos, percentual=p, consultado=consultado, projecoes=projecoes or {})
    if anterior and consultado <= anterior['consultado']:
        return estado
    if anterior:
        deltas = {k: v - anterior['votos'].get(k, v) for k, v in votos.items()}
        eventos = []
        if any(deltas.values()):
            eventos.append('Votos atualizados: ' + ' · '.join(f'{k} {v:+,.0f}'.replace(',', '.') for k, v in deltas.items()))
        def lider(v):
            if not v or max(v.values()) <= 0:
                return None
            nomes = [k for k, n in v.items() if n == max(v.values())]
            return nomes[0] if len(nomes) == 1 else None
        antes, agora = lider(anterior['votos']), lider(votos)
        if antes and agora and antes != agora:
            eventos.append(f'Mudança de liderança entre os candidatos acompanhados: {agora}')
        for marco in (25, 50, 75, 100):
            if anterior['percentual'] < marco <= p:
                eventos.append(f'{marco}% da apuração atingidos')
        if p < anterior['percentual']:
            eventos.append('O percentual foi revisado pela fonte')
        estado['deltas'] = deltas
        estado['eventos'] = (estado.get('eventos', []) + [(consultado, e) for e in eventos])[-30:]
    else:
        estado['deltas'] = {}
        estado['eventos'] = [(consultado, 'Acompanhamento iniciado nesta sessão')]
    estado['ultimo'] = atual
    estado['historico'] = (estado.get('historico', []) + [atual])[-120:]
    return estado


def horario(t):
    return datetime.fromtimestamp(t, timezone(timedelta(hours=-3))).strftime('%H:%M:%S')


def mostrar(chave, votos, percentual, consultado, projecoes=None, ensaio=False):
    chave = 'dinamica_' + chave
    estado = registrar(st.session_state.get(chave, {}), votos, percentual, consultado, projecoes)
    st.session_state[chave] = estado
    st.markdown('''<style>
.ao-status{padding:16px 20px;border:1px solid #c8d7e7;border-radius:20px;
background:linear-gradient(145deg,#fffdf5,#edf3f8);box-shadow:5px 8px 18px #20344b15;color:#153456}
.ao-barra{height:9px;border-radius:9px;background:#dfe8f2;margin-top:12px;overflow:hidden}
.ao-barra i{display:block;height:100%;background:linear-gradient(90deg,#88bcea,#2464aa);transition:width .7s ease}
.ao-novo{display:inline-block;padding:6px 12px;border-radius:12px;background:#e1f1e7;color:#174d31;margin:8px 8px 0 0;animation:ao-brilho 1.2s ease 1}
@keyframes ao-brilho{50%{box-shadow:0 0 16px #38a56955}}
@media(prefers-reduced-motion:reduce){.ao-novo{animation:none}.ao-barra i{transition:none}}
</style>''', unsafe_allow_html=True)
    p = estado['ultimo']['percentual']
    st.markdown(f'<div class="ao-status"><b>{"🧪 Ensaio" if ensaio else "📡 Dados oficiais · TSE"}</b> · consulta bem-sucedida às {horario(consultado)} (Brasília)<br>'
                f'<strong>{p:.1f}%</strong> apurado · histórico iniciado ao abrir esta sessão'
                f'<div class="ao-barra" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{p}" aria-label="Percentual apurado"><i style="width:{p}%"></i></div></div>', unsafe_allow_html=True)
    for nome, delta in estado.get('deltas', {}).items():
        if delta:
            texto = f'{nome}: {delta:+,.0f} votos desde a consulta anterior'.replace(',', '.')
            if delta < 0:
                texto += ' (revisão da fonte)'
            st.markdown(f'<span class="ao-novo">{escape(texto)}</span>', unsafe_allow_html=True)
    if not ensaio:
        restante = max(0, int(consultado + 90 - datetime.now(timezone.utc).timestamp()))
        components.html(f'''<div style="font:13px sans-serif;color:#53667d" id="tempo"></div><script>
let s={restante};const el=document.getElementById('tempo');function atualizar(){{el.textContent=s>0?'Próxima verificação em cerca de '+s+' s':'Aguardando a próxima verificação automática';s=Math.max(0,s-1)}}atualizar();setInterval(atualizar,1000);
</script>''', height=28)
    with st.expander('Evolução e últimas atualizações', expanded=False):
        h = estado['historico']
        if len(h) < 2:
            st.caption('Os gráficos aparecem após duas consultas bem-sucedidas. Recarregar a página reinicia este histórico.')
        else:
            nomes = list(votos)
            if len(nomes) >= 2:
                fig = go.Figure()
                for outro in nomes[1:]:
                    fig.add_scatter(x=[datetime.fromtimestamp(x['consultado'], timezone(timedelta(hours=-3))) for x in h],
                                    y=[x['votos'].get(nomes[0], 0)-x['votos'].get(outro, 0) for x in h],
                                    name=f'{nomes[0]} − {outro}', mode='lines+markers')
                fig.update_layout(title='Evolução da diferença nos votos apurados', yaxis_title='Diferença de votos', height=300)
                st.plotly_chart(fig, width='stretch', key=chave+'_votos')
            if projecoes:
                fig = go.Figure()
                tempos = [datetime.fromtimestamp(x['consultado'], timezone(timedelta(hours=-3))) for x in h]
                for nome in projecoes:
                    vals = [x['projecoes'].get(nome, (None, None, None)) for x in h]
                    fig.add_scatter(x=tempos,y=[v[2] for v in vals],mode='lines',line=dict(width=0),showlegend=False)
                    fig.add_scatter(x=tempos,y=[v[0] for v in vals],mode='lines',line=dict(width=0),fill='tonexty',showlegend=False)
                    fig.add_scatter(x=tempos,y=[v[1] for v in vals],mode='lines+markers',name=nome)
                fig.update_layout(title='Projeção do modelo e faixa ao longo da apuração',height=300,
                                  yaxis_title='Votos projetados' if 'deputado' in chave else '% dos votos válidos')
                st.plotly_chart(fig,width='stretch',key=chave+'_projecao')
                st.caption('Linhas: estimativa central do modelo. Áreas: faixas de incerteza fornecidas pelo modelo; não são votos oficiais nem garantia de resultado.')
        for t, evento in reversed(estado.get('eventos', [])):
            st.write(f'{horario(t)} · {evento}')


def falha(chave):
    estado = st.session_state.get('dinamica_' + chave)
    if estado:
        st.warning('A consulta falhou. Última consulta bem-sucedida às ' + horario(estado['ultimo']['consultado']) + ' (Brasília).')
        st.dataframe([{'Candidato':k,'Últimos votos apurados':v} for k,v in estado['ultimo']['votos'].items()],hide_index=True)


def telao():
    ativo = st.toggle('Modo telão', key='modo_telao_apuracao', help='Amplia os placares e reduz textos auxiliares. Desative para ver todos os detalhes.')
    if ativo:
        st.markdown('''<style>
.pl-votos,.dep-votes,.tt-num{font-size:clamp(3rem,6vw,5.5rem)!important}
.pl-nome,.dep-name{font-size:1.35rem!important}
[data-testid="stCaptionContainer"],.dep-reference,.dep-status{display:none}
.st-key-compartilhar_apuracao{display:none}
</style>''',unsafe_allow_html=True)
