"""Destaques factuais por regras explícitas; não altera previsões."""
from html import escape
import streamlit as st


def lider(votos):
    if not votos or max(votos.values())<=0:
        return None
    candidatos=[k for k,v in votos.items() if v==max(votos.values())]
    return candidatos[0] if len(candidatos)==1 else None


def analisar(anterior, atual):
    if anterior is None:
        return ['Acompanhamento iniciado. As mudanças aparecem após a próxima consulta.'], []
    fmt=lambda x:f'{x:+,.0f}'.replace(',','.')
    resumo=[]
    antes,agora=anterior['votos'],atual['votos']
    l1,l2=lider(antes),lider(agora)
    if l1 and l2 and l1!=l2:
        resumo.append(f'Mudança de liderança entre os candidatos acompanhados: {l1} → {l2}.')
    for nome,v in sorted(agora.items(),key=lambda item:abs(item[1]-antes.get(item[0],item[1])),reverse=True):
        if nome in antes and v!=antes[nome]:
            delta=v-antes[nome]
            resumo.append(f'{nome}: {fmt(delta)} votos desde a consulta anterior' + (' (revisão da fonte).' if delta<0 else '.'))
    dp=atual['percentual']-anterior['percentual']
    if abs(dp)>0.001:
        resumo.append(f'Apuração: {anterior["percentual"]:.1f}% → {atual["percentual"]:.1f}%.' + (' A fonte revisou o percentual.' if dp<0 else ''))
    destaques=[]
    antigas=anterior.get('unidades',{})
    for nome,u in atual.get('unidades',{}).items():
        if nome not in antigas:
            continue
        a=antigas[nome]
        delta={k:v-a['votos'][k] for k,v in u['votos'].items() if k in a['votos']}
        volume=sum(abs(v) for v in delta.values())
        la,lb=lider(a['votos']),lider(u['votos'])
        virada=bool(la and lb and la!=lb)
        if volume or abs(u['percentual']-a['percentual'])>0.001:
            linhas=[f'{k}: {fmt(v)}' for k,v in delta.items() if v]
            if virada:
                linhas.insert(0,f'Virada entre os candidatos acompanhados: {la} → {lb}')
            if any(v<0 for v in delta.values()):
                linhas.append('Inclui revisão negativa da fonte')
            linhas.append(f'{u["percentual"]:.1f}% apurado')
            destaques.append(dict(nome=nome,texto=' · '.join(linhas),volume=volume,virada=virada))
    destaques.sort(key=lambda x:(-int(x['virada']),-x['volume'],x['nome']))
    return resumo or ['Nenhuma mudança nos votos ou no percentual desde a consulta anterior.'], destaques[:5]


def mostrar(historico,ensaio=False):
    if not historico:
        return
    resumo,destaques=analisar(historico[-2] if len(historico)>1 else None,historico[-1])
    st.markdown('''<style>
.ed-card{padding:20px 24px;border-radius:22px;border:1px solid #d8d5c6;
background:linear-gradient(145deg,#fffdf5,#eeeade);color:#17263d;
box-shadow:6px 9px 20px #4a453118,inset 1px 1px 0 #ffffffcc;margin:12px 0}
.ed-card h4{margin:0 0 10px;color:#153456}.ed-card p{margin:6px 0}
.ed-unit{padding:10px 0;border-top:1px solid #d8d5c6}.ed-unit strong{color:#245b96}
</style>''',unsafe_allow_html=True)
    linhas=''.join(f'<p>{escape(x)}</p>' for x in resumo[:5])
    unidades=''.join(f'<div class="ed-unit"><strong>{escape(x["nome"])}</strong><p>{escape(x["texto"])}</p></div>' for x in destaques)
    st.markdown(f'<div class="ed-card"><h4>O que mudou agora?{" · ENSAIO" if ensaio else ""}</h4>{linhas}'
                f'{"<h4>Destaques da última consulta</h4>"+unidades if unidades else ""}</div>',unsafe_allow_html=True)
    st.caption('Seleção automática: primeiro viradas entre os candidatos acompanhados; depois maior variação absoluta de votos, incluindo revisões. Até cinco locais. Isso não declara eleição nem explica, por si só, mudanças da projeção.')
