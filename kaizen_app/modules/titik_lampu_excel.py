"""Modul Titik Lampu - ekspor Excel (rumus hidup, desain konsisten) dan PDF."""
from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from modules.titik_lampu_denah import denah_png

NAVY, AQUA, SOFT, LINE = "0F3D63", "35B6C9", "EAF3F9", "D5E1EB"
_THIN = Side(style="thin", color=LINE)
_BOX = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_F_FILL = PatternFill("solid", fgColor=NAVY)
_SOFT = PatternFill("solid", fgColor=SOFT)
_MID = Alignment(horizontal="center", vertical="center", wrap_text=True)
_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
_NW = Alignment(horizontal="left", vertical="center", wrap_text=False)
F_N = Font(name="Arial", size=10)
F_B = Font(name="Arial", size=10, bold=True)
F_IN = Font(name="Arial", size=10, color="0000FF")      # biru = input
F_H = Font(name="Arial", size=10, bold=True, color="FFFFFF")
F_I = Font(name="Arial", size=9, italic=True, color="6B7C8C")
F_T = Font(name="Arial", size=15, bold=True, color="FFFFFF")
F_S = Font(name="Arial", size=12, bold=True, color=NAVY)
MAIN = "'Titik Lampu'"


def _put(ws, ref, val, font=F_N, fill=None, al=_MID, fmt=None, border=True):
    c = ws[ref]
    c.value = val
    c.font, c.alignment = font, al
    if border:
        c.border = _BOX
    if fill:
        c.fill = fill
    if fmt:
        c.number_format = fmt


def _merge(ws, rng, val, **kw):
    ws.merge_cells(rng)
    _put(ws, rng.split(":")[0], val, **kw)
    if kw.get("border", True):
        for row in ws[rng]:
            for c in row:
                c.border = _BOX


def _judul(ws, rng, teks, tinggi=32):
    _merge(ws, rng, teks, font=F_T, fill=_F_FILL, al=_NW, border=False)
    ws.row_dimensions[int(rng.split(":")[0][1:])].height = tinggi


def _status_cf(ws, rng, first):
    for teks, warna, fc in [("MEMENUHI", "DDF3E6", "1E8E5A"), ("KURANG", "FCE8E6", "C0392B"), ("MANUAL", "FFF1CC", "C77700")]:
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'{first}="{teks}"'],
                                      fill=PatternFill("solid", bgColor=warna, fgColor=warna), font=Font(bold=True, color=fc)))


