"""Titik Lampu - tiga tab: Perhitungan, Rekap, Summary (SNI per tab; Summary memuat semuanya).

Dipanggil dari app.py:  "Modul N 💡 Titik Lampu": titik_lampu.render
Memerlukan modules/desain.py (sistem desain bersama).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules import titik_lampu_calc as tc
from modules import titik_lampu_excel, titik_lampu_html, titik_lampu_pdf

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.cache_data(show_spinner="Membuat PDF...")
def _buat_pdf(h: dict, data: dict, proyek: dict) -> bytes:
    return titik_lampu_pdf.buat_pdf(h, data, proyek)


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
    components.html(titik_lampu_html.render(h, data, proyek, bagian),
                    height=titik_lampu_html.tinggi(h, bagian), scrolling=True)


def render():
    data = tc.muat_data()
    P0 = tc.parameter_default(data)
    P = dict(P0)
    pr = data["parameter"]

    st.subheader("Titik Lampu")
    st.caption("Jumlah titik lampu per ruangan dengan metode lumen: N = (E × A) / (Φ × LLF × CU × n), dibulatkan ke atas. "
               "Nilai E (lux) mengikuti SNI 6197:2020 Tabel 1. Rumus ditampilkan agar bisa dicocokkan dengan Excel.")
    t_hitung, t_rekap, t_sum = st.tabs(["💡 Perhitungan", "📊 Rekap", "📋 Summary"])

    # ============================================================ input
    with t_hitung:
        _landasan(data, "hitung")
        st.markdown("#### Data Ruangan dan Lampu")
        c1, c2 = st.columns(2)
        P["llf"] = c1.number_input("LLF (light loss factor)", 0.1, 1.0, float(P0["llf"]), step=0.05, key="tl_llf",
                                   help=f"Rentang pada Excel: {pr['llf_min']}–{pr['llf_max']}.")
        P["cu"] = c2.number_input("CU (coefficient of utilization)", 0.1, 1.0, float(P0["cu"]), step=0.05, key="tl_cu",
                                  help=f"Rentang pada Excel: {pr['cu_min']:.0%}–{pr['cu_max']:.0%}.")
        st.caption("Satu baris = satu ruangan. Pilih Jenis Ruangan agar E (lux) terisi otomatis; pilih “Lainnya” lalu isi E Manual "
                   "bila ruangan tidak ada di tabel (taman, koridor, outdoor). Ruangan tanpa dimensi boleh diisi Titik Manual.")
        input_df = st.data_editor(
            tc.template_default(data), key="tl_ruang", num_rows="dynamic", width="stretch", hide_index=True,
            column_config={
                "Lantai": st.column_config.TextColumn("Lantai", help="Contoh: Lantai Satu"),
                "Nama Ruangan": st.column_config.TextColumn("Nama Ruangan"),
                "P (m)": st.column_config.NumberColumn("P (m)", min_value=0.0, step=0.05, format="%.2f"),
                "L (m)": st.column_config.NumberColumn("L (m)", min_value=0.0, step=0.05, format="%.2f"),
                "Jenis Ruangan": st.column_config.SelectboxColumn("Jenis Ruangan (SNI 6197:2020)",
                                                                   options=tc.opsi_ruangan(data), width="medium"),
                "E Manual (lux)": st.column_config.NumberColumn("E Manual (lux)", min_value=0.0, step=10.0, format="%d",
                                                                help="Mengganti E dari tabel. Wajib bila Jenis Ruangan = Lainnya."),
                "Jenis Lampu": st.column_config.SelectboxColumn("Jenis Lampu", options=tc.opsi_lampu(data)),
                "Watt (W)": st.column_config.NumberColumn("Watt (W)", min_value=0.0, step=1.0, format="%g"),
                "lm/W Manual": st.column_config.NumberColumn("lm/W Manual", min_value=0.0, step=5.0, format="%g",
                                                             help="Kosongkan untuk memakai lm/W bawaan jenis lampu."),
                "n (lampu/armatur)": st.column_config.NumberColumn("n (lampu/armatur)", min_value=1, step=1, format="%d"),
                "Titik Manual": st.column_config.NumberColumn("Titik Manual", min_value=0, step=1, format="%d",
                                                              help="Isi bila jumlah titik ditetapkan sendiri; menggantikan hasil hitungan."),
            },
        )
        with st.expander("Tabel tingkat pencahayaan yang tersedia"):
            tabel = pd.DataFrame(data["lux"])[["kelompok", "fungsi", "lux", "ra", "sumber"]]
            tabel.columns = ["Kelompok", "Fungsi ruang", "E (lux)", "Ra min", "Sumber"]
            st.dataframe(tabel, hide_index=True, width="stretch")
            st.caption(data["catatan_lux"])
            st.caption(data["sumber_lampu"])

    with t_sum:
        _landasan(data, None)
        with st.expander("Data proyek (kop laporan)"):
            p = data["proyek"]
            c1, c2, c3 = st.columns(3)
            proyek = {
                "pekerjaan": c1.text_input("Pekerjaan", p["pekerjaan"], key="tl_pekerjaan"),
                "lokasi": c2.text_input("Lokasi", p["lokasi"], key="tl_lokasi"),
                "tahun": c3.text_input("Tahun", p["tahun"], key="tl_tahun"),
                "item": p["item"],
            }

    # ============================================================ hitung
    h = tc.hitung(input_df, data, P)
    if h["tabel"].empty:
        for t in (t_hitung, t_rekap, t_sum):
            with t:
                st.info("Isi minimal satu ruangan yang lengkap: nama, dimensi (atau titik manual), jenis ruangan / E, jenis lampu, dan watt.")
        return

    # ============================================================ hasil per tab
    with t_hitung:
        for ruang in h["lainnya"]:
            st.caption(f"ℹ️ {ruang}: memakai E manual (tidak ada di tabel SNI 6197:2020).")
        _html(h, data, None, "hitung")
        with st.expander("Rumus yang digunakan", expanded=False):
            st.latex(r"A = P \times L; \qquad \Phi = W \times \frac{lm}{W}")
            st.latex(r"N = \frac{E \times A}{\Phi \times LLF \times CU \times n} \quad \Rightarrow \quad N_{titik} = \lceil N \rceil")
            st.latex(r"E_{tercapai} = \frac{N_{titik} \times \Phi \times LLF \times CU \times n}{A}")

    with t_rekap:
        _landasan(data, "rekap")
        _html(h, data, None, "rekap")

    with t_sum:
        _html(h, data, proyek, "ringkasan")
        xlsx = titik_lampu_excel.build_excel(h, data, proyek)
        d1, d2, _ = st.columns([1, 1, 3])
        d1.download_button("Unduh Excel (.xlsx)", xlsx, "Titik_Lampu.xlsx", mime=XLSX_MIME, on_click="ignore")
        if d2.button("Siapkan PDF"):
            pdf = _buat_pdf(h, data, proyek)
            d2.download_button("Unduh PDF", pdf, "Titik_Lampu.pdf", mime="application/pdf", on_click="ignore")
        st.caption("File Excel berisi rumus hidup, rekap, denah skematik, tabel standar pencahayaan, dan daftar SNI/peraturan (5 sheet).")
        with st.expander("Lembar perhitungan lengkap", expanded=False):
            _html(h, data, proyek, "lembar")
