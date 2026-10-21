"""Teste de carga da página do 2º turno: abre N "pessoas" (sessões Streamlit de verdade, via websocket),
cada uma carrega a página inteira e depois fica conectada recebendo as atualizações automáticas
(ao vivo a cada 60 s, contador a cada 30 s), exatamente como um navegador faz.

    pip install aiohttp "streamlit==<a mesma versão da produção>"   # só para os protos
    python carga_2t.py --url https://SEU-SERVICO.run.app --pessoas 300 --rampa 120 --duracao 300

Variáveis de ambiente equivalentes (para rodar como Cloud Run Job com várias tarefas):
    URL, PESSOAS, RAMPA, DURACAO, CAMINHO
Mede: tempo até a página terminar de carregar, tempo das atualizações automáticas, erros na tela
(exceções do Python), quedas de conexão e volume recebido. No fim imprime uma linha "RESUMO {...}".
"""
import argparse
import asyncio
import json
import os
import random
import statistics
import time
from urllib.parse import urlsplit

import aiohttp
from streamlit.proto.BackMsg_pb2 import BackMsg
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg

OK_TOTAL = ForwardMsg.ScriptFinishedStatus.Value("FINISHED_SUCCESSFULLY")
OK_FRAG = ForwardMsg.ScriptFinishedStatus.Value("FINISHED_FRAGMENT_RUN_SUCCESSFULLY")


class Placar:
    def __init__(self):
        self.carga, self.frag, self.erros_tela, self.falhas = [], [], 0, []
        self.bytes, self.conectados, self.max_conectados, self.carregadas = 0, 0, 0, 0

    def resumo(self):
        def p(v, q):
            return round(statistics.quantiles(v, n=100, method="inclusive")[q - 1], 2) if len(v) >= 2 else (round(v[0], 2) if v else None)
        return {"carregadas": self.carregadas, "pico_conectados": self.max_conectados,
                "carga_s_p50": p(self.carga, 50), "carga_s_p95": p(self.carga, 95), "carga_s_max": round(max(self.carga), 2) if self.carga else None,
                "atualizacoes": len(self.frag), "atualizacao_s_p50": p(self.frag, 50), "atualizacao_s_p95": p(self.frag, 95),
                "erros_na_tela": self.erros_tela, "falhas": len(self.falhas),
                "tipos_de_falha": sorted({f.split(":")[0] for f in self.falhas})[:8],
                "MB_recebidos": round(self.bytes / 1e6, 1)}


def rerun(query, page_hash="", page_name="", fragment="", auto=False):
    m = BackMsg()
    cs = m.rerun_script
    cs.query_string = query
    cs.page_script_hash = page_hash
    cs.page_name = page_name
    cs.fragment_id = fragment
    cs.is_auto_rerun = auto
    cs.context_info.timezone = "America/Sao_Paulo"
    cs.context_info.timezone_offset = 180
    cs.context_info.locale = "pt-BR"
    return m.SerializeToString()


