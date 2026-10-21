"""Contador de pessoas conectadas agora (para a página do 2º turno, inclusive no link ?so2t=1).

Como conta:
  1. Nesta instância do servidor: as sessões ativas do próprio Streamlit (cada aba de navegador aberta = 1 sessão).
     Se a API interna mudar, cai num registro de "batimentos" (cada sessão avisa a cada ~20 s).
  2. Entre instâncias (Cloud Run pode subir várias no domingo): cada instância grava o seu total num arquivo
     em PRESENCA_DIR (ou APURACAO_CACHE_DIR)/presenca/ e o painel soma os arquivos dos últimos 90 s.
     Só soma de verdade se essa pasta for compartilhada (bucket montado); sem isso, mostra a instância atual.
Nunca derruba a página: qualquer erro devolve o que der para contar.
"""
import json
import os
import socket
import threading
import time
import uuid
from pathlib import Path

JANELA = 90  # segundos sem sinal para uma sessão/instância deixar de contar
_ID_INSTANCIA = f"{os.environ.get('K_REVISION', 'local')}-{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
_trava = threading.Lock()
_batimentos = {}  # session_id -> último sinal (fallback)


def _pasta():
    base = os.environ.get("PRESENCA_DIR") or os.environ.get("APURACAO_CACHE_DIR") or "/tmp/eleicoes2026_2t"
    p = Path(base) / "presenca"
    try:
        p.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:  # noqa: BLE001
        return None


def _sessao_atual():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        return ctx.session_id if ctx else None
    except Exception:  # noqa: BLE001
        return None


def _sessoes_runtime():
    """Sessões com websocket aberto nesta instância, segundo o próprio Streamlit (None se a API não existir)."""
    try:
        from streamlit.runtime import Runtime
        rt = Runtime.instance()
        mgr = getattr(rt, "_session_mgr", None)
        if mgr is None:
            return None
        if hasattr(mgr, "num_active_sessions"):
            return int(mgr.num_active_sessions())
        return len(mgr.list_active_sessions())
    except Exception:  # noqa: BLE001
        return None


def bater():
    """Registra a sessão atual (chamar a cada execução do fragmento)."""
    sid = _sessao_atual() or "anon"
    agora = time.time()
    with _trava:
        _batimentos[sid] = agora
        for k in [k for k, t in _batimentos.items() if agora - t > JANELA]:
            del _batimentos[k]


def local():
    n = _sessoes_runtime()
    if n is None:
        with _trava:
            n = len(_batimentos)
    return max(int(n), 1)  # quem está vendo conta


_ultimo = {"ts": 0.0, "valor": (1, "esta instância")}
INTERVALO = 15  # s: com 1.000 pessoas o fragmento roda ~30 vezes/s; o arquivo é lido/gravado no máximo 1x a cada 15 s


def contar():
    """(total, detalhe): total de pessoas conectadas agora e de onde veio o número."""
    bater()
    agora = time.time()
    with _trava:
        if agora - _ultimo["ts"] < INTERVALO:
            return _ultimo["valor"]
        _ultimo["ts"] = agora
    valor = _contar()
    with _trava:
        _ultimo["valor"] = valor
    return valor


def _contar():
    n_local = local()
    pasta = _pasta()
    if pasta is None:
        return n_local, "esta instância"
    agora = time.time()
    try:
        (pasta / f"{_ID_INSTANCIA}.json").write_text(json.dumps({"n": n_local, "ts": agora}))
    except Exception:  # noqa: BLE001
        return n_local, "esta instância"
    total, inst = 0, 0
    for f in pasta.glob("*.json"):
        try:
            d = json.loads(f.read_text())
            if agora - float(d["ts"]) <= JANELA:
                total += int(d["n"])
                inst += 1
            elif agora - float(d["ts"]) > 3600:
                f.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            continue
    total = max(total, n_local)
    return total, f"{inst} instância(s)" if inst > 1 else "esta instância"


if __name__ == "__main__":
    print(contar())
