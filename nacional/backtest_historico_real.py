"""Backtest temporal parcial do ajuste de erro de 2º turno, em dados reais.

Uma pesquisa final por instituto. Treina a correção somente em eleições anteriores.
Não reproduz os seis agregadores nem o horizonte pré-primeiro-turno de 2026.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from historico import carregar, ELEICOES
from validacao_modelo import escrever_json
from validar_backtest import avaliar

RAIZ=Path(__file__).resolve().parent

def rodar():
    h=carregar(RAIZ/'dados/erro_historico_presidente.csv')
    h=h[h.turno==2].copy();h['fim_campo']=pd.to_datetime(h.fim_campo)
    h=h.sort_values('fim_campo').groupby(['ano','instituto']).tail(1)
    erros=h.groupby('ano').erro_margem.mean()
    linhas=[]
    for ano in (2014,2018,2022):
        anterior=erros[erros.index<ano].values
        teste=h[h.ano==ano]
        if len(anterior)<2 or teste.empty:raise ValueError('Histórico insuficiente')
        y=100*teste.pesq_pt/(teste.pesq_pt+teste.pesq_adv)
        est=float(y.mean()); dp=max(float(y.std(ddof=1)/np.sqrt(len(y))),1.)
        rng=np.random.default_rng(42+ano)
        base=rng.normal(est,dp,20000)
        corr=rng.uniform(0,1,20000)*rng.choice(anterior,20000)+rng.normal(0,.6*anterior.std(ddof=1),20000)
        corrigido=np.clip(base+corr/2,0,100)
        real=100*teste.urna_pt_validos/(teste.urna_pt_validos+teste.urna_adv_validos)
        if real.max()-real.min()>.1:raise ValueError('Resultados históricos contraditórios')
        urna=float(real.median())
        for nome,arr in [('sem_correcao',base),('erro_historico',corrigido)]:
            linhas.append({'modelo':nome,'eleicao':ano,'data_corte':str(teste.fim_campo.max().date()),
                           'data_eleicao':ELEICOES[(ano,2)],'prob_pt':float((arr>50).mean()),'pt_venceu':int(urna>50),
                           'voto_pt_previsto':float(np.median(arr)),'voto_pt_real':urna,
                           'p10':float(np.percentile(arr,10)),'p90':float(np.percentile(arr,90)),
                           'pesquisas':len(teste),'eleicoes_treino':len(anterior)})
    df=pd.DataFrame(linhas)
    resumo={'escopo':'backtest parcial da correção histórica com média das pesquisas finais; não valida pipeline pré-1º turno completo',
            'limites':['somente três eleições de teste','data de publicação não disponível; corte de campo','amostras ausentes: piso de DP de 1 ponto','nenhum parâmetro ajustado pelo resultado da eleição-alvo'],
            'metricas':{nome:avaliar(g) for nome,g in df.groupby('modelo')}}
    df.to_csv(RAIZ/'resultados/backtest_historico_real.csv',index=False)
    escrever_json(RAIZ/'resultados/backtest_historico_real.json',resumo)
    return resumo

if __name__=='__main__':print(rodar())
