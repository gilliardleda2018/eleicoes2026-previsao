"""Insere título e miniatura (Open Graph) no HTML do Streamlit.

O WhatsApp (e Telegram, Instagram, etc.) monta a prévia do link lendo as tags
<meta property="og:..."> do HTML inicial, sem rodar JavaScript. O Streamlit
serve sempre o mesmo index.html (lido do disco a cada visita) com o título
"Streamlit" e sem imagem, então gravamos as tags nesse arquivo.

É chamado pelo próprio painel ao abrir (não depende do Start Command) e também
pode rodar à parte: `python preparar_render.py`.

A imagem fica em static/og-eleicoes.jpg (servida em /app/static/og-eleicoes.jpg,
graças a server.enableStaticServing no .streamlit/config.toml).
"""
import html
import os
import re
from pathlib import Path

TITULO = "Eleições 2026 · 2º turno · Lula × Flávio"
DESCRICAO = "2º turno presidencial: previsão, apuração ao vivo do TSE, Maranhão por município e Tuntum por seção. Desenvolvido por Aggilli Intelligence."
MARCA = "<!-- og-eleicoes -->"


def gravar_open_graph() -> str:
    """Grava as tags no index.html do Streamlit. Só age quando há URL pública."""
    import streamlit

    base = (os.environ.get("PUBLIC_URL") or os.environ.get("RENDER_EXTERNAL_URL") or "").rstrip("/")
    if not base:
        return "sem PUBLIC_URL/RENDER_EXTERNAL_URL — nada feito (uso local)"
    indice = Path(streamlit.__file__).parent / "static" / "index.html"
    original = indice.read_text(encoding="utf-8")

    t, d = html.escape(TITULO), html.escape(DESCRICAO)
    img = f"{base}/app/static/og-eleicoes.jpg"
    tags = "".join([
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:locale" content="pt_BR">',
        f'<meta property="og:url" content="{base}/">',
        f'<meta property="og:image" content="{img}">',
        f'<meta property="og:image:secure_url" content="{img}">',
        '<meta property="og:image:type" content="image/jpeg">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta name="description" content="{d}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:image" content="{img}">',
    ])

    # Remove uma inserção anterior antes de gravar de novo (idempotente).
    texto = re.sub(re.escape(MARCA) + r".*?" + re.escape(MARCA), "", original, flags=re.S)
    texto = re.sub(r"<title>.*?</title>", f"<title>{t}</title>", texto, count=1, flags=re.S)
    # Antes de </head>: o <meta charset> continua no começo (senão os acentos quebram).
    texto = texto.replace("</head>", MARCA + tags + MARCA + "</head>", 1)
    if texto != original:
        indice.write_text(texto, encoding="utf-8")
        return f"Open Graph gravado em {indice}"
    return "Open Graph já estava gravado"


if __name__ == "__main__":
    print(gravar_open_graph())
