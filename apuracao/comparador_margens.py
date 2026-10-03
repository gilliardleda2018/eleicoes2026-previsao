"""Comparação descritiva de margens em cenários existentes; não recalcula modelos."""
import numpy as np
import streamlit as st


def resumir(a, b, margem):
    a, b = np.asarray(a,dtype=float), np.asarray(b,dtype=float)
    if a.shape!=b.shape or a.ndim!=1 or len(a)==0 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Cenários incompatíveis')
    if not np.isfinite(margem) or margem<0:
        raise ValueError('Margem inválida')
    diferenca=a-b
    return float(np.mean(diferenca>margem)),np.percentile(diferenca,[10,50,90])


def mostrar(resultado, deputados, ensaio=False):
    with st.expander('Comparar diferença de votos',expanded=False):
        st.caption('Maranhão inteiro · candidatos a deputado estadual acompanhados. Maioria aqui significa diferença de votos entre dois candidatos, não maioria absoluta nem confirmação de eleição.')
        chaves=list(resultado['cand'])
        alvo=st.selectbox('Candidato',chaves,format_func=lambda k:deputados[k][0],key='margem_candidato')
        rivais=[k for k in chaves if k!=alvo]
        outro=st.selectbox('Comparar com',rivais,format_func=lambda k:deputados[k][0],key='margem_referencia')
        margem=st.number_input('Diferença de votos a superar',min_value=0,max_value=10000000,value=5000,step=500,key='margem_votos')
        a,b=resultado['cand'][alvo],resultado['cand'][outro]
        freq,faixa=resumir(a['_amostras'],b['_amostras'],margem)
        fmt=lambda x:f'{x:,.0f}'.replace(',','.')
        st.write(f"Nos {len(a['_amostras']):,} cenários desta execução, {deputados[alvo][0]} supera {deputados[outro][0]} por mais de {fmt(margem)} votos em {freq:.1%} dos casos.".replace('3,000','3.000'))
        st.write(f'Diferença central projetada: {fmt(faixa[1])} votos. Faixa dos 80% centrais: {fmt(faixa[0])} a {fmt(faixa[2])}. Valores negativos indicam vantagem do outro candidato.')
        st.write(f"Diferença já apurada: {fmt(a['contado']-b['contado'])} votos.")
        st.warning('Frequência dos cenários do modelo, não garantia nem recomendação de aposta. Este modelo não tem calibração comprovada para decisões financeiras; pequenas margens e início de apuração exigem cautela. Não há indicação de valor a apostar ou de retorno esperado.')
        if ensaio:
            st.info('Ensaio: resultados simulados, não são votos de 2026.')
