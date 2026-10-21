"""Testes do modelo do 2º turno: dados oficiais conferidos, saídas coerentes e reprodutíveis."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import modelo_2t  # noqa: E402

CORTE = pd.Timestamp("2026-10-21")


class TestModelo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = modelo_2t.rodar(CORTE, salvar=False)

    def test_dados_oficiais(self):
        uf, mun, sec, br = modelo_2t.carregar_1t()  # valida somas internamente
        self.assertEqual((len(uf), len(mun), len(sec)), (28, 217, 97))
        self.assertEqual((br.lula, br.flavio), (53_879_538, 56_104_503))
        self.assertAlmostEqual(100 * br.flavio / br.validos, 47.03, places=2)

    def test_probabilidades(self):
        r = self.sim["resultado"]
        self.assertAlmostEqual(r["prob_lula"] + r["prob_flavio"], 1, places=6)
        p10, p50, p90 = r["lula_validos_p10_p50_p90"]
        self.assertTrue(40 < p10 < p50 < p90 < 60)

    def test_reprodutivel(self):
        outra = modelo_2t.rodar(CORTE, salvar=False)
        self.assertEqual(outra["resultado"], self.sim["resultado"])

    def test_corte_temporal(self):
        p = modelo_2t.pesquisas(pd.Timestamp("2026-10-12"))
        self.assertTrue((p.fim <= "2026-10-12").all())
        self.assertTrue((p.fim >= modelo_2t.INICIO_2T).all())

    def test_transferencia_em_faixa(self):
        for c, v in modelo_2t.transferencia().items():
            self.assertTrue(0 < v["lula_entre"] < 1 and 0 < v["decide"] <= 1, c)

    def test_calibracao(self):
        rng = np.random.default_rng(0)
        base = rng.normal(0, .5, (50, 30))
        pesos = rng.uniform(1, 10, 30)
        alvo = rng.uniform(.4, .6, 50)
        out = modelo_2t.calibrar(base, alvo, pesos)
        np.testing.assert_allclose((out * pesos / pesos.sum()).sum(axis=1), alvo, atol=1e-6)

    def test_saidas_salvas_coerentes(self):
        res = AQUI.parent / "resultados"
        uf = pd.read_csv(res / "ufs_2t.csv")
        mun = pd.read_csv(res / "ma_municipios_2t.csv")
        sec = pd.read_csv(res / "tuntum_secoes_2t.csv")
        self.assertTrue(uf.lula_2t.between(5, 95).all() and (uf.lula_2t_p10 <= uf.lula_2t).all()
                        and (uf.lula_2t <= uf.lula_2t_p90).all())
        ma = uf[uf.uf == "MA"].iloc[0]
        lula_mun = mun.votos_lula_2t.sum() / mun.validos_2t_est.sum() * 100
        self.assertAlmostEqual(lula_mun, ma.lula_2t, delta=1.0)  # medianas: só aproximado
        self.assertEqual(len(sec), 97)


if __name__ == "__main__":
    unittest.main()
