import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from historico import carregar
from validacao_modelo import decidir, escrever_json, filtrar_datas, sortear_transferencia, transferencia_implicita
from validar_backtest import avaliar


class Contratos(unittest.TestCase):
    def test_historico_sem_futuro(self):
        dates=['2022-09-21','2022-09-22','2022-10-02','2022-10-03','2022-11-01']
        rows=[dict(ano=2022,turno=1,instituto='I',fim_campo=d,pesq_pt=48,pesq_adv=42,
                   urna_pt_validos=48.4,urna_adv_validos=43.2) for d in dates]
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'h.csv';pd.DataFrame(rows).to_csv(p,index=False)
            self.assertEqual(carregar(p).fim_campo.tolist(),dates[1:3])

    def test_corte_divulgacao(self):
        p=pd.DataFrame({'fim':['2026-09-01','2026-10-03','2026-09-30'],
                        'divulgacao':['2026-09-02','2026-10-03','2026-10-03']})
        self.assertEqual(len(filtrar_datas(p,pd.Timestamp('2026-10-02'))),1)

    def test_data_invertida(self):
        with self.assertRaises(ValueError):
            filtrar_datas(pd.DataFrame({'inicio':['2026-10-03'],'fim':['2026-10-01']}),pd.Timestamp('2026-10-02'))

    def test_maioria_estrita(self):
        l,f,s,vl,vf=decidir([50,51],[40,39],[.49,.49])
        self.assertEqual(l.tolist(),[False,True]);self.assertEqual(vf.tolist(),[True,False])

    def test_nan_bloqueado(self):
        with self.assertRaises(ValueError):decidir([40],[40],[np.nan])

    def test_empate_exato(self):
        with self.assertRaises(ValueError):decidir([40],[40],[.5])

    def test_transferencia_dispersao_alta(self):
        x=sortear_transferencia([.1,.9,.1,.9],np.random.default_rng(42),1000)
        self.assertTrue(np.isfinite(x).all());self.assertTrue(set(x).issubset({.1,.9}))

    def test_transferencia_insuficiente(self):
        for valores in ([],[.4],[.2,.4,.6]):
            with self.assertRaises(ValueError):sortear_transferencia(valores,np.random.default_rng(42),10)

    def test_transferencia_duplicada(self):
        p=pd.DataFrame({'turno':[1,1,2],'instituto':['I']*3,'fim':['2026-09-01']*3,
                        'lula_val':[40,41,np.nan],'flavio_val':[40,39,np.nan],'lula_2p':[np.nan,np.nan,50]})
        with self.assertRaises(ValueError):transferencia_implicita(p)

    def test_json_nao_publica_nan(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'r.json';p.write_text('{"anterior": true}')
            with self.assertRaises(ValueError):escrever_json(p,{'x':np.nan})
            self.assertEqual(p.read_text(),'{"anterior": true}')

    def test_backtest_metricas(self):
        p=pd.DataFrame({'eleicao':[1,2,3],'data_corte':['2020-01-01']*3,'data_eleicao':['2020-02-01']*3,
                        'prob_pt':[.8,.2,.8],'pt_venceu':[1,0,1],'voto_pt_previsto':[52,48,52],
                        'voto_pt_real':[53,47,53],'p10':[48,44,48],'p90':[56,52,56]})
        r=avaliar(p);self.assertAlmostEqual(r['brier'],.04);self.assertEqual(r['mae_voto_pts'],1)
        p['data_corte']='2020-02-02'
        with self.assertRaises(ValueError):avaliar(p)


if __name__=='__main__':unittest.main()
