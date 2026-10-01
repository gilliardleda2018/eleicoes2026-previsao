"""Gera a miniatura da Aggilli para compartilhar a página inicial (static/compartilhar/inicio_aggilli.jpg)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from momento import _f

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "static" / "compartilhar" / "inicio_aggilli.jpg"
CIANO, BRANCO, SUAVE = (34, 211, 238), (255, 255, 255), (200, 225, 238)


def gerar(w=1200, h=630):
    img = Image.new("RGB", (w, h), (11, 22, 40))
    g = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(g)
    d.ellipse((-260, -320, 520, 360), fill=(20, 120, 160))
    d.ellipse((760, 300, 1500, 980), fill=(150, 20, 50))
    img = Image.blend(img, g.filter(ImageFilter.GaussianBlur(150)), .55).convert("RGBA")
    d = ImageDraw.Draw(img)
    # moldura fina
    camada = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(camada).rounded_rectangle((24, 24, w - 24, h - 24), 34, outline=(255, 255, 255, 60), width=2)
    img.alpha_composite(camada)
    logo = Image.open(RAIZ / "assets" / "aggilli_logo.png").convert("RGBA")
    lw = 430
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, ((w - lw) // 2, 52))
    d = ImageDraw.Draw(img)

    def centro(y, txt, fonte, cor):
        d.text(((w - d.textlength(txt, font=fonte)) / 2, y), txt, font=fonte, fill=cor)

    centro(240, "ELEIÇÕES 2026  ·  4 DE OUTUBRO", _f(26, 800), CIANO)
    f = _f(58, 900)
    a, e = "Modelo Preditivo ", "&"
    x = (w - d.textlength(a + e, font=f)) / 2
    d.text((x, 282), a, font=f, fill=BRANCO)
    d.text((x + d.textlength(a, font=f), 282), e, font=f, fill=(254, 223, 0))
    centro(346, "Apuração em Tempo Real", f, BRANCO)
    centro(432, "Presidente  ·  Governo do MA  ·  Senado  ·  Deputados  ·  Tuntum", _f(26, 700), SUAVE)
    # pílula
    txt = "Apuração ao vivo · domingo, a partir das 17h"
    fp = _f(28, 800)
    tw = d.textlength(txt, font=fp)
    x0 = (w - tw) / 2 - 40
    camada = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(camada).rounded_rectangle((x0, 484, x0 + tw + 80, 540), 28, fill=(255, 255, 255, 30),
                                             outline=(255, 255, 255, 90), width=2)
    img.alpha_composite(camada)
    d = ImageDraw.Draw(img)
    d.ellipse((x0 + 20, 504, x0 + 36, 520), fill=(34, 197, 94))
    d.text((x0 + 50, 495), txt, font=fp, fill=BRANCO)
    centro(566, "aggillintelligence.com.br/eleicoes_2026", _f(26, 700), CIANO)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(SAIDA, "JPEG", quality=90, optimize=True)
    return SAIDA


if __name__ == "__main__":
    print(gerar())
