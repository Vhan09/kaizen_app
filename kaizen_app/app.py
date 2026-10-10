"""Kaizen PBG - halaman utama + menu antar modul.

Jalankan:  streamlit run app.py
"""
import streamlit as st

from modules import ventilasi
from modules import cahaya_alami
from modules import titik_lampu
from modules import apar
from modules import pipa_hujan
from modules import ac, akli, beban_listrik, sanitasi
from utils.theme import inject_css

st.set_page_config(page_title="Kaizen PBG", page_icon="⚡", layout="wide")
inject_css()

# nama menu -> fungsi render (None = belum dikerjakan)
MODUL = {
    "Modul 1 📋 Tabel AKLI": akli.render,
    "Modul 2 ⚡ Beban Listrik (SLD)": beban_listrik.render,
    "Modul 3 ❄️ Kebutuhan AC": ac.render,
    "Modul 4 🚿 Sanitasi & Air Bersih": sanitasi.render,
    "Modul 5 🧯 Kebutuhan APAR": apar.render,
    "Modul 6 🌧️ Pipa Air Hujan": pipa_hujan.render,
    "Modul 7 💡 Titik Lampu Ruangan": titik_lampu.render,
    "Modul 8 🪟 Kebutuhan Pencahayaan Alami": cahaya_alami.render,
    "Modul 9 🪟 Kebutuhan Ventilasi": ventilasi.render,
    "Modul 10 💧 Resapan Biopori": None,
}

MODUL_KAWASAN = [
    "Listrik underground",
    "Fiber Optic",
    "PJU",
    "Air Bersih Kawasan",
    "IPAL",
]

with st.sidebar:
    st.markdown("### Kaizen PBG")
    st.caption("Perhitungan pendukung Persetujuan Bangunan Gedung")
    with st.expander("MEP (Mechanical Electrical Plumbing)", expanded=True):
        with st.expander("MEP Rumah", expanded=True):
            pilihan = st.radio("Modul rumah", list(MODUL.keys()), label_visibility="collapsed", key="kaizen_modul_rumah")
        with st.expander("MEP Kawasan", expanded=False):
            st.caption("Daftar modul kawasan")
            st.markdown("\n".join(f"- Modul {i}: {nama} _(belum tersedia)_" for i, nama in enumerate(MODUL_KAWASAN, start=1)))

render = MODUL[pilihan]
if render is None:
    st.title(pilihan)
    st.info("Modul ini dikerjakan setelah Modul 4 (Sanitasi & Air Bersih) selesai dan disetujui.")
else:
    render()
