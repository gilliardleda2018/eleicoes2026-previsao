"""Compartilhar "momento a momento": gera a imagem do instante da apuração (narrador ou Bruna eleita)
e mostra os botões de WhatsApp / Instagram / baixar dentro do próprio cartão."""
import base64
import io
import json
import re
from pathlib import Path
from urllib.parse import quote

import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "static" / "fonts" / "Montserrat.ttf"
FOTO_BRUNA = RAIZ / "assets" / "fotos" / "bruna.png"
LOGO = RAIZ / "assets" / "aggilli_logo.png"
LINK = "https://aggillintelligence.com.br/eleicoes_2026"
ROSA, NAVY = (224, 37, 151), (14, 27, 51)


def _f(tam, peso=800):
    try:
        f = ImageFont.truetype(str(FONTE), tam)
        try:
            f.set_variation_by_axes([peso])
        except Exception:  # noqa: BLE001
            pass
        return f
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def _sem_emoji(t):
    return re.sub(r"[\U0001F000-\U0001FAFF☀-➿️]", "", t).strip()


def _quebra(d, txt, fonte, largura):
    linhas, atual = [], ""
    for p in txt.split():
        teste = (atual + " " + p).strip()
        if d.textlength(teste, font=fonte) <= largura:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def _fundo(w, h, eleita):
    img = Image.new("RGB", (w, h), NAVY)
    g = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(g)
    d.ellipse((int(w * .35), -int(h * .15), int(w * 1.3), int(h * .75)), fill=ROSA)
    d.ellipse((-int(w * .4), int(h * .55), int(w * .5), int(h * 1.3)), fill=(34, 140, 190) if not eleita else (120, 40, 140))
    g = g.filter(ImageFilter.GaussianBlur(w // 6))
    return Image.blend(img, g, .5).convert("RGBA")


def arte(titulo, frase, vb, va, ve, apurado, eleita=False, fmt=lambda x: f"{x:,.0f}".replace(",", ".")):
    """Imagem 1080x1350 do momento (PNG em bytes)."""
    w, h = 1080, 1350
    img = _fundo(w, h, eleita)
    if FOTO_BRUNA.exists():
        b = Image.open(FOTO_BRUNA).convert("RGBA")
        b.thumbnail((620, 560), Image.LANCZOS)
        img.alpha_composite(b, (w - b.width + 30, 250))
    d = ImageDraw.Draw(img)
    x = 70
    selo = "BRUNA PESSOA ELEITA!" if eleita else f"APURAÇÃO AO VIVO · {apurado:.1f}% APURADO".replace(".", ",")
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    fs = _f(28, 700)
    lw = d.textlength(selo, font=fs) + 70
    od.rounded_rectangle((x, 70, x + lw, 128), radius=29, fill=(255, 255, 255, 34), outline=(255, 255, 255, 160), width=2)
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img)
    d.ellipse((x + 22, 92, x + 38, 108), fill=(255, 70, 90) if not eleita else (255, 210, 60))
    d.text((x + 50, 82), selo, font=fs, fill="white")
    y = 180
    for ln in _quebra(d, _sem_emoji(titulo), _f(68, 900), 560):
        d.text((x, y), ln, font=_f(68, 900), fill="white")
        y += 80
    y += 10
    for ln in _quebra(d, _sem_emoji(frase), _f(32, 600), 520)[:6]:
        d.text((x, y), ln, font=_f(32, 600), fill=(245, 200, 228))
        y += 44
    # placar
    yb = 840
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rounded_rectangle((50, yb, w - 50, yb + 330), radius=36, fill=(255, 255, 255, 236))
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img)
    col = (w - 100) / 3
    for i, (nome, v, cor) in enumerate((("BRUNA", vb, ROSA), ("ABIGAIL", va, (232, 112, 42)), ("ERIC", ve, (59, 111, 182)))):
        cx = 50 + col * i + col / 2
        for txt, fonte, c, dy in ((nome, _f(30, 800), cor, 40), (fmt(v), _f(62 if i == 0 else 50, 900), NAVY, 92),
                                  ("votos", _f(26, 600), (91, 100, 119), 175)):
            tw = d.textlength(txt, font=fonte)
            d.text((cx - tw / 2, yb + dy), txt, font=fonte, fill=c)
        if i:
            dif = vb - v
            txt = f"Bruna {'+' if dif >= 0 else '−'}{fmt(abs(dif))}"
            fonte = _f(26, 800)
            tw = d.textlength(txt, font=fonte)
            d.text((cx - tw / 2, yb + 225), txt, font=fonte, fill=(31, 157, 116) if dif >= 0 else (208, 84, 106))
    # rodapé
    if LOGO.exists():
        lg = Image.open(LOGO).convert("RGBA")
        lg.thumbnail((260, 110), Image.LANCZOS)
        img.alpha_composite(lg, (x - 8, h - lg.height - 50))
    fl = _f(30, 700)
    t = LINK.replace("https://", "")
    d.text((w - 70 - d.textlength(t, font=fl), h - 100), t, font=fl, fill="white")
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=90)
    return buf.getvalue()


