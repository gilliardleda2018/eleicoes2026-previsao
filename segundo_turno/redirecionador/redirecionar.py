"""Servidor mínimo que manda qualquer endereço antigo para a produção nova, mantendo caminho e parâmetros.
Ex.: https://apuracao-teste-...run.app/segundo_turno?so2t=1 → https://eleicoes2026-...run.app/segundo_turno?so2t=1"""
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DESTINO = os.environ["DESTINO"].rstrip("/")


class Redireciona(BaseHTTPRequestHandler):
    def _ir(self):
        self.send_response(301)
        self.send_header("Location", DESTINO + self.path)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    do_GET = do_HEAD = do_POST = _ir

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8080))), Redireciona).serve_forever()
