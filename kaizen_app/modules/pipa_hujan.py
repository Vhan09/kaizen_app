"""Pipa Air Hujan - empat tab: Debit Hujan, Roof Drain & Pipa Horizontal, Pipa Tegak, Summary.

Setiap tab hanya menampilkan SNI/peraturan yang berkaitan; tab Summary menampilkan semuanya.
Dipanggil dari app.py:  "Modul N 🌧️ Pipa Air Hujan": pipa_hujan.render
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules import pipa_hujan_calc as pc
from modules import pipa_hujan_excel, pipa_hujan_html
from modules import pipa_hujan_pdf

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_INCI = lambda x: f'Ø{x:g}"'.replace(".", ",")


@st.cache_data(show_spinner="Membuat PDF...")
def _buat_pdf(h: dict, data: dict, proyek: dict) -> bytes:
    return pipa_hujan_pdf.buat_pdf(h, data, proyek)


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
    components.html(pipa_hujan_html.render(h, data, proyek, bagian),
                    height=pipa_hujan_html.tinggi(h, bagian), scrolling=True)


def render():
    data = pc.muat_data()
    P0 = pc.parameter_default(data)
    P = dict(P0)
    ukuran, ukuran_tegak = data["ukuran_inci"], data["ukuran_tegak_inci"]

    st.subheader("Pipa Air Hujan")
    st.caption("Debit hujan dengan metode rasional, lalu pengecekan roof drain, pipa horizontal (SNI 8153:2015 Tabel 16), "
               "dan pipa tegak / kolektor. Pilih tab di bawah; Summary berisi skema, kesimpulan, dan unduhan.")
    t_debit, t_horiz, t_tegak, t_sum = st.tabs(["🌧️ Debit Hujan", "📐 Roof Drain & Pipa Horizontal",
                                                "🧱 Pipa Tegak / Kolektor", "📋 Summary"])

    # ============================================================ input
    with t_debit:
        _landasan(data, "debit")
        st.markdown("#### Data Atap dan Curah Hujan")
        P["I"] = st.number_input("Intensitas hujan rencana I (mm/jam)", 10.0, 500.0, float(P0["I"]), step=5.0,
                                 key="ph_I", help="Excel kamu memakai 150 mm/jam.")
        atap_df = st.data_editor(
            pc.template_atap(data), key="ph_atap", num_rows="dynamic", width="stretch", hide_index=True,
            column_config={
                "Bidang Atap": st.column_config.TextColumn("Bidang Atap", help="Contoh: Atap utama, Atap teras"),
                "Luas (m²)": st.column_config.NumberColumn("Luas A (m²)", min_value=0.0, step=0.5, format="%.2f"),
                "Koef. Limpasan (C)": st.column_config.NumberColumn("Koef. Limpasan (C)", min_value=0.0, max_value=1.0,
                                                                   step=0.05, format="%.2f"),
                "Jumlah Roof Drain": st.column_config.NumberColumn("Jumlah Roof Drain", min_value=1, step=1, format="%d"),
            },
        )
        st.caption("Beberapa bidang atap boleh diisi terpisah; debit dijumlahkan dan pipa cabang dicek terhadap bidang dengan "
                   "luas per roof drain terbesar.")

    with t_horiz:
        _landasan(data, "horizontal")
        st.markdown("#### Roof Drain dan Pipa Horizontal")
        c1, c2, c3 = st.columns(3)
        P["d_roof"] = c1.selectbox("Ø roof drain", ukuran, index=ukuran.index(3), format_func=_INCI, key="ph_dr")
        P["d_cabang"] = c2.selectbox("Ø pipa cabang", ukuran, index=ukuran.index(3), format_func=_INCI, key="ph_dc")
        P["s_cabang"] = c3.selectbox("Kemiringan pipa cabang", [1, 2, 4], format_func=lambda x: f"{x} %", key="ph_sc")
        c4, c5, _ = st.columns(3)
        P["d_gabung"] = c4.selectbox("Ø pipa horizontal gabungan", ukuran, index=ukuran.index(3), format_func=_INCI,
                                     key="ph_dg")
        P["s_gabung"] = c5.selectbox("Kemiringan pipa gabungan", [1, 2, 4], format_func=lambda x: f"{x} %", key="ph_sg")

    with t_tegak:
        _landasan(data, "tegak")
        st.markdown("#### Pipa Tegak / Kolektor Vertikal")
        c1, c2 = st.columns(2)
        P["d_tegak"] = c1.selectbox("Ø pipa kolektor vertikal", ukuran_tegak, index=ukuran_tegak.index(4),
                                    format_func=_INCI, key="ph_dt")
        P["cap_tegak"] = c2.number_input("Kapasitas pipa tegak dari Tabel 17 SNI 8153:2015 (m²)", 0.0, 1_000_000.0, 0.0,
                                         step=10.0, key="ph_cap",
                                         help="Isi dari dokumen SNI untuk Ø dan intensitas rencana. Kosongkan (0) bila belum ada.")

    with t_sum:
        _landasan(data, None)
        with st.expander("Data proyek (kop laporan)"):
            p = data["proyek"]
            c1, c2, c3 = st.columns(3)
            proyek = {
                "pekerjaan": c1.text_input("Pekerjaan", p["pekerjaan"], key="ph_pekerjaan"),
                "lokasi": c2.text_input("Lokasi", p["lokasi"], key="ph_lokasi"),
                "tahun": c3.text_input("Tahun", p["tahun"], key="ph_tahun"),
                "item": p["item"],
            }

    # ============================================================ hitung
    h = pc.hitung(atap_df, data, P)
    if h["zona"].empty:
        for t in (t_debit, t_horiz, t_tegak, t_sum):
            with t:
                st.info("Isi minimal satu bidang atap yang lengkap (nama, luas > 0, koefisien C 0–1, jumlah roof drain ≥ 1).")
        return

    # ============================================================ hasil per tab
    with t_debit:
        _html(h, data, None, "debit")
        with st.expander("Rumus yang digunakan", expanded=False):
            st.latex(r"Q = 0{,}00278 \times C \times I \times A")
            st.caption("Q = debit (m³/dt), C = koefisien limpasan, I = intensitas hujan (mm/jam), A = luas atap (Ha). "
                       "1 m³/dt = 1000 L/dt; 1 Ha = 10.000 m².")

    with t_horiz:
        _html(h, data, None, "horizontal")
        with st.expander("Cara pengecekan", expanded=False):
            st.latex(r"A_{dilayani} \le A_{maks}\ (\text{Tabel 16: } \varnothing,\ \text{kemiringan},\ I)")
            st.latex(r"A_{cabang} = \frac{A_{atap}}{n_{roof\ drain}}")
            st.caption("Kolom intensitas yang dipakai adalah nilai Tabel 16 terdekat di atas intensitas rencana "
                       "(25,4 / 50,8 / 76,2 / 101,6 / 127 / 162,4 mm/jam).")

    with t_tegak:
        _html(h, data, None, "tegak")

    with t_sum:
        _html(h, data, proyek, "ringkasan")
        xlsx = pipa_hujan_excel.build_excel(h, data, proyek)
        d1, d2, _ = st.columns([1, 1, 3])
        d1.download_button("Unduh Excel (.xlsx)", xlsx, "Pipa_Air_Hujan.xlsx", mime=XLSX_MIME, on_click="ignore")
        if d2.button("Siapkan PDF"):
            pdf = _buat_pdf(h, data, proyek)
            d2.download_button("Unduh PDF", pdf, "Pipa_Air_Hujan.pdf", mime="application/pdf", on_click="ignore")
        st.caption("File Excel berisi rumus hidup, skema sistem, Tabel 16 SNI 8153:2015, dan daftar SNI/peraturan (3 sheet).")
        with st.expander("Lembar perhitungan lengkap", expanded=False):
            _html(h, data, proyek, "lembar")
