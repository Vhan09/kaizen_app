"""Ekspor ke PDF - tanpa Streamlit (memakai reportlab).

Tabel SLD otomatis memakai kertas A4 landscape, atau A3 landscape bila kolom
armature banyak. Pangkat (mm²) ditulis dengan tag <super> agar tampil benar.
"""
from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules import akli_calc
from modules.beban_listrik_calc import COL_GRUP, COL_KABEL, COL_LAIN, COL_MCB, COL_NAMA
from utils.formatting import fmt_id

NAVY = colors.HexColor("#1F3864")
KUNING = colors.HexColor("#FFF200")
HIJAU = colors.HexColor("#00B050")
CATATAN = colors.HexColor("#FFF9C4")
ABU = colors.HexColor("#EEF2F8")
GARIS = colors.HexColor("#8C96A3")


# ------------------------------------------------------------------ helper
def _teks(s) -> str:
    """Teks aman untuk Paragraph; pangkat 2 jadi <super>."""
    return escape(str(s)).replace("²", "<super>2</super>")


def _gaya(nama: str, ukuran: float, **kw) -> ParagraphStyle:
    return ParagraphStyle(nama, fontName=kw.pop("fontName", "Helvetica"), fontSize=ukuran,
                          leading=ukuran + 1.8, **kw)


def _kaki(judul: str):
    def gambar(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#555555"))
        w, _ = doc.pagesize
        canvas.drawString(doc.leftMargin, 8 * mm, f"Kaizen PBG - {judul}")
        canvas.drawRightString(w - doc.rightMargin, 8 * mm,
                               f"Dicetak {datetime.now():%d-%m-%Y %H:%M}  |  Halaman {doc.page}")
        canvas.restoreState()
    return gambar


def _g(x) -> str:
    """Angka ala Indonesia tanpa nol berlebih: 2,5 / 0,45 / 13,9."""
    return f"{float(x):g}".replace(".", ",")


# ------------------------------------------------------------------ AKLI
def _tabel_akli(sub: pd.DataFrame, g_head: ParagraphStyle, lebar_total: float, ukuran: float) -> Table:
    kol = [k for k in akli_calc.COLS if k != "Fasa"]
    judul = {"VA": "VA", "VA Pembulatan": "VA<br/>Pembulatan", "kVA": "kVA",
             "Watt (PF 0,8)": "Watt<br/>(PF 0,8)", "Gol": "GOL", "MCB (A)": "MCB / MCCB<br/>(A)",
             "Tegangan (V)": "V", "Tipe Kabel": "Type Kabel", "Inti": "Inti",
             "Ukuran (mm²)": "Ukuran<br/>(mm<super>2</super>)"}
    rows = [[Paragraph(judul[k], g_head) for k in kol]]
    for _, r in sub.iterrows():
        baris = []
        for k in kol:
            v = r[k]
            if k in ("Gol", "Tipe Kabel"):
                baris.append(str(v))
            elif pd.isna(v):
                baris.append("")
            elif k in ("VA", "VA Pembulatan", "Watt (PF 0,8)"):
                baris.append(fmt_id(v))
            elif k in ("MCB (A)", "Tegangan (V)", "Inti"):
                baris.append(fmt_id(v))
            else:
                baris.append(_g(v))
        rows.append(baris)
    bobot = {"VA": 1.0, "VA Pembulatan": 1.2, "kVA": 0.8, "Watt (PF 0,8)": 1.1, "Gol": 0.6,
             "MCB (A)": 1.1, "Tegangan (V)": 0.7, "Tipe Kabel": 1.5, "Inti": 0.6, "Ukuran (mm²)": 1.1}
    tot = sum(bobot[k] for k in kol)
    t = Table(rows, colWidths=[lebar_total * bobot[k] / tot for k in kol], repeatRows=1)
    gaya = [
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), ukuran),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), KUNING), ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            gaya.append(("BACKGROUND", (0, i), (-1, i), ABU))
    t.setStyle(TableStyle(gaya))
    return t


