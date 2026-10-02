"""Treina cinco modelos em dados artificiais e testa a integração; não valida previsão real."""

def main():
    import pathlib,tempfile,shutil,json,runpy,sys,contextlib,io
    import numpy as np,pandas as pd
    from scipy.special import expit,logit
    src=pathlib.Path(__file__).resolve().parent
    tmp=pathlib.Path(tempfile.mkdtemp(prefix='audit_eleitoral_'));d=tmp/'dados';r=tmp/'resultados';d.mkdir();r.mkdir()
    for f in src.glob('*.py'):shutil.copy(f,tmp/f.name)
    ufs=['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']
    x=np.linspace(25,75,27);b=pd.DataFrame(dict(uf=ufs,regiao=['R'+str(i%5) for i in range(27)],validos22_2t=np.arange(1,28)*100000,haddad18_2t=x,haddad18_1t=x*.7,ciro18_1t=10+np.sin(x),lula22_2t=x+2*np.sin(x),lula22_1t=x*.8,ciro22_1t=5+np.cos(x)))
    b.to_csv(d/'base_ufs.csv',index=False);json.dump({u:[-30+i,-65+i] for i,u in enumerate(ufs)},open(d/'centroides_ufs.json','w'))
    json.dump({'data_corte':'2026-10-02','ensemble':{'lula_1t':{'est':44,'dp':1},'flavio_1t':{'est':40,'dp':1},'lula_2t':{'est':51,'dp':1}}},open(r/'ensemble_nacional.json','w'))
    h=[]
    dates={2006:['2006-10-01','2006-10-29'],2010:['2010-10-03','2010-10-31'],2014:['2014-10-05','2014-10-26'],2018:['2018-10-07','2018-10-28'],2022:['2022-10-02','2022-10-30']}
    for i,(y,ds) in enumerate(dates.items()):
     for t,date in enumerate(ds,1):
      for j in range(3):h.append(dict(ano=y,turno=t,instituto=f'I{j}',fim_campo=date,pesq_pt=52+i*.2+j*.1,pesq_adv=48-i*.2-j*.1,urna_pt_validos=50,urna_adv_validos=50))
    pd.DataFrame(h).to_csv(d/'erro_historico_presidente.csv',index=False);pd.DataFrame({'erro_margem':[-3,-4,-5]}).to_csv(d/'erro_2t_antecipado_2022.csv',index=False)
    p=[]
    for i in range(12):
     date=f'2026-09-{i+1:02d}';l=44+i*.03;f=40;transfer=.35+.05*np.sin(i)
     p.extend([dict(turno=1,instituto=f'I{i}',fim=date,lula_val=l,flavio_val=f,lula_2p=np.nan),dict(turno=2,instituto=f'I{i}',fim=date,lula_val=np.nan,flavio_val=np.nan,lula_2p=l+transfer*(100-l-f))])
    pd.DataFrame(p).to_csv(r/'pesquisas_nacionais_tratadas.csv',index=False)
    sys.path.insert(0,str(tmp))
    def execute():
     with contextlib.redirect_stdout(io.StringIO()):return runpy.run_path(str(tmp/'modelo_ufs_mc.py'))
    a=execute();snapshot=(r/'simulacao_nacional.json').read_bytes();aa=execute();print('MC REPETIVEL:',snapshot==(r/'simulacao_nacional.json').read_bytes())
    assert snapshot==(r/'simulacao_nacional.json').read_bytes()
    print('MC FINITO:',all(np.isfinite(a[k]).all() for k in ['L1','F1','R1','L2']))
    assert all(np.isfinite(a[k]).all() for k in ['L1','F1','R1','L2'])
    assert np.max(np.abs(a['L1']+a['F1']+a['R1']-100))<1e-8
    assert np.max(np.abs((a['uf_l2t']*a['w']).sum(axis=1)-a['L2'][a['sel']]))<1e-8
    assert np.mean(a['lula_leva'])+np.mean(a['flavio_leva'])==1
    print('CONSERVACAO 1T MAX ERRO:',np.max(np.abs(a['L1']+a['F1']+a['R1']-100)))
    print('CALIBRACAO UF MAX ERRO:',np.max(np.abs((a['uf_l2t']*a['w']).sum(axis=1)-a['L2'][a['sel']])))
    print('PROB SOMAM 1:',np.mean(a['lula_leva'])+np.mean(a['flavio_leva']))
    pd.DataFrame({'uf':ufs,'apoio_1t':['Lula']*27,'apoio_2t_tendencia':['Lula']*27}).to_csv(d/'governadores_apoio_2026.csv',index=False);gov=execute();print('GOV MUDA PROB NACIONAL:',a['sim']['resultado_final']!=gov['sim']['resultado_final']);assert a['sim']['resultado_final']==gov['sim']['resultado_final']
    print('TESTE VAZIO TRANSFERENCIA:')
    pd.DataFrame(p).assign(fim='2026-07-01').to_csv(r/'pesquisas_nacionais_tratadas.csv',index=False)
    try:
     empty=execute();print('SAIDA FINITA L2:',np.isfinite(empty['L2']).all(),'PROB FINAL:',empty['sim']['resultado_final']);print('JSON CONTEM NaN:', 'NaN' in (r/'simulacao_nacional.json').read_text());assert np.isfinite(empty['L2']).all();assert abs(sum(empty['sim']['resultado_final'].values())-1)<.001;assert not empty['sim']['transferencia_disponivel']
    except Exception:raise
    
    shutil.rmtree(tmp)

if __name__ == "__main__":
    main()
