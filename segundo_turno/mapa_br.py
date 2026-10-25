"""Mapa do Brasil por município (5.570) na apuração: vermelho = Lula à frente, azul = Flávio; tom = tamanho da vantagem.

Leve para 1.000+ pessoas: o servidor lê os municípios do TSE em segundo plano (a cada ~4 min, só dos estados que já
começaram a apurar, com leitura compartilhada entre instâncias) e desenha UMA imagem PNG por rodada; cada pessoa
recebe só a imagem. Se algo falhar, devolve a última leitura ou um mapa cinza — nunca derruba a página.
"""
import gzip
import io
import json
import os
import random
import threading
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
GEO = AQUI / "dados" / "br_municipios_px.json.gz"
UF_IBGE = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI",
           "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
           "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}
# vermelho = Lula, azul = Flávio; 3 tons pela vantagem (pontos percentuais)
TONS_L = ("#F3B2BD", "#E0607A", "#C8102E")
TONS_F = ("#BCC1E2", "#7C84C6", "#2B2F8F")
SEM_VOTO, FUNDO, BORDA_UF = "#AEB4BB", "#202124", "#FFFFFF"
INTERVALO, IDADE_OK, THREADS = 240, 300, 48

_trava = threading.Lock()
_estado = {"dados": {}, "ts": 0.0, "apurados": 0, "erro": None, "rodando": False, "png": None, "png_ts": -1}


def _geo():
    if "geo" not in _estado:
        with gzip.open(GEO, "rt", encoding="utf-8") as f:
            _estado["geo"] = json.load(f)
    return _estado["geo"]


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return "".join(c for c in s if c.isalnum())


def _get(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Aggilli Intelligence)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def mapeamento(base, cod):
    """{ibge: (uf, cd_tse)} pelo cadastro de municípios do TSE; se não houver, casa pelo nome dentro do estado."""
    ciclo, ele = cod["ciclo"], cod["eleicao"]
    mapa = {}
    try:
        cm = _get(f"{base}/{ciclo}/{ele}/config/mun-e{int(ele):06d}-cm.json", timeout=20)
        for abr in cm.get("abr", []):
            uf = str(abr.get("cd", "")).lower()
            for m in abr.get("mu", []):
                if m.get("cdi") and m.get("cd"):
                    mapa[str(m["cdi"])] = (uf, str(m["cd"]))
                elif m.get("cd"):
                    mapa.setdefault(("nome", uf, _norm(m.get("nm", ""))), (uf, str(m["cd"])))
    except Exception:  # noqa: BLE001
        pass
    if not any(isinstance(k, str) for k in mapa):  # sem código do IBGE no cadastro: casa pelo nome
        nomes = _geo()["nomes"]
        por_nome = {k: v for k, v in mapa.items() if isinstance(k, tuple)}
        mapa = {}
        for ibge, nm in nomes.items():
            uf = UF_IBGE.get(ibge[:2], "").lower()
            alvo = por_nome.get(("nome", uf, _norm(nm)))
            if alvo:
                mapa[ibge] = alvo
    return {k: v for k, v in mapa.items() if isinstance(k, str)}


def _ler_mun(base, cod, uf, cd):
    ciclo, ele = cod["ciclo"], cod["eleicao"]
    t = _get(f"{base}/{ciclo}/{ele}/dados/{uf}/{uf}{cd}-c0001-e{int(ele):06d}-u.json")
    votos = {}
    for carg in t.get("carg", []):
        if str(carg.get("cd")) != "1":
            continue
        for agr in carg.get("agr", []):
            for par in agr.get("par", []):
                for c in par.get("cand", []):
                    votos[str(c.get("n"))] = float(str(c.get("vap") or 0).replace(".", "").replace(",", ".") or 0)
    pst = float(str(t.get("s", {}).get("pst") or 0).replace(".", "").replace(",", ".") or 0)
    return votos.get("13", 0.0), votos.get("22", 0.0), pst


def coletar(base, cod, ufs_com_votos, mapa):
    """Lê do TSE os municípios dos estados que já começaram a apurar. {ibge: [lula, flavio, pst]}."""
    alvos = [(ibge, uf, cd) for ibge, (uf, cd) in mapa.items() if uf.upper() in ufs_com_votos]
    out = {}

    def um(a):
        ibge, uf, cd = a
        try:
            l, f, p = _ler_mun(base, cod, uf, cd)
            if l + f > 0:
                out[ibge] = [l, f, p]
        except Exception:  # noqa: BLE001
            pass
    with ThreadPoolExecutor(THREADS) as ex:
        list(ex.map(um, alvos))
    return out


