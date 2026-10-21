"""Encaixa a página do 2º turno no código que está em produção (apuracao-cloud), sem sobrescrever nada dele.

Uso, na raiz do projeto, depois do `git merge` (mantendo as versões de produção de app.py e comum.py):
    python3 segundo_turno/integrar_producao.py

O que faz (só se ainda não estiver feito):
  1. app.py   — registra a página do 2º turno e a torna a página inicial do link.
  2. comum.py — põe "🗳️ 2º turno" na barra de navegação.
  3. Confere se o projetor de apuracao/motor.py (usado pelo ao vivo do 2º turno) tem a assinatura esperada.
Não apaga nem reescreve outras partes dos arquivos. Mostra o que mudou.
"""
import inspect
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ok = True


def avisar(msg):
    print("  " + msg)


# ---------------------------------------------------------------- 1) app.py
app = RAIZ / "app.py"
t = app.read_text(encoding="utf-8")
if "segundo_turno" in t and "painel_2t.py" in t:
    avisar("app.py: página do 2º turno já registrada")
else:
    m = re.search(r"paginas\s*=\s*\[\s*\n", t)
    if not m:
        ok = False
        avisar("app.py: NÃO encontrei a lista `paginas = [` — me mande o app.py")
    else:
        t = t.replace('url_path="inicio", default=True', 'url_path="inicio"', 1)
        linha = ('    st.Page(RAIZ / "segundo_turno" / "painel_2t.py", title="2º turno · Lula × Flávio", icon="🗳️",\n'
                 '            url_path="segundo_turno", default=True),\n')
        t = t[:m.end()] + linha + t[m.end():]
        app.write_text(t, encoding="utf-8")
        avisar("app.py: 2º turno registrado como página inicial (Início continua em /inicio)")
# créditos do rodapé padrão: a página do 2º turno já tem os dela
t = app.read_text(encoding="utf-8")
if 'not in ("", "inicio")' in t:
    app.write_text(t.replace('not in ("", "inicio")', 'not in ("", "inicio", "segundo_turno")', 1), encoding="utf-8")
    avisar("app.py: rodapé padrão desligado na página do 2º turno (ela tem créditos próprios)")
elif "rodape_desenvolvedor()" in t and "segundo_turno" not in t.split("rodape_desenvolvedor()")[0][-300:]:
    avisar("app.py: o rodapé padrão pode aparecer duas vezes no 2º turno (só estética; me avise se aparecer)")

# ---------------------------------------------------------------- 2) comum.py
comum = RAIZ / "comum.py"
c = comum.read_text(encoding="utf-8")
if '"2t":' in c:
    avisar("comum.py: barra de navegação já tem o 2º turno")
else:
    m = re.search(r'PAGINAS\s*=\s*\{\s*"inicio":\s*\("inicio\.py",\s*"[^"]*"\),', c)
    if not m:
        ok = False
        avisar("comum.py: NÃO encontrei `PAGINAS = {\"inicio\": ...` — me mande o comum.py")
    else:
        c = c[:m.end()] + ' "2t": ("segundo_turno/painel_2t.py", "🗳️ 2º turno"),' + c[m.end():]
        comum.write_text(c, encoding="utf-8")
        avisar("comum.py: 2º turno incluído na barra de navegação")

# ---------------------------------------------------------------- 3) projetor
sys.path.insert(0, str(RAIZ / "apuracao"))
try:
    import motor  # noqa: E402
    params = list(inspect.signature(motor.projetar).parameters)
    esperado = ["unidades", "previsao", "numeros", "cand_a", "cand_b", "col_prev_a", "col_prev_b", "col_validos",
                "chave_prev"]
    if params[:len(esperado)] == esperado:
        avisar("apuracao/motor.py: projetar() compatível com o 2º turno")
    else:
        ok = False
        avisar(f"apuracao/motor.py: projetar() mudou ({params}) — me mande o arquivo")
except Exception as e:  # noqa: BLE001
    ok = False
    avisar(f"apuracao/motor.py: não consegui importar ({type(e).__name__}: {e})")

print("PRONTO" if ok else "PARE: algo precisa de ajuste (veja acima)")
sys.exit(0 if ok else 1)
