"""Mudanças locais entre consultas; independente de projeções e inferência."""
from datetime import datetime, timezone, timedelta
from html import escape
from math import isfinite
import streamlit as st
try:
    from .historico_servidor import gravar_ler
except ImportError:
    from historico_servidor import gravar_ler

TITULOS = {'presidente': 'Presidente', 'governador': 'Governador do Maranhão',
           'deputado': 'Assembleia Legislativa'}


def numero(v, sinal=False):
    return f'{v:+,.0f}' .replace(',', '.') if sinal else f'{v:,.0f}'.replace(',', '.')


def analisar(antes, agora):
    votos = agora['votos']
    linhas = []
    def lider(d):
        maior = max(d.values(), default=0)
        nomes = [k for k, v in d.items() if v == maior]
        return nomes[0] if maior > 0 and len(nomes) == 1 else None
    atual = lider(votos)
    if not any(votos.values()):
        linhas.append('Tuntum ainda não tem votos registrados para os candidatos acompanhados.')
    elif atual:
        outros = [v for k, v in votos.items() if k != atual]
        vantagem = votos[atual]-max(outros) if outros else None
        linhas.append(f'{atual} está à frente entre os candidatos acompanhados'
                      + (f' por {numero(vantagem)} votos.' if vantagem is not None else '.'))
    else:
        linhas.append('Empate na liderança entre os candidatos acompanhados.')
    if antes is None:
        return linhas + ['Primeira consulta local: as mudanças aparecem na próxima atualização.']
    if set(antes['votos']) != set(votos):
        return linhas + ['A lista de candidatos mudou; aguardando uma nova comparação local.']
    anterior = lider(antes['votos'])
    if anterior and atual and anterior != atual:
        linhas.append(f'Mudança de liderança em Tuntum: {anterior} → {atual}.')
    elif anterior and not atual and any(votos.values()):
        linhas.append('A liderança isolada deu lugar a um empate em Tuntum.')
    mudou = False
    for nome, v in votos.items():
        delta = v-antes['votos'][nome]
        if delta:
            mudou = True
            linhas.append(f'{nome}: {numero(delta, True)} votos desde a consulta anterior'
                          + (' (revisão da fonte).' if delta < 0 else '.'))
    for i, nome in enumerate(votos):
        for outro in list(votos)[i+1:]:
            antes_dif = antes['votos'][nome]-antes['votos'][outro]
            dif = votos[nome]-votos[outro]
            if dif != antes_dif:
                linhas.append(f'{nome} − {outro}: diferença passou de {numero(antes_dif, True)}'
                              f' para {numero(dif, True)} votos.')
    pa, pb = antes['percentual'], agora['percentual']
    if abs(pb-pa) > 0.001:
        mudou = True
        linhas.append(f'Seções apuradas em Tuntum: {pa:.1f}% → {pb:.1f}%.'
                      + (' Percentual revisado pela fonte.' if pb < pa else ''))
    if not mudou:
        linhas.append('Nenhuma mudança local desde a consulta anterior.')
    return linhas


def mostrar(disputa, turno, ensaio, votos, percentual, consultado):
    chave = f'tuntum_mudancas_{disputa}_{turno}_{ensaio}'
    historico = st.session_state.get(chave, [])
    indisponivel = votos is None or percentual is None
    if not indisponivel:
        votos = {str(k): float(v) for k, v in votos.items()}
        if any(not isfinite(v) or v < 0 for v in votos.values()) or not isfinite(float(percentual)):
            indisponivel = True
        elif not 0 <= float(percentual) <= 100:
            indisponivel = True
    if not indisponivel:
        atual = dict(votos=votos, percentual=float(percentual), consultado=float(consultado))
        if not ensaio:
            try:
                historico = gravar_ler(chave, atual)
            except Exception:
                st.caption('Histórico local de Tuntum indisponível no servidor; usando esta sessão.')
        if not historico or atual['consultado'] > historico[-1]['consultado']:
            historico = (historico + [atual])[-120:]
        st.session_state[chave] = historico
    if indisponivel:
        linhas = ['Dados locais de Tuntum indisponíveis nesta consulta.']
        if ensaio and disputa == 'presidente':
            linhas.append('O ensaio presidencial atual tem dados por estado, sem recorte municipal de Tuntum.')
        if historico:
            linhas.append('Último registro local mantido; não representa uma atualização nova.')
            linhas.extend(f'{nome}: {numero(v)} votos' for nome, v in historico[-1]['votos'].items())
    else:
        linhas = analisar(historico[-2] if len(historico) > 1 else None, historico[-1])
    fonte = 'ENSAIO · dados simulados, não são votos de 2026' if ensaio else 'TSE · votos locais, sem projeção'
    horario = ''
    if historico:
        horario = datetime.fromtimestamp(historico[-1]['consultado'], timezone(timedelta(hours=-3))).strftime('%H:%M:%S')
    st.markdown('''<style>
.tu-mudancas{background:linear-gradient(145deg,#fffdf5,#f1efe4 48%,#e6e4da);
border:1px solid #d8d5c6;border-top:3px solid #4678ab;border-radius:22px;padding:22px 24px;
box-shadow:8px 12px 24px #4a453129,inset 1px 1px 0 #fffef9;margin:16px 0;color:#17263d}
.tu-mudancas h4{margin:0 0 6px;color:#153456}.tu-mudancas small{color:#56667b}
.tu-mudancas p{margin:9px 0;line-height:1.5}
@media(max-width:640px){.tu-mudancas{padding:18px}.tu-mudancas h4{font-size:1.05rem}}
</style>''', unsafe_allow_html=True)
    texto = ''.join(f'<p>{escape(linha)}</p>' for linha in linhas)
    st.markdown(f'<div class="tu-mudancas"><h4>O que mudou em Tuntum?</h4>'
                f'<small>{escape(TITULOS[disputa])} · {turno}º turno · {escape(fonte)}</small>'
                f'{texto}<small>{"Última consulta local: "+horario+" (Brasília). " if horario else ""}'
                'Comparação só entre candidatos acompanhados; não declara eleição.</small></div>',
                unsafe_allow_html=True)
