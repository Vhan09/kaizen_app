"""Modul Resapan - skema potongan dan denah tiap opsi (PNG, Pillow). Ilustrasi proporsional, bukan gambar kerja."""
from __future__ import annotations

import math
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from modules.resapan_calc import fmt_id

W, H, S = 1500, 440, 2
CW, CH, GAP = 478, 414, 14
INK, NAVY, GREY, LINE, SOFT = "#1B2A3A", "#0F3D63", "#6B7C8C", "#D5E1EB", "#F4F8FB"
GOOD, WARN, BAD = "#1E8E5A", "#C77700", "#C0392B"
SOIL, SOIL_O, WATER, WATER_O, AQUA = "#EFE6D8", "#B7A58A", "#BFE3F5", "#2A7AB0", "#35B6C9"
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


def skema_png(h: dict) -> bytes:
    v, sl, sp, bp, P = h["vab"], h["lingkaran"], h["persegi"], h["biopori"], h["P"]
    img = Image.new("RGB", (W * S, H * S), "white")
    d = ImageDraw.Draw(img)
    s = lambda x: int(round(x * S))

    def rect(x0, y0, x1, y1, fill=None, outline=None, r=0, w=1):
        d.rounded_rectangle([s(x0), s(y0), s(x1), s(y1)], radius=s(r), fill=fill, outline=outline, width=s(w))

    def text(x, y, tx, size=13, bold=False, fill=INK, anchor="la"):
        d.text((s(x), s(y)), tx, font=_font(size, bold), fill=fill, anchor=anchor)

    def line(p, fill, w=2):
        d.line([(s(a), s(b)) for a, b in p], fill=fill, width=s(w))

    def putus(x0, y0, x1, y1, fill, w=2, seg=7, jeda=5):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(L // (seg + jeda)))
        for i in range(n + 1):
            a = i * (seg + jeda) / L
            if a >= 1:
                break
            b = min(1.0, (i * (seg + jeda) + seg) / L)
            line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill, w)

    # skala seragam: kedalaman terbesar -> 170 px ; lebar terbesar tidak lebih dari 120 px
    hmax = max(sl["H"], sp["H"], bp["t"])
    skala = min(170 / hmax, 115 / max(P["D"], P["P"], 0.01))

    def kartu(i, judul, n, chip_warna, bentuk, lines):
        cx = GAP + i * (CW + GAP)
        cy = 12
        rect(cx, cy, cx + CW, cy + CH, fill="white", outline=LINE, r=14, w=2)
        rect(cx, cy + 12, cx + 6, cy + 48, fill=chip_warna, r=2)
        text(cx + 20, cy + 14, judul, 15, True, INK)
        tt = f"{n} unit"
        fw = d.textlength(tt, font=_font(13, True)) / S
        rect(cx + CW - fw - 34, cy + 12, cx + CW - 14, cy + 38, fill=chip_warna, r=13)
        text(cx + CW - 24 - fw / 2, cy + 25, tt, 13, True, "white", "mm")

        # ---- potongan
        gx0, gx1, gy = cx + 24, cx + 262, cy + 108
        rect(gx0, gy, gx1, gy + 184, fill=SOIL, outline=None)
        for k in range(0, 260, 22):
            line([(gx0 + k, gy + 184), (gx0 + k + 14, gy + 170)], SOIL_O, 1)
        line([(gx0, gy), (gx1, gy)], INK, 3)
        text(gx0 + 4, gy - 16, "muka tanah", 11, False, GREY)
        if bentuk == "biopori":
            wd, dep = max(10, bp["d"] * skala), bp["t"] * skala
            wd = max(wd, 10)
        elif bentuk == "lingkaran":
            wd, dep = P["D"] * skala, sl["H"] * skala
        else:
            wd, dep = P["P"] * skala, sp["H"] * skala
        mx = (gx0 + gx1) / 2
        x0, x1, y1 = mx - wd / 2, mx + wd / 2, gy + dep
        rect(x0, gy, x1, y1, fill=WATER, outline=None)
        kedap = P["kedap"] and bentuk != "biopori"
        if kedap:
            line([(x0, gy), (x0, y1), (x1, y1), (x1, gy)], NAVY, 4)
        else:
            putus(x0, gy, x0, y1, NAVY, 3)
            putus(x1, gy, x1, y1, NAVY, 3)
            line([(x0, y1), (x1, y1)], NAVY, 3)
        # panah air hujan masuk
        line([(mx, gy - 34), (mx, gy - 6)], AQUA, 3)
        d.polygon([(s(mx - 6), s(gy - 12)), (s(mx + 6), s(gy - 12)), (s(mx), s(gy))], fill=AQUA)
        # dimensi
        dim_t = {"lingkaran": f"D = {fmt_id(P['D'], 2)} m", "persegi": f"B = {fmt_id(P['P'], 2)} m",
                 "biopori": f"Ø {fmt_id(bp['d'] * 100, 1)} cm"}[bentuk]
        text(mx, gy - 46, dim_t, 12, True, NAVY, "mm")
        hv = {"lingkaran": sl["H"], "persegi": sp["H"], "biopori": bp["t"]}[bentuk]
        xr = x1 + 22
        line([(xr, gy), (xr, y1)], GREY, 1.5)
        line([(xr - 5, gy), (xr + 5, gy)], GREY, 1.5)
        line([(xr - 5, y1), (xr + 5, y1)], GREY, 1.5)
        text(xr + 9, (gy + y1) / 2, f"H = {fmt_id(hv, 2)} m", 12, True, NAVY, "lm")

        # ---- denah
        px, py = cx + 372, cy + 180
        text(px, cy + 104, "denah", 11, False, GREY, "mm")
        if bentuk == "persegi":
            a, b = P["P"] * 70, P["L"] * 70
            rect(px - a / 2, py - b / 2, px + a / 2, py + b / 2, fill=WATER, outline=NAVY, r=2, w=3)
            text(px, py + b / 2 + 16, f"{fmt_id(P['P'], 2)} × {fmt_id(P['L'], 2)} m", 12, True, NAVY, "mm")
        else:
            r = (P["D"] / 2 * 70) if bentuk == "lingkaran" else max(4, bp["d"] / 2 * 70 * 2)
            d.ellipse([s(px - r), s(py - r), s(px + r), s(py + r)], fill=WATER, outline=NAVY, width=s(3))
            lab = f"Ø {fmt_id(P['D'], 2)} m" if bentuk == "lingkaran" else f"Ø {fmt_id(bp['d'] * 100, 1)} cm"
            text(px, py + r + 16, lab, 12, True, NAVY, "mm")

        # ---- keterangan
        y = cy + 316
        for k, (tx, bold, col) in enumerate(lines):
            text(cx + 22, y + k * 22, tx, 12, bold, col)

    ok_l = GOOD if sl["rasio_kap"] >= 1 else BAD
    ok_p = GOOD if sp["rasio_kap"] >= 1 else BAD
    kartu(0, "SUMUR RESAPAN LINGKARAN", sl["n"], ok_l, "lingkaran", [
        (f"Volume tampung/unit {fmt_id(sl['v_unit'], 2)} m³ · meresap {fmt_id(sl['v_rsp'], 3)} m³", False, INK),
        (f"H total {fmt_id(sl['h_total'], 2)} m → N = {fmt_id(sl['n_raw'], 2)} ≈ {sl['n']}", True, NAVY),
        (f"Kapasitas total {fmt_id(sl['kap'], 2)} m³ ({sl['rasio_kap'] * 100:.0f}% Vab)", True, ok_l)])
    kartu(1, "SUMUR RESAPAN PERSEGI", sp["n"], ok_p, "persegi", [
        (f"Volume tampung/unit {fmt_id(sp['v_unit'], 2)} m³ · meresap {fmt_id(sp['v_rsp'], 3)} m³", False, INK),
        (f"H total {fmt_id(sp['h_total'], 2)} m → N = {fmt_id(sp['n_raw'], 2)} ≈ {sp['n']}", True, NAVY),
        (f"Kapasitas total {fmt_id(sp['kap'], 2)} m³ ({sp['rasio_kap'] * 100:.0f}% Vab)", True, ok_p)])
    kartu(2, "LUBANG RESAPAN BIOPORI", bp["n1"], WARN, "biopori", [
        (f"Volume/lubang {fmt_id(bp['v_lubang'] * 1000, 1)} L · meresap {fmt_id(bp['v_rsp'] * 1000, 1)} L", False, INK),
        (f"Metode volume: {bp['n1']} lubang", True, NAVY),
        (f"Dengan peresapan: {bp['n2']} lubang", True, WARN)])

    out = img.resize((W, H), Image.LANCZOS)
    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
