import unittest
from streamlit.testing.v1 import AppTest
from apuracao.inferencia_ensaio import executar, simular, validar


class EnsaioTest(unittest.TestCase):
    def setUp(self):
        self.itens = [dict(nome='A',texto='10 votos',volume=10,virada=False),
                      dict(nome='B',texto='Virada',volume=5,virada=True)]

    def test_preserva_dados(self):
        resultado, status = executar(self.itens, lambda p:
                                    {'scores':[{'id':0,'score':0},{'id':1,'score':2}]})
        self.assertEqual(status, 'Resposta validada')
        self.assertIs(resultado[0], self.itens[1])
        self.assertIs(resultado[1], self.itens[0])

    def test_falhas_e_duplicacao(self):
        for cenario in ['Timeout','Resposta inválida']:
            resultado, status = simular(self.itens, cenario)
            self.assertEqual(resultado, self.itens)
            self.assertIn('regras locais', status)
        with self.assertRaises(ValueError):
            validar(self.itens, {'scores':[{'id':0,'score':1}]*2})

    def test_interface(self):
        codigo = '''from apuracao.inferencia_ensaio import mostrar_teste
mostrar_teste([dict(nome="A",texto="10 votos",volume=10,virada=False)], [])'''
        app = AppTest.from_string(codigo).run()
        self.assertFalse(app.exception)
        self.assertIn('Resposta validada', app.success[0].value)
        app.selectbox[0].select('Timeout').run()
        self.assertFalse(app.exception)
        self.assertIn('regras locais', app.warning[0].value)
        app.selectbox[0].select('Resposta inválida').run()
        self.assertFalse(app.exception)
        self.assertIn('regras locais', app.warning[0].value)
