"""Testes da redução da abstenção (1º → 2º turno) nos três níveis, sem internet.

    python -m unittest discover -s segundo_turno/testes -p "test_*.py" -v
"""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import abstencao_2t as ab  # noqa: E402
import motor_2t  # noqa: E402


class Taxa(unittest.TestCase):
    def test_usa_abstencao_do_tse_nas_secoes_totalizadas(self):
        # 50% apurado: 400 votaram e 100 faltaram nas seções totalizadas → 20%, não 1 - 400/1000
        df = pd.DataFrame({"comparecimento": [400.0], "abstencao": [100.0], "eleitorado": [1000.0], "pst": [50.0]})
        self.assertAlmostEqual(ab.taxa_2t(df).iloc[0], 20.0)

    def test_leitura_antiga_sem_coluna_de_abstencao(self):
        df = pd.DataFrame({"comparecimento": [800.0], "eleitorado": [1000.0], "pst": [100.0]})
        self.assertAlmostEqual(ab.taxa_2t(df).iloc[0], 20.0)
        parcial = pd.DataFrame({"comparecimento": [400.0], "eleitorado": [1000.0], "pst": [50.0]})
        self.assertAlmostEqual(ab.taxa_2t(parcial).iloc[0], 20.0)

    def test_eleitorado_do_1t_quando_a_leitura_nao_traz(self):
        df = pd.DataFrame({"comparecimento": [750.0], "pst": [100.0]})
        self.assertAlmostEqual(ab.taxa_2t(df, [1000.0]).iloc[0], 25.0)

    def test_sem_votos_fica_vazio(self):
        df = pd.DataFrame({"comparecimento": [0.0], "abstencao": [0.0], "eleitorado": [1000.0], "pst": [0.0]})
        self.assertTrue(np.isnan(ab.taxa_2t(df).iloc[0]))
        self.assertIsNone(ab.taxa_total(None))


class Niveis(unittest.TestCase):
    def setUp(self):
        self.uf, self.br, self.mun, self.ma, self.sec = motor_2t.ensaio(1.0, semente=7)

    def test_brasil_por_estado(self):
        t, tot = ab.brasil(self.uf, self.br)
        self.assertEqual(len(t), 27)  # sem exterior
        self.assertNotIn("ZZ", set(t.uf))
        self.assertTrue(t.abst_2t.notna().all())
        r = t.iloc[0]
        self.assertAlmostEqual(r.reducao, r.abst_1t - r.abst_2t)
        self.assertGreater(tot["abst_1t"], 15)  # 1º turno oficial: 21,1%
        self.assertLess(tot["abst_1t"], 25)
        self.assertIsNotNone(tot["abst_2t"])

    def test_maranhao_por_municipio_e_o_estado_bate_com_a_tabela_por_uf(self):
        t, tot = ab.maranhao(self.mun, self.ma, pd.DataFrame({"cd_tse": [ab.TUNTUM], "municipio": ["Tuntum"]}))
        self.assertEqual(len(t), 217)
        tu = ab.municipio(t, ab.TUNTUM)
        self.assertEqual(tu["nome"], "Tuntum")
        self.assertTrue(1 <= tu["posicao"] <= 217)
        uf, _ = ab.brasil(self.uf, self.br)
        self.assertAlmostEqual(uf.loc[uf.uf == "MA", "abst_2t"].iloc[0], tot["abst_2t"], places=2)

    def test_antes_da_apuracao_tudo_aguardando(self):
        vazio = pd.DataFrame({"unidade": [], "pst": []})
        t, tot = ab.maranhao(vazio, None, pd.DataFrame({"cd_tse": [], "municipio": []}))
        self.assertTrue((t.situacao == "aguardando").all())
        self.assertIsNone(tot["abst_2t"])
        self.assertIsNone(tot["reducao"])

    def test_secoes_compara_so_as_lidas(self):
        base = pd.DataFrame({"secao": ["0001", "0002", "0003"], "bairro": ["Centro", "Centro", "Povoado"],
                             "zona_tipo": ["Zona urbana", "Zona urbana", "Zona rural"], "Local": ["A", "A", "B"],
                             "aptos": [100, 200, 100], "comparecimento": [70, 160, 60]})
        v = pd.DataFrame({"secao": ["1", "3"], "aptos": [100, 100], "comparecimento": [80, 75]})
        s = ab.secoes(base, v)
        self.assertEqual(int(s.lida.sum()), 2)
        g = ab.por_grupo(s, "bairro").set_index("bairro")
        self.assertAlmostEqual(g.loc["Centro", "abst_1t"], 30.0)  # só a seção 0001 entra nos dois turnos
        self.assertAlmostEqual(g.loc["Centro", "abst_2t"], 20.0)
        self.assertEqual(g.loc["Centro", "a_mais"], 10)
        self.assertAlmostEqual(g.loc["Povoado", "reducao"], 15.0)
        r = ab.resumo_secoes(s)
        self.assertAlmostEqual(r["abst_1t"], 35.0)
        self.assertAlmostEqual(r["abst_2t"], 22.5)
        self.assertEqual(r["lidas"], 2)


if __name__ == "__main__":
    unittest.main()
