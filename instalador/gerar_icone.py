"""Gera instalador/icone.ico (circulo com degrade arco-iris), sem dependencias."""
import colorsys
import math
import os
import struct
import zlib

SIZES = (16, 24, 32, 48, 64, 256)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icone.ico")


def render(size):
    c = (size - 1) / 2
    outer = size / 2 - 0.5
    inner = outer * 0.42
    rows = []
    for y in range(size):
        row = bytearray(b"\x00")  # filtro PNG "None"
        for x in range(size):
            dx, dy = x - c, y - c
            d = math.hypot(dx, dy)
            # anel arco-iris com centro escuro
            a = min(1.0, max(0.0, outer - d + 0.5))
            if d < inner:
                r, g, b = 24, 24, 28
            else:
                hue = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0
                r, g, b = (int(v * 255) for v in colorsys.hsv_to_rgb(hue, 0.85, 1.0))
            row += bytes((r, g, b, int(a * 255)))
        rows.append(bytes(row))
    return png(size, b"".join(rows))


def png(size, raw):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main():
    images = [render(s) for s in SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for s, data in zip(SIZES, images):
        dim = 0 if s >= 256 else s
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    with open(OUT, "wb") as f:
        f.write(header + entries + b"".join(images))
    print(f"Icone gerado: {OUT}")


if __name__ == "__main__":
    main()
