"""Acaba com o aviso "Page not found" ao abrir /segundo_turno.

No Streamlit, a página padrão (default=True) só responde na raiz "/" — o url_path dela é ignorado. Por isso quem abre
.../segundo_turno?so2t=1 vê "Page not found" e só depois a página. Aqui a página padrão ganha um nome interno e
/segundo_turno e /2turno viram endereços escondidos da MESMA página. Idempotente. Uso (na raiz do projeto):
    python3 segundo_turno/corrigir_links.py
"""
import re
from pathlib import Path

app = Path(__file__).resolve().parents[1] / "app.py"
t = app.read_text(encoding="utf-8")
if 'url_path="2turno"' in t:
    print("app.py: já corrigido")
else:
    m = re.search(r'(\s*)st\.Page\(RAIZ / "segundo_turno" / "painel_2t\.py",(.*?)url_path="segundo_turno", default=True\),',
                  t, flags=re.S)
    if not m:
        raise SystemExit("PARE: não achei a página do 2º turno no app.py")
    ind = m.group(1).replace("\n", "")
    novo = (f'{m.group(1)}st.Page(RAIZ / "segundo_turno" / "painel_2t.py",{m.group(2)}url_path="pagina_2t", default=True),\n'
            f'{ind}st.Page(RAIZ / "segundo_turno" / "painel_2t.py", title="2º turno", url_path="segundo_turno", '
            f'visibility="hidden"),\n'
            f'{ind}st.Page(RAIZ / "segundo_turno" / "painel_2t.py", title="2º turno", url_path="2turno", '
            f'visibility="hidden"),')
    t = t[:m.start()] + novo + t[m.end():]
    t = t.replace('not in ("", "inicio", "segundo_turno")', 'not in ("", "inicio", "segundo_turno", "2turno", "pagina_2t")')
    app.write_text(t, encoding="utf-8")
    print("app.py: /segundo_turno e /2turno abrem a página do 2º turno sem aviso")
