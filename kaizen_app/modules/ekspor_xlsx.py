"""Ekspor ke Excel (.xlsx) - tanpa Streamlit.

File SLD memakai RUMUS HIDUP (Load, KA, total, VA, Ampere, saran kabel induk)
beserta nilai tersimpan, jadi angka langsung tampil di aplikasi apa pun dan
menghitung ulang bila sel kuning diubah di Excel.

MCB UP dan Cable adalah hasil aplikasi (dipilih dari beban menurut Tabel AKLI
dan nama sirkuit) sehingga ditulis sebagai nilai, bukan rumus.
"""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

from modules import akli_calc
from modules.beban_listrik_calc import COL_GRUP, COL_KABEL, COL_LAIN, COL_MCB, COL_NAMA
from utils.formatting import bulatkan

FONT = "Arial"
NAVY, KUNING, HIJAU, CATATAN, ABU = "#1F3864", "#FFF200", "#00B050", "#FFF9C4", "#EEF2F8"
GARIS = "#8C96A3"
NAMA_SHEET_AKLI = "AKLI"

AKLI_HEADER = {
    "Fasa": "Fasa", "VA": "VA", "VA Pembulatan": "VA Pembulatan", "kVA": "kVA",
    "Watt (PF 0,8)": "Watt (PF 0,8)", "Gol": "Gol", "MCB (A)": "MCB / MCCB (A)",
    "Tegangan (V)": "V", "Tipe Kabel": "Tipe Kabel", "Inti": "Inti",
    "Ukuran (mm²)": "Ukuran (mm²)",
}
AKLI_FORMAT = {  # format angka tiap kolom
    "Fasa": "0", "VA": "#,##0", "VA Pembulatan": "#,##0", "kVA": "General",
    "Watt (PF 0,8)": "#,##0", "Gol": "@", "MCB (A)": "0", "Tegangan (V)": "0",
    "Tipe Kabel": "@", "Inti": "0", "Ukuran (mm²)": "General",
}
AKLI_LEBAR = {"Fasa": 7, "VA": 11, "VA Pembulatan": 14, "kVA": 8, "Watt (PF 0,8)": 14,
              "Gol": 6, "MCB (A)": 15, "Tegangan (V)": 7, "Tipe Kabel": 16, "Inti": 7,
              "Ukuran (mm²)": 14}


# ------------------------------------------------------------------ helper
def _fmt(wb, **kw):
    return wb.add_format({"font_name": FONT, "font_size": 10, "valign": "vcenter", **kw})


def _kotak(**kw):
    return {"border": 1, "border_color": GARIS, **kw}


def _gabung(ws, r1, c1, r2, c2, data, fmt):
    """merge_range yang aman untuk 1 sel."""
    if (r1, c1) == (r2, c2):
        ws.write(r1, c1, data, fmt)
    else:
        ws.merge_range(r1, c1, r2, c2, data, fmt)


def _gabung_rumus(ws, r1, c1, r2, c2, rumus, fmt, nilai):
    if (r1, c1) != (r2, c2):
        ws.merge_range(r1, c1, r2, c2, "", fmt)
    ws.write_formula(r1, c1, rumus, fmt, nilai)


def _b0(x) -> str:
    """Bulat ke bilangan bulat (setengah naik, sama seperti ROUND Excel), sebagai teks."""
    return str(int(bulatkan(x, 0)))


def _g(x) -> str:
    """Angka -> teks ala Excel (tanpa pemisah ribuan), untuk nilai tersimpan rumus teks."""
    return f"{float(x):g}"