def akli_pdf(tabel: pd.DataFrame) -> bytes:
    t = akli_calc.normalisasi(tabel).sort_values(["Fasa", "MCB (A)"], kind="stable")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=14 * mm, bottomMargin=16 * mm,
                            title="Tabel AKLI", author="Kaizen PBG")
    lebar = doc.width
    g_judul = _gaya("judul", 14, fontName="Helvetica-Bold", spaceAfter=2)
    g_sub = _gaya("sub", 8, textColor=colors.HexColor("#555555"), spaceAfter=8)
    g_sec = _gaya("sec", 10, fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=4)
    g_head = _gaya("head", 8, fontName="Helvetica-Bold", alignment=TA_CENTER)

    isi = [Paragraph("TABEL AKLI - DAYA TERSEDIA, MCB / MCCB, DAN UKURAN KABEL", g_judul),
           Paragraph("Sumber: tabel AKLI yang tersimpan di aplikasi Kaizen PBG", g_sub)]
    for fasa, nama in ((1, "1 FASA - 220 V"), (3, "3 FASA - 380 V")):
        sub = t[t["Fasa"] == fasa]
        if sub.empty:
            continue
        isi.append(Paragraph(nama, g_sec))
        isi.append(_tabel_akli(sub, g_head, lebar, 8))
        isi.append(Spacer(1, 6))
    doc.build(isi, onFirstPage=_kaki("Tabel AKLI"), onLaterPages=_kaki("Tabel AKLI"))
    return buf.getvalue()


