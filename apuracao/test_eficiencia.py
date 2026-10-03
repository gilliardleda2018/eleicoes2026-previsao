import unittest
from streamlit.testing.v1 import AppTest
from apuracao.eficiencia import avaliar


class EficienciaTest(unittest.TestCase):
    def setUp(self):
        self.h=[dict(consultado=1,percentual=20,projecoes={'A':(80,90,100)}),
                dict(consultado=2,percentual=80,projecoes={'A':(95,105,115)}),
                dict(consultado=3,percentual=100,projecoes={'A':(110,110,110)})]

    def test_erro_e_cobertura_sem_final_no_teste(self):
        r=avaliar(self.h,{'A':110})[0]
        self.assertEqual(r['Projeções anteriores avaliadas'],2)
        self.assertEqual(r['Erro absoluto médio'],12.5)
        self.assertEqual(r['Faixas que contiveram o final (%)'],50)

    def test_sem_final_nao_inventa_precisao(self):
        r=avaliar(self.h)[0]
        self.assertNotIn('Erro absoluto médio',r)
        self.assertEqual(r['Variação da estimativa central'],5)

    def test_descarta_faixa_invalida(self):
        self.assertEqual(avaliar([dict(consultado=1,projecoes={'A':(5,4,3)})]),[])

    def test_interface(self):
        a=AppTest.from_string('from apuracao.eficiencia import mostrar\nmostrar([],ensaio=True)').run()
        self.assertFalse(a.exception)
        self.assertIn('aguardando',a.info[0].value)
