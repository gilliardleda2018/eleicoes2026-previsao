"""Contratos numéricos da projeção pública; não validam comportamento eleitoral."""
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from motor import projetar_votos


class ProjecaoDeputados(unittest.TestCase):
    def setUp(self):
        self.base = pd.read_csv(Path(__file__).with_name("deputados_previsao.csv"))
        self.base["total_esperado"] = self.base.total_dep_est_2022 * 1.03
        self.unidades = pd.DataFrame({"unidade": self.base.CD_MUNICIPIO, "pst": 0., "vv": 0., "v_15800": 0.})

    def rodar(self, unidades=None, base=None, **kwargs):
        return projetar_votos(self.unidades if unidades is None else unidades,
                             self.base if base is None else base,
                             {"bruna": "15800"}, {"bruna": "votos_projetados"}, **kwargs)

    def test_base_real(self):
        self.assertEqual(len(self.base), 217)
        self.assertEqual(self.base.votos_projetados.sum(), 53106)
        self.assertTrue(self.base.CD_MUNICIPIO.is_unique)

    def test_sem_apuracao_reproduz_saida_anterior(self):
        _, r = self.rodar()
        np.testing.assert_allclose(r["cand"]["bruna"]["final"], [41095.884358405296, 52511.34120404972, 68588.74733375166])
        self.assertEqual(r["apurado_pct"], 0)

    def test_resultado_completo_igual_ao_contado(self):
        u = self.unidades.assign(pst=100., v_15800=self.base.votos_projetados * 1.2)
        _, r = self.rodar(u)
        np.testing.assert_allclose(r["cand"]["bruna"]["final"], [u.v_15800.sum()] * 3)

    def test_parcial_reprodutivel_e_nao_menor_que_contado(self):
        u = self.unidades.assign(pst=25., v_15800=self.base.votos_projetados * .3)
        _, r = self.rodar(u)
        _, s = self.rodar(u)
        a = r["cand"]["bruna"]["_amostras"]
        np.testing.assert_array_equal(a, s["cand"]["bruna"]["_amostras"])
        self.assertTrue(np.isfinite(a).all())
        self.assertTrue((a >= u.v_15800.sum()).all())

    def test_rejeita_duplicados(self):
        for base, u in [(pd.concat([self.base, self.base.iloc[:1]]), self.unidades),
                        (self.base, pd.concat([self.unidades, self.unidades.iloc[:1]]))]:
            with self.assertRaises(ValueError):
                self.rodar(u, base)

    def test_rejeita_votos_invalidos(self):
        for value in [-1., np.nan, np.inf]:
            with self.assertRaises(ValueError):
                self.rodar(self.unidades.assign(v_15800=value))

    def test_rejeita_percentuais_invalidos(self):
        for value in [-1., 110., np.nan]:
            with self.assertRaises(ValueError):
                self.rodar(self.unidades.assign(pst=value))

    def test_rejeita_previsao_invalida(self):
        for value in [-1., np.nan, np.inf]:
            with self.assertRaises(ValueError):
                self.rodar(base=self.base.assign(votos_projetados=value))

    def test_rejeita_municipio_desconhecido(self):
        with self.assertRaises(ValueError):
            self.rodar(self.unidades.assign(unidade=-1).iloc[:1])

    def test_rejeita_parametros_invalidos(self):
        for kwargs in [{"n_boot": 0}, {"n_boot": 1.5}, {"forca_prior": 0}, {"forca_prior": np.inf}]:
            with self.assertRaises(ValueError):
                self.rodar(**kwargs)

    def test_municipios_sem_retorno_preservam_projecao(self):
        _, r = self.rodar(self.unidades.iloc[:1])
        self.assertEqual(r["unidades"], 217)
        self.assertEqual(r["cand"]["bruna"]["previsto"], 53106)


if __name__ == "__main__":
    unittest.main()