# ------------------------------------------------------------------ SLD
def sld_pdf(proyek: dict, sistem: dict, labels: list[str], out: dict,
            induk: dict | None, catatan: list[str]) -> bytes:
    hasil, qcols, watt = out["hasil"], out["qcols"], out["watt"]
    n, m = len(qcols), len(hasil)

    # kertas: A4 landscape, atau A3 bila kolom armature banyak
    tetap = [64, 46, 32, 34, 36, 54, 40]  # Nama, Grup, MCB, KA, Load, Cable, R
    lain = 40
    margin = 12 * mm
    pagesize = landscape(A4)
    if (pagesize[0] - 2 * margin - sum(tetap) - lain) / max(n, 1) < 31:
        pagesize = landscape(A3)
    lebar_tersedia = pagesize[0] - 2 * margin
    ukuran = 7 if pagesize == landscape(A4) else 8.5
    w_arm = max(22.0, (lebar_tersedia - sum(tetap) - lain) / max(n, 1))
    widths = tetap + [w_arm] * n + [lain]
    if sum(widths) > lebar_tersedia:  # sangat banyak kolom: kecilkan proporsional
        skala = lebar_tersedia / sum(widths)
        widths = [w * skala for w in widths]
        ukuran = max(5.0, ukuran * skala)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=pagesize, leftMargin=margin, rightMargin=margin,
                            topMargin=12 * mm, bottomMargin=15 * mm,
                            title="Perhitungan Kebutuhan Listrik (SLD)", author="Kaizen PBG")

    g_judul = _gaya("judul", 14, fontName="Helvetica-Bold", spaceAfter=2)
    g_sub = _gaya("sub", 8, textColor=colors.HexColor("#555555"), spaceAfter=6)
    g_kecil = _gaya("kecil", 8.5, alignment=TA_LEFT)
    g_kecil_b = _gaya("kecil_b", 8.5, fontName="Helvetica-Bold")
    g_h = _gaya("h", ukuran, fontName="Helvetica-Bold", alignment=TA_CENTER, textColor=colors.white)
    g_hy = _gaya("hy", ukuran, fontName="Helvetica-Bold", alignment=TA_CENTER)
    g_c = _gaya("c", ukuran, alignment=TA_CENTER)
    g_cl = _gaya("cl", ukuran, alignment=TA_LEFT)
    g_note = _gaya("note", ukuran, fontName="Helvetica-Oblique", alignment=TA_LEFT)
    g_lb = _gaya("lb", ukuran, fontName="Helvetica-Bold", alignment=TA_LEFT)

    isi = [Paragraph("PERHITUNGAN KEBUTUHAN LISTRIK (SLD)", g_judul),
           Paragraph("Dibuat dari aplikasi Kaizen PBG", g_sub)]

    # ---- identitas proyek
    ident = Table([[Paragraph(k, g_kecil_b), Paragraph(": " + _teks(v), g_kecil)] for k, v in [
        ("PEKERJAAN", proyek["pekerjaan"]), ("LOKASI", proyek["lokasi"]),
        ("TAHUN", proyek["tahun"]), ("ITEM PEKERJAAN", proyek["item"])]],
        colWidths=[34 * mm, lebar_tersedia - 34 * mm], hAlign="LEFT")
    ident.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    isi += [ident, Spacer(1, 6)]

    # ---- data sistem
    ds = [[Paragraph("Sistem", _gaya("dh", 8.5, fontName="Helvetica-Bold", textColor=colors.white)),
           Paragraph("Nilai", _gaya("dh2", 8.5, fontName="Helvetica-Bold", textColor=colors.white))]]
    for k, v in [("Tegangan Sistem", f"{fmt_id(sistem['tegangan'])} V"),
                 ("Faktor Daya (PF)", fmt_id(sistem["pf"], 2)),
                 ("Faktor Beban Puncak", fmt_id(sistem["faktor_puncak"], 2)),
                 ("Sistem Grounding", sistem["grounding"]),
                 ("Resistansi Grounding Max", sistem["res_grounding"]),
                 ("Proteksi Kebocoran", sistem["proteksi"])]:
        ds.append([Paragraph(_teks(k), g_kecil), Paragraph(_teks(v), g_kecil_b)])
    t_ds = Table(ds, colWidths=[48 * mm, 40 * mm], hAlign="LEFT")
    t_ds.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
                              ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    isi += [t_ds, Spacer(1, 6)]

    # ---- tabel utama
    nc = 8 + n  # jumlah kolom
    C_LAIN = 7 + n
    kosong = [""] * nc
    h0, h1, h2 = list(kosong), list(kosong), list(kosong)
    h0[0], h0[1] = Paragraph("Nama Sirkuit", g_h), Paragraph("Grouping<br/>Number", g_h)
    h0[2], h0[5], h0[7] = Paragraph("Circuit Breaker", g_h), Paragraph("Grouping Power", g_h), Paragraph("BEBAN", g_h)
    h0[C_LAIN] = Paragraph("Lain-lain<br/>(W)", g_h)
    for c, tk in zip(range(2, 7), ["MCB UP", "KA", "Load", "Cable", "R"]):
        h1[c] = Paragraph(tk, g_h)
    for i in range(n):
        h1[7 + i] = Paragraph(_teks(labels[i]), g_hy)
        h2[7 + i] = Paragraph(fmt_id(watt[i]), g_hy)
    rows = [h0, h1, h2]

    for _, r in hasil.iterrows():
        baris = [Paragraph(_teks(r[COL_NAMA]), g_cl), fmt_id(r[COL_GRUP]), fmt_id(r[COL_MCB]),
                 fmt_id(r["ka"], 2), fmt_id(r["load"]), Paragraph(_teks(r[COL_KABEL]), g_c),
                 Paragraph(f"<b>{fmt_id(r['load'])}</b>", g_c)]
        baris += [fmt_id(r[q], 0, kosong_jika_nol=True) for q in qcols]
        baris.append(fmt_id(r[COL_LAIN], 0, kosong_jika_nol=True))
        rows.append(baris)

    rt = 3 + m
    tot = [Paragraph("TOTAL LOAD", g_lb)] + [""] * 5 + [Paragraph(f"<b>{fmt_id(out['total_load'])}</b>", g_c)]
    tot += [fmt_id(x) for x in out["total_qty"]] + [fmt_id(out["total_lain"])]
    rows.append(tot)

    def baris_ringkas(label, nilai, catatan_txt):
        b = [Paragraph(label, g_lb)] + [""] * 5 + [Paragraph(f"<b>{_teks(nilai)}</b>", g_c)]
        b += [Paragraph(_teks(catatan_txt), g_note)] + [""] * n
        return b

    rows.append(baris_ringkas("VA (BEBAN PUNCAK WORST CASE SCENARIO)", f"{fmt_id(out['va'])} VA",
                              f"Catatan : Semua Elektronik Nyala Bersamaan (faktor puncak x{fmt_id(sistem['faktor_puncak'], 2)})"))
    rows.append(baris_ringkas("AMPERE", f"{fmt_id(out['ampere'], 2)} A",
                              f"Catatan : Ampere = VA / tegangan ({fmt_id(sistem['tegangan'])} V)"))
    ada_induk = induk is not None
    if ada_induk:
        if induk.get("ok"):
            nilai = induk["teks"]
            ket = (f"Catatan : Mengacu tabel AKLI 1 fasa - daya tersedia {fmt_id(induk['va_tersedia'])} VA, "
                   f"MCB induk {fmt_id(induk['mcb'])} A, {induk['tipe']}")
        else:
            nilai = "-"
            ket = (f"Catatan : Beban puncak {fmt_id(out['va'])} VA melebihi tabel AKLI 1 fasa "
                   f"(maks {fmt_id(induk['va_maks'])} VA), pertimbangkan sistem 3 fasa")
        rows.append(baris_ringkas("SARAN UKURAN KABEL INDUK (BEBAN KESELURUHAN)", nilai, ket))
    r_akhir = len(rows) - 1

    tb = Table(rows, colWidths=widths, repeatRows=3)
    st = [
        ("FONTNAME", (0, 3), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 3), (-1, -1), ukuran),
        ("ALIGN", (1, 3), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        # header
        ("BACKGROUND", (0, 0), (-1, 2), NAVY),
        ("BACKGROUND", (7, 1), (6 + n, 2), KUNING),
        ("SPAN", (0, 0), (0, 2)), ("SPAN", (1, 0), (1, 2)), ("SPAN", (2, 0), (4, 0)),
        ("SPAN", (5, 0), (6, 0)), ("SPAN", (7, 0), (6 + n, 0)), ("SPAN", (C_LAIN, 0), (C_LAIN, 2)),
    ]
    for c in range(2, 7):
        st.append(("SPAN", (c, 1), (c, 2)))
    if n == 1:  # SPAN 1 sel tidak diperlukan
        st = [s for s in st if s != ("SPAN", (7, 0), (6 + n, 0))]
    # kolom R & total
    st.append(("BACKGROUND", (6, 3), (6, 2 + m), ABU))
    # baris total (hijau) + ringkasan
    st += [("SPAN", (0, rt), (5, rt)), ("BACKGROUND", (0, rt), (6, rt), ABU),
           ("BACKGROUND", (7, rt), (C_LAIN, rt), HIJAU), ("TEXTCOLOR", (7, rt), (C_LAIN, rt), colors.white),
           ("FONTNAME", (7, rt), (C_LAIN, rt), "Helvetica-Bold")]
    for rr in range(rt + 1, r_akhir + 1):
        st += [("SPAN", (0, rr), (5, rr)), ("SPAN", (7, rr), (C_LAIN, rr)),
               ("BACKGROUND", (0, rr), (6, rr), ABU), ("BACKGROUND", (7, rr), (C_LAIN, rr), CATATAN)]
    tb.setStyle(TableStyle(st))
    isi.append(tb)

    # ---- catatan bawah tabel (satu blok utuh, tidak terpotong antar halaman)
    g_cat = _gaya("cat", 8.5, spaceAfter=1)
    blok = [Paragraph("<b>Catatan :</b>", g_cat),
            Paragraph("Pertimbangan penggunaan daya sesuai aturan keamanan 80% dari VA", g_cat),
            Paragraph(f"Total daya dalam satu bangunan dengan semua elektronik menyala "
                      f"<b>{fmt_id(out['total_load'])} W</b>", g_cat),
            Paragraph(f"Total Daya Semu (VA) dalam bangunan <b>{fmt_id(out['va'])} VA</b>", g_cat)]
    if catatan:
        blok += [Spacer(1, 6), Paragraph("<b>Catatan penyesuaian MCB &amp; kabel :</b>", g_cat)]
        blok += [Paragraph("- " + _teks(c), g_cat) for c in catatan]
    isi += [Spacer(1, 6), KeepTogether(blok)]

    doc.build(isi, onFirstPage=_kaki("Perhitungan Kebutuhan Listrik (SLD)"),
              onLaterPages=_kaki("Perhitungan Kebutuhan Listrik (SLD)"))
    return buf.getvalue()