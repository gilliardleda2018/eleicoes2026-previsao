"""Instala os cartões de redução da abstenção (aba de resultado do 2º turno) numa cópia do app que tem
alterações fora do GitHub (Cloud Shell, ~/apuracao-cloud), sem sobrescrever arquivos inteiros.

    cd ~/apuracao-cloud && python3 segundo_turno/carga/instalar_abstencao.py      # ou baixado do GitHub

Como funciona:
  1. Baixa do GitHub a versão de referência (branch segundo-turno) e a nova (branch abstencao-tres-niveis).
  2. Calcula cada trecho que mudou, com 3 linhas de contexto, e procura esse contexto no arquivo local.
  3. Só grava se TODOS os trechos encaixarem; antes faz backup em ~/backup_abstencao_<data>.
  4. Arquivos novos (abstencao_2t.py e o teste) são copiados.
Pode rodar de novo sem problema: trecho já aplicado é pulado.
"""
import difflib
import py_compile
import shutil
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = "https://raw.githubusercontent.com/gilliardleda2018/eleicoes2026-previsao"
BASE, NOVA = "segundo-turno", "abstencao-tres-niveis"
NOVOS = ["segundo_turno/abstencao_2t.py", "segundo_turno/testes/test_abstencao_2t.py"]
ALTERADOS = ["segundo_turno/motor_2t.py", "segundo_turno/painel_2t.py", "segundo_turno/testes/smoke_painel.py"]
CONTEXTO = 3


def baixar(ramo, caminho):
    with urllib.request.urlopen(f"{REPO}/{ramo}/{caminho}", timeout=30) as r:
        return r.read().decode("utf-8")


def trechos(antes, depois):
    """(texto antigo com contexto, texto novo com contexto) para cada mudança."""
    a, d = antes.splitlines(keepends=True), depois.splitlines(keepends=True)
    out = []
    for grupo in difflib.SequenceMatcher(None, a, d, autojunk=False).get_grouped_opcodes(CONTEXTO):
        i1, i2, j1, j2 = grupo[0][1], grupo[-1][2], grupo[0][3], grupo[-1][4]
        out.append(("".join(a[i1:i2]), "".join(d[j1:j2])))
    return out


def aplicar(local, mudancas, nome):
    erros = []
    for k, (velho, novo) in enumerate(mudancas, 1):
        if novo in local and novo.strip():
            print(f"   {nome}: trecho {k} já aplicado")
            continue
        n = local.count(velho)
        if n == 1:
            local = local.replace(velho, novo)
            print(f"   {nome}: trecho {k} aplicado")
        else:
            erros.append(f"{nome}: trecho {k} {'não encontrado' if n == 0 else f'aparece {n} vezes'}:\n"
                         + "".join("      | " + l for l in velho.splitlines(keepends=True)[:8]))
    return local, erros


def main():
    raiz = Path.cwd()
    if not (raiz / "segundo_turno" / "painel_2t.py").exists():
        sys.exit("Rode dentro da pasta do app (ex.: cd ~/apuracao-cloud).")
    print("== 1/4 baixando do GitHub")
    novos = {c: baixar(NOVA, c) for c in NOVOS}
    resultado, erros = {}, []
    print("== 2/4 encaixando as mudanças no código daqui")
    for c in ALTERADOS:
        local = (raiz / c).read_text(encoding="utf-8")
        res, err = aplicar(local, trechos(baixar(BASE, c), baixar(NOVA, c)), Path(c).name)
        resultado[c] = res
        erros += err
    if erros:
        print("\n⚠️  Nada foi alterado. Estes trechos não encaixaram (mande esta saída):\n")
        print("\n".join(erros))
        sys.exit(1)
    print("== 3/4 backup e gravação")
    bkp = Path.home() / f"backup_abstencao_{datetime.now():%Y%m%d_%H%M%S}"
    for c in ALTERADOS + NOVOS:
        if (raiz / c).exists():
            (bkp / c).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(raiz / c, bkp / c)
    for c, txt in {**resultado, **novos}.items():
        (raiz / c).write_text(txt, encoding="utf-8")
    print(f"   backup em {bkp}")
    print("== 4/4 conferência de sintaxe")
    for c in ALTERADOS + NOVOS:
        py_compile.compile(str(raiz / c), doraise=True)
    print("✅ Instalado. Próximo passo: testes e publicação.")


if __name__ == "__main__":
    main()
