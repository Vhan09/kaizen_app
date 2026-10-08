"""Kaizen PBG - halaman utama + menu antar modul.

Jalankan:  streamlit run app.py
"""
import streamlit as st

from kaizen_app.modules import pipa_hujan
from modules import ac, akli, beban_listrik, sanitasi
from utils.theme import inject_css

st.set_page_config(page_title="Kaizen PBG", page_icon="⚡", layout="wide")
inject_css()

# nama menu -> fungsi render (None = belum dikerjakan)
MODUL = {
    "Modul 1📋 Tabel AKLI": akli.render,
    "Modul 2⚡ Beban Listrik (SLD)": beban_listrik.render,
    "Modul 3❄️ Kebutuhan AC": ac.render,
    "Modul 4🚿 Sanitasi & Air Bersih": sanitasi.render,
    "Modul 5🧯 Kebutuhan APAR": None,
    "Modul 6🌧️ Pipa Air Hujan": pipa_hujan.render,
    "Modul 7💡 Titik Lampu Ruangan": None,
    "Modul 8🪟 Kebutuhan Pencahayaan Alami": None,
    "Modul 9🪟 Kebutuhan Ventilasi": None,
    "Modul 10💧 Resapan Biopori": None,
}

with st.sidebar:
    st.markdown("### Kaizen PBG")
    st.caption("Perhitungan pendukung Persetujuan Bangunan Gedung")
    pilihan = st.radio("Modul", list(MODUL.keys()), label_visibility="collapsed")

render = MODUL[pilihan]
if render is None:
    st.title(pilihan)
    st.info("Modul ini dikerjakan setelah Modul 4 (Sanitasi & Air Bersih) selesai dan disetujui.")
else:
    render()
