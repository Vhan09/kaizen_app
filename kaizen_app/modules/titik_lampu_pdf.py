"""Pembuatan laporan PDF titik lampu tanpa aplikasi eksternal."""
from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules import titik_lampu_calc as tc
from modules.titik_lampu_denah import denah_png

NAVY = colors.HexColor("#0F3D63")
PALE = colors.HexColor("#EAF3F9")
LINE = colors.HexColor("#D5E1EB")
GREEN = colors.HexColor("#E5F4EB")
RED = colors.HexColor("#FCE8E6")
AMBER = colors.HexColor("#FFF3D6")


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#65727D"))
    canvas.drawString(doc.leftMargin, 7 * mm, "Kaizen PBG - Perhitungan Titik Lampu")
    canvas.drawRightString(landscape(A4)[0] - doc.rightMargin, 7 * mm, f"Halaman {doc.page}")
    canvas.restoreState()


def _paragraph(value, style):
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)


def _format(value, digits=2):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if number != number or number in (float("inf"), float("-inf")):
        return "-"
    return tc.fmt_id(number, digits)


def _table(rows, widths, header_style, body_style, centered=()):
    centered_style = ParagraphStyle("tl_center", parent=body_style, alignment=TA_CENTER)
    cells = [[_paragraph(value, header_style) for value in rows[0]]]
    for row in rows[1:]:
        cells.append([_paragraph(value, centered_style if index in centered else body_style)
                      for index, value in enumerate(row)])
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def buat_pdf(h: dict, data: dict, proyek: dict) -> bytes:
    """Buat laporan PDF langsung dari hasil perhitungan titik lampu."""
    if h["tabel"].empty:
        raise ValueError("Isi minimal satu ruangan yang valid sebelum membuat PDF.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=10 * mm, bottomMargin=13 * mm,
        title="Perhitungan Titik Lampu", author="Kaizen PBG",
    )
    title = ParagraphStyle("tl_title", fontName="Helvetica-Bold", fontSize=14, leading=17,
                           textColor=NAVY, spaceAfter=3)
    subtitle = ParagraphStyle("tl_subtitle", fontName="Helvetica", fontSize=8, leading=10,
                              textColor=colors.HexColor("#536575"), spaceAfter=8)
    section = ParagraphStyle("tl_section", fontName="Helvetica-Bold", fontSize=9, leading=11,
                             textColor=NAVY, spaceBefore=8, spaceAfter=4)
    header = ParagraphStyle("tl_header", fontName="Helvetica-Bold", fontSize=6.5, leading=7.5,
                            textColor=colors.white, alignment=TA_CENTER)
    body = ParagraphStyle("tl_body", fontName="Helvetica", fontSize=6.5, leading=8)
    small = ParagraphStyle("tl_small", fontName="Helvetica", fontSize=6.5, leading=8)
    label = ParagraphStyle("tl_label", fontName="Helvetica-Bold", fontSize=7.5, leading=9,
                           textColor=NAVY)

    story = [
        _paragraph("PERHITUNGAN TITIK LAMPU", title),
        _paragraph("Metode lumen berdasarkan tingkat pencahayaan ruang dan data lampu yang dipilih", subtitle),
    ]

    project_rows = [[_paragraph(caption, label), _paragraph(proyek.get(key, "-"), body)]
                    for key, caption in (("pekerjaan", "Pekerjaan"), ("lokasi", "Lokasi"),
                                         ("tahun", "Tahun"), ("item", "Item pekerjaan"))]
    project = Table(project_rows, colWidths=[30 * mm, 120 * mm], hAlign="LEFT")
    project.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PALE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.extend([project, _paragraph("Ringkasan", section)])

    summary_rows = [
        ["Jumlah ruangan", str(h["n_ruang"]), "Total titik lampu", str(h["titik_total"])],
        ["Luas ruangan", f"{_format(h['area_total'])} m²", "Daya terpasang", f"{_format(h['daya_total'], 0)} W"],
        ["LLF", _format(h["P"]["llf"]), "CU", _format(h["P"]["cu"])],
        ["Rata-rata daya", f"{_format(h['wm2'], 1)} W/m²", "Di bawah target", str(h["n_kurang"])],
    ]
    summary = Table(summary_rows, colWidths=[38 * mm, 45 * mm, 38 * mm, 45 * mm], hAlign="LEFT")
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PALE), ("BACKGROUND", (2, 0), (2, -1), PALE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([summary, _paragraph("Perhitungan per ruangan", section)])

    detail_rows = [["No", "Lantai", "Ruangan", "P × L (m)", "Luas (m²)", "Jenis ruangan",
                    "Lampu", "E target (lux)", "N hitung", "Titik final", "E tercapai (lux)", "Status"]]
    for index, row in enumerate(h["tabel"].itertuples(index=False), start=1):
        dimensions = f"{_format(row.P)} × {_format(row.L)}" if row.A == row.A and row.A else "-"
        points = str(row.titik) + (" (manual)" if row.manual == row.manual and row.manual else "")
        detail_rows.append([
            str(index), row.Lantai, row.Ruangan, dimensions, _format(row.A), row.JenisR,
            f"{row.Lampu} {row.W:g} W", _format(row.E, 0), _format(row.raw), points,
            _format(row.e_cap, 0), row.status,
        ])
    detail_widths = [8, 23, 41, 21, 16, 37, 32, 17, 16, 17, 22, 21]
    detail_widths = [value * mm for value in detail_widths]
    detail = _table(detail_rows, detail_widths, header, body, centered=(0, 3, 4, 7, 8, 9, 10, 11))
    for index, row in enumerate(detail_rows[1:], start=1):
        color = GREEN if row[-1] == "MEMENUHI" else AMBER if row[-1] == "MANUAL" else RED
        detail.setStyle(TableStyle([("BACKGROUND", (11, index), (11, index), color)]))
    story.append(detail)

    story.append(_paragraph("Rekap per lantai", section))
    floor_rows = [["Lantai", "Ruangan", "Luas (m²)", "Titik lampu", "Daya (W)", "W/m²"]]
    for row in h["lantai"].itertuples(index=False):
        floor_rows.append([row.Lantai, str(row.ruang), _format(row.area), str(row.titik),
                           _format(row.daya, 0), _format(row.wm2, 1)])
    floor_rows.append(["TOTAL", str(h["n_ruang"]), _format(h["area_total"]), str(h["titik_total"]),
                       _format(h["daya_total"], 0), _format(h["wm2"], 1)])
    story.append(_table(floor_rows, [48, 25, 42, 42, 38, 39], header, body, centered=(1, 2, 3, 4, 5)))

    story.append(_paragraph("Rekap per jenis lampu", section))
    pivot = h["pivot"]
    pivot_rows = [["Jenis lampu", *[str(column) for column in pivot.columns]]]
    for name, row in pivot.iterrows():
        pivot_rows.append([str(name), *[str(int(value)) for value in row]])
    pivot_rows.append(["TOTAL", *[str(int(pivot[column].sum())) for column in pivot.columns]])
    pivot_widths = [52 * mm] + [(doc.width - 52 * mm) / max(1, len(pivot.columns))] * len(pivot.columns)
    story.append(_table(pivot_rows, pivot_widths, header, body, centered=tuple(range(1, len(pivot.columns) + 1))))

    story.append(_paragraph("Denah skematik titik lampu", section))
    image_bytes = denah_png(h)
    image_reader = ImageReader(BytesIO(image_bytes))
    image_width, image_height = image_reader.getSize()
    scale = min(doc.width / image_width, 145 * mm / image_height)
    story.extend([
        Image(BytesIO(image_bytes), width=image_width * scale, height=image_height * scale),
        Spacer(1, 3),
        _paragraph("Ilustrasi sebaran jumlah titik, bukan gambar teknis penempatan.", small),
        _paragraph("Kesimpulan", section),
        _paragraph(tc.kesimpulan(h), body),
    ])

    if h["peringatan"]:
        story.append(_paragraph("Catatan pemeriksaan", section))
        story.extend([_paragraph(f"- {note}", body) for note in h["peringatan"]])

    story.append(_paragraph("Landasan perencanaan / SNI dan peraturan", section))
    standards = [["Standar / peraturan", "Judul", "Peran", "Catatan"]]
    standards.extend([[item["kode"], item["judul"], item["peran"], item.get("catatan", "")]
                      for item in data["standar"]])
    story.append(_table(standards, [30, 68, 78, 100], header, small))
    story.extend([Spacer(1, 4), _paragraph(data.get("catatan_standar", ""), small)])

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()