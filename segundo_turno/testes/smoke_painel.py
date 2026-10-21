"""Teste de fumaça do painel do 2º turno SEM streamlit/plotly instalados: executa a página inteira com substitutos
que aceitam qualquer chamada, para pegar erros de Python e de dados (colunas, tipos, merges).
Não substitui abrir a página no navegador.

    python segundo_turno/testes/smoke_painel.py
"""
import runpy
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

RAIZ = Path(__file__).resolve().parents[2]
CHAMADAS = []


class Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __getattr__(self, nome):
        return getattr(ST, nome)


class Estado(dict):
    __getattr__ = dict.get

    def __setattr__(self, k, v):
        self[k] = v


class FakeSt(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.session_state = Estado()
        self.query_params = Estado()  # usado pelo modo TV da versão de produção do comum.py
        self.botoes = set()

    # decoradores
    def _decorador(self, *a, **k):
        if a and callable(a[0]) and not k:
            return a[0]
        return lambda f: f

    cache_data = cache_resource = fragment = _decorador

    def columns(self, spec, **k):
        return [Ctx() for _ in range(spec if isinstance(spec, int) else len(spec))]

    def tabs(self, nomes):
        return [Ctx() for _ in nomes]

    def container(self, *a, **k):
        return Ctx()

    expander = spinner = form = container

    def segmented_control(self, rotulo, opcoes, default=None, **k):
        CHAMADAS.append(("segmented_control", rotulo))
        return self.session_state.get(k.get("key")) or default or opcoes[0]

    def slider(self, rotulo, mi, ma, valor, *a, **k):
        return self.session_state.get(k.get("key")) or valor

    def number_input(self, rotulo, mi, ma, valor, *a, **k):
        return valor

    def selectbox(self, rotulo, opcoes, index=0, **k):
        return opcoes[index]

    def text_input(self, *a, **k):
        return self.session_state.get(k.get("key"), "")

    def button(self, rotulo, key=None, **k):
        return key in self.botoes

    def toggle(self, *a, **k):
        return False

    def __getattr__(self, nome):  # markdown, caption, metric, dataframe, plotly_chart, ...
        def f(*a, **k):
            CHAMADAS.append((nome, a[0] if a and isinstance(a[0], str) else type(a[0]).__name__ if a else ""))
            if nome == "dataframe" and a and hasattr(a[0], "to_html"):
                a[0].to_html()  # renderiza o Styler: pega erro de formatação
            if nome == "plotly_chart" and a and hasattr(a[0], "to_json"):
                a[0].to_json()  # com o plotly de verdade: valida e serializa a figura
            return Ctx()
        return f


ST = FakeSt()
sys.modules["streamlit"] = ST
sys.modules["streamlit.components"] = MagicMock()
sys.modules["streamlit.components.v1"] = MagicMock()
try:  # usa o plotly de verdade quando estiver instalado (valida cada figura)
    import plotly.express  # noqa: F401
    import plotly.graph_objects  # noqa: F401
    PLOTLY = "real"
except ImportError:
    for m in ("plotly", "plotly.express", "plotly.graph_objects", "plotly.io"):
        sys.modules[m] = MagicMock()
    PLOTLY = "substituto"
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "segundo_turno"))


def rodar(titulo, estado=None, botoes=()):
    ST.session_state.clear()
    ST.session_state.update(estado or {})
    ST.botoes = set(botoes)
    CHAMADAS.clear()
    runpy.run_path(str(RAIZ / "segundo_turno" / "painel_2t.py"), run_name="__main__")
    n_graf = sum(1 for c in CHAMADAS if c[0] == "plotly_chart")
    n_tab = sum(1 for c in CHAMADAS if c[0] == "dataframe")
    erros = [c for c in CHAMADAS if c[0] == "error"]
    print(f"OK {titulo}: {n_graf} gráficos, {n_tab} tabelas, {len(CHAMADAS)} chamadas" + (f", erros na tela: {erros}" if erros else ""))
    return n_graf, n_tab


if __name__ == "__main__":
    import motor_2t

    print("plotly:", PLOTLY)
    rodar("ensaio 35%", {"t2_modo": "Ensaio"})
    rodar("ensaio 100%", {"t2_modo": "Ensaio", "t2_frac": 100})
    rodar("ensaio 2% + busca", {"t2_modo": "Ensaio", "t2_frac": 2, "t2_busca_ma": "imperatriz"})
    # ao vivo com o TSE "respondendo" (dados do ensaio no formato do motor)
    uf, br, mun, ma, sec = motor_2t.ensaio(0.6, semente=3)
    motor_2t.apuracao_nacional = lambda cod=None: (uf, br, {"consultado": 0, "eleicao": "6258", "avisos": ["teste"]})
    motor_2t.apuracao_ma = lambda cod=None: (mun, ma, {"consultado": 0, "avisos": []})
    motor_2t.apuracao_secoes = lambda cod=None, cdmun=None: (sec, {"publicadas": len(sec), "lidas": len(sec)})
    rodar("ao vivo (simulado)", {"t2_modo": "Ao vivo"}, botoes={"t2_ler_sec"})
    # ao vivo com o TSE fora do ar e sem leitura anterior
    motor_2t.apuracao_nacional = lambda cod=None: (None, None, {"consultado": 0, "erro": "TSE fora", "avisos": []})
    rodar("ao vivo (TSE fora)", {"t2_modo": "Ao vivo"})
    print("Painel executado sem exceções.")
