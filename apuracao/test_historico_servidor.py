import os
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from apuracao.historico_servidor import gravar_ler, selos
from apuracao.dinamica import registrar


class EnsaioCompletoTest(unittest.TestCase):
    def test_zero_a_cem_e_recarga(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo=Path(pasta)/'h.db'
            for i in range(101):
                snap=dict(votos={'A':i*100,'B':i*90 if i<50 else i*120},percentual=i,
                          consultado=i+1,projecoes={'A':[10000,12000,15000]})
                gravar_ler('deputado',snap,arquivo)
            # Um visitante novo recupera todo o histórico, sem memória de sessão.
            registros=gravar_ler('deputado',arquivo=arquivo)
            self.assertEqual(len(registros),101)
            s={}
            viu_virada=False
            for x in registros:
                registrar(s,x['votos'],x['percentual'],x['consultado'],x['projecoes'])
                viu_virada=viu_virada or any('liderança' in e for _,e in s['eventos'])
            self.assertEqual(s['ultimo']['percentual'],100)
            self.assertTrue(any('100%' in e for _,e in s['eventos']))
            self.assertTrue(viu_virada)
            self.assertEqual(gravar_ler('outro_turno',arquivo=arquivo),[])

    def test_concorrencia_e_deduplicacao(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo=Path(pasta)/'h.db'
            snap=dict(votos={'A':1},percentual=1,consultado=1,projecoes={})
            with ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(lambda _:gravar_ler('x',snap,arquivo),range(12)))
            self.assertEqual(len(gravar_ler('x',arquivo=arquivo)),1)

    def test_selos_sem_inferencia(self):
        self.assertEqual(selos({'pst':100,'votos':{'13':1000},'eleito':{'13':True}}),[])
        dados={'totalizado':True,'nomes':{'13':'Lula','22':'Flávio'},
               'situacao':{'13':'Eleito','22':'2º turno'}}
        self.assertEqual(len(selos(dados)),3)
        self.assertEqual(selos(dados,True),[('Ensaio · resultado simulado','')])
        self.assertEqual(selos({'situacao':{'13':'Não eleito'}}),[])

    def test_interface_falha_e_telão(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as pasta:
            db=str(Path(pasta)/'h.db')
            code=f'''import os
os.environ['APURACAO_HISTORICO_DB']={db!r}
import streamlit as st
from apuracao import dinamica
dinamica.telao()
dinamica.mostrar('teste_1_False',{{'A':100,'B':90}},100,100,oficial={{'totalizado':True}})
dinamica.falha('teste_1_False')
'''
            a=AppTest.from_string(code).run()
            self.assertFalse(a.exception)
            self.assertTrue(a.warning)
            self.assertTrue(any('Totalizado' in x.value for x in a.success))
            a.toggle[0].set_value(True).run()
            self.assertFalse(a.exception)
            os.environ.pop('APURACAO_HISTORICO_DB',None)


if __name__=='__main__': unittest.main()
