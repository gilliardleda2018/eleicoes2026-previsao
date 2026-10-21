import json
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import storage

pasta = Path("/tmp/apuracao-coleta")
subprocess.run(
    [sys.executable, "coletor_tse.py", "--once", "--saida", str(pasta)],
    check=True,
)

with sqlite3.connect(pasta / "historico_oficial.sqlite3") as db:
    capturas = db.execute("SELECT COUNT(*) FROM capturas").fetchone()[0]
    erros = db.execute("SELECT COUNT(*) FROM erros").fetchone()[0]
    # quantos alvos o turno tem (2º turno: 4 de presidente + 3 de governador do MA, se houver)
    turno, esperados, origem = db.execute(
        "SELECT turno, alvos, origem FROM rodadas ORDER BY rowid DESC LIMIT 1").fetchone()

agora = datetime.now(timezone.utc)
prefixo = (
    f"coletas/{agora:%Y/%m/%d}/"
    f"{agora:%H%M%S}-t{turno}-{uuid.uuid4().hex}"
)
bucket = storage.Client().bucket(os.environ["BUCKET_HISTORICO"])

for nome in ("historico_oficial.sqlite3", "votos_2026_coleta.csv"):
    bucket.blob(f"{prefixo}/{nome}").upload_from_filename(
        str(pasta / nome),
        if_generation_match=0,
    )

resumo = {
    "consulta_em": agora.isoformat(),
    "turno": turno,
    "codigos": origem,
    "capturas": capturas,
    "esperadas": esperados,
    "erros": erros,
    "destino": f"gs://{bucket.name}/{prefixo}/",
}
bucket.blob(f"{prefixo}/resumo.json").upload_from_string(
    json.dumps(resumo, ensure_ascii=False),
    content_type="application/json",
    if_generation_match=0,
)
print(json.dumps(resumo, ensure_ascii=False), flush=True)
sys.exit(1 if erros or capturas != esperados else 0)
