"""Tema umum aplikasi (warna, tabel gaya Excel)."""
import streamlit as st

CSS = """
<style>
:root { --navy:#1F3864; --yellow:#FFF200; --green:#00B050; --line:#8C96A3; }

.block-container { padding-top: 1.5rem; max-width: 1500px; }

/* Kotak identitas proyek (seperti blok PEKERJAAN/LOKASI di Excel) */
table.proj { border-collapse: collapse; margin-bottom: .5rem; }
table.proj td { padding: 2px 10px 2px 0; font-size: 14px; vertical-align: top; }
table.proj td.k { font-weight: 700; white-space: nowrap; }

.sec-title { background: var(--navy); color: #fff; padding: 6px 12px;
             font-weight: 700; border-radius: 4px; margin: 1.2rem 0 .6rem 0; }

.badge-y { background: var(--yellow); color: #000; font-weight: 700;
           padding: 1px 8px; border-radius: 3px; font-size: 12px;
           border: 1px solid #b8b000; margin-right: 6px; }

/* Tabel hasil gaya Excel */
.xl-wrap { overflow-x: auto; }
table.xl { border-collapse: collapse; font-size: 13px; width: 100%;
           background: #fff; color: #111; }
table.xl th, table.xl td { border: 1px solid var(--line); padding: 4px 8px;
                           text-align: center; white-space: nowrap; }
table.xl th { background: var(--navy); color: #fff; font-weight: 700; }
table.xl th.y { background: var(--yellow); color: #000; }
table.xl td.l { text-align: left; }
table.xl td.g { background: var(--green); color: #fff; font-weight: 700; }
table.xl td.b { font-weight: 700; background: #EEF2F8; }
table.xl td.note { text-align: left; font-style: italic; background: #FFF9C4; }
table.xl td.zero { color: #bbb; }

.notes { font-size: 13px; line-height: 1.6; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def section_title(teks: str) -> None:
    st.markdown(f'<div class="sec-title">{teks}</div>', unsafe_allow_html=True)


def info_simpan(tersimpan: bool, nama: str) -> None:
    if tersimpan:
        st.caption(f"💾 Data {nama} tersimpan otomatis di folder data/")
    else:
        st.error(f"Data {nama} belum tersimpan. Periksa izin tulis pada folder data/")
