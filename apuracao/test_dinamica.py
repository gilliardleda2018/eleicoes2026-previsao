import unittest
from apuracao.dinamica import registrar


class HistoricoTest(unittest.TestCase):
    def test_cache_e_revisoes(self):
        s = {}
        registrar(s, {'A':100, 'B':90},20,1)
        registrar(s, {'A':100, 'B':90},20,1)
        self.assertEqual(len(s['historico']),1)
        registrar(s, {'A':120, 'B':140},55,2)
        self.assertEqual(s['deltas'],{'A':20,'B':50})
        self.assertTrue(any('liderança' in e for _,e in s['eventos']))
        self.assertTrue(any('50%' in e for _,e in s['eventos']))
        registrar(s, {'A':115,'B':140},54,3)
        self.assertEqual(s['deltas']['A'],-5)
        self.assertTrue(any('revisado' in e for _,e in s['eventos']))
        for i in range(4,160):
            registrar(s, {'A':i,'B':i+10},100,i)
        self.assertEqual(len(s['historico']),120)
        self.assertLessEqual(len(s['eventos']),30)

    def test_interface(self):
        from streamlit.testing.v1 import AppTest
        a = AppTest.from_string('''import streamlit as st
from apuracao import dinamica
dinamica.telao()
t=st.session_state.get('t',0)+1
st.session_state['t']=t
dinamica.mostrar('deputado_1_False',{'A':t*100,'B':t*80},t*25,t,{'A':[100,120,150],'B':[90,110,140]})
''').run()
        self.assertFalse(a.exception)
        a.run()
        self.assertFalse(a.exception)
        self.assertEqual(len(a.get('plotly_chart')),2)
        a.toggle[0].set_value(True).run()
        self.assertFalse(a.exception)


if __name__ == '__main__':
    unittest.main()
