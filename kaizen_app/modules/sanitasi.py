"""Modul 6 - Sanitasi & Air Bersih (air bersih, air limbah, tangki septik, resapan).

Dipanggil dari app.py:  "Modul 6 🚿 Sanitasi & Air Bersih": sanitasi.render
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules import sanitasi_calc as sc
from modules import sanitasi_excel, sanitasi_html

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.cache_data(show_spinner="Membuat PDF...")
def _buat_pdf(xlsx_bytes: bytes):
    return sanitasi_excel.excel_ke_pdf(xlsx_bytes)


def _landasan(data: dict) -> None:
    kode = [s["kode"] for s in data["standar"]]
    st.markdown("**Landasan Perencanaan / SNI:** " + " · ".join(kode))
    with st.expander("Rincian SNI & peraturan yang menjadi acuan"):
        tabel = pd.DataFrame(data["standar"]).rename(columns={
            "kode": "Standar / Peraturan", "judul": "Judul", "peran": "Peran pada Modul Ini", "catatan": "Catatan"})
        st.dataframe(tabel, hide_index=True, width="stretch")
        st.caption(data.get("catatan_standar", ""))


def _rumus(P: dict) -> None:
    st.latex(r"Q_{harian} = \sum \left(\text{jumlah} \times \text{standar pemakaian air}\right)")
    st.latex(rf"Q_{{rencana}} = Q_{{harian}} \times (1 + {P['faktor_puncak']:g})")
    st.latex(r"Q_{limbah} = Q_{dasar} \times f_{limbah}; \quad Q_{black} = Q_{limbah} \times f_{black}; \quad Q_{grey} = Q_{limbah} - Q_{black}")
    st.latex(r"V_{air} = \frac{Q_{limbah} \times t_d}{1000}; \quad V_{lumpur} = \frac{QL \times n \times PP}{1000}")
    st.latex(r"V_{tangki} = V_{air} + V_{lumpur} + (A \times h_{ambang}); \quad A = \frac{V_{air}+V_{lumpur}}{h_{air}}")
    st.latex(r"A_{resapan} = \frac{Q_{efluen}}{\text{daya serap tanah}}")
    st.caption("td = waktu detensi (hari), QL = produksi lumpur (L/orang/tahun), PP = periode pengurasan (tahun), "
               "n = jumlah pemakai, h = tinggi (m).")


def render():
    data = sc.muat_data()
    P0 = sc.parameter_default(data)

    st.subheader("Modul 6 — Sanitasi & Air Bersih")
    st.caption("Kebutuhan air bersih, air limbah (grey/black water), tangki septik, dan bidang/sumur resapan. "
               "Rumus yang dipakai ditampilkan di bawah agar bisa dicocokkan dengan Excel.")
    _landasan(data)

    with st.expander("Data proyek (kop laporan)"):
        p = data["proyek"]
        c1, c2, c3 = st.columns(3)
        proyek = {
            "pekerjaan": c1.text_input("Pekerjaan", p["pekerjaan"], key="san_pekerjaan"),
            "lokasi": c2.text_input("Lokasi", p["lokasi"], key="san_lokasi"),
            "tahun": c3.text_input("Tahun", p["tahun"], key="san_tahun"),
            "item": p["item"],
        }

    # ---------------------------------------------------------- 1. air bersih
    st.markdown("#### 1. Kebutuhan Air Bersih")
    st.caption("Pilih fungsi bangunan; standar pemakaian air mengikuti SNI 03-7065-2005 Tabel 1. "
               "Bangunan campuran (misal rumah + toko) bisa diisi lebih dari satu baris.")
    input_df = st.data_editor(
        sc.template_default(), key="san_penggunaan", num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "Fungsi": st.column_config.SelectboxColumn("Fungsi Bangunan", options=sc.opsi_fungsi(data)),
            "Jumlah": st.column_config.NumberColumn("Jumlah (sesuai satuan standar)", min_value=0.0, step=1.0,
                                                    help="Contoh: jumlah penghuni, tempat tidur, siswa, kursi, atau m²."),
            "Keterangan": st.column_config.TextColumn("Keterangan"),
        },
    )
    a1, a2 = st.columns(2)
    P = dict(P0)
    P["faktor_puncak"] = a1.number_input("Faktor puncak (peak time)", 0.0, 2.0, float(P0["faktor_puncak"]),
                                         step=0.05, key="san_fp", help="Excel kamu memakai 30% (0,30).")
    P["pembulatan"] = a2.number_input("Pembulatan volume tandon ke atas, kelipatan (m³)", 0.01, 5.0,
                                      float(P0["pembulatan"]), step=0.05, key="san_bulat")

    # ---------------------------------------------------------- 2. air limbah
    st.markdown("#### 2. Air Limbah")
    b1, b2, b3 = st.columns(3)
    P["dasar"] = b1.selectbox("Dasar debit air limbah", [sc.DASAR_PUNCAK, sc.DASAR_RATA], key="san_dasar")
    P["faktor_limbah"] = b2.number_input("Faktor air limbah (% dari debit dasar)", 0.1, 1.0,
                                         float(P0["faktor_limbah"]), step=0.05, key="san_fl",
                                         help="Excel: 100%. Acuan umum yang sering dipakai: 80%.")
    P["fraksi_black"] = b3.number_input("Fraksi black water (kakus)", 0.0, 1.0, float(P0["fraksi_black"]),
                                        step=0.05, key="san_fb", help="Excel: 20%.")

    # ---------------------------------------------------------- 3. septik
    st.markdown("#### 3. Tangki Septik (SNI 2398:2017)")
    sd = data["septik"]
    with st.expander("Parameter tangki septik", expanded=True):
        P["n_auto"] = st.checkbox("Jumlah pemakai diambil dari tabel (baris yang satuannya orang)", True, key="san_nauto")
        if not P["n_auto"]:
            P["n"] = st.number_input("Jumlah pemakai (orang)", 1, 10000, int(P0["n"]), step=1, key="san_n")
        s1, s2, s3 = st.columns(3)
        P["td"] = s1.number_input("Waktu detensi (hari)", 0.5, 10.0, float(P0["td"]), step=0.5, key="san_td",
                                  help=f"Rentang SNI: {sd['detensi_min']}–{sd['detensi_max']} hari.")
        P["ql"] = s2.number_input("Produksi lumpur (L/orang/tahun)", 1.0, 100.0, float(P0["ql"]), step=1.0,
                                  key="san_ql", help=f"Rentang SNI: {sd['lumpur_min']}–{sd['lumpur_max']}.")
        P["pp"] = s3.number_input("Periode pengurasan (tahun)", 1.0, 10.0, float(P0["pp"]), step=1.0, key="san_pp",
                                  help=f"Rentang SNI: {sd['pengurasan_min']}–{sd['pengurasan_max']} tahun.")
        s4, s5, s6 = st.columns(3)
        P["ambang"] = s4.number_input("Ambang bebas (m)", 0.0, 1.0, float(P0["ambang"]), step=0.05, key="san_amb")
        P["h_air"] = s5.number_input("Kedalaman air efektif (m)", 0.5, 4.0, float(P0["h_air"]), step=0.1, key="san_h")
        P["rasio"] = s6.number_input("Rasio panjang : lebar", 1.0, 5.0, float(P0["rasio"]), step=0.5, key="san_rasio")

    # ---------------------------------------------------------- 4. resapan
    st.markdown("#### 4. Bidang / Sumur Resapan")
    r1, r2 = st.columns(2)
    P["q_serap"] = r1.number_input("Daya serap tanah (L/m²/hari) — isi dari uji perkolasi", 0.0, 1000.0, 0.0,
                                   step=1.0, key="san_qs", help="Kosongkan (0) bila uji perkolasi belum ada.")
    P["d_sumur"] = r2.number_input("Diameter sumur resapan (m)", 0.3, 3.0, float(P0["d_sumur"]), step=0.1, key="san_d")

    with st.expander("Rumus yang digunakan", expanded=True):
        _rumus(P)

    h = sc.hitung_semua(input_df, data, P)
    if h["rinc"].empty:
        st.info("Isi minimal satu baris fungsi bangunan dengan jumlah lebih dari 0.")
        return

    # ---------------------------------------------------------- ringkasan
    m1, m2, m3 = st.columns(3)
    m1.metric("Kebutuhan Air Harian", f"{sc.fmt_id(h['q_harian'], 0)} L/hari")
    m2.metric("Volume Tandon Rencana", f"{sc.fmt_id(h['vol_rencana'], 2)} m³")
    m3.metric("Volume Tangki Septik (tercampur)", f"{sc.fmt_id(h['tc']['v_total'], 2)} m³")
    for w in h["peringatan"]:
        st.warning(w)
    st.info(f"Black water sistem terpisah: {sc.fmt_id(h['black'], 1)} L/hari (fraksi {P['fraksi_black']:.0%}); "
            f"pembanding contoh SNI {data['air_limbah']['black_water_l_org_hari']} L/orang/hari × {h['n']:g} orang = "
            f"{sc.fmt_id(h['cek_black_sni'], 1)} L/hari.")
    st.caption("Dimensi tangki di atas adalah estimasi dari volume. Ukuran minimum, jumlah ruang, dan detail konstruksi "
               "tetap mengikuti SNI 2398:2017.")

    # ---------------------------------------------------------- lembar
    st.markdown("### Lembar Perhitungan Sanitasi dan Air Bersih")
    components.html(sanitasi_html.render_html(h, data, proyek),
                    height=sanitasi_html.tinggi_html(h, data), scrolling=True)

    # ---------------------------------------------------------- unduh
    xlsx = sanitasi_excel.build_excel(h, data, proyek)
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("Unduh Excel (.xlsx)", xlsx, "Sanitasi_Air.xlsx", mime=XLSX_MIME, on_click="ignore")
    if d2.button("Siapkan PDF"):
        pdf = _buat_pdf(xlsx)
        if pdf:
            d2.download_button("Unduh PDF", pdf, "Sanitasi_Air.pdf", mime="application/pdf", on_click="ignore")
        else:
            d2.warning("PDF butuh LibreOffice terpasang di komputer ini.")
    st.caption("File Excel berisi rumus hidup, tabel pemakaian air SNI, dan daftar SNI/peraturan (3 sheet).")

    with st.expander("Tabel pemakaian air (SNI 03-7065-2005 Tabel 1)"):
        tabel = pd.DataFrame(data["pemakaian_air"])[["fungsi", "nilai", "satuan"]]
        tabel.columns = ["Penggunaan gedung", "Pemakaian air", "Satuan"]
        st.dataframe(tabel, hide_index=True, width="stretch")
        st.caption(f"{data['sumber_tabel']}. {data['catatan_tabel']}")
