"""Modul - Tabel AKLI (sumber data ukuran kabel & MCB)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from modules import akli_calc as calc
from modules import akli_calc as calc
from modules import ekspor_ui
from utils import storage
from utils.theme import section_title

KEY = "akli"


def ambil_tabel() -> pd.DataFrame:
    """Tabel AKLI aktif (dipakai juga oleh modul lain)."""
    ss = st.session_state
    if "akli_df" not in ss:
        ss.akli_df = calc.muat(storage.load(KEY))
    return ss.akli_df


def _reset() -> None:
    ss = st.session_state
    for k in [k for k in ss.keys() if k.startswith("akli_")]:
        del ss[k]
    storage.delete(KEY)


CFG = {
    "Fasa": None,  # disembunyikan, hanya untuk memisahkan 1 fasa / 3 fasa
    "VA": st.column_config.NumberColumn("VA", format="%d"),
    "VA Pembulatan": st.column_config.NumberColumn("VA Pembulatan", format="%d"),
    "kVA": st.column_config.NumberColumn("kVA", format="%g"),
    "Watt (PF 0,8)": st.column_config.NumberColumn("Watt (PF 0,8)", format="%d"),
    "Gol": st.column_config.TextColumn("Gol"),
    "MCB (A)": st.column_config.NumberColumn("MCB / MCCB (A)", min_value=0, format="%d"),
    "Tegangan (V)": st.column_config.NumberColumn("V", format="%d"),
    "Tipe Kabel": st.column_config.TextColumn("Tipe Kabel"),
    "Inti": st.column_config.NumberColumn("Inti", min_value=1, step=1, format="%d"),
    "Ukuran (mm²)": st.column_config.NumberColumn("Ukuran (mm²)", min_value=0, format="%g"),
}


def render() -> None:
    ss = st.session_state
    tabel = ambil_tabel()

    st.title("📋 Tabel AKLI")
    st.caption("Landasan data ukuran kabel dan MCB. Modul Beban Listrik membaca tabel ini otomatis.")

    section_title("Aturan kabel otomatis")
    st.markdown(
        "- Nama sirkuit mengandung **stk / stopkontak / kontak / AC / pompa / spare** → "
        "inti sesuai tabel (3 inti).\n"
        "- Nama sirkuit mengandung **lampu / lamp / DL / penerangan** → **2 inti**.\n"
        "- Jika dua jenis muncul bersamaan, stop kontak yang dipakai (3 inti, lebih aman).\n"
        "- Ukuran mm² diambil dari tabel di bawah menurut **MCB**. Jika MCB tidak persis ada "
        "di tabel, dipakai MCB terdekat di atasnya.\n"
        "- Tabel AKLI 1 fasa mencantumkan 3 inti. Untuk lampu, ukuran mm² tetap dari tabel, "
        "hanya jumlah intinya 2.\n"
        "- Saat ini aturan otomatis memakai tabel **1 fasa**."
    )

    section_title("Uji aturan kabel")
    u1, u2, u3 = st.columns([2, 1, 2])
    nama = u1.text_input("Nama sirkuit", value="STK AC LT.1", key="akli_uji_nama")
    mcb = u2.number_input("MCB (A)", min_value=0.0, value=10.0, step=1.0, key="akli_uji_mcb")
    teks, status = calc.kabel_otomatis(nama, mcb, tabel)
    u3.metric("Kabel", teks or "-", help=f"status: {status}")

    section_title("Data tabel AKLI")
    st.markdown('<span class="badge-y">INPUT</span> Nilai bisa dikoreksi langsung di tabel',
                unsafe_allow_html=True)

    t1 = tabel[tabel["Fasa"] == 1].reset_index(drop=True)
    t3 = tabel[tabel["Fasa"] == 3].reset_index(drop=True)
    st.markdown("**1 Fasa - 220 V**")
    e1 = st.data_editor(t1, hide_index=True, num_rows="fixed", column_config=CFG, key="akli_ed_1")
    st.markdown("**3 Fasa - 380 V**")
    e3 = st.data_editor(t3, hide_index=True, num_rows="fixed", column_config=CFG, key="akli_ed_3")

    ss.akli_df = calc.normalisasi(pd.concat([e1, e3], ignore_index=True))
    storage.save(KEY, {"tabel": storage.df_to_records(ss.akli_df)})
    st.caption("💾 Perubahan tersimpan otomatis di folder data/")
    
    section_title("Unduh / Ekspor")
    ekspor_ui.ekspor_akli(ss.akli_df)
    st.button("↺ Kembalikan ke tabel AKLI bawaan", on_click=_reset, key="akli_reset")
