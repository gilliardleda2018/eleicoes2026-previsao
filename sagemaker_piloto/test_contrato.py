import unittest
from datetime import datetime, timedelta, timezone
from sagemaker_piloto.contrato import aplicar, dentro_do_prazo, ordenar


class ContratoTest(unittest.TestCase):
    def setUp(self):
        self.inicio = datetime(2026, 10, 3, 15, tzinfo=timezone.utc)
        self.itens = [{'nome': 'A', 'texto': '10 votos'}, {'nome': 'B', 'texto': 'Revisão'}]
        self.resposta = {'scores': [{'id': 0, 'score': 0.1}, {'id': 1, 'score': 0.8}]}

    def test_prazo(self):
        self.assertFalse(dentro_do_prazo(None, self.inicio))
        self.assertFalse(dentro_do_prazo(self.inicio, self.inicio-timedelta(seconds=1)))
        self.assertTrue(dentro_do_prazo(self.inicio, self.inicio))
        self.assertTrue(dentro_do_prazo(self.inicio, self.inicio+timedelta(days=7, seconds=-1)))
        self.assertFalse(dentro_do_prazo(self.inicio, self.inicio+timedelta(days=7)))
        with self.assertRaises(ValueError):
            dentro_do_prazo(self.inicio.replace(tzinfo=None), self.inicio)

    def test_preserva_conteudo(self):
        resultado = ordenar(self.itens, self.resposta)
        self.assertIs(resultado[0], self.itens[1])
        self.assertIs(resultado[1], self.itens[0])

    def test_fallback(self):
        for chamadas, inicio in [(0, None), (5000, self.inicio), (-1, self.inicio)]:
            self.assertEqual(aplicar(self.itens, self.resposta, chamadas=chamadas,
                                    ativacao=inicio, agora=self.inicio), self.itens)

    def test_rejeita_resposta(self):
        ruins = [None, {'scores': []}, {'scores': [{'id': 0, 'score': 1}]*2},
                 {'scores': [{'id': 0, 'score': float('nan')}, {'id': 1, 'score': 1}]},
                 {'scores': [{'id': True, 'score': 1}, {'id': 0, 'score': 2}]},
                 {'scores': [{'id': 0, 'score': 1}, {'id': 2, 'score': 2}]},
                 dict(self.resposta, texto='Resultado inventado')]
        for resposta in ruins:
            self.assertEqual(aplicar(self.itens, resposta, ativacao=self.inicio,
                                    agora=self.inicio), self.itens)


if __name__ == '__main__':
    unittest.main()
