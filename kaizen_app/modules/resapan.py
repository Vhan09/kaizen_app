"""Resapan Air Hujan - lima tab: Volume Andil Banjir, Sumur Lingkaran, Sumur Persegi, Biopori, Summary.

Setiap tab hanya menampilkan SNI/peraturan yang berkaitan; tab Summary menampilkan semuanya.
Dipanggil dari app.py:  "Modul N 💧 Resapan": resapan.render
Memerlukan modules/desain.py (sistem desain bersama).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules import resapan_calc as rc
from modules import resapan_excel, resapan_html

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.cache_data(show_spinner="Membuat PDF...")
def _buat_pdf(xlsx_bytes: bytes):
    return resapan_excel.excel_ke_pdf(xlsx_bytes)


def _landasan(data: dict, kunci: str | None = None) -> None:
    """Daftar SNI/peraturan. kunci=None -> semua (Summary); selain itu hanya yang berkaitan dengan tab."""
    daftar = [s for s in data["standar"] if kunci is None or kunci in s["tab"]]
    st.markdown("**Landasan Perencanaan / SNI:** " + " · ".join(s["kode"] for s in daftar))
    with st.expander(f"Rincian SNI & peraturan ({len(daftar)})", expanded=kunci is None):
        tabel = pd.DataFrame(daftar)[["kode", "judul", "peran", "catatan"]]
        tabel.columns = ["Standar / Peraturan", "Judul", "Peran pada Modul Ini", "Catatan"]
        st.dataframe(tabel, hide_index=True, width="stretch")
        st.caption(data.get("catatan_standar", ""))


def _html(h, data, proyek, bagian):
    components.html(resapan_html.render(h, data, proyek, bagian),
                    height=resapan_html.tinggi(h, bagian), scrolling=True)


def render():
    data = rc.muat_data()
    P0 = rc.parameter_default(data)
    P = dict(P0)
    P["cek"] = dict(P0["cek"])

    st.subheader("Resapan Air Hujan")
    st.caption("Volume andil banjir (Vab) dihitung dengan rumus SNI 03-2453-2002 dan Permen PU 11/PRT/M/2014, lalu dipenuhi dengan "
               "sumur resapan lingkaran, sumur resapan persegi, atau lubang biopori. Rumus ditampilkan agar bisa dicocokkan dengan Excel.")
    t_vab, t_bulat, t_persegi, t_bio, t_sum = st.tabs(
        ["💧 Volume Andil Banjir", "⭕ Sumur Lingkaran", "⬜ Sumur Persegi", "🕳️ Biopori", "📋 Summary"])

    # ============================================================ input
    with t_vab:
        _landasan(data, "vab")
        st.markdown("#### Bidang Tadah dan Curah Hujan")
        c1, c2 = st.columns([2, 1])
        with c1:
            perm_df = st.data_editor(
                rc.template_permukaan(), key="rs_perm", num_rows="dynamic", width="stretch", hide_index=True,
                column_config={
                    "Permukaan": st.column_config.SelectboxColumn("Permukaan", options=rc.opsi_permukaan(data)),
                    "Luas (m²)": st.column_config.NumberColumn("Luas A (m²)", min_value=0.0, step=0.5, format="%.2f"),
                })
        with c2:
            P["R"] = st.number_input("Tinggi hujan harian R (mm/hari)", 10.0, 500.0, float(P0["R"]), step=5.0, key="rs_R",
                                     help="Excel kamu memakai 120 mm/hari. Pastikan sesuai periode ulang yang diminta dinas.")
            P["taman"] = st.checkbox("Hitung taman dalam Vab", False, key="rs_taman",
                                     help="Biasanya tidak dihitung bila pekarangan hijau menyerap air.")
        st.caption(data["catatan_c"])

        st.markdown("#### Data Tanah dan Lokasi")
        k1, k2, k3 = st.columns(3)
        P["k_cmjam"] = k1.number_input("Permeabilitas tanah K (cm/jam)", 0.1, 100.0, float(P0["k_cmjam"]), step=0.5, key="rs_K",
                                       help="Hasil uji lapangan. Syarat SNI 03-2453-2002: minimal 2,0 cm/jam.")
        P["rasio_kh"] = k2.number_input("Rasio Kh / Kv", 0.5, 5.0, float(P0["rasio_kh"]), step=0.5, key="rs_kh",
                                        help="Contoh SNI: permeabilitas horizontal (dinding) = 2 × vertikal (alas).")
        P["mat"] = k3.number_input("Kedalaman muka air tanah (m)", 0.0, 50.0, 0.0, step=0.5, key="rs_mat",
                                   help="Isi dari pengukuran; 0 = belum diisi. Syarat minimal 1,5 m pada musim hujan.")
        with st.expander("Konfirmasi persyaratan lokasi (SNI 03-2453-2002)"):
            cc1, cc2 = st.columns(2)
            P["cek"]["datar"] = cc1.checkbox("Lahan relatif datar", False, key="rs_c1")
            P["cek"]["tak_tercemar"] = cc1.checkbox("Air yang masuk adalah air hujan tidak tercemar", False, key="rs_c2")
            P["cek"]["perda"] = cc1.checkbox("Memenuhi peraturan daerah setempat", False, key="rs_c3")
            P["cek"]["pondasi"] = cc2.checkbox("Jarak ke pondasi bangunan ≥ 1 m", False, key="rs_c4")
            P["cek"]["sumur_air"] = cc2.checkbox("Jarak ke sumur air bersih / sumur resapan lain ≥ 3 m", False, key="rs_c5")
            P["cek"]["septik"] = cc2.checkbox("Jarak ke bidang/sumur resapan tangki septik ≥ 5 m", False, key="rs_c6")

    with t_bulat:
        _landasan(data, "lingkaran")
        st.markdown("#### Parameter Sumur Lingkaran")
        a1, a2 = st.columns(2)
        P["D"] = a1.number_input("Diameter sumur D (m)", 0.4, 3.0, float(P0["D"]), step=0.1, key="rs_D", help="Contoh SNI: 0,8 / 1,0 / 1,2 m.")
        P["H1"] = a2.number_input("Kedalaman rencana H (m)", 0.5, 10.0, float(P0["H1"]), step=0.25, key="rs_H1",
                                  help="Harus lebih kecil dari kedalaman muka air tanah.")
        P["kedap"] = st.checkbox("Dinding sumur kedap (hanya alas yang meresap)", False, key="rs_kedap",
                                 help="Buis beton berlubang/berpori = dinding tidak kedap (default). Berlaku juga untuk sumur persegi.")

    with t_persegi:
        _landasan(data, "persegi")
        st.markdown("#### Parameter Sumur Persegi")
        b1, b2, b3 = st.columns(3)
        P["P"] = b1.number_input("Panjang P (m)", 0.4, 5.0, float(P0["P"]), step=0.1, key="rs_P")
        P["L"] = b2.number_input("Lebar L (m)", 0.4, 5.0, float(P0["L"]), step=0.1, key="rs_L")
        P["H2"] = b3.number_input("Kedalaman rencana H (m)", 0.5, 10.0, float(P0["H2"]), step=0.25, key="rs_H2")
        st.caption("Pengaturan 'dinding kedap' diambil dari tab Sumur Lingkaran.")

    with t_bio:
        _landasan(data, "biopori")
        st.markdown("#### Parameter Lubang Biopori")
        d1, d2, d3 = st.columns(3)
        P["d_bio"] = d1.number_input("Diameter lubang d (m)", 0.05, 0.5, float(P0["d_bio"]), step=0.01, format="%.4f", key="rs_d",
                                     help="Pipa 4 inci = 0,1016 m. Acuan 10–25 cm.")
        P["t_bio"] = d2.number_input("Kedalaman lubang t (m)", 0.3, 5.0, float(P0["t_bio"]), step=0.1, key="rs_t",
                                     help="Acuan sekitar 1 m; Excel memakai 2 m.")
        P["harga"] = d3.number_input("Harga satuan per lubang (Rp)", 0.0, 10_000_000.0, float(P0["harga"]), step=5000.0, key="rs_hrg")
        e1, e2 = st.columns(2)
        P["I_jam"] = e1.number_input("Intensitas hujan I (mm/jam) — opsional", 0.0, 500.0, 0.0, step=5.0, key="rs_I",
                                     help="Untuk metode Brata & Nelistya (N = I × A / P).")
        P["P_lph"] = e2.number_input("Laju peresapan per lubang P (liter/jam) — opsional", 0.0, 5000.0, 0.0, step=10.0, key="rs_P_l",
                                     help="Diukur di lapangan; isi bersama intensitas hujan.")
        st.caption(data["biopori"]["catatan"])

    with t_sum:
        _landasan(data, None)
        with st.expander("Data proyek (kop laporan)"):
            p = data["proyek"]
            c1, c2, c3 = st.columns(3)
            proyek = {
                "pekerjaan": c1.text_input("Pekerjaan", p["pekerjaan"], key="rs_pekerjaan"),
                "lokasi": c2.text_input("Lokasi", p["lokasi"], key="rs_lokasi"),
                "tahun": c3.text_input("Tahun", p["tahun"], key="rs_tahun"),
                "item": p["item"],
            }

    # ============================================================ hitung
    h = rc.hitung_semua(perm_df, data, P)
    if h["kosong"]:
        for t in (t_vab, t_bulat, t_persegi, t_bio, t_sum):
            with t:
                st.info("Isi minimal satu bidang tadah (atap atau perkerasan) dengan luas lebih dari 0 pada tab Volume Andil Banjir.")
        return

    # ============================================================ hasil per tab
    with t_vab:
        _html(h, data, None, "vab")
        with st.expander("Rumus yang digunakan", expanded=False):
            st.latex(r"V_{ab} = 0{,}855 \times \sum (C \times A) \times \frac{R}{1000}")
            st.latex(r"t_e = \frac{0{,}9 \times R^{0{,}92}}{60}\ \text{(jam)}")

    with t_bulat:
        _html(h, data, None, "lingkaran")
        with st.expander("Rumus yang digunakan", expanded=False):
            st.latex(r"A_{alas} = \tfrac{1}{4}\pi D^2;\quad A_{dinding} = \pi D H")
            st.latex(r"K_{rata} = \frac{K_v A_{alas} + K_h A_{dinding}}{A_{total}};\quad V_{rsp} = \frac{t_e}{24} A_{total} K_{rata}")
            st.latex(r"H_{total} = \frac{V_{ab} - V_{rsp}}{A_{alas}};\quad n = \lceil H_{total} / H \rceil")

    with t_persegi:
        _html(h, data, None, "persegi")
        with st.expander("Rumus yang digunakan", expanded=False):
            st.latex(r"A_{alas} = P \times L;\quad A_{dinding} = 2(P + L) H")
            st.latex(r"H_{total} = \frac{V_{ab} - V_{rsp}}{A_{alas}};\quad n = \lceil H_{total} / H \rceil")

    with t_bio:
        _html(h, data, None, "biopori")
        with st.expander("Rumus yang digunakan", expanded=False):
            st.latex(r"V_{lubang} = \pi r^2 t;\quad N_A = \frac{V_{ab}}{V_{lubang}};\quad N_B = \frac{V_{ab}}{V_{lubang} + V_{rsp}}")
            st.latex(r"N_C = \frac{I \times A}{P}\ \text{(Brata \& Nelistya, 2008)}")

    with t_sum:
        _html(h, data, proyek, "ringkasan")
        xlsx = resapan_excel.build_excel(h, data, proyek)
        d1, d2, _ = st.columns([1, 1, 3])
        d1.download_button("Unduh Excel (.xlsx)", xlsx, "Resapan_Air_Hujan.xlsx", mime=XLSX_MIME, on_click="ignore")
        if d2.button("Siapkan PDF"):
            pdf = _buat_pdf(xlsx)
            if pdf:
                d2.download_button("Unduh PDF", pdf, "Resapan_Air_Hujan.pdf", mime="application/pdf", on_click="ignore")
            else:
                d2.warning("PDF butuh LibreOffice terpasang di komputer ini.")
        st.caption("File Excel berisi rumus hidup, skema opsi, tabel referensi, dan daftar SNI/peraturan (4 sheet).")
        with st.expander("Lembar perhitungan lengkap", expanded=False):
            _html(h, data, proyek, "lembar")
