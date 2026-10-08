"""Pembuatan laporan PDF pipa air hujan tanpa aplikasi eksternal."""
from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules import pipa_hujan_calc as pc

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
    canvas.drawString(doc.leftMargin, 8 * mm, "Kaizen PBG - Perhitungan Pipa Air Hujan")
    canvas.drawRightString(A4[0] - doc.rightMargin, 8 * mm, f"Halaman {doc.page}")
    canvas.restoreState()


def _paragraph(value, style):
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)


def _table(rows, widths, header_style, body_style):
    cells = [[_paragraph(value, header_style) for value in rows[0]]]
    cells.extend([[_paragraph(value, body_style) for value in row] for row in rows[1:]])
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
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
        if status == pc.OK:
            color = GREEN
        elif status == pc.TIDAK:
            color = RED
        elif status in ("BELUM DICEK", "DI LUAR TABEL"):
            color = AMBER
        else:
            continue
        table.setStyle(TableStyle([("BACKGROUND", (len(row) - 1, index), (-1, index), color)]))
    return table


def buat_pdf(h: dict, data: dict, proyek: dict) -> bytes:
    """Buat laporan PDF dari hasil perhitungan, tanpa konversi workbook."""
    if h["zona"].empty:
        raise ValueError("Isi minimal satu bidang atap yang valid sebelum membuat PDF.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=15 * mm,
        title="Perhitungan Pipa Air Hujan", author="Kaizen PBG",
    )
    title = ParagraphStyle("ph_title", fontName="Helvetica-Bold", fontSize=14, leading=17,
                           textColor=NAVY, spaceAfter=3)
    subtitle = ParagraphStyle("ph_subtitle", fontName="Helvetica", fontSize=8, leading=10,
                              textColor=colors.HexColor("#536575"), spaceAfter=9)
    section = ParagraphStyle("ph_section", fontName="Helvetica-Bold", fontSize=10, leading=13,
                             textColor=NAVY, spaceBefore=8, spaceAfter=5)
    header = ParagraphStyle("ph_header", fontName="Helvetica-Bold", fontSize=7, leading=8,
                            textColor=colors.white, alignment=TA_CENTER)
    body = ParagraphStyle("ph_body", fontName="Helvetica", fontSize=7.5, leading=9)
    small = ParagraphStyle("ph_small", fontName="Helvetica", fontSize=7, leading=8.5)
    label = ParagraphStyle("ph_label", fontName="Helvetica-Bold", fontSize=8, leading=10,
                           textColor=NAVY)

    story = [
        _paragraph("PERHITUNGAN PIPA AIR HUJAN", title),
        _paragraph("Debit hujan, roof drain, pipa horizontal, dan kolektor vertikal", subtitle),
    ]

    project_rows = []
    for key, caption in (("pekerjaan", "Pekerjaan"), ("lokasi", "Lokasi"),
                         ("tahun", "Tahun"), ("item", "Item pekerjaan")):
        project_rows.append([_paragraph(caption, label), _paragraph(proyek.get(key, "-"), body)])
    project = Table(project_rows, colWidths=[32 * mm, 154 * mm], hAlign="LEFT")
    project.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PALE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([project, _paragraph("Ringkasan perhitungan", section)])

    summary = [
        ["Intensitas hujan", f"{pc.fmt_id(h['I'], 1)} mm/jam", "Luas atap", f"{pc.fmt_id(h['A_tot'])} m2"],
        ["Koefisien limpasan rata-rata", pc.fmt_id(h["C_rata"], 2), "Jumlah roof drain", str(h["n_tot"])],
        ["Debit total", f"{pc.fmt_id(h['Q_m3'], 5)} m3/dt", "Debit total", f"{pc.fmt_id(h['Q_Ls'], 2)} L/dt"],
    ]
    summary_table = Table(summary, colWidths=[47 * mm, 46 * mm, 43 * mm, 50 * mm], hAlign="LEFT")
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PALE), ("BACKGROUND", (2, 0), (2, -1), PALE),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([summary_table, _paragraph("Data bidang atap", section)])

    roof_rows = [["Bidang atap", "Permukaan", "Luas (m2)", "C", "Jumlah drain", "Debit (L/dt)", "Luas/drain (m2)"]]
    for row in h["zona"].itertuples(index=False):
        roof_rows.append([row.Bidang, row.Permukaan, pc.fmt_id(row.A), pc.fmt_id(row.C, 2), str(row.n),
                          pc.fmt_id(row.Q_Ls, 3), pc.fmt_id(row.A_drain)])
    story.extend([_table(roof_rows, [28 * mm, 40 * mm, 22 * mm, 12 * mm, 22 * mm, 30 * mm, 31 * mm], header, body),
                  _paragraph(f"Ukuran roof drain yang dipilih: Ø{pc.ink(h['P']['d_roof'])}", small),
                  _paragraph("Pemeriksaan pipa horizontal", section)])

    horizontal_rows = [["Pemeriksaan", "Diameter", "Kemiringan", "Area dilayani (m2)",
                        "Kapasitas (m2)", "Min. diameter", "Status"]]
    for name, key in (("Pipa cabang", "cabang"), ("Pipa gabungan", "gabung")):
        result = h[key]
        minimum = f"Ø{pc.ink(result['minimum'])}" if result["minimum"] else "Tidak tersedia"
        horizontal_rows.append([
            name, f"Ø{pc.ink(result['ukuran'])}", f"{result['kemiringan']}%",
            pc.fmt_id(result["luas"]), pc.fmt_id(result["kapasitas"]) if result["kapasitas"] else "-",
            minimum, result["status"],
        ])
    story.extend([_table(horizontal_rows, [25 * mm, 20 * mm, 20 * mm, 30 * mm, 29 * mm, 32 * mm, 30 * mm], header, body),
                  _paragraph("Pemeriksaan pipa tegak / kolektor", section)])

    vertical = h["tegak"]
    vertical_rows = [["Diameter", "Area dilayani (m2)", "Kapasitas Tabel 17 (m2)", "Status"],
                     [f"Ø{pc.ink(vertical['ukuran'])}", pc.fmt_id(vertical["luas"]),
                      pc.fmt_id(vertical["kapasitas"]) if vertical["kapasitas"] is not None else "Di luar tabel",
                      vertical["status"]]]
    story.extend([_table(vertical_rows, [35 * mm, 48 * mm, 58 * mm, 45 * mm], header, body),
                  _paragraph("Kesimpulan", section), _paragraph(pc.kesimpulan(h, data), body)])

    t17 = data["tabel17"]
    table17_rows = [["Ø (inci)", "Debit (L/dt)"] +
                    [pc.fmt_id(value, 1 if not float(value).is_integer() else 0) for value in t17["intensitas"]]]
    for diameter, debit, luas in zip(t17["diameter_inci"], t17["debit_ls"], t17["luas_m2"]):
        table17_rows.append([pc.ink(diameter), f"{debit:g}".replace(".", ",")] + [pc.fmt_id(value, 0) for value in luas])
    story.extend([_paragraph("Tabel referensi Tabel 17 SNI 8153:2015 (luas maksimum m2)", section),
                  _paragraph(t17["sumber"] + " " + t17["catatan"], small),
                  _table(table17_rows, [13 * mm, 18 * mm] + [12.9 * mm] * 12, header, small)])

    if h["peringatan"]:
        story.append(_paragraph("Catatan pemeriksaan", section))
        story.extend([_paragraph(f"- {note}", body) for note in h["peringatan"]])

    story.append(_paragraph("Landasan perencanaan / SNI dan peraturan", section))
    standards = [["Standar / peraturan", "Judul", "Peran", "Catatan"]]
    standards.extend([[item["kode"], item["judul"], item["peran"], item.get("catatan", "")]
                      for item in data["standar"]])
    story.extend([_table(standards, [34 * mm, 40 * mm, 67 * mm, 45 * mm], header, small),
                  Spacer(1, 5), _paragraph(data.get("catatan_standar", ""), small)])

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()