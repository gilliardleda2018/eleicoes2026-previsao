"""Coleta oficial, isolada do dashboard. Eleições 2026 — 1º ou 2º turno (variável TURNO, padrão 2).

Os códigos de eleição vêm da configuração publicada pelo TSE (/oficial/comum/config/ele-c.json):
só entram os cargos que o TSE lista para aquele turno (no 2º turno: presidente e, se houver, governador do MA).
Se a configuração não responder, usa os códigos conhecidos (1º turno 6257/6259; 2º turno 6258 para presidente).
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time
from datetime import datetime, timezone
import urllib.request
import urllib.error

BASE='https://resultados.tse.jus.br/oficial/ele2026'
CONFIG='https://resultados.tse.jus.br/oficial/comum/config/ele-c.json'
TURNO=int(os.environ.get('TURNO','2'))
CARGOS={1:'Presidente',3:'Governador',5:'Senador',6:'Deputado Federal',7:'Deputado Estadual'}
CONHECIDOS={1:{1:6257,3:6259,5:6259,6:6259,7:6259},2:{1:6258}}
COLUNAS=['ano','turno','cargo','abrangencia','codigo_local','local','numero','nome','votos','percentual_apurado','consulta_em','origem','fonte','relevancia','rotulador','justificativa']
LOCAIS_MA=[('ma','Maranhão','UF'),('09393','Tuntum','municipio_MA'),('07315','Barra do Corda','municipio_MA')]
UA={'User-Agent':'AggilliApuracaoCollector/1.1','Accept':'application/json'}

def numero(v):
    if isinstance(v,bool) or v is None: raise ValueError('Número ausente ou inválido')
    n=float(str(v).replace(',','.'))
    if not math.isfinite(n) or n<0: raise ValueError('Número negativo/não finito')
    return n

def interpretar(raw,cargo):
    if not isinstance(raw,dict) or not isinstance(raw.get('carg'),list): raise ValueError('Leiaute unificado ausente')
    selecionados=[c for c in raw['carg'] if str(c.get('cd'))==str(cargo)]
    if len(selecionados)!=1: raise ValueError('Cargo ausente ou duplicado')
    pct=numero(raw.get('s',{}).get('pst'))
    if pct>100: raise ValueError('Percentual acima de 100')
    votos={};nomes={};situacao={}
    for agr in selecionados[0].get('agr',[]):
        for par in agr.get('par',[]):
            for cand in par.get('cand',[]):
                n=str(cand.get('n',''))
                if not n.isdigit() or n in votos: raise ValueError('Número de candidato inválido/duplicado')
                v=numero(cand.get('vap'))
                if not v.is_integer(): raise ValueError('Votos não inteiros')
                votos[n]=int(v);nomes[n]=str(cand.get('nmu') or cand.get('nm') or '')
                situacao[n]=str(cand.get('st') or '')
    if not votos: raise ValueError('Sem candidatos: resposta não é uma parcial válida')
    return {'percentual':pct,'votos':votos,'nomes':nomes,'situacao':situacao,'totalizado':raw.get('tf')}

def eleicoes_do_turno(turno=TURNO,cfg=None):
    """{cargo: código da eleição} para o turno, segundo o TSE. Governador/senado/deputados só se o MA estiver listado."""
    try:
        if cfg is None:
            with urllib.request.urlopen(urllib.request.Request(CONFIG,headers=UA),timeout=20) as r:
                cfg=json.load(r)
        achados={}
        for pl in cfg.get('pl',[]):
            for e in pl.get('e',[]):
                if str(e.get('t'))!=str(turno) or not str(pl.get('dt','')).endswith('2026'): continue
                for a in e.get('abr',[]):
                    uf=str(a.get('cd','')).lower()
                    for c in a.get('cp',[]):
                        cargo=int(c.get('cd',0))
                        if cargo in CARGOS and (cargo==1 or uf=='ma'):
                            achados[cargo]=int(e['cd'])
        if 1 in achados:
            return achados,'config do TSE'
    except Exception as e:  # noqa: BLE001
        print(json.dumps({'aviso':f'config do TSE indisponível ({e}); usando códigos conhecidos'},ensure_ascii=False),flush=True)
    return dict(CONHECIDOS[turno]),'códigos conhecidos'

def alvos(eleicoes=None):
    eleicoes=eleicoes or eleicoes_do_turno()[0]
    for cargo,ele in sorted(eleicoes.items()):
        for code,local,abr in LOCAIS_MA+([('br','Brasil','BR')] if cargo==1 else []):
            prefix=code if abr!='municipio_MA' else 'ma'+code
            uf='br' if code=='br' else 'ma'
            yield {'cargo':cargo,'eleicao':ele,'codigo':code,'local':local,'abrangencia':abr,'url':f'{BASE}/{ele}/dados/{uf}/{prefix}-c{cargo:04d}-e{ele:06d}-u.json'}

def preparar(db):
    db.execute('CREATE TABLE IF NOT EXISTS capturas (id INTEGER PRIMARY KEY, alvo TEXT NOT NULL, instante TEXT NOT NULL, hash TEXT NOT NULL, fonte TEXT NOT NULL, dados TEXT NOT NULL, raw TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS erros (instante TEXT, fonte TEXT, erro TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS rodadas (instante TEXT, turno INTEGER, alvos INTEGER, origem TEXT)')

def guardar(db,alvo,raw,instante):
    dados=interpretar(raw,alvo['cargo']);texto=json.dumps(dados,sort_keys=True,ensure_ascii=False,allow_nan=False)
    digest=hashlib.sha256(texto.encode()).hexdigest()
    chave=json.dumps(alvo,sort_keys=True)
    with db:
        anterior=db.execute('SELECT hash FROM capturas WHERE alvo=? ORDER BY id DESC LIMIT 1',(chave,)).fetchone()
        if anterior and anterior[0]==digest: return False
        cursor=db.execute('INSERT INTO capturas(alvo,instante,hash,fonte,dados,raw) VALUES (?,?,?,?,?,?)',(chave,instante,digest,alvo['url'],texto,json.dumps(raw,ensure_ascii=False,allow_nan=False)))
    return bool(cursor.rowcount)

def exportar(db,destino):
    temporario=destino.with_suffix('.csv.tmp')
    with temporario.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(COLUNAS)
        for a,ts,data in db.execute('SELECT alvo,instante,dados FROM capturas ORDER BY id'):
            alvo,d=json.loads(a),json.loads(data)
            turno=alvo.get('turno',1)  # capturas antigas (sem o campo) são do 1º turno
            for n,v in sorted(d['votos'].items()):
                w.writerow([2026,turno,CARGOS[alvo['cargo']],alvo['abrangencia'],alvo['codigo'],alvo['local'],n,d['nomes'][n],v,d['percentual'],ts,'TSE_OFICIAL_COLETA',alvo['url'],'','',''])
        f.flush();os.fsync(f.fileno())
    temporario.replace(destino)

def rodada(db):
    novos=erros=0
    eleicoes,origem=eleicoes_do_turno()
    lista=[dict(a,turno=TURNO) for a in alvos(eleicoes)]
    with db: db.execute('INSERT INTO rodadas VALUES (?,?,?,?)',(datetime.now(timezone.utc).isoformat(),TURNO,len(lista),origem))
    print(json.dumps({'turno':TURNO,'eleicoes':eleicoes,'origem':origem,'alvos':len(lista)},ensure_ascii=False),flush=True)
    for alvo in lista:
        instante=datetime.now(timezone.utc).isoformat()
        try:
            req=urllib.request.Request(alvo['url'],headers=UA)
            with urllib.request.urlopen(req,timeout=20) as response:
                if response.geturl()!=alvo['url']: raise ValueError('Redirecionamento inesperado')
                raw=json.load(response)
            novos+=guardar(db,alvo,raw,instante)
        except (urllib.error.URLError,ValueError,KeyError,TypeError) as e:
            erros+=1
            with db: db.execute('INSERT INTO erros VALUES (?,?,?)',(instante,alvo['url'],str(e)))
            print(json.dumps({'fonte':alvo['url'],'erro':str(e)},ensure_ascii=False),flush=True)
            if isinstance(e,urllib.error.HTTPError) and e.code in (403,429):
                return novos,erros,True
            # Evita insistência em URLs ainda não publicadas.
            if isinstance(e,urllib.error.HTTPError) and e.code==404 and erros>=3:
                return novos,erros,True
        time.sleep(0.2)
    return novos,erros,False

def main():
    p=argparse.ArgumentParser();p.add_argument('--saida',default=str(Path.home()/'apuracao-coleta'))
    p.add_argument('--once',action='store_true');p.add_argument('--intervalo',type=int,default=90)
    args=p.parse_args()
    if args.intervalo<90: p.error('Intervalo mínimo 90 segundos')
    root=Path(args.saida);root.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(root/'historico_oficial.sqlite3',timeout=30) as db:
        preparar(db)
        while True:
            novos,erros,bloqueio=rodada(db);exportar(db,root/'votos_2026_coleta.csv')
            print(json.dumps({'novas_parciais':novos,'erros':erros,'csv':str(root/'votos_2026_coleta.csv'),'proxima_consulta_segundos':660 if bloqueio else args.intervalo}),flush=True)
            if args.once: return
            time.sleep(660 if bloqueio else args.intervalo)

if __name__=='__main__': main()
