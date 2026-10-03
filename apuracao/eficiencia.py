"""Avalia projeções registradas; estabilidade não é precisão."""
import math
import streamlit as st


def avaliar(historico, referencia=None):
    resultados=[]
    nomes=set().union(*(x.get('projecoes',{}) for x in historico)) if historico else set()
    for nome in sorted(nomes):
        amostras=[]
        for x in historico:
            vals=x.get('projecoes',{}).get(nome)
            if vals is None or len(vals)!=3:
                continue
            try:
                lo,mid,hi=map(float,vals)
            except (ValueError,TypeError):
                continue
            if not all(math.isfinite(v) for v in (lo,mid,hi)) or not lo<=mid<=hi:
                continue
            amostras.append((x,lo,mid,hi))
        if not amostras:
            continue
        ultima=amostras[-1]
        linha={'Candidato':nome,'Largura da faixa atual':ultima[3]-ultima[1],
               'Variação da estimativa central':abs(ultima[2]-amostras[-2][2]) if len(amostras)>1 else None}
        if referencia is not None and nome in referencia:
            real=float(referencia[nome])
            if not math.isfinite(real):
                raise ValueError('Referência inválida')
            # Exclui a consulta final e as posteriores, inclusive pós-totalização.
            anteriores=[x for x in amostras if x[0].get('percentual',100)<100 and
                         x[0]['consultado']<historico[-1]['consultado']]
            if anteriores:
                linha.update({'Projeções anteriores avaliadas':len(anteriores),
                              'Erro absoluto médio':sum(abs(x[2]-real) for x in anteriores)/len(anteriores),
                              'Faixas que contiveram o final (%)':100*sum(x[1]<=real<=x[3] for x in anteriores)/len(anteriores),
                              'Erro da primeira projeção registrada':abs(anteriores[0][2]-real)})
        resultados.append(linha)
    return resultados


def mostrar(historico, referencia=None, ensaio=False, unidade='votos', tempo_calculo=None):
    with st.expander('Eficiência das projeções · avaliação nesta apuração',expanded=False):
        if referencia is None:
            st.info('Precisão aguardando resultado final de referência. Até lá, mostramos apenas estabilidade e largura das faixas.')
        elif ensaio:
            st.warning('Avaliação de ENSAIO: comparação com o total do cenário simulado. Não comprova precisão na eleição de 2026.')
        else:
            st.success('Comparação com o resultado final no mesmo recorte do painel, após totalização informada pelo TSE.')
        linhas=avaliar(historico,referencia)
        if linhas:
            st.dataframe(linhas,hide_index=True)
        else:
            st.caption('Ainda não há projeções registradas para avaliar nesta disputa.')
        st.caption(f'Unidade dos erros, variações e larguras: {unidade}. Erro menor é melhor. Faixa mais estreita indica menos dispersão, mas pode deixar o resultado fora dela. Estabilidade não significa acerto.')
        if tempo_calculo is not None:
            st.caption(f'Tempo do cálculo local nesta execução: {tempo_calculo:.3f} s. Não inclui coleta TSE, rede, renderização ou inferência AWS.')
        st.caption('A cobertura é descritiva das consultas desta apuração, que são correlacionadas; não é calibração em eleições independentes. A primeira projeção é apenas uma comparação interna, não um modelo concorrente. Probabilidades de vitória ainda exigem validação histórica própria.')
        st.caption('Custo e latência do SageMaker: indisponíveis enquanto a integração real não estiver ativa. Histórico depende da retenção do servidor; reinício/deploy no Render atual pode apagar registros.')
