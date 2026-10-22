"""Troca a miniatura do link (WhatsApp/Instagram) pela foto do embate Lula × Flávio (static/og-2turno.jpg).
Ajusta o preparar_render.py de produção (que grava as tags Open Graph). Idempotente. Uso, na raiz do projeto:
    python3 segundo_turno/trocar_imagem_link.py
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
pr = RAIZ / "preparar_render.py"
if not (RAIZ / "static" / "og-2turno.jpg").exists():
    raise SystemExit("PARE: falta static/og-2turno.jpg (rode o git checkout com static/og-2turno.jpg)")
t = pr.read_text(encoding="utf-8")
antes = sorted(set(re.findall(r"/app/static/[\w./-]+?\.(?:jpe?g|png|webp)(?:\?v=\w+)?", t)))
print("imagem(ns) usada(s) hoje no link:", antes or "nenhuma encontrada")
if not antes:
    raise SystemExit("PARE: não achei a imagem no preparar_render.py — rode: grep -n \"og:image\\|static\" preparar_render.py e me mande")
novo = re.sub(r"/app/static/[\w./-]+?\.(?:jpe?g|png|webp)(?:\?v=\w+)?", "/app/static/og-2turno.jpg?v=2210", t)
novo = re.sub(r'(og:image:type" content=")[^"]+', r"\1image/jpeg", novo)
novo = re.sub(r'^TITULO = ".*"$', 'TITULO = "Eleições 2026 · 2º turno · Lula × Flávio"', novo, flags=re.M)
novo = re.sub(r'^DESCRICAO = ".*"$', 'DESCRICAO = "Mais de 14 milhões de eleitores de Lula não votaram no 1º turno: veja onde '
              'eles estão no Brasil, no Maranhão e em Tuntum. Apuração ao vivo no domingo, 25/10. Aggilli Intelligence."',
              novo, flags=re.M)
if novo != t:
    pr.write_text(novo, encoding="utf-8")
    print("preparar_render.py: miniatura do link = foto do embate (og-2turno.jpg)")
else:
    print("preparar_render.py: já estava com a foto do embate")
