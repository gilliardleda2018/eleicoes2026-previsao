"""Testes do motor do 2º turno e do leitor de boletins de urna, sem internet (o TSE é simulado).

    python -m unittest discover -s segundo_turno/testes -p "test_*.py" -v
"""
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import bu  # noqa: E402
import motor_2t  # noqa: E402


def unificado(pst, lula, flavio, brancos=10, nulos=20):
    def num(v):
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if isinstance(v, float) else str(v)
    return {"tf": "n", "dt": "25/10/2026", "ht": "18:00:00",
            "s": {"pst": num(float(pst)), "ts": "100", "st": str(int(pst))},
            "e": {"te": "1000", "c": "800", "a": "200"},
            "v": {"vv": str(lula + flavio), "vb": str(brancos), "tvn": str(nulos)},
            "carg": [{"cd": "1", "agr": [{"par": [{"cand": [{"n": "13", "vap": str(lula)}]}]},
                                          {"par": [{"cand": [{"n": "22", "vap": str(flavio)}]}]}]}]}


class TSEFalso:
    """Serve respostas por trecho de URL; 404 para o resto."""

    def __init__(self, rotas):
        self.rotas, self.pedidos = rotas, []

    def __call__(self, url, timeout=15, binario=False):
        self.pedidos.append(url)
        for trecho, resp in self.rotas.items():
            if trecho in url:
                if isinstance(resp, Exception):
                    raise resp
                return resp
        raise urllib.error.HTTPError(url, 404, "não publicado", {}, None)


class TestBU(unittest.TestCase):
    def test_boletim_real_do_1o_turno(self):
        dados = (AQUI / "fixtures" / "bu_tuntum_z0079_s0001_1t_reduzido.dat").read_bytes()
        r = bu.extrair(dados, 6257, 9393)
        self.assertTrue(r["achou_eleicao"])
        self.assertEqual(r["votos"], {"13": 160, "14": 2, "22": 69, "70": 8})
        self.assertEqual((r["brancos"], r["nulos"], r["aptos"], r["comparecimento"]), (3, 7, 322, 249))
        self.assertEqual((r["local"], r["secao"]), (1015, 1))
        self.assertEqual(sum(r["votos"].values()) + r["brancos"] + r["nulos"], r["comparecimento"])

    def test_eleicao_ausente(self):
        dados = (AQUI / "fixtures" / "bu_tuntum_z0079_s0001_1t_reduzido.dat").read_bytes()
        self.assertFalse(bu.extrair(dados, 6258, 9393)["achou_eleicao"])

    def test_sintetico_2o_turno(self):
        b = bu.bu_sintetico(6258, 300, 250, {"13": 150, "22": 80}, 5, 15, secao=7, local=1260)
        r = bu.extrair(b, 6258, 9393)
        self.assertEqual(r["votos"], {"13": 150, "22": 80})
        self.assertEqual((r["local"], r["secao"], r["brancos"], r["nulos"]), (1260, 7, 5, 15))