def build_excel(h: dict, data: dict, proyek: dict) -> bytes:
    t, P = h["tabel"], h["P"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Titik Lampu"
    wr = wb.create_sheet("Rekap")
    wd = wb.create_sheet("Denah")
    wl = wb.create_sheet("Standar Pencahayaan")
    wn = wb.create_sheet("SNI & Peraturan")
    put = lambda *a, **k: _put(ws, *a, **k)
    merge = lambda *a, **k: _merge(ws, *a, **k)

    # ============================================ sheet Standar Pencahayaan
    _judul(wl, "B1:G1", "TINGKAT PENCAHAYAAN MINIMUM PER FUNGSI RUANG")
    for col, tx in zip("BCDEFG", ["No", "Kelompok", "Fungsi ruang", "E (lux)", "Ra min", "Sumber / keterangan"]):
        _put(wl, f"{col}3", tx, F_H, _F_FILL)
    for i, e in enumerate(data["lux"]):
        r = 4 + i
        _put(wl, f"B{r}", i + 1)
        _put(wl, f"C{r}", e["kelompok"], F_N, al=_LEFT)
        _put(wl, f"D{r}", e["fungsi"], F_B, al=_LEFT)
        _put(wl, f"E{r}", e["lux"], F_IN, fmt="#,##0")
        _put(wl, f"F{r}", e["ra"])
        _put(wl, f"G{r}", e["sumber"] + (f" · {e['ket']}" if e["ket"] else ""), F_N, al=_LEFT)
        if e["kelompok"].startswith("Tambahan"):
            for col in "BCDEFG":
                wl[f"{col}{r}"].fill = PatternFill("solid", fgColor="FFF9EC")
    fin = 4 + len(data["lux"]) + 1
    _merge(wl, f"B{fin}:G{fin}", data["catatan_lux"], font=F_I, al=_LEFT, border=False)
    wl.row_dimensions[fin].height = 66
    for col, w in {"A": 2, "B": 5, "C": 16, "D": 34, "E": 10, "F": 9, "G": 62}.items():
        wl.column_dimensions[col].width = w
    wl.sheet_properties.pageSetUpPr.fitToPage = True
    wl.page_setup.fitToWidth, wl.page_setup.fitToHeight = 1, 1

    # ============================================ sheet SNI & peraturan
    _judul(wn, "B1:F1", "LANDASAN PERENCANAAN: SNI & PERATURAN TERKAIT TITIK LAMPU")
    for col, tx in zip("BCDEF", ["No", "Standar / Peraturan", "Judul", "Peran pada perhitungan", "Catatan"]):
        _put(wn, f"{col}3", tx, F_H, _F_FILL)
    for i, s in enumerate(data["standar"]):
        r = 4 + i
        _put(wn, f"B{r}", i + 1)
        _put(wn, f"C{r}", s["kode"], F_B, al=_LEFT)
        _put(wn, f"D{r}", s["judul"], F_N, al=_LEFT)
        _put(wn, f"E{r}", s["peran"], F_N, al=_LEFT)
        _put(wn, f"F{r}", s["catatan"], F_N, al=_LEFT)
        wn.row_dimensions[r].height = 44
    _put(wn, f"B{5 + len(data['standar'])}", data["catatan_standar"], F_I, al=_NW, border=False)
    for col, w in {"A": 2, "B": 5, "C": 30, "D": 44, "E": 52, "F": 40}.items():
        wn.column_dimensions[col].width = w
    wn.page_setup.orientation = "landscape"
    wn.sheet_properties.pageSetUpPr.fitToPage = True
    wn.page_setup.fitToWidth, wn.page_setup.fitToHeight = 1, 0

    # ============================================ sheet Denah
    _judul(wd, "B1:N1", "DENAH SKEMATIK TITIK LAMPU (ILUSTRASI JUMLAH, BUKAN GAMBAR TEKNIS PENEMPATAN)")
    img = XLImage(BytesIO(denah_png(h)))
    img.width = 1150
    img.height = int(1150 * (img.height / max(1, img.width))) if False else int(1150 * 1108 / 1390)
    ws_h = wd
    ws_h.add_image(img, "B3")
    wd.sheet_view.showGridLines = False
    wd.page_setup.orientation = "landscape"
    wd.sheet_properties.pageSetUpPr.fitToPage = True
    wd.page_setup.fitToWidth, wd.page_setup.fitToHeight = 1, 1

    # ============================================ sheet utama
    lebar = {"A": 2, "B": 5, "C": 30, "D": 8, "E": 8, "F": 9, "G": 17, "H": 8, "I": 12, "J": 7, "K": 8, "L": 9, "M": 7,
             "N": 7, "O": 5, "P": 11, "Q": 14, "R": 10, "S": 9, "T": 9, "U": 9, "V": 11, "W": 15, "X": 11, "Y": 12, "Z": 18}
    for col, w in lebar.items():
        ws.column_dimensions[col].width = w
    _judul(ws, "B1:X1", "PERHITUNGAN JUMLAH TITIK LAMPU PADA BANGUNAN — METODE LUMEN", 34)
    for r, (lab, key) in enumerate([("PEKERJAAN", "pekerjaan"), ("LOKASI", "lokasi"), ("TAHUN", "tahun"),
                                    ("ITEM PEKERJAAN", "item")], start=3):
        merge(f"B{r}:C{r}", lab, font=Font(name="Arial", size=10, bold=True, color=NAVY), fill=_SOFT, al=_NW, border=False)
        merge(f"D{r}:L{r}", f": {proyek.get(key, '')}", font=F_N, fill=_SOFT, al=_NW, border=False)
    merge("B8:X8", "Landasan — Tingkat pencahayaan: SNI 6197:2020 Tabel 1 · Perancangan pencahayaan buatan: SNI 03-6575-2001 "
                   "(lengkap pada sheet 'SNI & Peraturan')", font=F_I, al=_LEFT, border=False)

    r = 10

    def sec(no, judul):
        nonlocal r
        put(f"B{r}", no, F_H, _F_FILL)
        merge(f"C{r}:X{r}", judul, font=F_S, al=_NW, border=False)
        for ci in range(3, 25):
            ws.cell(row=r, column=ci).border = Border(bottom=Side(style="medium", color=AQUA))
        ws.row_dimensions[r].height = 22
        r += 1

    sec(1, "Dasar Perhitungan")
    merge(f"C{r}:H{r}", "N = (E × A) / (Φ × LLF × CU × n)", font=Font(name="Cambria", size=13, italic=True, color=NAVY),
          fill=_SOFT, al=_MID)
    merge(f"I{r}:N{r}", "Φ = W × (lm/W)", font=Font(name="Cambria", size=13, italic=True, color=NAVY), fill=_SOFT, al=_MID)
    ws.row_dimensions[r].height = 26
    r += 1
    for a, b in [("N", "jumlah armatur lampu (titik) — dibulatkan ke atas"), ("E", "kuat penerangan / target penerangan (lux)"),
                 ("P, L, A", "panjang, lebar (m), luas ruangan A = P × L (m²)"),
                 ("Φ", "fluks cahaya satu lampu (lumen);  W = daya lampu (watt);  lm/W = luminous efficacy"),
                 ("LLF", "light loss factor / faktor cahaya rugi (0,7 – 0,8)"),
                 ("CU", "coefficient of utilization / faktor penambahan cahaya (50% – 60%)"),
                 ("n", "jumlah lampu dalam 1 armatur")]:
        put(f"C{r}", f"{a}  =  {b}", F_I, al=_NW, border=False)
        r += 1
    r += 1

    sec(2, "Parameter")
    put(f"C{r}", "LLF (light loss factor)", al=_LEFT)
    put(f"D{r}", P["llf"], F_IN, fmt="0.00")
    LLF = f"$D${r}"
    r += 1
    put(f"C{r}", "CU (coefficient of utilization)", al=_LEFT)
    put(f"D{r}", P["cu"], F_IN, fmt="0.00")
    CU = f"$D${r}"
    r += 2

    sec(3, "Tabel Perhitungan Titik Lampu")
    h1 = r
    h2 = r + 2
    heads = [("B", "NO"), ("C", "NAMA RUANGAN"), ("D", "P (m)"), ("E", "L (m)"), ("F", "Area (m²)"), ("G", "Jenis Ruangan (SNI 6197:2020)"),
             ("H", "E (lux)"), ("I", "Jenis Lampu"), ("J", "W (watt)"), ("K", "L/W (lm/W)"), ("L", "Lumen (Φ)"), ("M", "LLF"),
             ("N", "CU"), ("O", "n"), ("P", "E × A"), ("Q", "Φ × LLF × CU × n"), ("R", "N (hitung)"), ("S", "Round Up"),
             ("T", "Titik manual"), ("U", "Titik final"), ("V", "E tercapai (lux)"), ("W", "Status"), ("X", "Daya (W)")]
    for col, tx in heads:
        merge(f"{col}{h1}:{col}{h2}", tx, font=F_H, fill=_F_FILL)
    ws.row_dimensions[h1].height = 22
    ws.row_dimensions[h2].height = 22
    r = h2 + 1
    first = r
    nomor_baris = []
    for lt, grp in t.groupby("Lantai", sort=False):
        merge(f"B{r}:X{r}", lt.upper(), font=F_B, fill=_SOFT, al=_NW)
        r += 1
        for i, x in enumerate(grp.itertuples(), start=1):
            nm = lambda v: None if (v is None or v != v) else v
            put(f"B{r}", i)
            put(f"C{r}", x.Ruangan, F_IN, al=_LEFT)
            put(f"D{r}", nm(x.P), F_IN, fmt="0.00")
            put(f"E{r}", nm(x.L), F_IN, fmt="0.00")
            put(f"F{r}", f'=IF(AND(ISNUMBER(D{r}),ISNUMBER(E{r})),D{r}*E{r},"")', fmt="0.00")
            put(f"G{r}", x.JenisR, F_IN, al=_LEFT)
            put(f"H{r}", nm(x.E), F_IN, fmt="#,##0")
            put(f"I{r}", x.Lampu, F_IN)
            put(f"J{r}", x.W, F_IN, fmt="0")
            put(f"K{r}", x.lmw, F_IN, fmt="0")
            put(f"L{r}", f"=J{r}*K{r}", fmt="#,##0")
            put(f"M{r}", f"={LLF}", fmt="0.00")
            put(f"N{r}", f"={CU}", fmt="0.00")
            put(f"O{r}", x.n, F_IN, fmt="0")
            put(f"P{r}", f'=IF(F{r}="","",H{r}*F{r})', fmt="#,##0")
            put(f"Q{r}", f"=L{r}*M{r}*N{r}*O{r}", fmt="#,##0")
            put(f"R{r}", f'=IF(P{r}="","",P{r}/Q{r})', fmt="0.00")
            put(f"S{r}", f'=IF(R{r}="","",MAX(1,ROUNDUP(ROUND(R{r},9),0)))', fmt="0")
            put(f"T{r}", nm(x.manual), F_IN, fmt="0")
            put(f"U{r}", f'=IF(T{r}<>"",T{r},S{r})', F_B, fmt="0")
            put(f"V{r}", f'=IF(OR(F{r}="",U{r}=""),"",U{r}*Q{r}/F{r})', fmt="#,##0")
            put(f"W{r}", f'=IF(F{r}="","MANUAL",IF(V{r}>=H{r}-0.000001,"MEMENUHI","KURANG"))', F_B)
            put(f"X{r}", f'=IF(U{r}="","",U{r}*J{r}*O{r})', fmt="#,##0")
            ws[f"Y{r}"] = lt
            ws[f"Z{r}"] = f'=I{r}&" "&J{r}&" W"'
            nomor_baris.append(r)
            r += 1
    last = r - 1
    merge(f"B{r}:E{r}", "TOTAL", font=F_B, fill=_SOFT, al=_NW)
    put(f"F{r}", f"=SUM(F{first}:F{last})", F_B, _SOFT, fmt="#,##0.00")
    for ci in range(7, 25):
        put(f"{chr(64 + ci)}{r}", None, F_B, _SOFT)
    put(f"U{r}", f"=SUM(U{first}:U{last})", F_B, _SOFT, fmt="0")
    put(f"X{r}", f"=SUM(X{first}:X{last})", F_B, _SOFT, fmt="#,##0")
    tot = r
    r += 1
    _status_cf(ws, f"W{first}:W{last}", f"W{first}")
    put(f"B{r}", "Round Up dihitung otomatis (naik ke bilangan bulat berikutnya, minimal 1). Titik manual diisi bila jumlah titik "
                 "ditetapkan sendiri (mis. ruangan tanpa dimensi); nilai tersebut menggantikan hasil Round Up.", F_I, al=_NW, border=False)
    r += 2

    sec(4, "Kesimpulan")
    kes = (f'="Perhitungan jumlah titik lampu menggunakan metode lumen dengan LLF "&TEXT({LLF},"0.00")&" dan CU "&TEXT({CU},"0.00")&". '
           f'Pada "&COUNTA(C{first}:C{last})&" ruangan dibutuhkan "&U{tot}&" titik lampu dengan daya terpasang "&TEXT(X{tot},"#,##0")&" W. "&'
           f'IF(COUNTIF(W{first}:W{last},"KURANG")=0,"Seluruh ruangan berdimensi memenuhi tingkat pencahayaan target.",'
           f'COUNTIF(W{first}:W{last},"KURANG")&" ruangan masih di bawah target; periksa titik manual.")')
    merge(f"C{r}:X{r}", kes, font=F_N, fill=PatternFill("solid", fgColor="F1FAF5"), al=_LEFT)
    ws.row_dimensions[r].height = 44
    r += 2
    merge(f"B{r}:X{r}", "Keterangan: sel biru = input (boleh diubah); sel hitam = rumus otomatis. Nilai E diambil dari sheet 'Standar Pencahayaan'. "
          + data["catatan_standar"], font=F_I, al=_LEFT, border=False)
    ws.row_dimensions[r].height = 28

    ws.column_dimensions["Y"].hidden = True
    ws.column_dimensions["Z"].hidden = True
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = f"D{first}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0

    # ============================================ sheet Rekap
    lantai = list(h["lantai"]["Lantai"])
    rng = lambda col: f"{MAIN}!${col}${first}:${col}${last}"
    _judul(wr, "B1:H1", "REKAP TITIK LAMPU")
    _put(wr, "B3", "Rekap per Lantai", F_S, al=_NW, border=False)
    for col, tx in zip("BCDEFG", ["Lantai", "Ruangan", "Luas (m²)", "Titik lampu", "Daya (W)", "W/m²"]):
        _put(wr, f"{col}4", tx, F_H, _F_FILL)
    rr = 5
    for lt in lantai:
        _put(wr, f"B{rr}", lt, F_B, al=_LEFT)
        _put(wr, f"C{rr}", f'=COUNTIFS({rng("Y")},$B{rr})', fmt="0")
        _put(wr, f"D{rr}", f'=SUMIFS({rng("F")},{rng("Y")},$B{rr})', fmt="#,##0.00")
        _put(wr, f"E{rr}", f'=SUMIFS({rng("U")},{rng("Y")},$B{rr})', F_B, fmt="0")
        _put(wr, f"F{rr}", f'=SUMIFS({rng("X")},{rng("Y")},$B{rr})', fmt="#,##0")
        _put(wr, f"G{rr}", f'=IF(D{rr}>0,SUMIFS({rng("X")},{rng("Y")},$B{rr},{rng("F")},">0")/D{rr},"")', fmt="0.0")
        rr += 1
    _put(wr, f"B{rr}", "TOTAL", F_B, _SOFT, al=_LEFT)
    for col, nf in zip("CDEF", ["0", "#,##0.00", "0", "#,##0"]):
        _put(wr, f"{col}{rr}", f"=SUM({col}5:{col}{rr - 1})", F_B, _SOFT, fmt=nf)
    _put(wr, f"G{rr}", f'=IF(D{rr}>0,SUMIFS({rng("X")},{rng("F")},">0")/D{rr},"")', F_B, _SOFT, fmt="0.0")
    rr += 3
    _put(wr, f"B{rr}", "Rekap per Jenis Lampu (acuan kolom DL pada Modul Beban Listrik / SLD)", F_S, al=_NW, border=False)
    rr += 1
    _put(wr, f"B{rr}", "Jenis lampu", F_H, _F_FILL)
    for i, lt in enumerate(lantai):
        _put(wr, f"{chr(67 + i)}{rr}", lt, F_H, _F_FILL)
    ct = chr(67 + len(lantai))
    _put(wr, f"{ct}{rr}", "Total", F_H, _F_FILL)
    p0 = rr + 1
    rr += 1
    for lab in h["pivot"].index:
        _put(wr, f"B{rr}", lab, F_B, al=_LEFT)
        for i, lt in enumerate(lantai):
            col = chr(67 + i)
            _put(wr, f"{col}{rr}", f'=SUMIFS({rng("U")},{rng("Y")},{col}${p0 - 1},{rng("Z")},$B{rr})', fmt='0;-0;"–"')
        _put(wr, f"{ct}{rr}", f"=SUM(C{rr}:{chr(66 + len(lantai))}{rr})", F_B, fmt="0")
        rr += 1
    _put(wr, f"B{rr}", "TOTAL", F_B, _SOFT, al=_LEFT)
    for i in range(len(lantai) + 1):
        col = chr(67 + i)
        _put(wr, f"{col}{rr}", f"=SUM({col}{p0}:{col}{rr - 1})", F_B, _SOFT, fmt="0")
    for col, w in {"A": 2, "B": 26, "C": 14, "D": 14, "E": 14, "F": 14, "G": 12, "H": 12}.items():
        wr.column_dimensions[col].width = w
    wr.sheet_view.showGridLines = False
    wr.sheet_properties.pageSetUpPr.fitToPage = True
    wr.page_setup.fitToWidth, wr.page_setup.fitToHeight = 1, 1

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


