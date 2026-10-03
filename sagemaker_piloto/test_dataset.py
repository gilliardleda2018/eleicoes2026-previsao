import unittest
from sagemaker_piloto.dataset import extrair, dividir_rotulados


class DatasetTest(unittest.TestCase):
    def test_mudanca_e_revisao(self):
        a = {'consultado': 1, 'unidades': {'Tuntum': {'percentual': 10, 'votos': {'A': 10, 'B': 8}}}}
        b = {'consultado': 2, 'unidades': {'Tuntum': {'percentual': 20, 'votos': {'A': 9, 'B': 12}}}}
        linha = extrair('dinamica_governador_1_False', [b, a, b])[0]
        self.assertEqual((linha['volume'], linha['virada'], linha['revisao']), (5, 1, 1))
        self.assertIsNone(linha['relevancia'])
        with self.assertRaises(ValueError):
            extrair('dinamica_governador_1_True', [a, b])

    def test_sem_rotulos_nao_treina(self):
        with self.assertRaises(ValueError):
            dividir_rotulados([])
        with self.assertRaises(ValueError):
            dividir_rotulados([{'origem': 'historico_oficial_painel', 'relevancia': None}])

    def test_corte_preserva_grupos(self):
        linhas = [{'grupo': str(i), 'instante': i, 'origem': 'historico_oficial_painel',
                   'rotulador': 'teste de contrato', 'relevancia': i % 4,
                   'volume': 10, 'virada': 0, 'revisao': 0, 'percentual': 10,
                   'delta_percentual': 1} for i in range(40) for _ in range(2)]
        treino, teste = dividir_rotulados(linhas)
        self.assertLess(max(x['instante'] for x in treino), min(x['instante'] for x in teste))
        self.assertFalse({x['grupo'] for x in treino} & {x['grupo'] for x in teste})