class TestMotor(unittest.TestCase):
    def setUp(self):
        self._get = motor_2t._get
        self.tmp = tempfile.TemporaryDirectory()
        motor_2t.CACHE = Path(self.tmp.name)
        motor_2t.ESPERA = 0

    def tearDown(self):
        motor_2t._get = self._get
        self.tmp.cleanup()

    def test_codigos_pelo_config(self):
        cfg = {"pl": [{"cd": "3221", "dt": "25/10/2026", "e": [
            {"cd": "6288", "t": "1", "nm": "Consulta Popular", "abr": [{"cp": [{"cd": "26"}]}]},
            {"cd": "6258", "t": "2", "nm": "Federal 2º Turno", "abr": [{"cp": [{"cd": "1"}]}]}]}]}
        motor_2t._get = TSEFalso({"ele-c.json": cfg})
        c = motor_2t.codigos()
        self.assertEqual((c["eleicao"], c["pleito"], c["origem"]), ("6258", "3221", "config do TSE"))

    def test_codigos_sem_config(self):
        motor_2t._get = TSEFalso({"ele-c.json": urllib.error.URLError("fora")})
        c = motor_2t.codigos()
        self.assertEqual((c["eleicao"], c["pleito"]), ("6258", "3221"))

    def test_unificado_e_reserva_simplificado(self):
        cod = {"ciclo": "ele2026", "eleicao": "6258"}
        simpl = {"pst": "12,50", "vv": "300", "e": "1000", "c": "400", "cand": [{"n": "13", "vap": "200"},
                                                                                 {"n": "22", "vap": "100"}]}
        motor_2t._get = TSEFalso({"dados-simplificados/ba/ba-c0001-e006258-r.json": simpl})
        t = motor_2t.ler_total(cod, "ba")
        self.assertEqual((t["leiaute"], t["pst"], t["votos"]["13"]), ("simplificado", 12.5, 200))
        motor_2t._get = TSEFalso({"dados/ba/ba-c0001-e006258-u.json": unificado(37.5, 700, 300)})
        t = motor_2t.ler_total(cod, "ba")
        self.assertEqual((t["leiaute"], t["pst"], t["votos"]["22"], t["validos"]), ("unificado", 37.5, 300, 1000))

    def test_brasil_cai_para_soma_das_ufs_e_depois_cache(self):
        cod = {"ciclo": "ele2026", "eleicao": "6258", "origem": "teste"}
        rotas = {f"dados/{u.lower()}/{u.lower()}-c0001": unificado(50.0, 60, 40) for u in motor_2t.UFS}
        motor_2t._get = TSEFalso(rotas)
        uf, br, info = motor_2t.apuracao_nacional(cod)
        self.assertEqual(len(uf), 28)
        self.assertEqual(br["leiaute"], "soma das UFs")
        self.assertEqual(br["votos"]["13"], 60 * 28)
        self.assertTrue(any("soma das UFs" in a for a in info["avisos"]))
        motor_2t._get = TSEFalso({})  # TSE fora do ar: usa a última leitura boa
        uf2, br2, info2 = motor_2t.apuracao_nacional(cod)
        self.assertTrue(info2["desatualizado"])
        self.assertEqual(br2["votos"]["13"], 60 * 28)

    def test_boletins_de_secao_com_cache(self):
        cod = {"ciclo": "ele2026", "eleicao": "6258", "pleito": "3221"}
        cs = {"abr": [{"cd": "ma", "mu": [{"cd": "09393", "zon": [{"cd": "0079", "sec": [
            {"ns": "0001", "da": "25/10/2026", "ha": "17:20:00"}, {"ns": "0002", "da": "25/10/2026", "ha": "17:25:00"}]}]}]}]}
        aux = {"st": "Totalizada", "hashes": [{"hash": "abc", "st": "Totalizado", "arq": [{"nm": "x-bu.dat", "tp": "bu"}]}]}
        b1 = bu.bu_sintetico(6258, 300, 250, {"13": 150, "22": 80}, 5, 15, secao=1)
        rotas = {"ma-p003221-cs.json": cs, "s0001-aux.json": aux, "0001/abc/x-bu.dat": b1}
        tse = TSEFalso(rotas)
        motor_2t._get = tse
        tab, info = motor_2t.apuracao_secoes(cod, "09393")
        self.assertEqual((info["publicadas"], info["lidas"]), (2, 1))  # seção 2 ainda sem boletim
        self.assertEqual(tab.iloc[0][["lula", "flavio", "local"]].tolist(), [150, 80, 1015])
        antes = len(tse.pedidos)
        motor_2t.apuracao_secoes(cod, "09393")
        self.assertFalse(any("x-bu.dat" in u for u in tse.pedidos[antes:]))  # boletim lido do cache

    def test_ensaio_e_projecao(self):
        uf, br, mun, ma, sec = motor_2t.ensaio(1.0, semente=1)
        self.assertAlmostEqual(br["pst"], 100, delta=0.5)
        import pandas as pd
        prev = pd.read_csv(AQUI.parent / "resultados" / "ufs_2t.csv")
        _, r = motor_2t.projetar(uf, prev, "uf")
        real = 100 * br["votos"]["13"] / br["validos"]
        self.assertAlmostEqual(r["final_a"][1], real, delta=0.3)


if __name__ == "__main__":
    unittest.main()
