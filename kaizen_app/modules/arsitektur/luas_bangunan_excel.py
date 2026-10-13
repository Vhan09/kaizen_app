"""Excel export for ARS-01: Luas & Intensitas Bangunan."""
from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

_NAVY = "1F3864"
_YELLOW = "FFF200"
_PALE = "EEF2F8"
_LINE = Side(style="thin", color="8C96A3")
_BOX = Border(left=_LINE, right=_LINE, top=_LINE, bottom=_LINE)
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
_INPUT_FONT = Font(name="Arial", size=10, color="0000FF")
_NORMAL_FONT = Font(name="Arial", size=10)
_BOLD_FONT = Font(name="Arial", size=10, bold=True)


def _style_row(ws, row: int, start_col: int, end_col: int, fill: str) -> None:
    for cells in ws.iter_rows(min_row=row, max_row=row, min_col=start_col, max_col=end_col):
        for cell in cells:
            cell.fill = PatternFill("solid", fgColor=fill)
            cell.font = _BOLD_FONT
            cell.border = _BOX
            cell.alignment = _CENTER


def build_excel(inputs: dict, result: dict, project: dict, notes: list[str]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Luas & Intensitas"
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "B17"

    ws.merge_cells("B2:F2")
    ws["B2"] = "PERHITUNGAN LUAS & INTENSITAS BANGUNAN"
    ws["B2"].font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    ws["B2"].fill = PatternFill("solid", fgColor=_NAVY)
    ws["B2"].alignment = _CENTER
    ws.row_dimensions[2].height = 28

    project_rows = [
        ("Pekerjaan", project.get("pekerjaan", "")),
        ("Lokasi", project.get("lokasi", "")),
        ("Tahun", project.get("tahun", "")),
        ("Item pekerjaan", "Luas & Intensitas Bangunan"),
    ]
    for row, (label, value) in enumerate(project_rows, start=4):
        ws.cell(row, 2, label).font = _BOLD_FONT
        ws.cell(row, 2).alignment = _LEFT
        ws.cell(row, 3, value).font = _INPUT_FONT
        ws.cell(row, 3).alignment = _LEFT

    ws.merge_cells("B10:C10")
    ws["B10"] = "DATA DAN BATAS YANG DIINPUT"
    _style_row(ws, 10, 2, 3, _YELLOW)
    input_rows = [
        ("Luas lahan (m²)", inputs["land_area_m2"], "0.00"),
        ("Luas tapak bangunan (m²)", inputs["footprint_area_m2"], "0.00"),
        ("Luas area hijau KDH (m²)", inputs["green_area_m2"], "0.00"),
        ("Total luas lantai manual (m²; opsional)", inputs.get("total_floor_area_manual_m2"), "0.00"),
        ("Batas maksimum KDB (%)", inputs["limits"]["max_kdb_percent"], "0.00"),
        ("Batas maksimum KLB", inputs["limits"]["max_klb"], "0.0000"),
        ("Batas minimum KDH (%)", inputs["limits"]["min_kdh_percent"], "0.00"),
    ]
    for row, (label, value, number_format) in enumerate(input_rows, start=11):
        ws.cell(row, 2, label).font = _NORMAL_FONT
        cell = ws.cell(row, 3, value)
        cell.font = _INPUT_FONT
        cell.alignment = _CENTER
        cell.number_format = number_format
        for col in (2, 3):
            ws.cell(row, col).border = _BOX
    ws.merge_cells("B16:C16")
    ws["B16"] = "LUAS LANTAI PER TINGKAT"
    _style_row(ws, 16, 2, 3, _YELLOW)
    ws["B17"], ws["C17"] = "Tingkat", "Luas lantai (m²)"
    _style_row(ws, 17, 2, 3, _NAVY)
    for cell in ws[17][1:3]:
        cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    first_floor_row = 18
    for index, area in enumerate(inputs["floor_areas_m2"], start=1):
        row = first_floor_row + index - 1
        ws.cell(row, 2, f"Tingkat {index}").font = _NORMAL_FONT
        ws.cell(row, 3, area).font = _INPUT_FONT
        ws.cell(row, 3).number_format = "0.00"
        for col in (2, 3):
            ws.cell(row, col).border = _BOX
            ws.cell(row, col).alignment = _CENTER
    last_floor_row = first_floor_row + len(inputs["floor_areas_m2"]) - 1

    total_row = last_floor_row + 1
    ws.cell(total_row, 2, "Jumlah luas lantai").font = _BOLD_FONT
    ws.cell(total_row, 3, f"=SUM(C{first_floor_row}:C{last_floor_row})").font = _BOLD_FONT
    ws.cell(total_row, 3).number_format = "0.00"
    for col in (2, 3):
        ws.cell(total_row, col).fill = PatternFill("solid", fgColor=_PALE)
        ws.cell(total_row, col).border = _BOX

    result_start = total_row + 3
    ws.merge_cells(start_row=result_start, start_column=2, end_row=result_start, end_column=4)
    ws.cell(result_start, 2, "HASIL PERHITUNGAN")
    _style_row(ws, result_start, 2, 4, _YELLOW)
    header_row = result_start + 1
    for col, label in enumerate(("Parameter", "Hasil", "Batas input"), start=2):
        ws.cell(header_row, col, label)
    _style_row(ws, header_row, 2, 4, _NAVY)
    for cell in ws[header_row][1:4]:
        cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")

    kdb_row, klb_row, kdh_row, rem_row = header_row + 1, header_row + 2, header_row + 3, header_row + 4
    total_area_ref = f"C{total_row}" if inputs.get("total_floor_area_manual_m2") is None else "C14"
    rows = [
        ("KDB (%)", f"=C12/C11*100", "=C15", "0.00"),
        ("KLB", f"={total_area_ref}/C11", "=C16", "0.0000"),
        ("KDH (%)", "=C13/C11*100", "=C17", "0.00"),
        ("Sisa lahan di luar tapak (m²)", "=C11-C12", None, "0.00"),
    ]
    for row, (label, formula, limit_formula, fmt) in enumerate(rows, start=header_row + 1):
        ws.cell(row, 2, label).font = _NORMAL_FONT
        ws.cell(row, 3, formula).font = _BOLD_FONT
        ws.cell(row, 3).number_format = fmt
        if limit_formula:
            ws.cell(row, 4, limit_formula).number_format = fmt
        for col in range(2, 5):
            ws.cell(row, col).border = _BOX
    checks_row = rem_row + 2
    ws.merge_cells(start_row=checks_row, start_column=2, end_row=checks_row, end_column=4)
    ws.cell(checks_row, 2, "PEMERIKSAAN TERHADAP BATAS INPUT PENGGUNA")
    _style_row(ws, checks_row, 2, 4, _NAVY)
    ws.cell(checks_row, 2).font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    for offset, (label, formula) in enumerate([
        ("KDB", f'=IF(C{kdb_row}<=C15,"Di bawah/sama dengan batas","Di atas batas")'),
        ("KLB", f'=IF(C{klb_row}<=C16,"Di bawah/sama dengan batas","Di atas batas")'),
        ("KDH", f'=IF(C{kdh_row}>=C17,"Di atas/sama dengan batas","Di bawah batas")'),
    ], start=1):
        row = checks_row + offset
        ws.cell(row, 2, label).font = _NORMAL_FONT
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=4)
        ws.cell(row, 3, formula).font = _BOLD_FONT
        for col in range(2, 5):
            ws.cell(row, col).border = _BOX

    notes_row = checks_row + 5
    ws.merge_cells(start_row=notes_row, start_column=2, end_row=notes_row, end_column=6)
    ws.cell(notes_row, 2, "CATATAN DAN BATASAN")
    _style_row(ws, notes_row, 2, 6, _YELLOW)
    for index, note in enumerate(notes, start=1):
        row = notes_row + index
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
        ws.cell(row, 2, f"{index}. {note}")
        ws.cell(row, 2).alignment = _LEFT
        ws.cell(row, 2).font = Font(name="Arial", size=9, italic=True)
    disclaimer_row = notes_row + len(notes) + 1
    ws.merge_cells(start_row=disclaimer_row, start_column=2, end_row=disclaimer_row, end_column=6)
    ws.cell(disclaimer_row, 2, "Pemeriksaan di atas hanya dibandingkan dengan batas input pengguna dan bukan penetapan kepatuhan hukum.")
    ws.cell(disclaimer_row, 2).alignment = _LEFT
    ws.cell(disclaimer_row, 2).font = Font(name="Arial", size=9, bold=True, color=_NAVY)

    for col, width in {"A": 3, "B": 40, "C": 24, "D": 28, "E": 16, "F": 16}.items():
        ws.column_dimensions[col].width = width
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "1:2"
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True

    output = BytesIO()
    wb.save(output)
    return output.getvalue()
