"""Comparações descritivas municipais; não modifica projeções."""
import math
import streamlit as st
from historico_servidor import gravar_ler

RECORTES = [('Bruna Pessoa', 'bruna', 'Tuntum', 'eric_costa_2022', 'Eric Costa'),
            ('Bruna Pessoa', 'bruna', 'Barra do Corda', 'eric_costa_2022', 'Eric Costa'),
            ('Abigail Cunha', 'abigail', 'Tuntum', 'abigail_2022', 'Abigail Cunha')]


def calcular(votos, validos, percentual, referencia, total_estadual, anterior=None):
    valores = [votos, validos, percentual, referencia, total_estadual]
    if not all(math.isfinite(float(x)) and x >= 0 for x in valores) or percentual > 100:
        raise ValueError('Dados municipais inválidos')
    return dict(votos=votos, percentual=percentual,
                participacao=100*votos/validos if validos > 0 else None,
                historico=100*votos/referencia if referencia > 0 else None,
                contribuicao=100*votos/total_estadual if total_estadual > 0 else None,
                diferenca=votos-referencia,
                novos=votos-anterior['votos'] if anterior else None)


def numero(x, casas=0):
    return f'{x:,.{casas}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def mostrar(d, info, ensaio=False):
    st.subheader('Acompanhamento local · Tuntum e Barra do Corda')
    if ensaio:
        st.warning('ENSAIO: os votos de Bruna são fictícios; Abigail usa uma simulação parcial dos dados de 2022. Não são resultados de 2026.')
    instante = info.get('consultado_em')
    if ensaio:
        import time
        instante = time.time()
    for nome, candidato, municipio, coluna, referencia_nome in RECORTES:
        linhas = d[d.municipio == municipio]
        with st.container(border=True):
            st.markdown(f'**{nome} · {municipio}**')
            if linhas.empty or instante is None:
                st.caption('Dados municipais indisponíveis nesta consulta.')
                continue
            row = linhas.iloc[0]
            votos = float(row[f'real_{candidato}'])
            snapshot = dict(consultado=float(instante), votos=votos, percentual=float(row.pst))
            chave = f'recorte_local_{candidato}_{municipio}_{ensaio}'
            if ensaio:
                historico = st.session_state.setdefault(chave, [])
                historico.append(snapshot)
                del historico[:-120]
            else:
                try:
                    historico = gravar_ler(chave, snapshot)
                except (OSError, ValueError, __import__('sqlite3').Error):
                    historico = [snapshot]
                    st.caption('Histórico indisponível; exibindo a consulta atual.')
            anteriores = [x for x in historico if x['consultado'] < instante]
            ref = float(row[coluna])
            x = calcular(votos, float(row.vv), float(row.pst), ref,
                         float(d[f'real_{candidato}'].sum()), anteriores[-1] if anteriores else None)
            cols = st.columns(3)
            cols[0].metric('Votos apurados', numero(votos))
            cols[1].metric('Seções apuradas', numero(x['percentual'], 1)+'%')
            cols[2].metric('Referência de 2022', numero(ref))
            st.caption(f'Referência histórica: {referencia_nome} no mesmo município, conforme a base do projeto.')
            if x['novos'] is not None:
                verbo = 'Revisão: variação de' if x['novos'] < 0 else 'Votos novos desde a consulta anterior:'
                st.write(f"{verbo} {numero(x['novos'])} votos.")
            else:
                st.caption('Primeira consulta registrada; ainda sem comparação entre atualizações.')
            if x['participacao'] is not None:
                st.write(f"Participação nos votos válidos locais apurados: {numero(x['participacao'], 2)}%.")
            if x['historico'] is not None:
                st.write(f"Total {'do ensaio' if ensaio else 'atual'} equivale a {numero(x['historico'], 1)}% da referência de 2022; diferença de {numero(x['diferenca'])} votos.")
            if x['contribuicao'] is not None:
                st.write(f"Este município representa {numero(x['contribuicao'], 1)}% dos votos da candidata já apurados no Maranhão.")
            if row.pst < 100:
                st.caption('Apuração incompleta: comparar votos parciais com o total de 2022 não determina crescimento ou queda no resultado final.')
            st.caption('Comparação descritiva; não demonstra transferência de eleitores nem efeito causal de apoios políticos. Faixas estaduais não são faixas municipais.')
