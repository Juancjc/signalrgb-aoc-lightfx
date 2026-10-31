"""Gera instalador/icone.ico no mesmo desenho do docs/logo.svg.

Anel arco-iris com centro escuro e o nome JotAC. Requer Pillow (pip install pillow).
Nos tamanhos pequenos o texto nao fica legivel, entao vira so "J" (32 px) ou some (16/24 px).
"""
import colorsys
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZES = (16, 24, 32, 48, 64, 128, 256)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icone.ico")
SCALE = 4  # desenha maior e reduz, para bordas suaves
DARK = (22, 22, 27, 255)
FONTS = ("segoeuib.ttf", "arialbd.ttf")


def font(px):
    for name in FONTS:
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            pass
    return ImageFont.load_default()


def render(size):
    s = size * SCALE
    c = s / 2
    outer = s / 2 - SCALE
    # anel mais grosso nos tamanhos pequenos, para continuar visivel
    width = outer * (0.42 if size < 32 else 0.30)
    inner = outer - width
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # anel arco-iris: fatias de cor, o centro e coberto depois
    ring = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    steps = 180
    box = (c - outer, c - outer, c + outer, c + outer)
    for i in range(steps):
        r, g, b = (int(v * 255) for v in colorsys.hsv_to_rgb(i / steps, 0.85, 1.0))
        rd.pieslice(box, -90 + 360 * i / steps, -90 + 360 * (i + 1.5) / steps, fill=(r, g, b, 255))
    if size >= 48:  # brilho suave em volta do anel
        glow = ring.filter(ImageFilter.GaussianBlur(s * 0.02))
        img.alpha_composite(glow)
    img.alpha_composite(ring)
    draw.ellipse((c - inner, c - inner, c + inner, c + inner), fill=DARK)

    if size >= 48:
        # ponto do Motion Point a 45 graus
        mid = (outer + inner) / 2
        px, py = c + mid * math.cos(-math.pi / 4), c + mid * math.sin(-math.pi / 4)
        dot = width * 0.28
        draw.ellipse((px - dot, py - dot, px + dot, py + dot), fill=(255, 255, 255, 255))

    text = "JotAC" if size >= 48 else "J" if size >= 32 else ""
    if text:
        # o texto ocupa ~78% do centro escuro
        px = int(inner * (0.62 if len(text) > 1 else 1.3))
        f = font(px)
        l, t, r, b = draw.textbbox((0, 0), text, font=f)
        draw.text((c - (l + r) / 2, c - (t + b) / 2), text, font=f, fill=(242, 242, 245, 255))

    return img.resize((size, size), Image.LANCZOS)


def main():
    images = [render(s) for s in SIZES]
    images[-1].save(OUT, format="ICO", sizes=[(s, s) for s in SIZES], append_images=images[:-1])
    print(f"Icone gerado: {OUT}")


if __name__ == "__main__":
    main()