def _compartilhado():
    pasta = os.environ.get("APURACAO_COMPARTILHADO", "").strip()
    return Path(pasta) / "leituras" / "municipios_br.json" if pasta else None


def _rodada(motor):
    arq = _compartilhado()
    agora = time.time()
    if arq is not None:
        try:
            s = json.loads(arq.read_text(encoding="utf-8"))
            if agora - float(s["ts"]) < IDADE_OK:  # outra instância já leu há pouco
                with _trava:
                    _estado.update(dados=s["dados"], ts=float(s["ts"]), erro=None)
                return
        except Exception:  # noqa: BLE001
            pass
    cod = motor.codigos()
    uf_v, br_v, _ = motor.apuracao_nacional()
    if uf_v is None or not len(uf_v):
        return
    ufs = {str(u).upper() for u, p in zip(uf_v.unidade, uf_v.pst) if float(p or 0) > 0}
    if not ufs:
        return
    if "mapa" not in _estado or not _estado["mapa"]:
        _estado["mapa"] = mapeamento(motor.BASE, cod)
    dados = coletar(motor.BASE, cod, ufs, _estado["mapa"])
    if dados:
        with _trava:
            _estado.update(dados=dados, ts=time.time(), erro=None)
        if arq is not None:
            try:
                arq.parent.mkdir(parents=True, exist_ok=True)
                arq.write_text(json.dumps({"ts": time.time(), "dados": dados}), encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass


def iniciar(motor):
    """Liga a leitura em segundo plano (uma vez por servidor)."""
    with _trava:
        if _estado["rodando"]:
            return
        _estado["rodando"] = True

    def laco():
        while True:
            try:
                _rodada(motor)
            except Exception as e:  # noqa: BLE001
                _estado["erro"] = f"{type(e).__name__}: {e}"
            time.sleep(INTERVALO)
    threading.Thread(target=laco, daemon=True, name="mapa_br").start()


def ensaio(uf_v):
    """Cenário de teste: cada município herda o % do seu estado com variação e parte dos municípios apurados."""
    rng = random.Random(7)
    geo = _geo()
    pct = {str(u).upper(): (float(l) / max(float(v), 1), float(p))
           for u, l, v, p in zip(uf_v.unidade, uf_v.get("v_13", 0), uf_v.vv, uf_v.pst)}
    out = {}
    for ibge in geo["mun"]:
        uf = UF_IBGE.get(ibge[:2])
        if uf not in pct or rng.random() * 100 > pct[uf][1] * 1.3:
            continue
        p = min(.97, max(.03, pct[uf][0] + rng.gauss(0, .12)))
        out[ibge] = [p * 1000, (1 - p) * 1000, pct[uf][1]]
    return out


def cor(lula, flavio):
    tot = lula + flavio
    if tot <= 0:
        return SEM_VOTO
    m = 100 * (lula - flavio) / tot
    tons = TONS_L if m >= 0 else TONS_F
    a = abs(m)
    return tons[0] if a < 5 else tons[1] if a < 20 else tons[2]


def desenhar(dados, largura=1200):
    """PNG do mapa (bytes)."""
    from PIL import Image, ImageDraw
    geo = _geo()
    esc = geo["escala"]
    W, H = geo["w"] * esc, geo["h"] * esc
    im = Image.new("RGB", (W, H), FUNDO)
    d = ImageDraw.Draw(im)
    for ibge, aneis in geo["mun"].items():
        v = dados.get(ibge)
        c = cor(v[0], v[1]) if v else SEM_VOTO
        for a in aneis:
            pts = list(zip(a[0::2], a[1::2]))
            d.polygon(pts, fill=c, outline="#8E949B" if v is None else None)
    for aneis in geo["ufs"].values():
        for a in aneis:
            pts = list(zip(a[0::2], a[1::2]))
            d.line(pts + [pts[0]], fill=BORDA_UF, width=3)
    im = im.resize((largura, int(H * largura / W)), Image.LANCZOS)
    buf = io.BytesIO()
    try:  # paleta reduzida: imagem ~3x menor
        im.quantize(colors=48).save(buf, format="PNG", optimize=True)
    except Exception:  # noqa: BLE001
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def imagem_atual():
    """(png, n_municípios_com_votos, ts) da leitura ao vivo; redesenha só quando chegam dados novos."""
    with _trava:
        dados, ts = _estado["dados"], _estado["ts"]
        if _estado["png"] is not None and _estado["png_ts"] == ts:
            return _estado["png"], len(dados), ts
    png = desenhar(dados)
    with _trava:
        _estado.update(png=png, png_ts=ts)
    return png, len(dados), ts
