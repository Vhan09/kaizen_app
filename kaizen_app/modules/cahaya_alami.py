"""Pencahayaan Alami - tiga tab: Perhitungan, Rekap, Summary (SNI per tab; Summary memuat semuanya).

Dipanggil dari app.py:  "Modul N ☀️ Kebutuhan Pencahayaan Alami": cahaya_alami.render
Memerlukan modules/desain.py (sistem desain bersama).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules import cahaya_alami_calc as cc
from modules import cahaya_alami_excel, cahaya_alami_html
from modules import cahaya_alami_pdf

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.cache_data(show_spinner="Membuat PDF...")
def _buat_pdf(h: dict, data: dict, proyek: dict) -> bytes:
    return cahaya_alami_pdf.buat_pdf(h, data, proyek)


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
    components.html(cahaya_alami_html.render(h, data, proyek, bagian),
                    height=cahaya_alami_html.tinggi(h, bagian), scrolling=True)


def render():
    data = cc.muat_data()

    st.subheader("Kebutuhan Pencahayaan Alami")
    st.caption("Pemeriksaan awal pencahayaan alami: rasio luas bukaan terhadap luas lantai (Aj/Ar) per ruangan. "
               "Rumus ditampilkan agar bisa dicocokkan dengan Excel.")
    t_hitung, t_rekap, t_sum = st.tabs(["🪟 Perhitungan", "📊 Rekap", "📋 Summary"])

    # ============================================================ input
    with t_hitung:
        _landasan(data, "hitung")
        st.markdown("#### Parameter")
        opsi = cc.opsi_ambang(data)
        pilih = st.selectbox("Ambang rasio minimum Aj/Ar", opsi, index=0, key="ca_ambang")
        nilai = next(a["nilai"] for a in data["ambang"] if a["label"] == pilih)
        if nilai is None:
            nilai = st.number_input("Ambang kustom (% dari luas lantai)", 1.0, 50.0, 10.0, step=0.5, key="ca_kustom") / 100
        st.caption("Rasio ini aturan praktis (Excel: minimal 10–12% luas lantai). Penilaian formal SNI 03-2396-2001 memakai faktor langit "
                   "dan belum dihitung di modul ini.")

        st.markdown("#### Data Ruangan")
        ruang_df = st.data_editor(
            cc.template_ruang(), key="ca_ruang", num_rows="dynamic", width="stretch", hide_index=True,
            column_config={
                "Lantai": st.column_config.TextColumn("Lantai", help="Contoh: Lantai Satu"),
                "Nama Ruangan": st.column_config.TextColumn("Nama Ruangan", help="Nama harus unik; dipakai untuk menghubungkan bukaan."),
                "P (m)": st.column_config.NumberColumn("P (m)", min_value=0.0, step=0.05, format="%.2f"),
                "L (m)": st.column_config.NumberColumn("L (m)", min_value=0.0, step=0.05, format="%.2f"),
                "Jenis Ruang": st.column_config.SelectboxColumn("Jenis Ruang", options=data["jenis_ruang"],
                                                                help="Area terbuka (garasi, teras, taman) tidak dihitung."),
            },
        )
        opsi_ruangan = list(dict.fromkeys(
            nama.strip()
            for nama in ruang_df["Nama Ruangan"].dropna().astype(str)
            if nama.strip()
        ))
        st.markdown("#### Data Bukaan Cahaya (Jendela)")
        st.caption("Satu baris = satu jenis bukaan. Pilih ruangan dari daftar yang mengikuti tabel Data Ruangan; satu ruangan boleh punya "
                   "beberapa baris. Faktor efektif 1,0 = seluruh luas bukaan dihitung; kurangi bila ada kisi, rangka tebal, atau penghalang.")
        bukaan_df = st.data_editor(
            cc.template_bukaan(), key="ca_bukaan", num_rows="dynamic", width="stretch", hide_index=True,
            column_config={
                "Ruangan": st.column_config.SelectboxColumn("Ruangan", options=opsi_ruangan, width="medium"),
                "Jenis Bukaan": st.column_config.SelectboxColumn("Jenis Bukaan", options=data["jenis_bukaan"]),
                "Lebar (m)": st.column_config.NumberColumn("Lebar (m)", min_value=0.0, step=0.05, format="%.2f"),
                "Tinggi (m)": st.column_config.NumberColumn("Tinggi (m)", min_value=0.0, step=0.05, format="%.2f"),
                "Jumlah": st.column_config.NumberColumn("Jumlah", min_value=1, step=1, format="%d"),
                "Faktor Efektif": st.column_config.NumberColumn("Faktor Efektif", min_value=0.1, max_value=1.0, step=0.05, format="%.2f"),
            },
        )

    with t_sum:
        _landasan(data, None)
        with st.expander("Data proyek (kop laporan)"):
            p = data["proyek"]
            c1, c2, c3 = st.columns(3)
            proyek = {
                "pekerjaan": c1.text_input("Pekerjaan", p["pekerjaan"], key="ca_pekerjaan"),
                "lokasi": c2.text_input("Lokasi", p["lokasi"], key="ca_lokasi"),
                "tahun": c3.text_input("Tahun", p["tahun"], key="ca_tahun"),
                "item": p["item"],
            }

    # ============================================================ hitung
    h = cc.hitung(ruang_df, bukaan_df, data, float(nilai))
    if h["tabel"].empty or not h.get("n_dinilai"):
        for t in (t_hitung, t_rekap, t_sum):
            with t:
                st.info("Isi minimal satu ruangan tertutup dengan dimensi (P × L) dan data bukaannya.")
        return

    # ============================================================ hasil per tab
    with t_hitung:
        _html(h, data, None, "hitung")
        with st.expander("Rumus yang digunakan", expanded=False):
            st.latex(r"A_j = \sum \left(\text{lebar} \times \text{tinggi} \times \text{jumlah} \times f_{efektif}\right); \qquad A_r = P \times L")
            st.latex(rf"\text{{Rasio}} = \frac{{A_j}}{{A_r}} \ge {cc.pct_bersih(h['ambang'])}; \qquad A_{{j,min}} = {cc.pct_bersih(h['ambang'])} \times A_r")

    with t_rekap:
        _landasan(data, "rekap")
        _html(h, data, None, "rekap")

    with t_sum:
        _html(h, data, proyek, "ringkasan")
        xlsx = cahaya_alami_excel.build_excel(h, data, proyek)
        pdf = _buat_pdf(h, data, proyek)
        d1, d2, _ = st.columns([1, 1, 3])
        d1.download_button("Unduh Excel (.xlsx)", xlsx, "Pencahayaan_Alami.xlsx", mime=XLSX_MIME, on_click="ignore")
        d2.download_button("Unduh PDF", pdf, "Pencahayaan_Alami.pdf", mime="application/pdf", on_click="ignore")
        st.caption("File Excel berisi rumus hidup, rekap per lantai, ilustrasi proporsional, dan daftar SNI/peraturan (4 sheet).")
        with st.expander("Lembar perhitungan lengkap", expanded=False):
            _html(h, data, proyek, "lembar")
