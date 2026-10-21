"""Teste offline do coletor (sem rede): códigos por turno e alvos."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import coletor_tse as c
cfg = {"pl": [{"cd": "3220", "dt": "04/10/2026", "e": [{"cd": "6257", "t": "1", "abr": [{"cd": "BR", "cp": [{"cd": "1"}]}]},
                                                     {"cd": "6259", "t": "1", "abr": [{"cd": "MA", "cp": [{"cd": "3"}, {"cd": "5"}, {"cd": "6"}, {"cd": "7"}]}]}]},
              {"cd": "3221", "dt": "25/10/2026", "e": [{"cd": "6258", "t": "2", "abr": [{"cd": "BR", "cp": [{"cd": "1"}]}]},
                                                     {"cd": "6260", "t": "2", "abr": [{"cd": "SP", "cp": [{"cd": "3"}]}]}]}]}
e2, o = c.eleicoes_do_turno(2, cfg); assert e2 == {1: 6258} and o == "config do TSE", e2
e1, _ = c.eleicoes_do_turno(1, cfg); assert e1 == {1: 6257, 3: 6259, 5: 6259, 6: 6259, 7: 6259}, e1
cfg["pl"][1]["e"][1]["abr"].append({"cd": "MA", "cp": [{"cd": "3"}]})
assert c.eleicoes_do_turno(2, cfg)[0] == {1: 6258, 3: 6260}
a = list(c.alvos({1: 6258}))
assert len(a) == 4 and a[-1]["url"].endswith("/6258/dados/br/br-c0001-e006258-u.json"), a[-1]
assert a[1]["url"].endswith("/6258/dados/ma/ma09393-c0001-e006258-u.json"), a[1]
assert len(list(c.alvos(e1))) == 16  # igual ao 1º turno original
print("OK: 2º turno =", e2, "| alvos:", len(a))
