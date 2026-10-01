"""Diagnóstico da apuração ao vivo: testa, deste computador, se o TSE responde e se os arquivos são lidos.

Uso (na pasta do projeto):
    python apuracao/diagnostico.py              # ambiente oficial (resultados.tse.jus.br)
    set TSE_AMBIENTE=simulado && python apuracao/diagnostico.py   # ambiente de teste do TSE (Windows)
Antes das 17h do domingo é normal o total aparecer com 0% apurado; o importante é "arquivo OK".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motor  # noqa: E402

if __name__ == "__main__":
    falhas = 0
    for etapa, ok, detalhe in motor.diagnostico():
        falhas += not ok
        print(f"{'OK  ' if ok else 'FALHOU'}  {etapa}: {detalhe}")
    print("\nTudo certo." if not falhas else f"\n{falhas} etapa(s) com falha — veja o detalhe acima.")
