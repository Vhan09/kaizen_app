"""Ekspor laporan pencahayaan alami ke PDF tanpa aplikasi tambahan."""
from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules.cahaya_alami_calc import fmt_id, kesimpulan, pct, pct_bersih

NAVY = colors.HexColor("#0F3D63")
AQUA = colors.HexColor("#35B6C9")
SOFT = colors.HexColor("#EAF3F9")
LINE = colors.HexColor("#D5E1EB")
GREEN = colors.HexColor("#DDF3E6")
RED = colors.HexColor("#FCE8E6")
GRAY = colors.HexColor("#ECEFF2")


def _teks(value) -> str:
    safe = str(value).encode("cp1252", "replace").decode("cp1252")
    return escape(safe).replace("\n", "<br/>")


def _angka(value, digits: int = 2) -> str:
    if value is None or value != value:
        return "-"
    return fmt_id(float(value), digits)


def _gaya(nama: str, ukuran: float, **kw) -> ParagraphStyle:
    return ParagraphStyle(
        nama,
        fontName=kw.pop("fontName", "Helvetica"),
        fontSize=ukuran,
        leading=kw.pop("leading", ukuran + 2),
        **kw,
    )


def buat_pdf(h: dict, data: dict, proyek: dict) -> bytes:
    """Buat laporan PDF dari data hitungan, tanpa mengonversi workbook Excel."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Perhitungan Pencahayaan Alami",
        author="Kaizen PBG",
    )
    lebar = doc.width
    judul = _gaya("judul", 15, fontName="Helvetica-Bold", textColor=NAVY, spaceAfter=3)
    subjudul = _gaya("subjudul", 8, textColor=colors.HexColor("#555555"), spaceAfter=8)
    bagian = _gaya("bagian", 10, fontName="Helvetica-Bold", textColor=NAVY, spaceBefore=9, spaceAfter=4)
    normal = _gaya("normal", 8)
    kecil = _gaya("kecil", 7, leading=9)
    kecil_kiri = _gaya("kecil_kiri", 7, leading=9, alignment=TA_LEFT)
    tengah = _gaya("tengah", 7, leading=9, alignment=TA_CENTER)
    header = _gaya("header", 7, leading=9, fontName="Helvetica-Bold",
                   textColor=colors.white, alignment=TA_CENTER)
    label = _gaya("label", 8, fontName="Helvetica-Bold", textColor=NAVY)

    def para(value, style=kecil_kiri):
        return Paragraph(_teks(value), style)

    def header_footer(canvas, page_doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(doc.leftMargin, 10 * mm, landscape(A4)[0] - doc.rightMargin, 10 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(doc.leftMargin, 6 * mm, "Kaizen PBG - Kebutuhan Pencahayaan Alami")
        canvas.drawRightString(landscape(A4)[0] - doc.rightMargin, 6 * mm,
                               f"Dicetak {datetime.now():%d-%m-%Y %H:%M} | Halaman {page_doc.page}")
        canvas.restoreState()

    def section_table(rows, widths, font_size=7):
        table = LongTable(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, LINE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        for row_index in range(1, len(rows)):
            if row_index % 2 == 0:
                table.setStyle(TableStyle([("BACKGROUND", (0, row_index), (-1, row_index), SOFT)]))
        return table

    isi = [
        Paragraph("PERHITUNGAN KEBUTUHAN PENCAHAYAAN ALAMI", judul),
        Paragraph("Pemeriksaan awal rasio luas bukaan cahaya terhadap luas lantai", subjudul),
    ]

    identitas = [
        [para("PEKERJAAN", label), para(proyek.get("pekerjaan", "-"), normal),
         para("LOKASI", label), para(proyek.get("lokasi", "-"), normal)],
        [para("TAHUN", label), para(proyek.get("tahun", "-"), normal),
         para("ITEM PEKERJAAN", label), para(proyek.get("item", "-"), normal)],
    ]
    ident = Table(identitas, colWidths=[25 * mm, lebar * 0.39, 25 * mm, lebar * 0.39])
    ident.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), SOFT),
        ("BACKGROUND", (2, 0), (2, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    isi += [ident, Spacer(1, 5)]

    isi.append(Paragraph("Ringkasan Hasil", bagian))
    ringkasan = [[
        para("Ruang tertutup dinilai", tengah),
        para("Memenuhi", tengah),
        para("Belum memenuhi", tengah),
        para("Rasio keseluruhan", tengah),
        para("Ambang minimum", tengah),
    ], [
        para(str(h["n_dinilai"]), label),
        para(str(h["n_ok"]), label),
        para(str(h["n_kurang"]), label),
        para(pct(h["rasio_total"]) if h["rasio_total"] is not None else "-", label),
        para(pct_bersih(h["ambang"]), label),
    ]]
    ring = Table(ringkasan, colWidths=[lebar / 5] * 5)
    ring.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    isi += [ring, Spacer(1, 5)]
    isi.append(Paragraph("Metode: Aj = jumlah (lebar x tinggi x jumlah x faktor efektif); Ar = P x L; rasio = Aj / Ar. "
                         f"Ambang yang dipakai: {pct_bersih(h['ambang'])} dari luas lantai.", normal))
    isi.append(Paragraph(_teks(data["catatan_metode"]), kecil))

    isi.append(Paragraph("Perhitungan per Ruangan", bagian))
    rows = [[para(x, header) for x in (
        "Lantai", "Nama Ruangan", "P x L (m)", "Ar (m2)", "Aj (m2)",
        "Rasio Aj/Ar", "Aj minimum (m2)", "Selisih (m2)", "Keterangan",
    )]]
    for row in h["tabel"].itertuples():
        panjang, lebar_ruang = _angka(row.P), _angka(row.L)
        dimensi = f"{panjang} x {lebar_ruang}" if panjang != "-" and lebar_ruang != "-" else "-"
        rasio = pct(row.rasio) if row.rasio is not None and row.rasio == row.rasio else "-"
        selisih = _angka(row.selisih, 3)
        rows.append([
            para(row.Lantai, tengah), para(row.Ruangan), para(dimensi, tengah),
            para(_angka(row.Ar), tengah), para(_angka(row.Aj, 3), tengah),
            para(rasio, tengah), para(_angka(row.aj_min, 3), tengah),
            para(selisih, tengah), para(row.status, tengah),
        ])
    widths = [lebar * x for x in (0.11, 0.18, 0.10, 0.09, 0.09, 0.10, 0.11, 0.10, 0.12)]
    per_ruang = section_table(rows, widths)
    for i, row in enumerate(h["tabel"].itertuples(), start=1):
        warna = GREEN if row.status == "MEMENUHI" else RED if row.status in ("KURANG", "TIDAK ADA BUKAAN") else GRAY
        per_ruang.setStyle(TableStyle([("BACKGROUND", (8, i), (8, i), warna)]))
    isi.append(per_ruang)

    isi.append(Paragraph("Rekap per Lantai", bagian))
    rekap_rows = [[para(x, header) for x in (
        "Lantai", "Ruang tertutup", "Area terbuka", "Luas lantai (m2)",
        "Luas bukaan (m2)", "Rasio", "Memenuhi", "Kurang",
    )]]
    for row in h["lantai"].itertuples():
        rekap_rows.append([
            para(row.Lantai), para(str(int(row.ruang)), tengah), para(str(int(row.terbuka)), tengah),
            para(_angka(row.ar), tengah), para(_angka(row.aj, 3), tengah),
            para(pct(row.rasio) if row.rasio == row.rasio else "-", tengah),
            para(str(int(row.ok)), tengah), para(str(int(row.kurang)), tengah),
        ])
    rekap_rows.append([
        para("TOTAL", label), para(str(h["n_dinilai"]), tengah), para(str(h["n_terbuka"]), tengah),
        para(_angka(h["ar_total"]), tengah), para(_angka(h["aj_total"], 3), tengah),
        para(pct(h["rasio_total"]) if h["rasio_total"] is not None else "-", tengah),
        para(str(h["n_ok"]), tengah), para(str(h["n_kurang"]), tengah),
    ])
    isi.append(section_table(rekap_rows, [lebar / 8] * 8))

    isi.append(Paragraph("Daftar Bukaan Cahaya", bagian))
    bukaan_rows = [[para(x, header) for x in (
        "Ruangan", "Jenis Bukaan", "Lebar x Tinggi (m)", "Jumlah", "Faktor efektif", "Aj (m2)",
    )]]
    for row in h["bukaan"].itertuples():
        bukaan_rows.append([
            para(row.Ruangan), para(row.Jenis), para(f"{_angka(row.W)} x {_angka(row.H)}", tengah),
            para(str(row.n), tengah), para(_angka(row.f), tengah), para(_angka(row.Aj, 3), tengah),
        ])
    if h["bukaan"].empty:
        bukaan_rows.append([para("Belum ada data bukaan.", kecil_kiri), "", "", "", "", ""])
    else:
        bukaan_rows.append([
            para("TOTAL", label), "", "", "", "",
            para(_angka(h["bukaan"]["Aj"].sum(), 3), label),
        ])
    isi.append(section_table(bukaan_rows, [lebar * x for x in (0.25, 0.20, 0.20, 0.12, 0.13, 0.10)]))

    isi.append(Paragraph("Kesimpulan dan Saran", bagian))
    isi.append(Paragraph(_teks(kesimpulan(h)), normal))
    kurang = h["tabel"][h["tabel"]["status"].isin(["KURANG", "TIDAK ADA BUKAAN"])]
    if kurang.empty:
        isi.append(Paragraph("Tidak ada ruang tertutup yang memerlukan saran penambahan bukaan berdasarkan ambang ini.", normal))
    else:
        saran_rows = [[para(x, header) for x in ("Ruangan", "Status", "Saran")]]
        for row in kurang.itertuples():
            saran_rows.append([para(row.Ruangan), para(row.status, tengah), para(row.saran_utama)])
        isi.append(section_table(saran_rows, [lebar * 0.18, lebar * 0.16, lebar * 0.66]))
    isi.append(Paragraph(
        "Rasio Aj/Ar adalah pemeriksaan awal, bukan penilaian formal SNI. Verifikasi faktor langit sesuai "
        "SNI 03-2396-2001, kondisi panas/silau, privasi, kebocoran, dan keamanan struktur dengan tenaga ahli.",
        kecil,
    ))

    isi.append(Paragraph("Landasan Perencanaan / SNI & Peraturan", bagian))
    standar_rows = [[para(x, header) for x in ("Standar / Peraturan", "Judul", "Peran", "Catatan")]]
    for standar in data["standar"]:
        standar_rows.append([
            para(standar["kode"]), para(standar["judul"]), para(standar["peran"]), para(standar["catatan"]),
        ])
    isi.append(section_table(standar_rows, [lebar * x for x in (0.17, 0.29, 0.30, 0.24)]))
    isi.append(Spacer(1, 4))
    isi.append(Paragraph(_teks(data.get("catatan_standar", "")), kecil))

    doc.build(isi, onFirstPage=header_footer, onLaterPages=header_footer)
    return buf.getvalue()