async def pessoa(i, base, caminho, query, duracao, placar, timeout_carga):
    partes = urlsplit(base)
    ws_url = ("wss" if partes.scheme == "https" else "ws") + f"://{partes.netloc}/_stcore/stream"
    jar = aiohttp.CookieJar(unsafe=True)  # guarda o cookie de afinidade de sessão do Cloud Run
    try:
        async with aiohttp.ClientSession(cookie_jar=jar, timeout=aiohttp.ClientTimeout(total=None)) as s:
            async with s.get(f"{base}/{caminho}?{query}", timeout=aiohttp.ClientTimeout(total=60)) as r:
                await r.read()
                if r.status >= 500:
                    raise RuntimeError(f"HTTP {r.status}: página inicial")
            token = next((c.value for c in jar if c.key == "_streamlit_xsrf"), "PLACEHOLDER_AUTH_TOKEN")
            async with s.ws_connect(ws_url, protocols=("streamlit", token), max_msg_size=0, heartbeat=25,
                                    headers={"Origin": base}, compress=15) as ws:
                placar.conectados += 1
                placar.max_conectados = max(placar.max_conectados, placar.conectados)
                try:
                    t0 = time.monotonic()
                    await ws.send_bytes(rerun(query, page_name=caminho))
                    page_hash, pend, fragmentos = "", {}, {}
                    fim = t0 + duracao
                    carregou = False
                    while time.monotonic() < fim:
                        espera = 5.0 if carregou else max(0.1, t0 + timeout_carga - time.monotonic())
                        try:
                            msg = await ws.receive(timeout=espera)
                        except asyncio.TimeoutError:
                            if not carregou:
                                raise RuntimeError("timeout: a página não terminou de carregar")
                            msg = None
                        if msg is not None:
                            if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                raise RuntimeError(f"conexão caiu ({msg.type.name})")
                            if msg.type != aiohttp.WSMsgType.BINARY:
                                continue
                            placar.bytes += len(msg.data)
                            f = ForwardMsg()
                            f.ParseFromString(msg.data)
                            tipo = f.WhichOneof("type")
                            if tipo == "new_session":
                                page_hash = f.new_session.page_script_hash
                            elif tipo == "delta" and f.delta.WhichOneof("type") == "new_element" \
                                    and f.delta.new_element.WhichOneof("type") == "exception":
                                placar.erros_tela += 1
                            elif tipo == "auto_rerun":
                                fragmentos[f.auto_rerun.fragment_id] = f.auto_rerun.interval
                            elif tipo == "script_finished":
                                if f.script_finished == OK_TOTAL and not carregou:
                                    carregou = True
                                    placar.carregadas += 1
                                    placar.carga.append(time.monotonic() - t0)
                                    agora = time.monotonic()
                                    pend = {fid: agora + iv * random.uniform(.3, 1) for fid, iv in fragmentos.items()}
                                elif pend.get("_em_curso"):
                                    inicio = pend.pop("_em_curso")
                                    if f.script_finished == OK_FRAG:
                                        placar.frag.append(time.monotonic() - inicio)
                        # dispara as atualizações automáticas como o navegador faria
                        if pend.get("_em_curso") and time.monotonic() - pend["_em_curso"] > 120:
                            raise RuntimeError("timeout: atualização automática sem resposta em 120 s")
                        if carregou and "_em_curso" not in pend:
                            agora = time.monotonic()
                            for fid, quando in list(pend.items()):
                                if not fid.startswith("_") and agora >= quando:
                                    pend[fid] = agora + fragmentos[fid]
                                    pend["_em_curso"] = agora
                                    await ws.send_bytes(rerun(query, page_hash, caminho, fid, True))
                                    break
                finally:
                    placar.conectados -= 1
    except Exception as e:  # noqa: BLE001
        placar.falhas.append(f"{type(e).__name__}: {e}"[:160])


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("URL", ""))
    ap.add_argument("--caminho", default=os.environ.get("CAMINHO", "segundo_turno"))
    ap.add_argument("--query", default=os.environ.get("QUERY", "so2t=1&modo=vivo"))
    ap.add_argument("--pessoas", type=int, default=int(os.environ.get("PESSOAS", 100)))
    ap.add_argument("--rampa", type=float, default=float(os.environ.get("RAMPA", 60)), help="segundos para todos entrarem")
    ap.add_argument("--duracao", type=float, default=float(os.environ.get("DURACAO", 240)), help="segundos que cada um fica")
    ap.add_argument("--timeout-carga", type=float, default=90)
    a = ap.parse_args()
    if not a.url:
        ap.error("informe --url (endereço do serviço)")
    base = a.url.rstrip("/")
    placar = Placar()

    async def relatorio():
        while True:
            await asyncio.sleep(15)
            r = placar.resumo()
            print(f"[{time.strftime('%H:%M:%S')}] conectados {placar.conectados} · carregadas {r['carregadas']} · "
                  f"carga p95 {r['carga_s_p95']} s · atualização p95 {r['atualizacao_s_p95']} s · "
                  f"falhas {r['falhas']} · erros na tela {r['erros_na_tela']}", flush=True)

    rel = asyncio.create_task(relatorio())
    tarefas = []
    for i in range(a.pessoas):
        tarefas.append(asyncio.create_task(pessoa(i, base, a.caminho, a.query, a.duracao, placar, a.timeout_carga)))
        await asyncio.sleep(a.rampa / max(a.pessoas, 1))
    await asyncio.gather(*tarefas)
    rel.cancel()
    r = placar.resumo()
    r["pessoas"] = a.pessoas
    if placar.falhas:
        r["exemplos_de_falha"] = placar.falhas[:3]
    print("RESUMO " + json.dumps(r, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
