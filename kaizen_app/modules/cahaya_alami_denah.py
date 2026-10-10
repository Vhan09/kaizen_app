"""Modul Pencahayaan Alami - ilustrasi perbandingan luas bukaan vs luas lantai (PNG, Pillow).

Blok biru = luas bukaan (Aj), garis putus-putus = luas minimum (ambang x Ar), keduanya digambar PROPORSIONAL
terhadap luas lantai (bukan posisi jendela sebenarnya).
"""
from __future__ import annotations

import math
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from modules.cahaya_alami_calc import KURANG, OK, TANPA, TERBUKA, fmt_id, pct, pct_bersih

S = 2
TW, TH, GAP, COLS, HEAD = 330, 236, 14, 4, 44
INK, NAVY, GREY, LINE, SOFT = "#1B2A3A", "#0F3D63", "#6B7C8C", "#D5E1EB", "#F4F8FB"
GOOD, WARN, BAD, MUTE = "#1E8E5A", "#C77700", "#C0392B", "#8A99A8"
SKY, SKY_O = "#8EC9EA", "#2A7AB0"
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


def _ada(x) -> bool:
    return x is not None and x == x and x != 0


def denah_png(h: dict) -> bytes:
    t, thr = h["tabel"], h["ambang"]
    lantai = list(dict.fromkeys(t["Lantai"]))
    tinggi = 58
    for lt in lantai:
        tinggi += HEAD + math.ceil(int((t["Lantai"] == lt).sum()) / COLS) * (TH + GAP)
    lebar = COLS * (TW + GAP) + GAP
    img = Image.new("RGB", (lebar * S, tinggi * S), "white")
    d = ImageDraw.Draw(img)
    s = lambda v: int(round(v * S))

    def rect(x0, y0, x1, y1, fill=None, outline=None, r=0, w=1):
        d.rounded_rectangle([s(x0), s(y0), s(x1), s(y1)], radius=s(r), fill=fill, outline=outline, width=s(w))

    def text(x, y, tx, size=13, bold=False, fill=INK, anchor="la"):
        d.text((s(x), s(y)), tx, font=_font(size, bold), fill=fill, anchor=anchor)

    def putus(x0, y0, x1, y1, warna, w=2, seg=6, jeda=4):
        """kotak garis putus-putus"""
        for (ax, ay, bx, by) in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]:
            L = math.hypot(bx - ax, by - ay)
            n = max(1, int(L // (seg + jeda)))
            for i in range(n + 1):
                a = i * (seg + jeda) / L
                b = min(1.0, (i * (seg + jeda) + seg) / L)
                if a >= 1:
                    break
                d.line([(s(ax + (bx - ax) * a), s(ay + (by - ay) * a)), (s(ax + (bx - ax) * b), s(ay + (by - ay) * b))],
                       fill=warna, width=s(w))

    def potong(tx, size, maks):
        f = _font(size, True)
        while d.textlength(tx, font=f) / S > maks and len(tx) > 4:
            tx = tx[:-2]
        return tx

    # legenda
    rect(GAP, 14, GAP + 18, 32, fill=SKY, outline=SKY_O, r=3, w=1.5)
    text(GAP + 26, 23, "Luas bukaan (Aj)", 12, True, INK, "lm")
    putus(GAP + 170, 14, GAP + 188, 32, WARN)
    text(GAP + 196, 23, f"Luas minimum ({pct_bersih(thr)} × Ar)", 12, True, INK, "lm")
    text(GAP + 400, 23, "Blok digambar proporsional terhadap luas lantai, bukan posisi jendela.", 11, False, GREY, "lm")

    y = 50
    for lt in lantai:
        grp = t[t["Lantai"] == lt]
        f = _font(14, True)
        wd = d.textlength(lt.upper(), font=f) / S
        rect(GAP, y + 4, GAP + wd + 28, y + 32, fill=NAVY, r=14)
        text(GAP + 14, y + 18, lt.upper(), 14, True, "white", "lm")
        ok, kr = int((grp["status"] == OK).sum()), int(grp["status"].isin([KURANG, TANPA]).sum())
        text(GAP + wd + 44, y + 18, f"{len(grp)} ruangan · {ok} memenuhi · {kr} kurang", 13, False, GREY, "lm")
        y += HEAD
        for i, r in enumerate(grp.itertuples()):
            cx, cy = GAP + (i % COLS) * (TW + GAP), y + (i // COLS) * (TH + GAP)
            warna = {OK: GOOD, KURANG: BAD, TANPA: BAD, TERBUKA: MUTE}[r.status]
            rect(cx, cy, cx + TW, cy + TH, fill="white", outline=LINE, r=12, w=2)
            rect(cx, cy + 10, cx + 5, cy + 46, fill=warna, r=2)
            text(cx + 16, cy + 12, potong(r.Ruangan, 14, TW - 150), 14, True, INK)
            sub = (f"{r.P:g} × {r.L:g} m  ·  {fmt_id(r.Ar)} m²" if _ada(r.Ar) else "tanpa dimensi")
            text(cx + 16, cy + 31, sub, 11, False, GREY)
            lab = {OK: "MEMENUHI", KURANG: "KURANG", TANPA: "TANPA BUKAAN", TERBUKA: "TERBUKA"}[r.status]
            fw = d.textlength(lab, font=_font(11, True)) / S
            rect(cx + TW - fw - 28, cy + 12, cx + TW - 10, cy + 34, fill=warna, r=11)
            text(cx + TW - 19 - fw / 2, cy + 23, lab, 11, True, "white", "mm")

            ax0, ay0, aw, ah = cx + 14, cy + 52, TW - 28, 118
            if r.status == TERBUKA:
                rw, rh = aw * 0.62, ah * 0.62
                rx, ry = ax0 + (aw - rw) / 2, ay0 + (ah - rh) / 2
                putus(rx, ry, rx + rw, ry + rh, MUTE)
                text(rx + rw / 2, ry + rh / 2, "Area terbuka", 13, True, MUTE, "mm")
                text(rx + rw / 2, ry + rh / 2 + 18, "tidak dihitung", 11, False, MUTE, "mm")
                text(cx + 16, cy + TH - 40, "Garasi / teras / taman: tanpa syarat rasio bukaan", 11, False, GREY)
                continue
            sk = min(aw / r.P, ah / r.L)
            rw, rh = r.P * sk, r.L * sk
            rx, ry = ax0 + (aw - rw) / 2, ay0 + (ah - rh) / 2
            rect(rx, ry, rx + rw, ry + rh, fill=SOFT, outline=NAVY, r=4, w=2)
            fa = math.sqrt(min(max(r.rasio, 0), 1))
            fm = math.sqrt(min(thr, 1))
            if fa > 0:
                d.rectangle([s(rx + 2), s(ry + rh - rh * fa), s(rx + rw * fa), s(ry + rh - 2)], fill=SKY, outline=SKY_O, width=s(1.5))
            putus(rx + 2, ry + rh - rh * fm, rx + rw * fm, ry + rh - 2, WARN)

            text(cx + 16, cy + TH - 50, f"Aj {fmt_id(r.Aj)} m²  /  Ar {fmt_id(r.Ar)} m²  =  {pct(r.rasio)}", 11, False, INK)
            if r.status == OK:
                ket = f"minimum {fmt_id(r.aj_min)} m²  ·  lebih {fmt_id(r.selisih, 3 if abs(r.selisih) < 0.01 else 2)} m²"
            elif r.status == KURANG:
                ket = f"minimum {fmt_id(r.aj_min)} m²  ·  kurang {fmt_id(-r.selisih, 3)} m²"
            else:
                ket = f"tidak ada bukaan  ·  butuh ≥ {fmt_id(r.aj_min)} m²"
            text(cx + 16, cy + TH - 30, ket, 12, True, warna)
        y += math.ceil(len(grp) / COLS) * (TH + GAP)

    out = img.resize((lebar, tinggi), Image.LANCZOS)
    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
