"""Leitura do Boletim de Urna (BU) publicado pelo TSE em resultados.tse.jus.br/.../arquivo-urna/.

O arquivo `*-bu.dat` é DER (ASN.1). Não usamos o esquema completo: percorremos a árvore e reconhecemos as
estruturas pela forma, como foi conferido com os BUs reais do 1º turno de 2026 (as 97 seções de Tuntum somaram
exatamente o total oficial do município):

- ResultadoVotacaoPorEleicao: SEQUENCE { idEleicao INTEGER, qtdEleitoresAptos INTEGER, ... }
- ResultadoVotacao:           SEQUENCE { tipoCargo ENUMERATED, qtdComparecimento INTEGER, ... }
- TotalVotosVotavel:          SEQUENCE { [1] tipoVoto, [2] quantidadeVotos, [3] { partido, codigo, ... }?, ... }
  tipoVoto 1 = nominal, 2 = branco, 3 = nulo (outros tipos somam como "outros_tipos").
- Identificação da seção:     SEQUENCE { SEQUENCE { municipio, zona }, local, secao }
O conteúdo do BU vem dentro de um envelope (OCTET STRING com DER dentro), que também é aberto.
"""
from dataclasses import dataclass, field


@dataclass
class No:
    cls: int
    cons: bool
    tag: int
    raw: bytes = b""
    filhos: list = field(default_factory=list)

    @property
    def inteiro(self):
        return int.from_bytes(self.raw, "big") if self.raw and not self.cons and not self.filhos else None


def _ler(b, ini, fim, profundidade=0):
    nos = []
    i = ini
    while i < fim:
        t = b[i]
        i += 1
        cls, cons, tag = t >> 6, bool(t & 0x20), t & 0x1F
        if tag == 0x1F:
            tag = 0
            while b[i] & 0x80:
                tag = (tag << 7) | (b[i] & 0x7F)
                i += 1
            tag = (tag << 7) | b[i]
            i += 1
        n = b[i]
        i += 1
        if n & 0x80:
            k = n & 0x7F
            n = int.from_bytes(b[i:i + k], "big")
            i += k
        if i + n > fim:
            raise ValueError("DER truncado")
        no = No(cls, cons, tag)
        if cons:
            no.filhos = _ler(b, i, i + n, profundidade + 1)
        else:
            no.raw = bytes(b[i:i + n])
            # OCTET STRING com DER dentro (envelope do BU)
            if n > 2 and b[i] in (0x30, 0x60, 0x61) and profundidade < 12:
                try:
                    dentro = _ler(b, i, i + n, profundidade + 1)
                    if dentro:
                        no.filhos = dentro
                except (ValueError, IndexError):
                    pass
        nos.append(no)
        i += n
    return nos


def arvore(dados: bytes):
    return _ler(memoryview(dados), 0, len(dados))


def _int(no):
    return int.from_bytes(no.raw, "big") if (no and not no.cons and no.raw and len(no.raw) <= 8) else None


def extrair(dados: bytes, eleicao: int, municipio: int | None = None):
    """Votos de uma eleição (ex.: 6258 = presidente 2º turno) num BU.
    Retorna {"aptos", "comparecimento", "votos": {numero: qtd}, "brancos", "nulos", "outros_tipos", "local", "secao"}."""
    raiz = arvore(dados)
    out = {"aptos": None, "comparecimento": None, "votos": {}, "brancos": 0, "nulos": 0, "outros_tipos": 0,
           "local": None, "secao": None, "achou_eleicao": False}

    def ident(nos):
        for no in nos:
            f = no.filhos
            if f:
                f0 = f[0].filhos
                if (len(f) >= 3 and f0 and len(f0) >= 2 and _int(f0[0]) is not None and _int(f[1]) is not None
                        and (municipio is None or _int(f0[0]) == municipio) and out["local"] is None):
                    out["local"], out["secao"] = _int(f[1]), _int(f[2])
                    return
                ident(f)

    def votos(nos):
        for no in nos:
            f = no.filhos
            if not f:
                continue
            if (len(f) >= 2 and f[0].cls == 2 and f[0].tag == 1 and f[1].cls == 2 and f[1].tag == 2
                    and not f[0].cons and not f[1].cons):
                tipo, q = _int(f[0]), _int(f[1]) or 0
                if tipo == 1 and len(f) >= 3 and f[2].cls == 2 and f[2].tag == 3 and len(f[2].filhos) >= 2:
                    num = str(_int(f[2].filhos[1]))
                    out["votos"][num] = out["votos"].get(num, 0) + q
                elif tipo == 2:
                    out["brancos"] += q
                elif tipo == 3:
                    out["nulos"] += q
                else:
                    out["outros_tipos"] += q
                continue
            if f[0].cls == 0 and f[0].tag == 10 and len(f) >= 2 and _int(f[1]) is not None and out["comparecimento"] is None:
                out["comparecimento"] = _int(f[1])
            votos(f)

    def achar(nos):
        for no in nos:
            f = no.filhos
            if not f:
                continue
            if len(f) >= 2 and f[0].cls == 0 and f[0].tag == 2 and _int(f[0]) == eleicao and _int(f[1]) is not None:
                out["achou_eleicao"] = True
                out["aptos"] = _int(f[1])
                votos(f[2:])
                return
            achar(f)

    ident(raiz)
    achar(raiz)
    return out


# ---------------------------------------------------------------- utilitário para testes (gera um BU sintético)
def _der(tag, conteudo: bytes):
    n = len(conteudo)
    if n < 0x80:
        tam = bytes([n])
    else:
        nb = n.to_bytes((n.bit_length() + 7) // 8, "big")
        tam = bytes([0x80 | len(nb)]) + nb
    return bytes([tag]) + tam + conteudo


def _i(v, tag=0x02):
    return _der(tag, v.to_bytes(max(1, (v.bit_length() + 8) // 8), "big"))


def bu_sintetico(eleicao, aptos, comparecimento, nominais: dict, brancos, nulos, municipio=9393, zona=79, local=1015,
                 secao=1):
    """BU mínimo com a mesma forma dos reais (para testes sem internet)."""
    seq = lambda *p: _der(0x30, b"".join(p))
    totais = []
    for num, q in nominais.items():
        totais.append(seq(_i(1, 0x81), _i(q, 0x82), _der(0xA3, _i(int(num[:2])) + _i(int(num)) + _i(1)), _der(0x04, b"\0" * 8)))
    totais.append(seq(_i(2, 0x81), _i(brancos, 0x82), _der(0x04, b"\0" * 8)))
    totais.append(seq(_i(3, 0x81), _i(nulos, 0x82), _der(0x04, b"\0" * 8)))
    cargo = seq(seq(_i(1, 0x81)), _i(1), seq(*totais))
    resultado = seq(_i(1, 0x0A), _i(comparecimento), seq(cargo))
    por_eleicao = seq(_i(eleicao), _i(aptos), _i(aptos), _i(0), seq(resultado))
    identificacao = _der(0xA0, seq(seq(_i(municipio), _i(zona)), _i(local), _i(secao)))
    bu = seq(seq(_der(0x18, b"20261025T170000")), identificacao, seq(por_eleicao))
    return seq(_i(1), _der(0x04, bu))
