"""Ensaio do contrato de inferência, sem chamadas AWS nem aprendizado."""
import math
import streamlit as st


def validar(itens, resposta):
    if not isinstance(resposta, dict) or set(resposta) != {'scores'}:
        raise ValueError('Resposta inválida')
    scores = resposta['scores']
    if not isinstance(scores, list) or len(scores) != len(itens):
        raise ValueError('Quantidade de scores inválida')
    ids = set()
    for item in scores:
        if not isinstance(item, dict) or set(item) != {'id', 'score'}:
            raise ValueError('Score inválido')
        i, score = item['id'], item['score']
        if type(i) is not int or i not in range(len(itens)) or i in ids:
            raise ValueError('ID inválido ou duplicado')
        if type(score) not in (int, float) or not math.isfinite(score):
            raise ValueError('Score não finito')
        ids.add(i)
    return [itens[x['id']] for x in sorted(scores, key=lambda x: (-x['score'], x['id']))]


def executar(itens, invocar):
    """Transporte injetável; timeout/resposta inválida preservam o placar local."""
    pacote = {'schema': 1, 'items': [{'id': i, 'volume': float(x['volume']),
                                    'virada': bool(x['virada'])}
                                   for i, x in enumerate(itens)]}
    try:
        return validar(itens, invocar(pacote)), 'Resposta validada'
    except (TimeoutError, ConnectionError, ValueError, TypeError):
        return list(itens), 'Falha simulada: regras locais mantidas'


def simular(itens, cenario):
    def transporte(pacote):
        if cenario == 'Timeout':
            raise TimeoutError('Teste local')
        if cenario == 'Resposta inválida':
            return {'scores': [{'id': -1, 'score': float('nan')} ]}
        # Mantém a ordem das regras. Isso testa o contrato, não treina um modelo.
        return {'scores': [{'id': x['id'], 'score': len(pacote['items'])-x['id']}
                           for x in pacote['items']]}
    return executar(itens, transporte)


def mostrar_teste(itens, historico):
    with st.expander('Teste de integração da inferência · ENSAIO', expanded=True):
        st.info('Resposta simulada localmente. Sem chamada ao SageMaker, sem cobrança de inferência e sem modelo treinado neste teste.')
        cenario = st.selectbox('Cenário da resposta', ['Normal', 'Timeout', 'Resposta inválida'],
                              key='ensaio_inferencia_resposta')
        resultado, status = simular(itens, cenario)
        if status == 'Resposta validada':
            st.success(status + ' · simulação local')
        else:
            st.warning(status)
        st.caption('O teste verifica IDs, pontuações e retorno às regras. Votos, projeções e chances não são alterados. Na apuração oficial este simulador fica desligado.')
        if not itens:
            st.caption('Ainda não há mudanças por local para ordenar. Avance o percentual do ensaio após uma primeira consulta. Senado e deputado federal fornecem apenas resumo global neste painel.')
        st.caption('Dados ao vivo: a coleta TSE já existe no painel. O ranking via SageMaker depende de endpoint, modelo validado e limites de uso; ainda não está ativo.')
    return resultado
