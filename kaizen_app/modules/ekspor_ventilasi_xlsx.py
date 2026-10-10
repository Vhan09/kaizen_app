"""Ekspor Penghawaan Alami ke Excel (.xlsx) - tanpa Streamlit.

Rumus hidup: ubah sel kuning (rasio, ACH minimum, jenis / metode ruangan, dimensi bukaan dan ruang,
debit exhaust) dan Av, Ar, rasio, syarat, selisih, ACH, serta STATUS kepatuhan menghitung ulang.
Nilai tersimpan ikut ditulis agar angka langsung tampil di aplikasi apa pun.
"""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from modules import ventilasi_calc as calc
from modules.ekspor_xlsx import (
    ABU, CATATAN, GARIS, HIJAU, KUNING, NAVY, _fmt, _gabung, _gabung_rumus, _kotak,
)
from modules.ventilasi_html import DASAR_STANDAR

NC = 25  # jumlah kolom tabel utama
LEBAR = [5, 26, 18, 16, 18, 7, 8, 8, 9, 8, 8, 9, 9, 10, 10, 9, 7, 9, 10, 10, 9, 9, 9, 20, 11]


def ventilasi_xlsx(proyek: dict, entri: dict, h: dict) -> bytes:
    rasio = float(entri["rasio"])
    ach = calc.normalisasi_ach(entri["ach"])

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet("Penghawaan")

    # ---- format
    f_judul = _fmt(wb, bold=True, font_size=14)
    f_sub = _fmt(wb, italic=True, font_color="#555555")
    f_k = _fmt(wb, bold=True)
    f_teks = _fmt(wb)
    f_wrap = _fmt(wb, text_wrap=True, valign="top")
    f_sec = _fmt(wb, bold=True, font_color="#FFFFFF", bg_color=NAVY)
    f_head = _fmt(wb, **_kotak(bold=True, font_color="#FFFFFF", bg_color=NAVY, align="center", text_wrap=True))
    f_lbl = _fmt(wb, **_kotak(align="left"))
    f_grp = _fmt(wb, **_kotak(bold=True, bg_color="#DCE6F5", font_color=NAVY, align="left"))
    f_c = _fmt(wb, **_kotak(align="center"))
    f_in_pct = _fmt(wb, **_kotak(bg_color=KUNING, align="center", num_format="0.0%"))
    f_in_n = _fmt(wb, **_kotak(bg_color=KUNING, align="center", num_format="#,##0.##"))
    f_in_t = _fmt(wb, **_kotak(bg_color=KUNING, align="left"))
    f_in_tc = _fmt(wb, **_kotak(bg_color=KUNING, align="center"))
    f_n3 = _fmt(wb, **_kotak(align="center", num_format="#,##0.000"))
    f_n3b = _fmt(wb, **_kotak(align="center", bold=True, bg_color=ABU, num_format="#,##0.000;[Red]-#,##0.000"))
    f_n1 = _fmt(wb, **_kotak(align="center", num_format="#,##0.0"))
    f_n0 = _fmt(wb, **_kotak(align="center", num_format="#,##0"))
    f_pct = _fmt(wb, **_kotak(align="center", num_format="0.0%"))
    f_stat = _fmt(wb, **_kotak(align="center", bold=True))
    f_tot_lbl = _fmt(wb, **_kotak(bold=True, bg_color=ABU, align="left"))
    f_tot_n = _fmt(wb, **_kotak(bold=True, bg_color=ABU, align="center", num_format="0"))
    f_ok = wb.add_format({"bg_color": "#E3F6E8", "font_color": "#0B6B2E", "bold": True})
    f_no = wb.add_format({"bg_color": "#FDE7E7", "font_color": "#B00020", "bold": True})
    f_warn = wb.add_format({"bg_color": "#FFF3CD", "font_color": "#7A5C00", "bold": True})
    f_na = wb.add_format({"bg_color": "#EEF2F8", "font_color": "#444444", "bold": True})

    for c, w in enumerate(LEBAR):
        ws.set_column(c, c, w)

    # ---- judul + identitas
    ws.write(0, 0, "PERHITUNGAN PENGHAWAAN ALAMI & VENTILASI MEKANIS", f_judul)
    ws.write(1, 0, f"Dibuat dari aplikasi Kaizen PBG - {datetime.now():%d-%m-%Y %H:%M}", f_sub)
    for i, (k, v) in enumerate([("PEKERJAAN", proyek["pekerjaan"]), ("LOKASI", proyek["lokasi"]),
                                ("TAHUN", proyek["tahun"]), ("ITEM PEKERJAAN", proyek["item"])]):
        _gabung(ws, 3 + i, 0, 3 + i, 1, k, f_k)
        _gabung(ws, 3 + i, 2, 3 + i, 12, f": {v}", f_teks)

    # ---- dasar standar
    r = 8
    _gabung(ws, r, 0, r, NC - 1, "DASAR STANDAR", f_sec)
    for i, (t, d) in enumerate(DASAR_STANDAR):
        ws.set_row(r + 1 + i, 30)
        _gabung(ws, r + 1 + i, 0, r + 1 + i, 14, f"{t}: {d}", f_wrap)
    ws.set_row(r + 4, 30)
    _gabung(ws, r + 4, 0, r + 4, 14,
            f"Dasar rasio yang dipakai pada file ini: {entri['dasar']}. SNI 6572-2:2024 (bangunan residensial) "
            "tercatat berlaku di BSN namun belum dapat diverifikasi; ubah rasio pada sel kuning bila perlu.", f_wrap)

    # ---- parameter (sel kuning)
    r = 14
    _gabung(ws, r, 0, r, NC - 1, "PARAMETER (sel kuning dapat diubah)", f_sec)
    _gabung(ws, r + 1, 0, r + 1, 1, "Rasio minimum Av / Ar", f_lbl)
    ws.write_number(r + 1, 2, rasio, f_in_pct)
    RASIO = xl_rowcol_to_cell(r + 1, 2, row_abs=True, col_abs=True)
    ws.write_string(r + 3, 1, "Jenis ruang", f_head)
    ws.write_string(r + 3, 2, "ACH minimum", f_head)
    r_ach0 = r + 4
    for i, j in enumerate(calc.JENIS):
        ws.write_string(r_ach0 + i, 1, j, f_lbl)
        ws.write_number(r_ach0 + i, 2, float(ach.loc[ach[calc.C_ACH_JENIS] == j, calc.C_ACH].iloc[0]), f_in_n)
    r_ach1 = r_ach0 + len(calc.JENIS) - 1
    rng_jenis = f"$B${r_ach0 + 1}:$B${r_ach1 + 1}"
    rng_ach = f"$C${r_ach0 + 1}:$C${r_ach1 + 1}"
    _gabung(ws, r_ach0, 3, r_ach1, 8,
            "ACH = pertukaran udara per jam (SNI 03-6572-2001 Tabel 4.4.1). Nilai 0 = SNI tidak memberi acuan.", f_wrap)

    # ---- header tabel utama
    h0 = r_ach1 + 3
    ws.set_row(h0, 24)
    ws.set_row(h0 + 1, 34)
    for c, t in [(0, "No"), (1, "Nama Ruangan"), (2, "Jenis"), (3, "Metode"), (4, "Bukaan\nmenghadap"),
                 (12, "Rasio\nAv/Ar"), (13, "Syarat Av\nmin (m²)"), (14, "Selisih\n(m²)"),
                 (15, "Alami ≥\nsyarat?"), (23, "STATUS"), (24, "Tambahan\nbukaan (m²)")]:
        _gabung(ws, h0, c, h0 + 1, c, t, f_head)
    _gabung(ws, h0, 5, h0, 8, "Av - Ventilasi", f_head)
    _gabung(ws, h0, 9, h0, 11, "Ar - Ruangan", f_head)
    _gabung(ws, h0, 16, h0, 22, "Ventilasi mekanis (exhaust)", f_head)
    for c, t in zip(range(5, 12), ["Jml", "P (m)", "L (m)", "A (m²)", "P (m)", "L (m)", "A (m²)"]):
        ws.write_string(h0 + 1, c, t, f_head)
    for c, t in zip(range(16, 23), ["T (m)", "V (m³)", "Q\n(m³/menit)", "Q\n(m³/jam)", "ACH\nhasil", "ACH\nmin", "Exhaust ≥\nACH min?"]):
        ws.write_string(h0 + 1, c, t, f_head)

    # ---- isi
    rr = h0 + 2
    body_awal = rr
    for lantai, daftar in h["kelompok"]:
        _gabung(ws, rr, 0, rr, NC - 1, lantai.upper(), f_grp)
        rr += 1
        for i, b in enumerate(daftar, start=1):
            x = rr + 1
            ws.write_number(rr, 0, i, f_c)
            ws.write_string(rr, 1, b["nama"], f_in_t)
            ws.write_string(rr, 2, b["jenis"], f_in_tc)
            ws.write_string(rr, 3, b["metode"], f_in_tc)
            ws.write_string(rr, 4, b["hadap"], f_in_tc)
            ws.write_number(rr, 5, b["jml"], f_in_n)
            ws.write_number(rr, 6, b["vp"], f_in_n)
            ws.write_number(rr, 7, b["vl"], f_in_n)
            ws.write_formula(rr, 8, f"=F{x}*G{x}*H{x}", f_n3, b["av"])
            ws.write_number(rr, 9, b["rp"], f_in_n)
            ws.write_number(rr, 10, b["rl"], f_in_n)
            ws.write_formula(rr, 11, f"=J{x}*K{x}", f_n3, b["ar"])
            ws.write_formula(rr, 12, f"=IF(L{x}>0,I{x}/L{x},0)", f_pct, b["rasio"])
            ws.write_formula(rr, 13, f"={RASIO}*L{x}", f_n3, b["av_min"])
            ws.write_formula(rr, 14, f"=I{x}-N{x}", f_n3b, b["selisih"])
            ws.write_formula(rr, 15, f'=IF(L{x}<=0,"-",IF(ROUND(O{x},6)>=0,"Ya","Tidak"))', f_c, b["alami_txt"])
            ws.write_number(rr, 16, b["t"], f_in_n)
            ws.write_formula(rr, 17, f"=L{x}*Q{x}", f_n3, b["vol"])
            ws.write_number(rr, 18, b["q_menit"], f_in_n)
            ws.write_formula(rr, 19, f"=S{x}*60", f_n0, b["q_jam"])
            ws.write_formula(rr, 20, f"=IF(R{x}>0,T{x}/R{x},0)", f_n1, b["ach"])
            ws.write_formula(rr, 21, f"=IFERROR(INDEX({rng_ach},MATCH(C{x},{rng_jenis},0)),0)", f_n0, b["ach_min"])
            ws.write_formula(
                rr, 22,
                f'=IF(T{x}<=0,"-",IF(R{x}<=0,"Tidak",IF(OR(V{x}<=0,ROUND(U{x}-V{x},6)>=0),"Ya","Tidak")))',
                f_c, b["exh_txt"])
            sa = (f'IF(AND(P{x}="Ya",NOT(AND(C{x}="{calc.JENIS_SANITASI}",E{x}="Ruang bersebelahan"))),'
                  f'IF(E{x}="Ruang bersebelahan","{calc.ST_TINJAU}","{calc.ST_SESUAI}"),"")')
            status = (
                f'=IF(C{x}="{calc.JENIS_TERBUKA}","{calc.ST_TERBUKA}",'
                f'IF(L{x}<=0,"{calc.ST_DATA}",'
                f'IF(AND(ISNUMBER(SEARCH("Exhaust",D{x})),R{x}<=0),"{calc.ST_DATA}",'
                f'IF(D{x}="Exhaust",IF(W{x}="Ya","{calc.ST_EXH}","{calc.ST_TIDAK}"),'
                f'IF(D{x}="Alami + Exhaust",'
                f'IF({sa}="{calc.ST_SESUAI}","{calc.ST_SESUAI}",IF(W{x}="Ya","{calc.ST_EXH}",'
                f'IF({sa}<>"",{sa},"{calc.ST_TIDAK}"))),'
                f'IF({sa}<>"",{sa},"{calc.ST_TIDAK}"))))))'
            )
            ws.write_formula(rr, 23, status, f_stat, b["status"])
            ws.write_formula(
                rr, 24,
                f'=IF(AND(L{x}>0,ROUND(O{x},6)<0,X{x}="{calc.ST_TIDAK}",D{x}<>"Exhaust"),-O{x},0)',
                f_n3, b["tambah"])
            ws.data_validation(rr, 2, rr, 2, {"validate": "list", "source": calc.JENIS})
            ws.data_validation(rr, 3, rr, 3, {"validate": "list", "source": calc.METODE})
            ws.data_validation(rr, 4, rr, 4, {"validate": "list", "source": calc.HADAP})
            rr += 1
    body_akhir = rr - 1
    rng_status = f"$X${body_awal + 1}:$X${body_akhir + 1}"
    rng_s = f"X{body_awal + 1}:X{body_akhir + 1}"
    for teks, fm in [(calc.ST_SESUAI, f_ok), (calc.ST_EXH, f_ok), (calc.ST_TIDAK, f_no),
                     (calc.ST_TINJAU, f_warn), (calc.ST_DATA, f_warn), (calc.ST_TERBUKA, f_na)]:
        ws.conditional_format(rng_s, {"type": "cell", "criteria": "==", "value": f'"{teks}"', "format": fm})

    # ---- rekap (rumus COUNTIF)
    rr += 1
    _gabung(ws, rr, 0, rr, NC - 1, "REKAP KEPATUHAN", f_sec)
    for i, st_ in enumerate([calc.ST_SESUAI, calc.ST_EXH, calc.ST_TIDAK, calc.ST_TINJAU, calc.ST_DATA, calc.ST_TERBUKA]):
        _gabung(ws, rr + 1 + i, 0, rr + 1 + i, 3, st_, f_tot_lbl)
        ws.write_formula(rr + 1 + i, 4, f'=COUNTIF({rng_status},"{st_}")', f_tot_n, h["hitungan"][st_])
    rr += 8

    # ---- catatan
    ws.write(rr, 0, "Catatan perbaikan (saat file dibuat) :", f_k)
    daftar = [f"{b['lantai']} - {b['nama']}: {b['ket']}" for b in h["perbaikan"]] or \
             ["Seluruh ruangan yang dinilai memenuhi dasar yang dipilih."]
    for i, t in enumerate(daftar):
        ws.set_row(rr + 1 + i, 30 if len(t) > 130 else 16)
        _gabung(ws, rr + 1 + i, 0, rr + 1 + i, 14, f"- {t}", f_wrap)
    rr += len(daftar) + 2
    ws.write(rr, 0, "Keterangan file ini :", f_k)
    for i, t in enumerate([
        "- Sel kuning dapat diubah; Av, Ar, rasio, syarat, selisih, ACH, status, dan rekap dihitung ulang otomatis.",
        "- Syarat ventilasi alami: Av >= rasio x Ar. Ventilasi mekanis: ACH = Q (m3/jam) / (P x L x T) >= ACH minimum.",
        "- Keterangan per ruangan dan perbandingan dasar rasio ada pada aplikasi dan PDF.",
    ]):
        ws.write(rr + 1 + i, 0, t, f_teks)

    ws.set_landscape()
    ws.set_paper(8)  # A3, tabel lebar
    ws.fit_to_pages(1, 0)
    ws.activate()
    wb.close()
    return buf.getvalue()
