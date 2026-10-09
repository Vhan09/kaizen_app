"""Modul Titik Lampu - denah skematik (PNG, Pillow). Ilustrasi sebaran titik, BUKAN gambar teknis penempatan."""
from __future__ import annotations

import math
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from modules.titik_lampu_calc import fmt_id

S = 2                                   # supersampling
TW, TH, GAP, COLS, HEAD = 330, 236, 14, 4, 44
INK, NAVY, GREY, LINE, SOFT = "#1B2A3A", "#0F3D63", "#6B7C8C", "#D5E1EB", "#F4F8FB"
GOOD, WARN, BAD = "#1E8E5A", "#C77700", "#C0392B"
LAMP, LAMP_O, GLOW = "#F6C945", "#B98900", "#FFF1BD"
_FONTS: dict = {}


def _font(size: int, bold: bool = False):
    key = (size, bold)
    if key not in _FONTS:
        names = (["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold
                 else ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
        f = None
        for n in names:
            try:
                f = ImageFont.truetype(n, size * S)
                break
            except OSError:
                continue
        _FONTS[key] = f or ImageFont.load_default(size=size * S)
    return _FONTS[key]


def _posisi(n: int, p: float, l: float):
    """Titik terdistribusi merata menurut proporsi ruangan (koordinat 0..1)."""
    if n <= 0:
        return []
    if n == 1:
        return [(0.5, 0.5)]
    kolom = max(1, min(n, round(math.sqrt(n * (p / l))))) if p and l else math.ceil(math.sqrt(n))
    baris = math.ceil(n / kolom)
    out, sisa = [], n
    for j in range(baris):
        k = min(kolom, sisa)
        sisa -= k
        out += [((i + 0.5) / k, (j + 0.5) / baris) for i in range(k)]
    return out


def _ada(x) -> bool:
    return x is not None and x == x and x != 0


def denah_png(h: dict) -> bytes:
    t = h["tabel"]
    lantai = list(dict.fromkeys(t["Lantai"]))
    tinggi = 20
    for lt in lantai:
        n = int((t["Lantai"] == lt).sum())
        tinggi += HEAD + math.ceil(n / COLS) * (TH + GAP)
    lebar = COLS * (TW + GAP) + GAP
    img = Image.new("RGB", (lebar * S, tinggi * S), "white")
    d = ImageDraw.Draw(img)
    s = lambda v: int(round(v * S))

    def rect(x0, y0, x1, y1, fill=None, outline=None, r=0, w=1):
        d.rounded_rectangle([s(x0), s(y0), s(x1), s(y1)], radius=s(r), fill=fill, outline=outline, width=s(w))

    def text(x, y, tx, size=13, bold=False, fill=INK, anchor="la"):
        d.text((s(x), s(y)), tx, font=_font(size, bold), fill=fill, anchor=anchor)

    def potong(tx, size, maks, bold=True):
        f = _font(size, bold)
        while d.textlength(tx, font=f) / S > maks and len(tx) > 4:
            tx = tx[:-2]
        return tx

    y = 12
    for lt in lantai:
        grp = t[t["Lantai"] == lt]
        f = _font(14, True)
        wd = d.textlength(lt.upper(), font=f) / S
        rect(GAP, y + 4, GAP + wd + 28, y + 32, fill=NAVY, r=14)
        text(GAP + 14, y + 18, lt.upper(), 14, True, "white", "lm")
        text(GAP + wd + 44, y + 18, f"{len(grp)} ruangan · {int(grp['titik'].sum())} titik lampu", 13, False, GREY, "lm")
        y += HEAD
        for i, r in enumerate(grp.itertuples()):
            cx, cy = GAP + (i % COLS) * (TW + GAP), y + (i // COLS) * (TH + GAP)
            ok = r.status == "MEMENUHI"
            warna = GOOD if ok else (WARN if r.status == "MANUAL" else BAD)
            rect(cx, cy, cx + TW, cy + TH, fill="white", outline=LINE, r=12, w=2)
            rect(cx, cy + 10, cx + 5, cy + 46, fill=warna, r=2)
            text(cx + 16, cy + 12, potong(r.Ruangan, 14, TW - 112), 14, True, INK)
            text(cx + 16, cy + 31, (f"{r.P:g} × {r.L:g} m  ·  {fmt_id(r.A)} m²" if _ada(r.A) else "tanpa dimensi"), 11, False, GREY)
            tt = f"{r.titik} titik"
            fw = d.textlength(tt, font=_font(12, True)) / S
            rect(cx + TW - fw - 30, cy + 12, cx + TW - 10, cy + 36, fill=warna, r=12)
            text(cx + TW - 20 - fw / 2, cy + 24, tt, 12, True, "white", "mm")
            # ruangan
            ax0, ay0, aw, ah = cx + 14, cy + 54, TW - 28, 118
            if _ada(r.A):
                sk = min(aw / r.P, ah / r.L)
                rw, rh = r.P * sk, r.L * sk
            else:
                rw, rh = aw * 0.6, ah * 0.6
            rx, ry = ax0 + (aw - rw) / 2, ay0 + (ah - rh) / 2
            rect(rx, ry, rx + rw, ry + rh, fill=SOFT, outline=NAVY, r=4, w=2)
            for px, py in _posisi(r.titik, r.P if _ada(r.P) else 1, r.L if _ada(r.L) else 1):
                x, yy = rx + px * rw, ry + py * rh
                d.ellipse([s(x - 13), s(yy - 13), s(x + 13), s(yy + 13)], fill=GLOW)
                d.ellipse([s(x - 6.5), s(yy - 6.5), s(x + 6.5), s(yy + 6.5)], fill=LAMP, outline=LAMP_O, width=s(1.5))
            # keterangan
            text(cx + 16, cy + TH - 50, f"{r.Lampu} {r.W:g} W  ·  E target {fmt_id(r.E, 0) if _ada(r.E) else '–'} lux", 11, False, INK)
            ket = f"E tercapai {fmt_id(r.e_cap, 0)} lux" if _ada(r.e_cap) else "titik ditetapkan manual"
            text(cx + 16, cy + TH - 30, ket, 12, True, warna)
        y += math.ceil(len(grp) / COLS) * (TH + GAP)

    out = img.resize((lebar, tinggi), Image.LANCZOS)
    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
