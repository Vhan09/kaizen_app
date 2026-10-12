"""Pembuatan laporan PDF formal resapan air hujan tanpa LibreOffice."""
from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules import resapan_calc as rc

NAVY = colors.HexColor("#0F3D63")
PALE = colors.HexColor("#EAF3F9")
LINE = colors.HexColor("#D5E1EB")
GREEN = colors.HexColor("#DDF3E6")
RED = colors.HexColor("#FCE8E6")
AMBER = colors.HexColor("#FFF1CC")
MUTED = colors.HexColor("#65727D")


def _footer(canvas, doc):
    canvas.saveState()
    width, _ = landscape(A4)
    canvas.setStrokeColor(LINE)
    canvas.line(doc.leftMargin, 10 * mm, width - doc.rightMargin, 10 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 6 * mm, "Kaizen PBG | Laporan Perhitungan Resapan Air Hujan")
    canvas.drawRightString(width - doc.rightMargin, 6 * mm, f"Halaman {doc.page}")
    canvas.restoreState()


def _p(value, style):
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)


def _table(rows, widths, header_style, body_style):
    cells = [[_p(value, header_style) for value in rows[0]]]
    cells.extend([[_p(value, body_style) for value in row] for row in rows[1:]])
    table = LongTable(cells, colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    for index, row in enumerate(rows[1:], start=1):
        status = str(row[-1])
        if status == rc.OK:
            shade = GREEN
        elif status == rc.TIDAK:
            shade = RED
        elif status == rc.BELUM:
            shade = AMBER
        else:
            continue
        table.setStyle(TableStyle([("BACKGROUND", (len(row) - 1, index), (-1, index), shade)]))
    return table


def buat_pdf(h: dict, data: dict, proyek: dict) -> bytes:
    """Buat laporan landscape A4 dengan tabel yang membungkus teks dan tidak melewati margin."""
    if h.get("kosong"):
        raise ValueError("Isi minimal satu bidang tadah yang valid sebelum membuat PDF.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=15 * mm,
        title="Laporan Perhitungan Resapan Air Hujan",
        author="Kaizen PBG",
    )
    title = ParagraphStyle(
        "resapan_title", fontName="Helvetica-Bold", fontSize=15, leading=18,
        textColor=NAVY, alignment=TA_CENTER, spaceAfter=3,
    )
    subtitle = ParagraphStyle(
        "resapan_subtitle", fontName="Helvetica", fontSize=8, leading=10,
        textColor=MUTED, alignment=TA_CENTER, spaceAfter=9,
    )
    section = ParagraphStyle(
        "resapan_section", fontName="Helvetica-Bold", fontSize=10, leading=13,
        textColor=NAVY, spaceBefore=8, spaceAfter=5, keepWithNext=True,
    )
    header = ParagraphStyle(
        "resapan_header", fontName="Helvetica-Bold", fontSize=7, leading=8,
        textColor=colors.white, alignment=TA_CENTER,
    )
    body = ParagraphStyle("resapan_body", fontName="Helvetica", fontSize=7.5, leading=9)
    small = ParagraphStyle("resapan_small", fontName="Helvetica", fontSize=7, leading=8.5)
    label = ParagraphStyle(
        "resapan_label", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=NAVY,
    )
    story = [
        _p("LAPORAN PERHITUNGAN RESAPAN AIR HUJAN", title),
        _p("Sumur resapan dan lubang biopori | Kaizen PBG", subtitle),
    ]

    project_rows = [
        [_p(caption, label), _p(proyek.get(key, "-") or "-", body)]
        for key, caption in (
            ("pekerjaan", "Pekerjaan"),
            ("lokasi", "Lokasi"),
            ("tahun", "Tahun"),
            ("item", "Item pekerjaan"),
        )
    ]
    project_table = Table(project_rows, colWidths=[35 * mm, 238 * mm], hAlign="LEFT")
    project_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PALE),
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([project_table, _p("Ringkasan perhitungan", section)])

    v = h["vab"]
    summary_rows = [
        ["Volume andil banjir (Vab)", f"{rc.fmt_id(v['vab'], 3)} m3",
         "Luas bidang tadah", f"{rc.fmt_id(v['A_tadah'])} m2"],
        ["Curah hujan harian (R)", f"{rc.fmt_id(v['R'], 0)} mm/hari",
         "Koefisien limpasan rata-rata", rc.fmt_id(v["C_rata"], 3)],
        ["Durasi hujan efektif (te)", f"{rc.fmt_id(v['te'], 3)} jam",
         "Jumlah opsi resapan", "Sumur lingkaran, sumur persegi, dan biopori"],
    ]
    summary_table = Table(
        [[_p(value, label if index % 2 == 0 else body) for index, value in enumerate(row)]
         for row in summary_rows],
        colWidths=[48 * mm, 38 * mm, 51 * mm, 136 * mm],
        hAlign="LEFT",
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PALE),
        ("BACKGROUND", (2, 0), (2, -1), PALE),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([summary_table, _p("Rincian bidang tadah", section)])

    area_rows = [["Permukaan", "Luas (m2)", "Koefisien C", "C x A", "Perhitungan"]]
    for area in v["rinc"].itertuples(index=False):
        area_rows.append([
            area.Permukaan, rc.fmt_id(area.A), rc.fmt_id(area.C, 2), rc.fmt_id(area.CA),
            "Dihitung" if area.dihitung else "Tidak dihitung",
        ])
    area_rows.append([
        "TOTAL BIDANG TADAH", rc.fmt_id(v["A_tadah"]), "-", rc.fmt_id(v["CA"]), "Vab",
    ])
    area_table = _table(area_rows, [91 * mm, 35 * mm, 35 * mm, 35 * mm, 77 * mm], header, body)
    story.extend([area_table, Spacer(1, 7), _p(rc.kesimpulan(h), body)])

    story.extend([PageBreak(), _p("DETAIL OPSI DAN KAPASITAS RESAPAN", title)])
    story.append(_p("Perbandingan opsi", section))
    options = rc.opsi_ringkas(h)
    option_rows = [["Opsi resapan", "Dimensi", "Jumlah", "Volume tampung (m3)", "Kapasitas total (m3)", "Kapasitas / Vab"]]
    for row in options.itertuples(index=False, name=None):
        name, dimension, count, volume, capacity, ratio = row
        option_rows.append([
            str(name), str(dimension), str(count), rc.fmt_id(volume, 3), rc.fmt_id(capacity, 3),
            f"{rc.fmt_id(ratio * 100, 1)}%",
        ])
    story.append(_table(
        option_rows,
        [58 * mm, 48 * mm, 23 * mm, 43 * mm, 48 * mm, 53 * mm],
        header, body,
    ))

    story.append(_p("Perhitungan sumur resapan", section))
    wells = [("Parameter", "Sumur lingkaran", "Sumur persegi")]
    well_labels = (
        ("Dimensi", "dim"),
        ("Luas alas (m2)", "a_alas"),
        ("Luas dinding (m2)", "a_dinding"),
        ("Luas resap total (m2)", "a_total"),
        ("Konduktivitas rata-rata (m/hari)", "k_rata"),
        ("Volume meresap (m3)", "v_rsp"),
        ("Volume storasi (m3)", "v_sto"),
        ("Kedalaman total (m)", "h_total"),
        ("Jumlah sumur", "n"),
        ("Kapasitas total (m3)", "kap"),
        ("Kapasitas terhadap Vab", "rasio_kap"),
    )
    for caption, key in well_labels:
        vals = []
        for result in (h["lingkaran"], h["persegi"]):
            value = result[key]
            if key == "dim":
                vals.append(str(value))
            elif key == "n":
                vals.append(str(value))
            elif key == "rasio_kap":
                vals.append(f"{rc.fmt_id(value * 100, 1)}%" if value is not None else "-")
            else:
                vals.append(rc.fmt_id(value, 3))
        wells.append([caption, *vals])
    story.append(_table(wells, [91 * mm, 89 * mm, 93 * mm], header, body))

    story.append(_p("Perhitungan biopori", section))
    bp = h["biopori"]
    bio_rows = [
        ["Metode", "Dasar hitung", "Jumlah lubang", "Kapasitas total (m3)"],
        ["A. Metode volume (konservatif)", f"Vab / volume lubang ({rc.fmt_id(bp['v_lubang'], 5)} m3)",
         str(bp["n1"]), rc.fmt_id(bp["n1"] * bp["v_lubang"], 3)],
        ["B. Memperhitungkan peresapan", f"Vab / (volume + resap; {rc.fmt_id(bp['v_total'], 5)} m3)",
         str(bp["n2"]), rc.fmt_id(bp["n2"] * bp["v_total"], 3)],
        ["C. Brata & Nelistya", "N = I x A / P" if bp["n3"] is not None else "Isi intensitas hujan dan laju peresapan",
         str(bp["n3"]) if bp["n3"] is not None else "Belum dihitung", "-"],
    ]
    story.append(_table(bio_rows, [60 * mm, 105 * mm, 35 * mm, 62 * mm], header, body))
    story.append(_p(
        f'Parameter biopori: ukuran pipa {bp["d_in"]}" (diameter hitung {rc.fmt_id(bp["d"], 4)} m), '
        f'kedalaman {rc.fmt_id(bp["t"], 2)} m. Konversi inci belum memperhitungkan diameter dalam/luar dan ketebalan dinding pipa.',
        small,
    ))
    if h["peringatan"]:
        story.append(_p("Catatan teknis", section))
        for warning in h["peringatan"]:
            story.append(_p(f"- {warning}", small))

    story.extend([PageBreak(), _p("PEMERIKSAAN PERSYARATAN DAN ACUAN", title)])
    story.append(_p("Pemeriksaan persyaratan lokasi dan teknis", section))
    requirement_rows = [["Persyaratan", "Acuan", "Hasil pemeriksaan", "Status"]]
    for requirement in h["req"]:
        requirement_rows.append([
            requirement["teks"], requirement["acuan"], requirement["ket"], requirement["status"],
        ])
    story.append(_table(
        requirement_rows,
        [91 * mm, 53 * mm, 91 * mm, 38 * mm],
        header, body,
    ))

    story.append(_p("Landasan perencanaan", section))
    standards = [["Standar / peraturan", "Judul", "Peran pada perhitungan", "Catatan"]]
    for standard in data["standar"]:
        standards.append([
            standard["kode"], standard["judul"], standard["peran"], standard["catatan"] or "-",
        ])
    story.append(_table(standards, [38 * mm, 56 * mm, 82 * mm, 97 * mm], header, small))
    story.append(Spacer(1, 6))
    story.append(_p(data.get("catatan_standar", ""), small))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
