"""Ekspor APAR ke PDF (A4 portrait) - tanpa Streamlit, memakai reportlab."""
from __future__ import annotations

import io

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules import apar_calc as calc
from modules.apar_html import CATATAN_TABEL, DASAR_PERATURAN, _n
from modules.ekspor_pdf import ABU, CATATAN, GARIS, HIJAU, NAVY, _gaya, _kaki, _teks
from utils.formatting import fmt_id

HIJAU_MUDA = colors.HexColor("#E3F6E8")


def _bar(teks: str, lebar: float) -> Table:
    """Judul seksi: bilah biru tua."""
    t = Table([[Paragraph(_teks(teks), _gaya("bar", 9.5, fontName="Helvetica-Bold", textColor=colors.white))]],
              colWidths=[lebar])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def apar_pdf(proyek: dict, entri: dict, tabel: pd.DataFrame, h: dict) -> bytes:
    tabel = calc.normalisasi_tabel(tabel)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=12 * mm, bottomMargin=14 * mm,
                            title="Perhitungan Kebutuhan APAR", author="Kaizen PBG")
    W = doc.width

    g_judul = _gaya("judul", 14, fontName="Helvetica-Bold", spaceAfter=2)
    g_sub = _gaya("sub", 8, textColor=colors.HexColor("#555555"), spaceAfter=6)
    g_k = _gaya("k", 8.5, fontName="Helvetica-Bold")
    g_t = _gaya("t", 8.5, alignment=TA_LEFT)
    g_tb = _gaya("tb", 8.5, fontName="Helvetica-Bold", alignment=TA_LEFT)
    g_c = _gaya("c", 8.5, alignment=TA_CENTER)
    g_cb = _gaya("cb", 8.5, fontName="Helvetica-Bold", alignment=TA_CENTER)
    g_h = _gaya("h", 8.5, fontName="Helvetica-Bold", alignment=TA_CENTER, textColor=colors.white)
    g_note = _gaya("note", 8, fontName="Helvetica-Oblique", alignment=TA_LEFT)
    g_cat = _gaya("cat", 8.5, spaceAfter=2)
    g_ph = _gaya("ph", 8.5, textColor=colors.white, fontName="Helvetica-Bold")

    isi = [Paragraph("PERHITUNGAN KEBUTUHAN APAR", g_judul),
           Paragraph("Dibuat dari aplikasi Kaizen PBG", g_sub)]

    # ---- identitas
    ident = Table([[Paragraph(k, g_k), Paragraph(": " + _teks(v), g_t)] for k, v in [
        ("PEKERJAAN", proyek["pekerjaan"]), ("LOKASI", proyek["lokasi"]),
        ("TAHUN", proyek["tahun"]), ("ITEM PEKERJAAN", proyek["item"])]],
        colWidths=[34 * mm, W - 34 * mm], hAlign="LEFT")
    ident.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    isi += [ident, Spacer(1, 5)]

    # ---- dasar peraturan
    jarak_reg = float(entri["jarak_reg"])
    blok = [_bar("DASAR PERATURAN DAN STANDAR", W), Spacer(1, 3)]
    for t, d in DASAR_PERATURAN:
        blok.append(Paragraph(f"<b>{_teks(t)}</b> - {_teks(d)}", g_cat))
    blok.append(Paragraph(
        "Persyaratan proteksi dapat dipenuhi dengan APAR berkemampuan lebih tinggi, asalkan jarak tempuh ke "
        f"APAR yang lebih besar tidak melebihi <b>{_n(jarak_reg)} m</b> (jarak antar APAR {_n(jarak_reg)} meter) "
        "dan jumlah kebutuhan APAR mengikuti tabel di bawah ini.", g_cat))
    isi += [KeepTogether(blok), Spacer(1, 6)]

    # ---- tabel acuan kelas A (kolom terpilih disorot)
    nilai = {r[calc.C_KELAS]: r for _, r in tabel.iterrows()}
    kelas = h["kelas"]
    jj = calc.KELAS.index(kelas)
    rows = [
        [Paragraph("No", g_h), Paragraph("Kriteria", g_h), Paragraph("Hunian bahaya kebakaran", g_h), "", ""],
        ["", "", *[Paragraph(k, g_h) for k in calc.KELAS]],
    ]
    spec = [
        ("Daya padam minimum APAR tunggal", calc.C_MINA, lambda v: f"{_n(v)}-A", {"Ringan": "1", "Sedang": "1", "Berat": "2"}),
        ("Luas lantai maksimum per unit A", calc.C_PERA, lambda v: f"{_n(v)} m²", {}),
        ("Luas lantai maksimum per APAR", calc.C_MAKS, lambda v: f"{_n(v)} m²", {k: "3" for k in calc.KELAS}),
        ("Jarak tempuh maksimum ke APAR", calc.C_JARAK, lambda v: f"{_n(v)} m", {k: "3" for k in calc.KELAS}),
    ]
    for i, (judul, kol, fm, penanda) in enumerate(spec, start=1):
        sel = []
        for k in calc.KELAS:
            teks = _teks(fm(nilai[k][kol])) + (f"<super>({penanda[k]})</super>" if k in penanda else "")
            sel.append(Paragraph(teks, g_cb if k == kelas else g_c))
        rows.append([str(i), Paragraph(_teks(judul), g_t), *sel])
    t1 = Table(rows, colWidths=[12 * mm, W - 12 * mm - 3 * 34 * mm, 34 * mm, 34 * mm, 34 * mm], repeatRows=2)
    t1.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 1), NAVY),
        ("SPAN", (0, 0), (0, 1)), ("SPAN", (1, 0), (1, 1)), ("SPAN", (2, 0), (4, 0)),
        ("BACKGROUND", (2 + jj, 1), (2 + jj, 1), HIJAU),
        ("BACKGROUND", (2 + jj, 2), (2 + jj, -1), HIJAU_MUDA),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
    ]))
    catatan = [Paragraph("<b>Catatan:</b>", g_cat)]
    catatan += [Paragraph(f"{i}. {_teks(t)}", _gaya(f"cn{i}", 8, leftIndent=10, firstLineIndent=-10, spaceAfter=1))
                for i, t in enumerate(CATATAN_TABEL, start=1)]
    isi.append(KeepTogether([
        _bar("UKURAN APAR DAN PENEMPATANNYA UNTUK BAHAYA KEBAKARAN KELAS A", W), Spacer(1, 3), t1,
        Spacer(1, 3), *catatan,
    ]))
    isi.append(Spacer(1, 5))

    # ---- input yang dipakai
    ds = [[Paragraph("Data Input", g_ph), Paragraph("Nilai", g_ph)]]
    # jenis / kapasitas / rating ditampilkan pada bagian Rekomendasi (hindari pengulangan)
    for k, v in [("Klasifikasi hunian", f"Bahaya kebakaran {kelas.lower()}"),
                 ("Batas jarak tempuh regulasi", f"{_n(jarak_reg)} m")]:
        ds.append([Paragraph(_teks(k), g_t), Paragraph(_teks(v), g_tb)])
    t_in = Table(ds, colWidths=[60 * mm, 60 * mm], hAlign="LEFT")
    t_in.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
                              ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    isi.append(KeepTogether([_bar("DATA INPUT", W), Spacer(1, 3), t_in]))
    isi.append(Spacer(1, 5))

    # ---- perhitungan jumlah APAR per lantai
    rows = [[Paragraph(x, g_h) for x in ["No", "Lantai / Area", "Luas Lantai", "Cakupan<br/>per APAR",
                                         "Luas ÷<br/>Cakupan", "Jumlah APAR"]]]
    for i, r in enumerate(h["lantai"], start=1):
        tanpa = h["cakupan"] <= 0
        rows.append([str(i), Paragraph(_teks(r["lantai"] or "-"), g_t), Paragraph(_teks(f"{_n(r['luas'])} m²"), g_c),
                     "-" if tanpa else Paragraph(_teks(f"{_n(h['cakupan'])} m²"), g_c),
                     "-" if tanpa else fmt_id(r["rasio"], 2),
                     Paragraph(f"<b>{'-' if r['jumlah'] is None else str(r['jumlah']) + ' buah'}</b>", g_c)])
    rt = len(rows)
    rows.append([Paragraph("TOTAL KEBUTUHAN APAR", g_tb), "", Paragraph(_teks(f"{_n(h['total_luas'])} m²"), g_cb), "", "",
                 Paragraph(f"<b>{'-' if h['total'] is None else str(h['total']) + ' buah'}</b>", g_cb)])
    rows.append([Paragraph(
        "Catatan : Kebutuhan jumlah APAR = Luas lantai ÷ Cakupan per APAR, dibulatkan ke atas "
        "(minimal 1 APAR pada tiap lantai yang berisi).", g_note), "", "", "", "", ""])
    t2 = Table(rows, colWidths=[12 * mm, W - 12 * mm - 4 * 29 * mm, 29 * mm, 29 * mm, 29 * mm, 29 * mm], repeatRows=1)
    t2.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("SPAN", (0, rt), (1, rt)), ("BACKGROUND", (0, rt), (4, rt), ABU),
        ("BACKGROUND", (5, rt), (5, rt), HIJAU), ("TEXTCOLOR", (5, rt), (5, rt), colors.white),
        ("SPAN", (0, rt + 1), (-1, rt + 1)), ("BACKGROUND", (0, rt + 1), (-1, rt + 1), CATATAN),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
    ]))
    isi.append(KeepTogether([_bar("PERHITUNGAN JUMLAH APAR", W), Spacer(1, 3), t2]))
    isi.append(Spacer(1, 5))

    # ---- rekomendasi
    total = "-" if h["total"] is None else f"{h['total']} buah"
    rek = [[Paragraph("Rekomendasi APAR", g_ph), Paragraph("Nilai", g_ph)]]
    for k, v in [("Jenis", entri["jenis"]), ("Kapasitas", entri["kapasitas"]), ("Rating", entri["rating"]),
                 ("Maks jarak tempuh", f"{_n(h['jarak_pakai'])} m")]:
        rek.append([Paragraph(_teks(k), g_t), Paragraph(_teks(v), g_tb)])
    rek.append([Paragraph("Jumlah APAR yang dibutuhkan", g_tb),
                Paragraph(f"<b>{_teks(total)}</b>", _gaya("rw", 9, alignment=TA_CENTER, textColor=colors.white))])
    t3 = Table(rek, colWidths=[60 * mm, 60 * mm], hAlign="LEFT")
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
        ("BACKGROUND", (0, -1), (0, -1), ABU), ("BACKGROUND", (1, -1), (1, -1), HIJAU),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    isi.append(KeepTogether([_bar("REKOMENDASI APAR", W), Spacer(1, 3), t3]))

    # ---- catatan
    teks_catatan = list(h["catatan"]) + list(h["info"]) + [
        "Dasar APAR tidak boleh kurang dari 15 cm di atas permukaan lantai (PER.04/MEN/1980).",
    ]
    blok = [Paragraph("<b>Catatan :</b>", g_cat)] + [Paragraph("- " + _teks(t), g_cat) for t in teks_catatan]
    isi += [Spacer(1, 5), KeepTogether(blok)]

    doc.build(isi, onFirstPage=_kaki("Perhitungan Kebutuhan APAR"), onLaterPages=_kaki("Perhitungan Kebutuhan APAR"))
    return buf.getvalue()
