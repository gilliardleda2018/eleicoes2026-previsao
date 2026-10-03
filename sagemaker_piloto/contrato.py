"""Contrato preparatório; não faz chamadas AWS nem altera o painel."""
from datetime import datetime, timedelta, timezone
from math import isfinite

CONTA = '614471945241'
REGIAO = 'us-east-1'
TETO_USD = 50
LIMITE_CHAMADAS = 5000


def dentro_do_prazo(ativacao, agora):
    """Datas conscientes de fuso; sete dias, nunca renovados no reinício."""
    if ativacao is None:
        return False
    if ativacao.tzinfo is None or agora.tzinfo is None:
        raise ValueError('Datas devem conter fuso horário')
    inicio = ativacao.astimezone(timezone.utc)
    return inicio <= agora.astimezone(timezone.utc) < inicio + timedelta(days=7)


def ordenar(destaques, resposta):
    """Aceita só uma permutação dos IDs enviados, com pontuações finitas.

    Textos e valores eleitorais vêm das regras locais; nunca do endpoint.
    Os IDs são posições da lista de destaques, não identidades de eleitores.
    """
    if not isinstance(resposta, dict) or set(resposta) != {'scores'}:
        raise ValueError('Resposta inválida')
    scores = resposta['scores']
    if not isinstance(scores, list) or len(scores) != len(destaques):
        raise ValueError('Quantidade de scores inválida')
    vistos = set()
    for item in scores:
        if not isinstance(item, dict) or set(item) != {'id', 'score'}:
            raise ValueError('Item inválido')
        idx, score = item['id'], item['score']
        if type(idx) is not int or idx not in range(len(destaques)) or idx in vistos:
            raise ValueError('ID inválido ou duplicado')
        if type(score) not in (int, float) or not isfinite(score):
            raise ValueError('Score inválido')
        vistos.add(idx)
    indices = sorted(scores, key=lambda x: (-x['score'], x['id']))
    return [destaques[x['id']] for x in indices]


def aplicar(destaques, resposta, *, ativacao=None, agora=None, chamadas=0):
    """Retorna regras locais fora do prazo, sem saldo ou com resposta inválida.

    Contagem é um contrato: precisa de armazenamento atômico global antes de
    integrar chamadas reais. Não representa um controle de cobrança da AWS.
    """
    agora = agora or datetime.now(timezone.utc)
    if (type(chamadas) is not int or chamadas < 0 or chamadas >= LIMITE_CHAMADAS
            or not dentro_do_prazo(ativacao, agora)):
        return list(destaques)
    try:
        return ordenar(destaques, resposta)
    except ValueError:
        return list(destaques)
