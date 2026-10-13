"""PDF export for ARS-01: Luas & Intensitas Bangunan."""
from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from utils.formatting import fmt_id

_NAVY = colors.HexColor("#1F3864")
_PALE = colors.HexColor("#EEF2F8")
_LINE = colors.HexColor("#8C96A3")


def _fmt(value: float, decimals: int = 2) -> str:
    return fmt_id(value, decimals)


def build_pdf(inputs: dict, result: dict, project: dict, notes: list[str]) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=18 * mm,
        title="Luas & Intensitas Bangunan",
        author="Kaizen PBG",
    )
    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCustom", parent=base["Title"], fontName="Helvetica-Bold",
        fontSize=15, leading=18, textColor=_NAVY, alignment=TA_LEFT, spaceAfter=4,
    )
    small = ParagraphStyle(
        "SmallCustom", parent=base["BodyText"], fontSize=8, leading=11,
        textColor=colors.HexColor("#555555"),
    )
    body = ParagraphStyle("BodyCustom", parent=base["BodyText"], fontSize=9, leading=12)
    header = ParagraphStyle(
        "HeaderCustom", parent=body, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=TA_CENTER,
    )
    story = [
        Paragraph("LUAS &amp; INTENSITAS BANGUNAN", title),
        Paragraph("Laporan perhitungan ARS-01 · Kaizen PBG", small),
        Spacer(1, 5 * mm),
    ]

    identity = [
        ["Pekerjaan", escape(str(project.get("pekerjaan", "")))],
        ["Lokasi", escape(str(project.get("lokasi", "")))],
        ["Tahun", escape(str(project.get("tahun", "")))],
        ["Item pekerjaan", "Luas &amp; Intensitas Bangunan"],
    ]
    project_table = Table(identity, colWidths=[35 * mm, 135 * mm], hAlign="LEFT")
    project_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.extend([project_table, Spacer(1, 5 * mm)])

    story.append(Paragraph("DATA PERHITUNGAN", base["Heading2"]))
    input_rows = [
        [Paragraph("Parameter", header), Paragraph("Nilai", header)],
        ["Luas lahan", f"{_fmt(result['land_area_m2'])} m²"],
        ["Luas tapak bangunan", f"{_fmt(result['footprint_area_m2'])} m²"],
        ["Luas total lantai yang dihitung", f"{_fmt(result['total_floor_area_m2'])} m²"],
        ["Luas area hijau yang dihitung sebagai KDH", f"{_fmt(result['green_area_m2'])} m²"],
        ["Sisa lahan di luar tapak", f"{_fmt(result['remaining_land_m2'])} m²"],
    ]
    input_table = Table(input_rows, colWidths=[112 * mm, 58 * mm], repeatRows=1)
    input_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, _LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _PALE]),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([input_table, Spacer(1, 5 * mm)])

    story.append(Paragraph("HASIL DAN PERBANDINGAN DENGAN BATAS INPUT", base["Heading2"]))
    limits = result["limits_used"]
    checks = result["checks"]
    results_rows = [
        [Paragraph("Indikator", header), Paragraph("Hasil", header),
         Paragraph("Batas input", header), Paragraph("Perbandingan", header)],
        ["KDB", f"{_fmt(result['kdb_percent'])}%", f"maks. {_fmt(limits['max_kdb_percent'])}%",
         "Di bawah/sama dengan batas" if checks["kdb_pass"] else "Di atas batas"],
        ["KLB", _fmt(result["klb"], 4), f"maks. {_fmt(limits['max_klb'], 4)}",
         "Di bawah/sama dengan batas" if checks["klb_pass"] else "Di atas batas"],
        ["KDH", f"{_fmt(result['kdh_percent'])}%", f"min. {_fmt(limits['min_kdh_percent'])}%",
         "Di atas/sama dengan batas" if checks["kdh_pass"] else "Di bawah batas"],
    ]
    result_table = Table(results_rows, colWidths=[28 * mm, 32 * mm, 38 * mm, 72 * mm], repeatRows=1)
    result_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, _LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _PALE]),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([result_table, Spacer(1, 5 * mm)])

    story.append(Paragraph("LUAS LANTAI PER TINGKAT", base["Heading2"]))
    floor_rows = [[Paragraph("Tingkat", header), Paragraph("Luas lantai (m²)", header)]]
    floor_rows.extend(
        [[f"Tingkat {index}", _fmt(float(area))] for index, area in enumerate(inputs["floor_areas_m2"], 1)]
    )
    floor_table = Table(floor_rows, colWidths=[112 * mm, 58 * mm], repeatRows=1)
    floor_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, _LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _PALE]),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([floor_table, Spacer(1, 5 * mm)])

    story.append(Paragraph("RUMUS", base["Heading2"]))
    formulas = [
        "KDB = luas tapak bangunan ÷ luas lahan × 100%",
        "KLB = luas total lantai yang dihitung ÷ luas lahan",
        "KDH = luas area hijau yang dihitung ÷ luas lahan × 100%",
    ]
    story.extend(Paragraph(escape(formula), body) for formula in formulas)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("CATATAN DAN BATASAN", base["Heading2"]))
    story.extend(Paragraph("• " + escape(note), body) for note in notes)
    story.append(Paragraph(
        "<b>Perbandingan pada laporan ini hanya terhadap batas input pengguna, bukan penetapan kepatuhan hukum. "
        "Periksa ketentuan tata ruang dan definisi luas yang berlaku pada lokasi proyek.</b>",
        body,
    ))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(document.leftMargin, 9 * mm, "Kaizen PBG - Luas & Intensitas Bangunan")
        canvas.drawRightString(
            A4[0] - document.rightMargin,
            9 * mm,
            f"Dicetak {datetime.now():%d-%m-%Y %H:%M}  |  Halaman {document.page}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
