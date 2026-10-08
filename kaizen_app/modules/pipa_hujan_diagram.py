"""Modul Pipa Air Hujan - skema sistem (PNG, digambar dengan Pillow).

Satu sumber gambar dipakai untuk tampilan web, Excel, dan PDF. Pillow sudah terpasang bersama Streamlit.
"""
from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from modules.pipa_hujan_calc import OK, fmt_id, ink

W, H, S = 1500, 560, 2          # kanvas (px) dan faktor supersampling

INK, NAVY, BLUE, AQUA = "#1B2A3A", "#0F3D63", "#2A7AB0", "#35B6C9"
SOFT, LINE, GREY = "#EAF3F9", "#C9D8E4", "#6B7C8C"
GOOD, WARN, BAD = "#1E8E5A", "#C77700", "#C0392B"

_FONT_CACHE: dict = {}


def _font(size: int, bold: bool = False):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    names = (["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold
             else ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
    f = None
    for n in names:
        try:
            f = ImageFont.truetype(n, size * S)
            break
        except OSError:
            continue
    if f is None:
        f = ImageFont.load_default(size=size * S)
    _FONT_CACHE[key] = f
    return f


def _tone(status: str) -> str:
    return GOOD if status == OK else (BAD if status == "TIDAK MEMENUHI" else WARN)


def diagram_png(h: dict, data: dict) -> bytes:
    img = Image.new("RGB", (W * S, H * S), "white")
    d = ImageDraw.Draw(img)
    s = lambda v: int(round(v * S))

    def rect(x0, y0, x1, y1, fill=None, outline=None, r=0, w=1):
        d.rounded_rectangle([s(x0), s(y0), s(x1), s(y1)], radius=s(r), fill=fill, outline=outline, width=s(w))

    def poly(pts, fill=None, outline=None, w=1):
        d.polygon([(s(x), s(y)) for x, y in pts], fill=fill, outline=outline)
        if outline:
            d.line([(s(x), s(y)) for x, y in pts + [pts[0]]], fill=outline, width=s(w), joint="curve")

    def text(x, y, t, size=16, bold=False, fill=INK, anchor="la"):
        d.text((s(x), s(y)), t, font=_font(size, bold), fill=fill, anchor=anchor)

    def pill(x, y, t, fill=SOFT, color=NAVY, size=16):
        f = _font(size, True)
        wd = d.textlength(t, font=f) / S
        rect(x, y, x + wd + 22, y + 30, fill=fill, outline=LINE, r=15, w=1)
        text(x + 11, y + 15, t, size, True, color, "lm")

    P, I = h["P"], h["I"]
    c, g, tg = h["cabang"], h["gabung"], h["tegak"]
    n = max(1, h["n_tot"])

    rect(2, 2, W - 2, H - 2, fill="white", outline=LINE, r=18, w=2)
    text(26, 20, "SKEMA SISTEM AIR HUJAN ATAP", 14, True, GREY)

    # --- parameter hujan
    pill(26, 52, f"I = {I:g} mm/jam", "#E3F6F9", "#127A88")
    pill(206, 52, f"C = {fmt_id(h['C_rata'])}", "#E3F6F9", "#127A88")
    pill(356, 52, f"A = {fmt_id(h['A_tot'])} m²", "#E3F6F9", "#127A88")

    # --- hujan
    for row, y0 in enumerate((104, 134)):
        for x in range(60 + (row * 23), 900, 46):
            d.line([(s(x), s(y0)), (s(x - 9), s(y0 + 22))], fill=AQUA, width=s(3))

    # --- atap (miring tipis)
    def y_bawah(x):
        return 218 - (x - 70) * (20 / 830)
    poly([(70, 192), (900, 172), (900, 198), (70, 218)], fill="#DCE7F0", outline=NAVY, w=3)

    # --- roof drain
    pipa_y = 352
    draw_n = min(n, 6)
    xs = [150 + i * (680 / max(1, draw_n - 1)) for i in range(draw_n)] if draw_n > 1 else [490]
    for x in xs:
        yb = y_bawah(x)
        rect(x - 7, yb + 18, x + 7, pipa_y, fill=BLUE, outline=NAVY, w=1.5)
        poly([(x - 20, yb - 4), (x + 20, yb - 4), (x + 9, yb + 20), (x - 9, yb + 20)], fill="#9CC4E0", outline=NAVY, w=2)
    text(30, 236, "Roof drain", 15, True, NAVY)
    text(30, 256, f"Ø{ink(P['d_roof'])} × {n} titik", 15, True, NAVY)
    if n > draw_n:
        text(30, 276, "(digambar 6 titik)", 12, False, GREY)
    xa = (xs[0] + xs[1]) / 2 if len(xs) > 1 else 300
    text(xa, y_bawah(xa) - 14, "ATAP", 15, True, NAVY, "mm")

    # --- pipa horizontal
    rect(110, pipa_y, 1090, pipa_y + 24, fill=BLUE, outline=NAVY, r=4, w=2)
    d.line([(s(160), s(pipa_y + 52)), (s(1040), s(pipa_y + 52 + 14))], fill=GREY, width=s(2))
    d.polygon([(s(1040), s(pipa_y + 66)), (s(1022), s(pipa_y + 54)), (s(1028), s(pipa_y + 70))], fill=GREY)
    text(160, pipa_y + 70, f"Pipa horizontal Ø{ink(P['d_gabung'])}  ·  kemiringan {P['s_gabung']} %", 16, True, NAVY)
    text(160, pipa_y + 92, f"Pipa cabang Ø{ink(P['d_cabang'])} ({P['s_cabang']} %)  ·  Tabel 16 SNI 8153:2015, kolom {fmt_id(h['I_tabel'], 1)} mm/jam",
         14, False, GREY)

    # --- pipa tegak + pembuangan
    rect(1090, pipa_y, 1120, 478, fill=NAVY, outline=NAVY, r=4)
    text(1138, 396, f"Pipa tegak / kolektor Ø{ink(P['d_tegak'])}", 16, True, NAVY)
    text(1138, 418, f"Q = {fmt_id(h['Q_Ls'])} L/dt", 14, False, GREY)
    rect(1104, 462, 1200, 482, fill=BLUE, outline=NAVY, r=3, w=2)
    rect(1200, 438, 1450, 500, fill="#E3F6F9", outline="#127A88", r=10, w=2)
    text(1325, 469, "Bak kontrol / saluran drainase", 14, True, "#127A88", "mm")

    # --- tanah
    d.line([(s(30), s(500)), (s(1190), s(500))], fill=INK, width=s(3))
    for x in range(36, 1190, 22):
        d.line([(s(x), s(500)), (s(x - 12), s(518))], fill=LINE, width=s(2))

    # --- kartu ringkasan
    def kartu(y, label, nilai, status=None):
        rect(985, y, 1450, y + 66, fill="white", outline=LINE, r=12, w=2)
        col = _tone(status) if status else NAVY
        rect(985, y, 995, y + 66, fill=col, r=4)
        text(1012, y + 11, label, 14, False, GREY)
        text(1012, y + 33, nilai, 22, True, INK)
        if status:
            t = "MEMENUHI" if status == OK else ("TIDAK MEMENUHI" if status == "TIDAK MEMENUHI" else status)
            f = _font(12, True)
            wd = d.textlength(t, font=f) / S
            rect(1436 - wd - 20, y + 20, 1436, y + 46, fill=col, r=13)
            text(1436 - wd / 2 - 10, y + 33, t, 12, True, "white", "mm")

    kartu(26, "Debit rencana (metode rasional)", f"{fmt_id(h['Q_Ls'])} L/dt")
    kartu(104, f"Luas per roof drain  ≤  Ø{ink(c['ukuran'])} pada {c['kemiringan']} %",
          f"{fmt_id(c['luas'])} m²  ≤  {fmt_id(c['kapasitas'], 0)} m²", c["status"])
    kartu(182, f"Luas total  ≤  pipa gabungan Ø{ink(g['ukuran'])}",
          f"{fmt_id(g['luas'])} m²  ≤  {fmt_id(g['kapasitas'], 0)} m²", g["status"])

    out = img.resize((W, H), Image.LANCZOS)
    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