# ------------------------------------------------------------------ AKLI
def _tulis_akli(wb, ws, tabel: pd.DataFrame, judul: str) -> dict:
    """Tulis tabel AKLI. Return info rentang baris 1 fasa (nomor baris Excel, 1-based)."""
    t = akli_calc.normalisasi(tabel)
    t = t.sort_values(["Fasa", "MCB (A)"], kind="stable").reset_index(drop=True)

    f_judul = _fmt(wb, bold=True, font_size=14)
    f_sub = _fmt(wb, italic=True, font_color="#555555")
    f_head = _fmt(wb, **_kotak(bold=True, bg_color=KUNING, align="center", text_wrap=True))

    ws.write(0, 0, judul, f_judul)
    ws.write(1, 0, f"Sumber: tabel AKLI (diedit di aplikasi Kaizen PBG) - dibuat {datetime.now():%d-%m-%Y %H:%M}", f_sub)
    baris_head = 3
    ws.set_row(baris_head, 30)
    for c, kol in enumerate(akli_calc.COLS):
        ws.write(baris_head, c, AKLI_HEADER[kol], f_head)
        ws.set_column(c, c, AKLI_LEBAR[kol])

    fmts = {kol: _fmt(wb, **_kotak(align="center", num_format=AKLI_FORMAT[kol]))
            for kol in akli_calc.COLS}
    for i, row in t.iterrows():
        r = baris_head + 1 + i
        for c, kol in enumerate(akli_calc.COLS):
            v = row[kol]
            if isinstance(v, str):
                ws.write_string(r, c, v, fmts[kol])
            elif pd.isna(v):
                ws.write_blank(r, c, None, fmts[kol])
            else:
                ws.write_number(r, c, float(v), fmts[kol])

    satu = t.index[t["Fasa"] == 1].tolist()
    info = {"satu_fasa": None}
    if satu:
        info["satu_fasa"] = (baris_head + 1 + satu[0] + 1, baris_head + 1 + satu[-1] + 1)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    return info


