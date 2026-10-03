import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).parent))
from recortes_locais import calcular

class RecortesTest(unittest.TestCase):
    def test_parcial(self):
        x = calcular(200, 1000, 25, 400, 2000, {'votos':150})
        self.assertEqual((x['participacao'], x['historico'], x['contribuicao'], x['novos']), (20,50,10,50))
    def test_zero(self):
        x = calcular(0,0,0,129,0)
        self.assertIsNone(x['participacao'])
        self.assertIsNone(x['contribuicao'])
        self.assertIsNone(x['novos'])
    def test_revisao(self):
        self.assertEqual(calcular(90,1000,50,129,100,{'votos':100})['novos'], -10)
    def test_invalido(self):
        for pct in (101,float('nan'),-1):
            with self.assertRaises(ValueError):
                calcular(0,0,pct,129,0)
