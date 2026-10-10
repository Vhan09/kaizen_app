"""Ekspor Penghawaan Alami ke PDF (A4 lanskap) - tanpa Streamlit, memakai reportlab."""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules import ventilasi_calc as calc
from modules.ekspor_pdf import ABU, GARIS, NAVY, _gaya, _kaki
from modules.ekspor_pdf import _teks as _teks_dasar
from modules.ventilasi_html import DASAR_STANDAR, status_kelas
from utils.formatting import fmt_id

LATAR = {"ok": colors.HexColor("#E3F6E8"), "no": colors.HexColor("#FDE7E7"),
         "warn": colors.HexColor("#FFF3CD"), "na": colors.HexColor("#EEF2F8")}
TEKS = {"ok": "#0B6B2E", "no": "#B00020", "warn": "#7A5C00", "na": "#444444"}
GRUP = colors.HexColor("#DCE6F5")


def _teks(s) -> str:
    """Teks aman untuk Paragraph. Simbol >= ditulis '>=' (glyph U+2265 tidak ada di font standar PDF)."""
    return _teks_dasar(str(s).replace("≥", ">=")).replace("³", "<super>3</super>")


def _d(x, nd=2) -> str:
    return "-" if not x else fmt_id(x, nd)


def ventilasi_pdf(proyek: dict, entri: dict, h: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=14 * mm,
                            title="Perhitungan Penghawaan Alami", author="Kaizen PBG")
    W = doc.width
    rasio = float(entri["rasio"])

    g_judul = _gaya("judul", 15, fontName="Helvetica-Bold", spaceAfter=2)
    g_sub = _gaya("sub", 8, textColor=colors.HexColor("#555555"), spaceAfter=6)
    g_bar = _gaya("bar", 9.5, fontName="Helvetica-Bold", textColor=colors.white)
    g_t = _gaya("t", 8.5, alignment=TA_LEFT)
    g_tb = _gaya("tb", 8.5, fontName="Helvetica-Bold", alignment=TA_LEFT)
    g_c = _gaya("c", 7, alignment=TA_CENTER)
    g_cl = _gaya("cl", 7, alignment=TA_LEFT)
    g_h = _gaya("h", 7, fontName="Helvetica-Bold", alignment=TA_CENTER, textColor=colors.white)
    g_grp = _gaya("grp", 7.5, fontName="Helvetica-Bold", alignment=TA_LEFT, textColor=NAVY)
    g_cat = _gaya("cat", 8.5, spaceAfter=2, leftIndent=8, firstLineIndent=-8)

    def bar(teks: str) -> Table:
        t = Table([[Paragraph(_teks(teks), g_bar)]], colWidths=[W])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY),
                               ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        return t

    def sel_status(b: dict) -> Paragraph:
        k = status_kelas(b["status"])
        if b["status"] == calc.ST_TERBUKA:  # ruang terbuka: cukup statusnya, tanpa keterangan berulang
            return Paragraph(f'<font color="{TEKS[k]}"><b>{_teks(b["status"])}</b></font>', g_cl)
        return Paragraph(
            f'<font color="{TEKS[k]}"><b>{_teks(b["status"])}</b></font><br/>'
            f'<font size="6.2">{_teks(b["ket"])}</font>', g_cl)

    base = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2)]

    isi = [Paragraph("PERHITUNGAN PENGHAWAAN ALAMI &amp; VENTILASI MEKANIS", g_judul),
           Paragraph("Dasar: SNI 03-6572-2001 - dibuat dari aplikasi Kaizen PBG", g_sub)]

    ident = Table([[Paragraph(k, g_tb), Paragraph(": " + _teks(v), g_t)] for k, v in [
        ("PEKERJAAN", proyek["pekerjaan"]), ("LOKASI", proyek["lokasi"]),
        ("TAHUN", proyek["tahun"]), ("ITEM PEKERJAAN", proyek["item"])]],
        colWidths=[34 * mm, W - 34 * mm], hAlign="LEFT")
    ident.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    isi += [ident, Spacer(1, 5)]

    # ---- dasar standar + parameter
    ach = calc.normalisasi_ach(entri["ach"])
    ach_txt = ", ".join(f"{r[calc.C_ACH_JENIS]} {fmt_id(r[calc.C_ACH], 0) if r[calc.C_ACH] > 0 else '-'}"
                        for _, r in ach.iterrows() if r[calc.C_ACH_JENIS] != calc.JENIS_TERBUKA)
    blok = [bar("DASAR STANDAR DAN PARAMETER"), Spacer(1, 3)]
    blok += [Paragraph(f"<b>{_teks(t)}</b> - {_teks(d)}", g_cat) for t, d in DASAR_STANDAR]
    blok += [Paragraph(f"<b>Dasar rasio dipakai:</b> {_teks(entri['dasar'])} (syarat Av minimum = "
                       f"{fmt_id(rasio * 100, 1)}% × Ar).", g_cat),
             Paragraph(f"<b>ACH minimum ventilasi mekanis (kali/jam):</b> {_teks(ach_txt)}.", g_cat),
             Spacer(1, 5)]
    isi.append(KeepTogether(blok))

    # ---- A. tabel penghawaan alami
    lebar_tetap = [18, 98, 62, 20, 26, 26, 36, 26, 26, 36, 34, 40, 40]
    kolom = lebar_tetap + [W - sum(lebar_tetap)]
    nc = len(kolom)
    kosong = [""] * nc
    r0, r1 = list(kosong), list(kosong)
    r0[0], r0[1], r0[2] = Paragraph("No", g_h), Paragraph("Nama Ruangan", g_h), Paragraph("Jenis", g_h)
    r0[3] = Paragraph("Av - Ventilasi (m²)".replace("²", "<super>2</super>"), g_h)
    r0[7] = Paragraph("Ar - Ruangan (m²)".replace("²", "<super>2</super>"), g_h)
    r0[10], r0[11], r0[12] = (Paragraph("Rasio<br/>Av/Ar", g_h), Paragraph("Syarat Av<br/>min (m²)".replace("²", "<super>2</super>"), g_h),
                              Paragraph("Selisih<br/>(m²)".replace("²", "<super>2</super>"), g_h))
    r0[13] = Paragraph("Keterangan", g_h)
    for c, t in zip(range(3, 10), ["Jml", "P", "L", "A", "P", "L", "A"]):
        r1[c] = Paragraph(t, g_h)
    rows = [r0, r1]
    stil = list(base) + [
        ("BACKGROUND", (0, 0), (-1, 1), NAVY),
        ("SPAN", (3, 0), (6, 0)), ("SPAN", (7, 0), (9, 0)),
    ]
    for c in (0, 1, 2, 10, 11, 12, 13):
        stil.append(("SPAN", (c, 0), (c, 1)))
    for lantai, daftar in h["kelompok"]:
        rows.append([Paragraph(_teks(lantai.upper()), g_grp)] + [""] * (nc - 1))
        stil += [("SPAN", (0, len(rows) - 1), (-1, len(rows) - 1)), ("BACKGROUND", (0, len(rows) - 1), (-1, len(rows) - 1), GRUP)]
        for i, b in enumerate(daftar, start=1):
            k = status_kelas(b["status"])
            if b["status"] == calc.ST_TERBUKA:
                tengah = [Paragraph("tidak dihitung", g_c)] + [""] * 9
                rows.append([Paragraph(str(i), g_c), Paragraph(_teks(b["nama"]), g_cl), Paragraph(_teks(b["jenis"]), g_cl),
                             *tengah, sel_status(b)])
                rr = len(rows) - 1
                stil += [("SPAN", (3, rr), (12, rr)), ("BACKGROUND", (3, rr), (12, rr), LATAR["na"])]
            else:
                neg = round(b["selisih"], 6) < 0
                rows.append([
                    Paragraph(str(i), g_c), Paragraph(_teks(b["nama"]), g_cl), Paragraph(_teks(b["jenis"]), g_cl),
                    Paragraph(_d(b["jml"], 0), g_c), Paragraph(_d(b["vp"]), g_c), Paragraph(_d(b["vl"]), g_c),
                    Paragraph(fmt_id(b["av"], 3), g_c), Paragraph(_d(b["rp"]), g_c), Paragraph(_d(b["rl"]), g_c),
                    Paragraph(fmt_id(b["ar"], 3), g_c), Paragraph(fmt_id(b["rasio"] * 100, 1) + "%", g_c),
                    Paragraph(fmt_id(b["av_min"], 3), g_c),
                    Paragraph(f'<font color="{"#B00020" if neg else "#111111"}">{fmt_id(b["selisih"], 3)}</font>', g_c),
                    sel_status(b)])
            stil.append(("BACKGROUND", (nc - 1, len(rows) - 1), (nc - 1, len(rows) - 1), LATAR[k]))
    ta = Table(rows, colWidths=kolom, repeatRows=2)
    ta.setStyle(TableStyle(stil))
    isi += [bar("A. PENGHAWAAN ALAMI - syarat: Av >= rasio × Ar"), Spacer(1, 3), ta, Spacer(1, 6)]

    # ---- B. exhaust
    if h["exhaust"]:
        kep = [Paragraph(t, g_h) for t in ["No", "Ruangan", "Volume P × L × T (m³)".replace("m³", "m<super>3</super>"),
                                           "Q (m³/menit)".replace("m³", "m<super>3</super>"),
                                           "Q (m³/jam)".replace("m³", "m<super>3</super>"), "ACH hasil<br/>(kali/jam)",
                                           "ACH min<br/>(SNI 4.4.1)", "Q min (m³/jam)".replace("m³", "m<super>3</super>"),
                                           "Keterangan"]]
        rb = list(kep)
        rows_b = [rb]
        stil_b = list(base) + [("BACKGROUND", (0, 0), (-1, 0), NAVY)]
        for i, b in enumerate(h["exhaust"], start=1):
            k = status_kelas(b["status"])
            rows_b.append([
                Paragraph(str(i), g_c), Paragraph(_teks(b["nama"]), g_cl),
                Paragraph(f'{fmt_id(b["rp"], 2)} × {fmt_id(b["rl"], 2)} × {fmt_id(b["t"], 2)} = {fmt_id(b["vol"], 3)}', g_c),
                Paragraph(fmt_id(b["q_menit"], 2), g_c), Paragraph(fmt_id(b["q_jam"], 0), g_c),
                Paragraph(f"<b>{fmt_id(b['ach'], 1)}</b>", g_c),
                Paragraph("-" if b["ach_min"] <= 0 else fmt_id(b["ach_min"], 0), g_c),
                Paragraph("-" if b["q_min"] <= 0 else fmt_id(b["q_min"], 0), g_c), sel_status(b)])
            stil_b.append(("BACKGROUND", (8, i), (8, i), LATAR[k]))
        wb_ = [18, 110, 130, 60, 60, 60, 60, 66]
        tb = Table(rows_b, colWidths=wb_ + [W - sum(wb_)], repeatRows=1)
        tb.setStyle(TableStyle(stil_b))
        isi.append(KeepTogether([bar("B. VENTILASI MEKANIS (EXHAUST) - syarat: ACH >= acuan SNI Tabel 4.4.1"),
                                 Spacer(1, 3), tb,
                                 Paragraph("ACH = Q (m³/jam) ÷ volume ruang; Q (m³/jam) = Q (m³/menit) × 60.".replace("m³", "m<super>3</super>"),
                                           _gaya("cp", 7.5, textColor=colors.HexColor("#555555"))),
                                 Spacer(1, 6)]))

    # ---- C. perbandingan rasio
    kep = [Paragraph(t, g_h) for t in ["Dasar rasio ventilasi alami", "Ruang dinilai", "Sesuai", "Tidak sesuai",
                                       "Perlu tinjauan", "Ruang terbuka"]]
    rows_c = [kep]
    for bd in entri["banding"]:
        rows_c.append([Paragraph(f"<b>{_teks(bd['dasar'])}</b>", g_cl), Paragraph(str(bd["dinilai"]), g_c),
                       Paragraph(f"<b>{bd['sesuai']}</b>", g_c), Paragraph(f"<b>{bd['tidak']}</b>", g_c),
                       Paragraph(str(bd["tinjau"]), g_c), Paragraph(str(bd["terbuka"]), g_c)])
    wc = [W * 0.34] + [W * 0.10] * 5
    tc = Table(rows_c, colWidths=wc, hAlign="LEFT")
    tc.setStyle(TableStyle(base + [("BACKGROUND", (0, 0), (-1, 0), NAVY),
                                   ("BACKGROUND", (2, 1), (2, -1), LATAR["ok"]), ("BACKGROUND", (3, 1), (3, -1), LATAR["no"])]))
    isi.append(KeepTogether([bar("C. PERBANDINGAN DASAR RASIO"), Spacer(1, 3), tc, Spacer(1, 6)]))

    # ---- D. rekomendasi perbaikan
    if h["perbaikan"]:
        butir = [Paragraph(f"{i}. <b>{_teks(b['lantai'])} - {_teks(b['nama'])}</b> ({_teks(b['status'])}): {_teks(b['ket'])}", g_cat)
                 for i, b in enumerate(h["perbaikan"], start=1)]
    else:
        butir = [Paragraph("Seluruh ruangan yang dinilai telah memenuhi dasar yang dipilih.", g_cat)]
    isi.append(KeepTogether([bar("D. REKOMENDASI PERBAIKAN"), Spacer(1, 3), *butir, Spacer(1, 4),
                             Paragraph("Catatan: SNI 6572-2:2024 (bangunan residensial) tercatat berlaku di BSN; angkanya belum "
                                       "dapat diverifikasi dan perlu dicocokkan sebelum dokumen diserahkan.",
                                       _gaya("cn", 7.5, fontName="Helvetica-Oblique", textColor=colors.HexColor("#555555")))]))

    doc.build(isi, onFirstPage=_kaki("Perhitungan Penghawaan Alami"), onLaterPages=_kaki("Perhitungan Penghawaan Alami"))
    return buf.getvalue()
