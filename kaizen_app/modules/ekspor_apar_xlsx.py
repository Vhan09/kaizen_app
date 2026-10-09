"""Ekspor APAR ke Excel (.xlsx) - tanpa Streamlit.

Rumus hidup: ubah sel kuning (klasifikasi, rating, jarak, luas lantai, tabel acuan) dan
cakupan, jumlah APAR per lantai, serta total menghitung ulang. Nilai tersimpan ikut ditulis
sehingga angka langsung tampil di aplikasi apa pun.
"""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from modules import apar_calc as calc
from modules.apar_html import CATATAN_TABEL, DASAR_PERATURAN
from modules.ekspor_xlsx import (
    ABU, CATATAN, GARIS, HIJAU, KUNING, NAVY, _fmt, _gabung, _gabung_rumus, _kotak,
)


def apar_xlsx(proyek: dict, entri: dict, tabel: pd.DataFrame, h: dict) -> bytes:
    tabel = calc.normalisasi_tabel(tabel)
    lantai = calc.normalisasi_lantai(entri["lantai"])

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet("APAR")

    # ---- format
    f_judul = _fmt(wb, bold=True, font_size=14)
    f_sub = _fmt(wb, italic=True, font_color="#555555")
    f_k = _fmt(wb, bold=True)
    f_teks = _fmt(wb)
    f_wrap = _fmt(wb, text_wrap=True, valign="top")
    f_sec = _fmt(wb, bold=True, font_color="#FFFFFF", bg_color=NAVY)
    f_head = _fmt(wb, **_kotak(bold=True, font_color="#FFFFFF", bg_color=NAVY, align="center", text_wrap=True))
    f_lbl = _fmt(wb, **_kotak(align="left", text_wrap=True))
    f_lbl_b = _fmt(wb, **_kotak(align="left", bold=True, bg_color=ABU))
    f_c = _fmt(wb, **_kotak(align="center"))
    f_in_t = _fmt(wb, **_kotak(bg_color=KUNING, align="center"))
    f_in_tl = _fmt(wb, **_kotak(bg_color=KUNING, align="left"))
    f_in_n = _fmt(wb, **_kotak(bg_color=KUNING, align="center", num_format="#,##0.##"))
    f_in_a = _fmt(wb, **_kotak(bg_color=KUNING, align="center", num_format='0.##"-A"'))
    f_in_m2 = _fmt(wb, **_kotak(bg_color=KUNING, align="center", num_format='#,##0.## "m²"'))
    f_in_m = _fmt(wb, **_kotak(bg_color=KUNING, align="center", num_format='#,##0.## "m"'))
    f_n = _fmt(wb, **_kotak(align="center", num_format="#,##0.##"))
    f_n2 = _fmt(wb, **_kotak(align="center", num_format="#,##0.00"))
    f_m2 = _fmt(wb, **_kotak(align="center", num_format='#,##0.## "m²"'))
    f_m = _fmt(wb, **_kotak(align="center", num_format='#,##0.## "m"'))
    f_a = _fmt(wb, **_kotak(align="center", num_format='0.##"-A"'))
    f_tot_l = _fmt(wb, **_kotak(bold=True, bg_color=ABU, align="left"))
    f_tot_c = _fmt(wb, **_kotak(bold=True, bg_color=ABU, align="center", num_format="#,##0.##"))
    f_tot_g = _fmt(wb, **_kotak(bold=True, font_color="#FFFFFF", bg_color=HIJAU, align="center",
                                 num_format='0 "buah"'))
    f_val_b = _fmt(wb, **_kotak(bold=True, align="left"))
    f_note = _fmt(wb, **_kotak(italic=True, bg_color=CATATAN, align="left", text_wrap=True))

    ws.set_column(0, 0, 6)
    ws.set_column(1, 1, 46)
    ws.set_column(2, 5, 19)

    # ---- judul + identitas
    ws.write(0, 0, "PERHITUNGAN KEBUTUHAN APAR", f_judul)
    ws.write(1, 0, f"Dibuat dari aplikasi Kaizen PBG - {datetime.now():%d-%m-%Y %H:%M}", f_sub)
    for i, (k, v) in enumerate([("PEKERJAAN", proyek["pekerjaan"]), ("LOKASI", proyek["lokasi"]),
                                ("TAHUN", proyek["tahun"]), ("ITEM PEKERJAAN", proyek["item"])]):
        _gabung(ws, 3 + i, 0, 3 + i, 1, k, f_k)
        _gabung(ws, 3 + i, 2, 3 + i, 5, f": {v}", f_teks)

    # ---- dasar peraturan
    r = 8
    _gabung(ws, r, 0, r, 5, "DASAR PERATURAN DAN STANDAR", f_sec)
    for i, (t, d) in enumerate(DASAR_PERATURAN):
        ws.set_row(r + 1 + i, 30)
        _gabung(ws, r + 1 + i, 0, r + 1 + i, 5, f"{t} - {d}", f_wrap)
    jarak_reg = float(entri["jarak_reg"])
    ws.set_row(r + 4, 42)
    _gabung(ws, r + 4, 0, r + 4, 5,
            "Persyaratan proteksi dapat dipenuhi dengan APAR berkemampuan lebih tinggi, asalkan jarak tempuh "
            f"ke APAR yang lebih besar tidak melebihi {jarak_reg:g} m (jarak antar APAR {jarak_reg:g} meter) "
            "dan jumlah kebutuhan APAR mengikuti tabel di bawah ini.", f_wrap)

    # ---- tabel acuan kelas A (sel kuning = bisa diubah, dipakai rumus)
    r = 14
    _gabung(ws, r, 0, r, 5, "UKURAN APAR DAN PENEMPATANNYA UNTUK BAHAYA KEBAKARAN KELAS A", f_sec)
    r_h = r + 2  # baris nama kelas (Ringan/Sedang/Berat)
    _gabung(ws, r + 1, 0, r + 2, 0, "No", f_head)
    _gabung(ws, r + 1, 1, r + 2, 1, "Kriteria", f_head)
    _gabung(ws, r + 1, 2, r + 1, 4, "Hunian bahaya kebakaran", f_head)
    for j, k in enumerate(calc.KELAS):
        ws.write_string(r_h, 2 + j, k, f_head)
    kriteria = [
        ("Daya padam minimum APAR tunggal (catatan 1, 2)", calc.C_MINA, f_in_a),
        ("Luas lantai maksimum per unit A", calc.C_PERA, f_in_m2),
        ("Luas lantai maksimum per APAR (catatan 3)", calc.C_MAKS, f_in_m2),
        ("Jarak tempuh maksimum ke APAR (catatan 3)", calc.C_JARAK, f_in_m),
    ]
    r_kri = {}
    for i, (judul, kol, fm) in enumerate(kriteria):
        rr = r_h + 1 + i
        r_kri[kol] = rr
        ws.write_number(rr, 0, i + 1, f_c)
        ws.write_string(rr, 1, judul, f_lbl)
        for j, k in enumerate(calc.KELAS):
            ws.write_number(rr, 2 + j, float(tabel.loc[tabel[calc.C_KELAS] == k, kol].iloc[0]), fm)
    rc = r_h + 1 + len(kriteria)
    for i, t in enumerate(CATATAN_TABEL):
        ws.set_row(rc + i, 30)
        _gabung(ws, rc + i, 0, rc + i, 5, f"Catatan {i + 1}: {t}", f_wrap)

    rng_h = f"$C${r_h + 1}:$E${r_h + 1}"

    # ---- input
    r = rc + len(CATATAN_TABEL) + 1
    _gabung(ws, r, 0, r, 5, "DATA INPUT (sel kuning dapat diubah)", f_sec)
    inputs = [
        ("Klasifikasi hunian bahaya kebakaran", entri["kelas"], f_in_t),
        ("Jenis APAR", entri["jenis"], f_in_t),
        ("Kapasitas", entri["kapasitas"], f_in_t),
        ("Rating APAR (contoh 2A:10BC)", entri["rating"], f_in_t),
        ("Batas jarak tempuh ke APAR menurut regulasi (m)", jarak_reg, f_in_m),
    ]
    r_in = {}
    for i, (judul, v, fm) in enumerate(inputs):
        rr = r + 1 + i
        r_in[i] = rr
        _gabung(ws, rr, 0, rr, 1, judul, f_lbl)
        if isinstance(v, str):
            ws.write_string(rr, 2, v, fm)
        else:
            ws.write_number(rr, 2, v, fm)
    ws.data_validation(r_in[0], 2, r_in[0], 2, {"validate": "list", "source": calc.KELAS})
    KLAS = xl_rowcol_to_cell(r_in[0], 2, row_abs=True, col_abs=True)
    RAT = xl_rowcol_to_cell(r_in[3], 2, row_abs=True, col_abs=True)
    REG = xl_rowcol_to_cell(r_in[4], 2, row_abs=True, col_abs=True)

    # ---- perhitungan
    r = r + len(inputs) + 2
    _gabung(ws, r, 0, r, 5, "PERHITUNGAN", f_sec)

    def indeks(kol: str) -> str:
        rr = r_kri[kol] + 1
        return f"INDEX($C${rr}:$E${rr},MATCH({KLAS},{rng_h},0))"

    s = f'SUBSTITUTE(SUBSTITUTE({RAT},"-","")," ","")'
    baris = [
        ("Rating-A APAR (dibaca dari teks rating)",
         f'=IFERROR(VALUE(LEFT({s},SEARCH("A",{s})-1)),0)', h["rating_a"], f_n),
        ("Daya padam minimum yang disyaratkan", "=" + indeks(calc.C_MINA), h["min_a"], f_a),
        ("Luas lantai maksimum per unit A", "=" + indeks(calc.C_PERA), h["per_a"], f_m2),
        ("Luas lantai maksimum per APAR", "=" + indeks(calc.C_MAKS), h["maks"], f_m2),
        ("Jarak tempuh maksimum menurut tabel", "=" + indeks(calc.C_JARAK), h["jarak_tabel"], f_m),
    ]
    pos = {}
    for i, (judul, rumus, nilai, fm) in enumerate(baris):
        rr = r + 1 + i
        pos[i] = rr
        _gabung(ws, rr, 0, rr, 1, judul, f_lbl)
        ws.write_formula(rr, 2, rumus, fm, float(nilai))
    A_ = xl_rowcol_to_cell(pos[0], 2, row_abs=True, col_abs=True)
    MIN_ = xl_rowcol_to_cell(pos[1], 2, row_abs=True, col_abs=True)
    PER_ = xl_rowcol_to_cell(pos[2], 2, row_abs=True, col_abs=True)
    MAKS_ = xl_rowcol_to_cell(pos[3], 2, row_abs=True, col_abs=True)
    JTAB_ = xl_rowcol_to_cell(pos[4], 2, row_abs=True, col_abs=True)

    rr = r + 1 + len(baris)
    _gabung(ws, rr, 0, rr, 1, "Cakupan per APAR = min(luas maks per APAR, rating-A x luas per unit A)", f_lbl)
    ws.write_formula(rr, 2, f"=IF({A_}>0,MIN({MAKS_},{A_}*{PER_}),0)", f_m2, float(h["cakupan"]))
    CAK = xl_rowcol_to_cell(rr, 2, row_abs=True, col_abs=True)
    rr += 1
    _gabung(ws, rr, 0, rr, 1, "Jarak tempuh yang dipakai (terkecil antara tabel dan regulasi)", f_lbl)
    ws.write_formula(rr, 2, f"=IF({REG}>0,MIN({JTAB_},{REG}),{JTAB_})", f_m, float(h["jarak_pakai"]))
    JARAK = xl_rowcol_to_cell(rr, 2, row_abs=True, col_abs=True)
    rr += 1
    _gabung(ws, rr, 0, rr, 1, "Kecukupan rating terhadap daya padam minimum", f_lbl)
    ws.write_formula(rr, 2, f'=IF({A_}=0,"Tidak ada rating A",IF({A_}>={MIN_},"Memenuhi","Kurang dari minimum"))',
                     f_c, h["status_rating"])

    # ---- jumlah APAR per lantai
    r = rr + 2
    _gabung(ws, r, 0, r, 5, "KEBUTUHAN JUMLAH APAR PER LANTAI", f_sec)
    for c, t in enumerate(["No", "Lantai / Area", "Luas Lantai (m²)", "Cakupan per APAR (m²)",
                           "Luas ÷ Cakupan", "Jumlah APAR (buah)"]):
        ws.write_string(r + 1, c, t, f_head)
    ws.set_row(r + 1, 30)
    awal = r + 2
    for i, row in enumerate(h["lantai"]):
        rr = awal + i
        x = rr + 1
        ws.write_number(rr, 0, i + 1, f_c)
        ws.write_string(rr, 1, str(row["lantai"]), f_in_tl)
        ws.write_number(rr, 2, float(row["luas"]), f_in_m2)
        ws.write_formula(rr, 3, f"={CAK}", f_m2, float(h["cakupan"]))
        ws.write_formula(rr, 4, f"=IF(D{x}>0,C{x}/D{x},0)", f_n2, float(row["rasio"]))
        ws.write_formula(rr, 5, f"=IF(C{x}>0,IF(D{x}>0,MAX(1,ROUNDUP(ROUND(E{x},6),0)),0),0)",
                         _fmt(wb, **_kotak(bold=True, align="center", num_format='0 "buah"')),
                         float(row["jumlah"] or 0))
    akhir = awal + len(h["lantai"]) - 1
    rt = akhir + 1
    _gabung(ws, rt, 0, rt, 1, "TOTAL KEBUTUHAN APAR", f_tot_l)
    ws.write_formula(rt, 2, f"=SUM(C{awal + 1}:C{akhir + 1})", _fmt(wb, **_kotak(
        bold=True, bg_color=ABU, align="center", num_format='#,##0.## "m²"')), float(h["total_luas"]))
    ws.write_blank(rt, 3, None, f_tot_l)
    ws.write_blank(rt, 4, None, f_tot_l)
    ws.write_formula(rt, 5, f"=SUM(F{awal + 1}:F{akhir + 1})", f_tot_g, float(h["total"] or 0))
    TOTAL = xl_rowcol_to_cell(rt, 5, row_abs=True, col_abs=True)
    ws.set_row(rt + 1, 30)
    _gabung(ws, rt + 1, 0, rt + 1, 5,
            "Catatan : Kebutuhan jumlah APAR = Luas lantai ÷ Cakupan per APAR, dibulatkan ke atas "
            "(minimal 1 APAR pada tiap lantai yang berisi).", f_note)

    # ---- rekomendasi
    r = rt + 3
    _gabung(ws, r, 0, r, 5, "REKOMENDASI APAR", f_sec)
    JEN = xl_rowcol_to_cell(r_in[1], 2, row_abs=True, col_abs=True)
    KAP = xl_rowcol_to_cell(r_in[2], 2, row_abs=True, col_abs=True)
    rek = [
        ("Jenis", f"={JEN}", entri["jenis"], f_val_b),
        ("Kapasitas", f"={KAP}", entri["kapasitas"], f_val_b),
        ("Rating", f"={RAT}", entri["rating"], f_val_b),
        ("Maks jarak tempuh", f"={JARAK}", float(h["jarak_pakai"]), f_m),
    ]
    for i, (judul, rumus, nilai, fm) in enumerate(rek):
        rr = r + 1 + i
        _gabung(ws, rr, 0, rr, 1, judul, f_lbl)
        ws.write_formula(rr, 2, rumus, fm, nilai)
    rr = r + 1 + len(rek)
    _gabung(ws, rr, 0, rr, 1, "Jumlah APAR yang dibutuhkan", f_lbl_b)
    ws.write_formula(rr, 2, f"={TOTAL}", f_tot_g, float(h["total"] or 0))

    # ---- catatan
    rr += 2
    teks_catatan = list(h["catatan"]) + list(h["info"]) + [
        "Dasar APAR tidak boleh kurang dari 15 cm di atas permukaan lantai (PER.04/MEN/1980).",
    ]
    ws.write(rr, 0, "Catatan :", f_k)
    for i, t in enumerate(teks_catatan):
        _gabung(ws, rr + 1 + i, 0, rr + 1 + i, 5, f"- {t}", f_wrap)
        ws.set_row(rr + 1 + i, 30 if len(t) > 95 else 16)
    rr += len(teks_catatan) + 2
    ws.write(rr, 0, "Keterangan file ini :", f_k)
    ket = [
        "- Sel berwarna kuning dapat diubah; cakupan, jumlah APAR per lantai, dan total dihitung ulang otomatis.",
        "- Jenis dan kapasitas APAR hanya keterangan; yang memengaruhi hitungan adalah rating (angka sebelum huruf A).",
    ]
    for i, t in enumerate(ket):
        ws.write(rr + 1 + i, 0, t, f_teks)

    ws.set_portrait()
    ws.set_paper(9)
    ws.fit_to_pages(1, 0)
    ws.activate()
    wb.close()
    return buf.getvalue()
