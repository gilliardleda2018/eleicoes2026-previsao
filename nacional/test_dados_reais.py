"""Regressão dos contratos das saídas reais e das dez seções do painel."""
import json
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

RAIZ=Path(__file__).resolve().parent

class DadosReais(unittest.TestCase):
    def test_json_finito_e_probabilidades(self):
        def rejeitar(x):raise ValueError(f'Constante JSON inválida: {x}')
        for path in (RAIZ/'resultados').glob('*.json'):
            json.loads(path.read_text(),parse_constant=rejeitar)
        s=json.loads((RAIZ/'resultados/simulacao_nacional.json').read_text())
        self.assertAlmostEqual(sum(s['resultado_final'].values()),1.,places=3)
        self.assertTrue(s['transferencia_disponivel']);self.assertGreaterEqual(s['segundo_turno']['transferencia_medida']['pares'],4)

    def test_base_uf_e_pesquisas(self):
        u=pd.read_csv(RAIZ/'resultados/ufs_previsao.csv')
        self.assertEqual(u.uf.nunique(),27)
        self.assertTrue(np.isfinite(u[['lula_1t','flavio_1t','lula_2t','prob_lula_vence_uf_2t']]).all().all())
        p=pd.read_csv(RAIZ/'resultados/pesquisas_nacionais_tratadas.csv')
        self.assertTrue(p.status.eq('confirmada').all())
        corte=json.loads((RAIZ/'resultados/ensemble_nacional.json').read_text())['data_corte']
        self.assertTrue((pd.to_datetime(p.fim)<=pd.Timestamp(corte)).all())
        self.assertFalse(p.duplicated(['turno','instituto','fim']).any())

    def test_dez_secoes_painel(self):
        at=AppTest.from_file(str(RAIZ/'painel_nacional.py'),default_timeout=30).run()
        self.assertFalse(at.exception)
        for secao in ['📊 Pesquisas','🧠 Modelos','🗺️ Mapa','🏙️ Estados','🧭 Regiões','📰 Mídia',
                      '🎛️ Cenários','📚 Nossa base','ℹ️ Metodologia']:
            with self.subTest(secao=secao):
                at.session_state['secao_br']=secao;at.run()
                self.assertEqual(at.session_state['secao_br'],secao)
                self.assertFalse(at.exception,[e.message for e in at.exception])
        at.session_state['secao_br']='🎛️ Cenários';at.run()
        at.slider[0].set_value(5.).run()
        self.assertFalse(at.exception)
        at.slider[1].set_value(.5).run()
        self.assertFalse(at.exception)

if __name__=='__main__':unittest.main()
