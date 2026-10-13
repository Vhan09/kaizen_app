"""Kaizen PBG - halaman utama + menu antar modul.

Jalankan:  streamlit run app.py
"""
import streamlit as st

from modules.mep import (
    ac,
    akli,
    apar,
    beban_listrik,
    cahaya_alami,
    pipa_hujan,
    resapan,
    sanitasi,
    titik_lampu,
    ventilasi,
)
from modules.arsitektur import luas_bangunan_view
from utils.theme import inject_css

st.set_page_config(page_title="Kaizen PBG", page_icon="⚡", layout="wide")
inject_css()

MODUL_MEP = {
    "Modul 1 📋 Tabel AKLI": akli.render,
    "Modul 2 ⚡ Beban Listrik (SLD)": beban_listrik.render,
    "Modul 3 ❄️ Kebutuhan AC": ac.render,
    "Modul 4 🚿 Sanitasi & Air Bersih": sanitasi.render,
    "Modul 5 🧯 Kebutuhan APAR": apar.render,
    "Modul 6 🌧️ Pipa Air Hujan": pipa_hujan.render,
    "Modul 7 💡 Titik Lampu Ruangan": titik_lampu.render,
    "Modul 8 🪟 Kebutuhan Pencahayaan Alami": cahaya_alami.render,
    "Modul 9 🪟 Kebutuhan Ventilasi": ventilasi.render,
    "Modul 10 💧 Resapan Biopori": resapan.render,
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
    bidang = st.radio(
        "Bidang keilmuan",
        ["MEP", "Sipil", "Arsitektur"],
        key="kaizen_bidang",
    )

if bidang == "MEP":
    with st.sidebar:
        with st.expander("MEP Rumah", expanded=True):
            pilihan = st.radio(
                "Modul rumah",
                list(MODUL_MEP.keys()),
                label_visibility="collapsed",
                key="kaizen_modul_rumah",
            )
        with st.expander("MEP Kawasan", expanded=False):
            st.caption("Daftar modul kawasan")
            st.markdown(
                "\n".join(
                    f"- Modul {i}: {nama} _(belum tersedia)_"
                    for i, nama in enumerate(MODUL_KAWASAN, start=1)
                )
            )
    MODUL_MEP[pilihan]()
elif bidang == "Arsitektur":
    luas_bangunan_view.render()
else:
    st.title(f"Bidang {bidang}")
    st.info(
        f"Ruang kerja {bidang} sudah disiapkan. Modul perhitungan untuk bidang ini "
        "belum tersedia."
    )