def botoes(texto, imagem, nome_arquivo, altura=96):
    """Ícones dentro do cartão: WhatsApp (texto + link), Instagram/compartilhar (imagem do momento) e baixar."""
    b64 = base64.b64encode(imagem).decode()
    wa = f"https://wa.me/?text={quote(texto)}"
    components.html(f"""
<style>
  body {{margin: 0; font-family: Manrope, Arial, sans-serif;}}
  .ic {{display: flex; justify-content: center; align-items: center; gap: 18px; padding: 4px 0;}}
  .ic a, .ic button {{background: none; border: 0; padding: 0; cursor: pointer; text-decoration: none;}}
  .ic img {{width: 50px; height: 50px; transition: transform .15s; filter: drop-shadow(0 5px 10px rgba(27,42,65,.2));}}
  .ic a:hover img, .ic button:hover img {{transform: translateY(-2px) scale(1.06);}}
  .bx {{font: 800 13px Manrope, Arial; color: #12233F; background: #FFFFFF; border: 1.5px solid #C9D3E0 !important;
       border-radius: 999px !important; padding: 9px 14px !important;}}
  .tt {{text-align: center; font: 800 12px Manrope, Arial; letter-spacing: .12em; color: #5B6477;}}
  #msg {{text-align: center; font-size: 12px; color: #3A4458; min-height: 14px;}}
</style>
<div class="tt">COMPARTILHE ESTE MOMENTO</div>
<div class="ic">
  <a href="{wa}" target="_blank" rel="noopener" title="WhatsApp"><img src="/app/static/icones/whatsapp.png" alt="WhatsApp"></a>
  <button id="ig" title="Instagram e outros apps"><img src="/app/static/icones/instagram.png" alt="Instagram"></button>
  <a class="bx" id="dl" download="{nome_arquivo}" href="#">⬇ Imagem</a>
</div>
<div id="msg"></div>
<script>
const B64 = "{b64}";
const TEXTO = {json.dumps(texto)};
function arquivo() {{
  const bin = atob(B64), u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return new File([u], "{nome_arquivo}", {{type: "image/jpeg"}});
}}
const url = URL.createObjectURL(arquivo());
document.getElementById("dl").href = url;
const msg = t => document.getElementById("msg").textContent = t;
document.getElementById("ig").addEventListener("click", async () => {{
  const nav = (window.parent && window.parent.navigator && window.parent.navigator.share) ? window.parent.navigator : navigator;
  try {{ await (window.parent.navigator.clipboard || navigator.clipboard).writeText({json.dumps(LINK)}); }} catch (e) {{}}
  try {{
    const f = arquivo();
    if (nav.canShare && nav.canShare({{files: [f]}})) {{ await nav.share({{files: [f], text: TEXTO}}); return; }}
  }} catch (e) {{ if (e && e.name === "AbortError") return; }}
  document.getElementById("dl").click();
  msg("Imagem baixada e link copiado: publique no Instagram e cole o link no adesivo Link.");
}});
</script>""", height=altura)


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _circulo(foto, d, cor):
    out = Image.new("RGBA", (d + 24, d + 24), (0, 0, 0, 0))
    od = ImageDraw.Draw(out)
    od.ellipse((0, 0, d + 24, d + 24), fill=cor + (255,))
    od.ellipse((7, 7, d + 17, d + 17), fill=(255, 255, 255, 255))
    if foto and Path(foto).exists():
        f = Image.open(foto).convert("RGBA")
        w, h = f.size
        q = min(w, h)
        f = f.crop(((w - q) // 2, 0, (w - q) // 2 + q, q)).resize((d, d), Image.LANCZOS)
        m = Image.new("L", (d, d), 0)
        ImageDraw.Draw(m).ellipse((0, 0, d, d), fill=255)
        out.paste(f, (12, 12), m)
    return out


def arte_duelo(selo, titulo, frase, a, b, destaque=None, fmt=lambda x: f"{x:,.0f}".replace(",", ".")):
    """Imagem 1080x1350 do resultado do turno. a/b = (nome, votos, % válidos, cor hex, caminho da foto).
    destaque = índice (0/1) do vencedor, ou None (2º turno)."""
    w, h = 1080, 1350
    img = Image.new("RGB", (w, h), NAVY)
    g = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(g)
    d.ellipse((-300, 300, 520, 1100), fill=_hex(a[3]))
    d.ellipse((560, 300, 1380, 1100), fill=_hex(b[3]))
    g = g.filter(ImageFilter.GaussianBlur(170))
    img = Image.blend(img, g, .55).convert("RGBA")
    d = ImageDraw.Draw(img)
    fs = _f(28, 700)
    lw = d.textlength(selo, font=fs) + 70
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle(((w - lw) / 2, 70, (w + lw) / 2, 128), radius=29, fill=(255, 255, 255, 34),
                                         outline=(255, 255, 255, 160), width=2)
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img)
    d.text(((w - lw) / 2 + 35, 82), selo, font=fs, fill="white")
    y = 165
    for ln in _quebra(d, _sem_emoji(titulo), _f(64, 900), 940)[:2]:
        d.text(((w - d.textlength(ln, font=_f(64, 900))) / 2, y), ln, font=_f(64, 900), fill="white")
        y += 76
    y += 8
    for ln in _quebra(d, _sem_emoji(frase), _f(30, 600), 900)[:4]:
        d.text(((w - d.textlength(ln, font=_f(30, 600))) / 2, y), ln, font=_f(30, 600), fill=(225, 232, 242))
        y += 42
    yc = max(y + 30, 560)
    for i, (nome, votos, pct, cor, foto) in enumerate((a, b)):
        cx = 270 if i == 0 else 810
        dd = 300 if destaque in (None, i) else 230
        c = _circulo(foto, dd, _hex(cor))
        img.alpha_composite(c, (int(cx - c.width / 2), yc + (0 if destaque in (None, i) else 50)))
        d = ImageDraw.Draw(img)
        ytxt = yc + 340
        for txt, fonte, cc in ((nome.upper(), _f(34, 800), "white"), (fmt(votos), _f(56, 900), "white"),
                               (f"{pct:.2f}% dos válidos".replace(".", ","), _f(28, 600), (225, 232, 242))):
            d.text((cx - d.textlength(txt, font=fonte) / 2, ytxt), txt, font=fonte, fill=cc)
            ytxt += 62
        if destaque == i:
            t = "ELEITO"
            fonte = _f(30, 900)
            tw = d.textlength(t, font=fonte) + 40
            d.rounded_rectangle((cx - tw / 2, yc - 30, cx + tw / 2, yc + 14), radius=22, fill=(255, 210, 60))
            d.text((cx - tw / 2 + 20, yc - 26), t, font=fonte, fill=NAVY)
    if destaque is None:
        fx = _f(70, 900)
        d.text((w / 2 - d.textlength("×", font=fx) / 2, yc + 110), "×", font=fx, fill="white")
    if LOGO.exists():
        lg = Image.open(LOGO).convert("RGBA")
        lg.thumbnail((260, 110), Image.LANCZOS)
        img.alpha_composite(lg, (62, h - lg.height - 50))
    fl = _f(30, 700)
    t = LINK.replace("https://", "")
    d.text((w - 70 - d.textlength(t, font=fl), h - 100), t, font=fl, fill="white")
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=90)
    return buf.getvalue()