def akli_xlsx(tabel: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet(NAMA_SHEET_AKLI)
    _tulis_akli(wb, ws, tabel, "TABEL AKLI - DAYA TERSEDIA, MCB / MCCB, DAN UKURAN KABEL")
    wb.close()
    return buf.getvalue()


# ------------------------------------------------------------------ SLD
def sld_xlsx(proyek: dict, sistem: dict, labels: list[str], out: dict,
             induk: dict | None, catatan: list[str], tabel_akli: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet("SLD")
    ws_akli = wb.add_worksheet(NAMA_SHEET_AKLI)
    info_akli = _tulis_akli(wb, ws_akli, tabel_akli, "TABEL AKLI (acuan perhitungan SLD)")

    hasil, qcols, watt = out["hasil"], out["qcols"], out["watt"]
    n, m = len(qcols), len(hasil)
    C_LAIN = 7 + n

    # ---- format
    f_judul = _fmt(wb, bold=True, font_size=14)
    f_sub = _fmt(wb, italic=True, font_color="#555555")
    f_k = _fmt(wb, bold=True)
    f_teks = _fmt(wb)
    f_head = _fmt(wb, **_kotak(bold=True, font_color="#FFFFFF", bg_color=NAVY, align="center", text_wrap=True))
    f_head_y = _fmt(wb, **_kotak(bold=True, bg_color=KUNING, align="center", text_wrap=True))
    f_head_y_n = _fmt(wb, **_kotak(bold=True, bg_color=KUNING, align="center", num_format="#,##0"))
    f_lbl = _fmt(wb, **_kotak())
    f_in_n0 = _fmt(wb, **_kotak(bg_color=KUNING, align="center", num_format="#,##0"))
    f_in_n2 = _fmt(wb, **_kotak(bg_color=KUNING, align="center", num_format="0.00"))
    f_in_t = _fmt(wb, **_kotak(bg_color=KUNING, align="left"))
    f_nama = _fmt(wb, **_kotak(align="left"))
    f_c = _fmt(wb, **_kotak(align="center"))
    f_n0 = _fmt(wb, **_kotak(align="center", num_format="#,##0"))
    f_n2 = _fmt(wb, **_kotak(align="center", num_format="#,##0.00"))
    f_r = _fmt(wb, **_kotak(align="center", bold=True, bg_color=ABU, num_format="#,##0"))
    f_cnt_in = _fmt(wb, **_kotak(align="center", num_format="#,##0"))
    f_tot_lbl = _fmt(wb, **_kotak(bold=True, bg_color=ABU, align="left"))
    f_tot_r = _fmt(wb, **_kotak(bold=True, bg_color=ABU, align="center", num_format="#,##0"))
    f_tot_g = _fmt(wb, **_kotak(bold=True, font_color="#FFFFFF", bg_color=HIJAU, align="center", num_format="#,##0"))
    f_va = _fmt(wb, **_kotak(bold=True, bg_color=ABU, align="center", num_format='#,##0 "VA"'))
    f_amp = _fmt(wb, **_kotak(bold=True, bg_color=ABU, align="center", num_format='#,##0.00 "A"'))
    f_kabel = _fmt(wb, **_kotak(bold=True, bg_color=ABU, align="center"))
    f_note = _fmt(wb, **_kotak(italic=True, bg_color=CATATAN, align="left"))

    # ---- lebar kolom
    ws.set_column(0, 0, 26)
    ws.set_column(1, 1, 14)
    ws.set_column(2, 4, 10)
    ws.set_column(5, 5, 13)
    ws.set_column(6, 6, 12)
    ws.set_column(7, C_LAIN - 1, 11)
    ws.set_column(C_LAIN, C_LAIN, 11)

    # ---- judul + data proyek
    ws.write(0, 0, "PERHITUNGAN KEBUTUHAN LISTRIK (SLD)", f_judul)
    ws.write(1, 0, f"Dibuat dari aplikasi Kaizen PBG - {datetime.now():%d-%m-%Y %H:%M}", f_sub)
    for i, (k, v) in enumerate([("PEKERJAAN", proyek["pekerjaan"]), ("LOKASI", proyek["lokasi"]),
                                ("TAHUN", proyek["tahun"]), ("ITEM PEKERJAAN", proyek["item"])]):
        ws.write(3 + i, 0, k, f_k)
        ws.write(3 + i, 1, f": {v}", f_teks)

    # ---- data sistem (sel kuning = input; dipakai rumus)
    ws.write(8, 0, "Sistem", f_head)
    ws.write(8, 1, "Nilai", f_head)
    param = [
        ("Tegangan Sistem (V)", float(sistem["tegangan"]), f_in_n0),
        ("Faktor Daya (PF)", float(sistem["pf"]), f_in_n2),
        ("Faktor Beban Puncak", float(sistem["faktor_puncak"]), f_in_n2),
        ("Sistem Grounding", str(sistem["grounding"]), f_in_t),
        ("Resistansi Grounding Max", str(sistem["res_grounding"]), f_in_t),
        ("Proteksi Kebocoran", str(sistem["proteksi"]), f_in_t),
    ]
    for i, (k, v, fm) in enumerate(param):
        ws.write(9 + i, 0, k, f_lbl)
        if isinstance(v, str):
            ws.write_string(9 + i, 1, v, fm)
        else:
            ws.write_number(9 + i, 1, v, fm)
    V = xl_rowcol_to_cell(9, 1, row_abs=True, col_abs=True)
    PF = xl_rowcol_to_cell(10, 1, row_abs=True, col_abs=True)
    FP = xl_rowcol_to_cell(11, 1, row_abs=True, col_abs=True)

    # ---- header tabel utama (3 baris, mirip tampilan aplikasi)
    r0 = 16
    ws.set_row(r0, 22)
    ws.set_row(r0 + 1, 30)
    _gabung(ws, r0, 0, r0 + 2, 0, "Nama Sirkuit", f_head)
    _gabung(ws, r0, 1, r0 + 2, 1, "Grouping\nNumber", f_head)
    _gabung(ws, r0, 2, r0, 4, "Circuit Breaker", f_head)
    _gabung(ws, r0, 5, r0, 6, "Grouping Power", f_head)
    _gabung(ws, r0, 7, r0, 6 + n, "BEBAN", f_head)
    _gabung(ws, r0, C_LAIN, r0 + 2, C_LAIN, "Lain-lain\n(W)", f_head)
    for c, teks in zip(range(2, 7), ["MCB UP", "KA", "Load", "Cable", "R"]):
        _gabung(ws, r0 + 1, c, r0 + 2, c, teks, f_head)
    for i in range(n):
        ws.write_string(r0 + 1, 7 + i, labels[i], f_head_y)
        ws.write_number(r0 + 2, 7 + i, float(watt[i]), f_head_y_n)

    # rentang watt (baris header ke-3) untuk SUMPRODUCT
    baris_watt = r0 + 3  # nomor baris Excel (1-based) dari baris header ke-3
    rng_watt = f"${xl_col_to_name(7)}${baris_watt}:${xl_col_to_name(6 + n)}${baris_watt}"

    # ---- isi baris sirkuit
    rb = r0 + 3
    for i, (_, r) in enumerate(hasil.iterrows()):
        xr = rb + i + 1  # nomor baris Excel
        rr = rb + i
        ws.write_string(rr, 0, str(r[COL_NAMA]), f_nama)
        ws.write_number(rr, 1, float(r[COL_GRUP]), f_c)
        ws.write_number(rr, 2, float(r[COL_MCB]), f_c)
        ws.write_formula(rr, 3, f"=IFERROR(E{xr}/({V}*{PF}),0)", f_n2, float(r["ka"]))
        rng_cnt = f"{xl_col_to_name(7)}{xr}:{xl_col_to_name(6 + n)}{xr}"
        ws.write_formula(rr, 4, f"=SUMPRODUCT({rng_watt},{rng_cnt})+{xl_col_to_name(C_LAIN)}{xr}",
                         f_n0, float(r["load"]))
        ws.write_string(rr, 5, str(r[COL_KABEL]), f_c)
        ws.write_formula(rr, 6, f"=E{xr}", f_r, float(r["load"]))
        for j, q in enumerate(qcols):
            v = float(r[q])
            if v:
                ws.write_number(rr, 7 + j, v, f_cnt_in)
            else:
                ws.write_blank(rr, 7 + j, None, f_cnt_in)
        v = float(r[COL_LAIN])
        if v:
            ws.write_number(rr, C_LAIN, v, f_cnt_in)
        else:
            ws.write_blank(rr, C_LAIN, None, f_cnt_in)

    first_x, last_x = rb + 1, rb + m  # nomor baris Excel baris sirkuit pertama & terakhir

    # ---- total
    rt = rb + m
    xt = rt + 1
    _gabung(ws, rt, 0, rt, 5, "TOTAL LOAD", f_tot_lbl)
    ws.write_formula(rt, 6, f"=SUM(G{first_x}:G{last_x})", f_tot_r, float(out["total_load"]))
    for j in range(n):
        cn = xl_col_to_name(7 + j)
        ws.write_formula(rt, 7 + j, f"=SUM({cn}{first_x}:{cn}{last_x})", f_tot_g, float(out["total_qty"][j]))
    cl = xl_col_to_name(C_LAIN)
    ws.write_formula(rt, C_LAIN, f"=SUM({cl}{first_x}:{cl}{last_x})", f_tot_g, float(out["total_lain"]))

    # ---- VA & Ampere
    rv, xv = rt + 1, rt + 2
    _gabung(ws, rv, 0, rv, 5, "VA (BEBAN PUNCAK WORST CASE SCENARIO)", f_tot_lbl)
    ws.write_formula(rv, 6, f"=G{xt}*{FP}", f_va, float(out["va"]))
    _gabung_rumus(ws, rv, 7, rv, C_LAIN,
                  f'="Catatan : Semua Elektronik Nyala Bersamaan (faktor puncak x"&{FP}&")"', f_note,
                  f"Catatan : Semua Elektronik Nyala Bersamaan (faktor puncak x{_g(sistem['faktor_puncak'])})")

    ra, xa = rt + 2, rt + 3
    _gabung(ws, ra, 0, ra, 5, "AMPERE", f_tot_lbl)
    ws.write_formula(ra, 6, f"=IFERROR(G{xv}/{V},0)", f_amp, float(out["ampere"]))
    _gabung_rumus(ws, ra, 7, ra, C_LAIN, f'="Catatan : Ampere = VA / tegangan ("&{V}&" V)"', f_note,
                  f"Catatan : Ampere = VA / tegangan ({_g(sistem['tegangan'])} V)")

    # ---- saran kabel induk (rumus ke sheet AKLI, tabel 1 fasa)
    baris_akhir = ra
    if info_akli["satu_fasa"]:
        a, b = info_akli["satu_fasa"]

        def rng(kolom: str) -> str:
            return f"{NAMA_SHEET_AKLI}!${kolom}${a}:${kolom}${b}"

        idx = f'(COUNTIF({rng("B")},"<"&G{xv})+1)'
        ada = f'{idx}<=ROWS({rng("B")})'
        rumus_kabel = (f'=IF({ada},INDEX({rng("J")},{idx})&"x"&SUBSTITUTE(INDEX({rng("K")},{idx}),".",",")&" mm²","-")')
        rumus_note = (
            f'=IF({ada},"Catatan : Mengacu tabel AKLI 1 fasa - daya tersedia "&INDEX({rng("B")},{idx})'
            f'&" VA, MCB induk "&INDEX({rng("G")},{idx})&" A, "&INDEX({rng("I")},{idx}),'
            f'"Catatan : Beban puncak melebihi tabel AKLI 1 fasa, pertimbangkan sistem 3 fasa")'
        )
        if induk and induk.get("ok"):
            nilai_kabel = induk["teks"]
            nilai_note = (f"Catatan : Mengacu tabel AKLI 1 fasa - daya tersedia {_g(induk['va_tersedia'])} VA, "
                          f"MCB induk {_g(induk['mcb'])} A, {induk['tipe']}")
        else:
            nilai_kabel = "-"
            nilai_note = "Catatan : Beban puncak melebihi tabel AKLI 1 fasa, pertimbangkan sistem 3 fasa"
        ri = rt + 3
        _gabung(ws, ri, 0, ri, 5, "SARAN UKURAN KABEL INDUK (BEBAN KESELURUHAN)", f_tot_lbl)
        ws.write_formula(ri, 6, rumus_kabel, f_kabel, nilai_kabel)
        _gabung_rumus(ws, ri, 7, ri, C_LAIN, rumus_note, f_note, nilai_note)
        baris_akhir = ri

    # ---- catatan bawah tabel
    rc = baris_akhir + 2
    ws.write(rc, 0, "Catatan :", f_k)
    ws.write(rc + 1, 0, "Pertimbangan penggunaan daya sesuai aturan keamanan 80% dari VA", f_teks)
    ws.write_formula(rc + 2, 0,
                     f'="Total daya dalam satu bangunan dengan semua elektronik menyala "&ROUND(G{xt},0)&" W"',
                     f_teks, f"Total daya dalam satu bangunan dengan semua elektronik menyala {_b0(out['total_load'])} W")
    ws.write_formula(rc + 3, 0, f'="Total Daya Semu (VA) dalam bangunan "&ROUND(G{xv},0)&" VA"',
                     f_teks, f"Total Daya Semu (VA) dalam bangunan {_b0(out['va'])} VA")
    rc += 5
    if catatan:
        ws.write(rc, 0, "Catatan penyesuaian MCB & kabel :", f_k)
        for i, c in enumerate(catatan):
            ws.write(rc + 1 + i, 0, f"- {c}", f_teks)
        rc += len(catatan) + 2
    ws.write(rc, 0, "Keterangan file ini :", f_k)
    for i, t in enumerate([
        "- Sel berwarna kuning dapat diubah; Load, KA, total, VA, Ampere, dan saran kabel induk dihitung ulang otomatis.",
        "- MCB UP dan Cable adalah hasil aplikasi (dipilih dari beban sesuai Tabel AKLI dan nama sirkuit), ditulis sebagai nilai, "
        "bukan rumus, sehingga tidak ikut berubah bila beban diubah di Excel.",
        "- Saran kabel induk dihitung dari Beban Puncak (VA) terhadap kolom VA tabel AKLI 1 fasa pada sheet AKLI.",
    ]):
        ws.write(rc + 1 + i, 0, t, f_teks)

    # ---- cetak
    ws.set_landscape()
    ws.set_paper(8 if n > 12 else 9)  # A3 untuk tabel lebar, selain itu A4
    ws.fit_to_pages(1, 0)
    ws.set_default_row(16)
    ws.set_row(r0, 22)
    ws.set_row(r0 + 1, 30)
    ws.activate()
    wb.close()
    return buf.getvalue()