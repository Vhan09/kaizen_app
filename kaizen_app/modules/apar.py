"""Modul - Perhitungan Kebutuhan APAR (sheet 'Apar')."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from modules import apar_calc as calc
from modules import ekspor_ui
from modules.apar_html import (
    catatan_tabel_html, hitung_html, peraturan_html, rekomendasi_html, tabel_kelas_a_html,
)
from modules.beban_listrik_html import header_proyek_html
from utils import storage
from utils.theme import section_title

KEY = "apar"
BADGE = '<span class="badge-y">INPUT</span>'

# Nilai kotak isian yang harus selamat saat pindah menu (Streamlit membuang nilai widget
# yang tidak digambar), disimpan juga di ap_cache lalu dipulihkan.
WIDGET_KEYS = [
    "ap_pekerjaan", "ap_lokasi", "ap_tahun", "ap_item",
    "ap_kelas", "ap_jenis", "ap_kap", "ap_rating", "ap_jarak",
]
JARAK_MIN, JARAK_MAKS = 1.0, 100.0


# ------------------------------------------------------------------ state
def _sanitasi() -> list[str]:
    """Kembalikan isian yang tidak sah ke nilai bawaan dan beri tahu pengguna."""
    ss = st.session_state
    pesan = []
    if ss.get("ap_kelas") not in calc.KELAS:
        pesan.append(f"Klasifikasi '{ss.get('ap_kelas')}' tidak dikenal, dikembalikan ke {calc.KELAS_BAWAAN}.")
        ss["ap_kelas"] = calc.KELAS_BAWAAN
    if ss.get("ap_jenis") not in calc.JENIS:
        pesan.append(f"Jenis APAR '{ss.get('ap_jenis')}' tidak dikenal, dikembalikan ke {calc.JENIS_BAWAAN}.")
        ss["ap_jenis"] = calc.JENIS_BAWAAN
    try:
        v = float(ss.get("ap_jarak"))
        ok = JARAK_MIN <= v <= JARAK_MAKS
    except (TypeError, ValueError):
        v, ok = None, False
    if ok:
        ss["ap_jarak"] = v
    else:
        pesan.append(f"Batas jarak tempuh {ss.get('ap_jarak')} m tidak wajar ({JARAK_MIN:g}-{JARAK_MAKS:g} m), "
                     f"dikembalikan ke {calc.JARAK_REGULASI_BAWAAN:g} m.")
        ss["ap_jarak"] = calc.JARAK_REGULASI_BAWAAN
    return pesan


def _init() -> list[str]:
    ss = st.session_state
    if "ap_ready" not in ss:
        _isi_awal()
    for k in WIDGET_KEYS:  # pulihkan nilai yang terhapus karena pindah menu
        if k not in ss:
            ss[k] = ss.ap_cache[k]
    return _sanitasi()


def _isi_awal() -> None:
    ss = st.session_state
    d = calc.muat_state(storage.load(KEY), storage.load("beban_listrik"))
    p = d["proyek"]
    ss.ap_pekerjaan, ss.ap_lokasi, ss.ap_tahun, ss.ap_item = p["pekerjaan"], p["lokasi"], p["tahun"], p["item"]
    ss.ap_kelas, ss.ap_jenis = d["kelas"], d["jenis"]
    ss.ap_kap, ss.ap_rating, ss.ap_jarak = d["kapasitas"], d["rating"], d["jarak"]
    ss.ap_lantai, ss.ap_tabel = d["lantai"], d["tabel"]
    ss.ap_verl = 0
    ss.ap_hapus_l = 0
    ss.ap_cache = {k: ss[k] for k in WIDGET_KEYS}
    ss.ap_ready = True


def _reset() -> None:
    ss = st.session_state
    for k in [k for k in ss.keys() if k.startswith("ap_")]:
        del ss[k]
    storage.delete(KEY)


def _tambah_lantai() -> None:
    ss = st.session_state
    baru = pd.DataFrame([{calc.C_LANTAI: f"Lantai {len(ss.ap_lantai) + 1}", calc.C_LUAS: 0.0}])
    ss.ap_lantai = calc.normalisasi_lantai(pd.concat([ss.ap_lantai, baru], ignore_index=True))
    ss.ap_verl += 1


def _hapus_lantai() -> None:
    ss = st.session_state
    if len(ss.ap_lantai) <= 1:
        return
    idx = int(ss.get("ap_hapus_l", 0))
    ss.ap_lantai = ss.ap_lantai.drop(index=idx).reset_index(drop=True)
    ss.ap_hapus_l = 0
    ss.ap_verl += 1


def _proyek() -> dict:
    ss = st.session_state
    return {"pekerjaan": ss.ap_pekerjaan, "lokasi": ss.ap_lokasi, "tahun": ss.ap_tahun, "item": ss.ap_item}


def _entri() -> dict:
    ss = st.session_state
    return {"kelas": ss.ap_kelas, "jenis": ss.ap_jenis, "kapasitas": ss.ap_kap,
            "rating": ss.ap_rating, "jarak_reg": float(ss.ap_jarak), "lantai": ss.ap_lantai}


# ------------------------------------------------------------------ halaman
def render() -> None:
    pesan_koreksi = _init()
    ss = st.session_state

    st.title("🧯 Perhitungan Kebutuhan APAR")
    st.caption("Alat Pemadam Api Ringan untuk kebakaran Kelas A - kolom kuning diisi manual, sisanya otomatis.")
    for m in pesan_koreksi:
        st.warning(m)

    # ---- 1. Data proyek
    section_title("1. Data Proyek")
    st.markdown(f"{BADGE} Identitas proyek (terisi awal dari modul Beban Listrik bila sudah ada)",
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.text_input("Pekerjaan", key="ap_pekerjaan")
    c2.text_input("Lokasi", key="ap_lokasi")
    c1.text_input("Tahun", key="ap_tahun")
    c2.text_input("Item Pekerjaan", key="ap_item")

    # ---- 2. Dasar peraturan
    section_title("2. Dasar Peraturan & Standar")
    st.markdown(peraturan_html(ss.ap_jarak), unsafe_allow_html=True)

    # ---- 3. Input
    section_title("3. Input Perhitungan")
    k1, k2 = st.columns(2)
    k1.selectbox(
        "Klasifikasi hunian", calc.KELAS, key="ap_kelas",
        format_func=lambda k: f"Hunian bahaya kebakaran {k.lower()}",
        help="Rumah tinggal umumnya digolongkan bahaya kebakaran ringan.",
    )
    k2.number_input(
        "Batas jarak tempuh ke APAR (m)", min_value=JARAK_MIN, max_value=JARAK_MAKS, step=1.0, key="ap_jarak",
        help="Batas regulasi (bawaan 15 m). Jarak yang dipakai = yang terkecil antara tabel dan batas ini.",
    )
    j1, j2, j3 = st.columns([2, 1, 1])
    j1.selectbox("Jenis APAR", list(calc.JENIS), key="ap_jenis")
    j2.text_input("Kapasitas", key="ap_kap", help="Contoh: 3 kg")
    j3.text_input("Rating", key="ap_rating",
                  help="Contoh 2A:10BC. Rating-A dibaca dari angka sebelum huruf A.")
    st.caption(f"{ss.ap_jenis}: {calc.JENIS[ss.ap_jenis]}. Isi rating sesuai label pada tabung.")

    st.markdown(f"{BADGE} **Luas lantai bangunan** (tambah baris untuk tiap lantai)", unsafe_allow_html=True)
    lantai_ed = st.data_editor(
        ss.ap_lantai, hide_index=True, num_rows="fixed", key=f"ap_lantai_ed_{ss.ap_verl}",
        column_config={
            calc.C_LANTAI: st.column_config.TextColumn("Lantai / Area", width="medium"),
            calc.C_LUAS: st.column_config.NumberColumn("Luas (m²)", min_value=0, step=1, format="%g"),
        },
    )
    ss.ap_lantai = calc.normalisasi_lantai(lantai_ed)
    a1, a2, a3 = st.columns([1, 2, 1])
    a1.button("➕ Tambah lantai", on_click=_tambah_lantai)
    a2.selectbox(
        "Hapus lantai", options=list(range(len(ss.ap_lantai))),
        format_func=lambda i: f"{i + 1}. {ss.ap_lantai.loc[i, calc.C_LANTAI] or '(kosong)'}",
        key="ap_hapus_l", label_visibility="collapsed",
    )
    a3.button("🗑️ Hapus lantai", on_click=_hapus_lantai)
    st.caption("Rumah dua lantai umumnya memerlukan APAR pada tiap lantai, jadi isi luas setiap lantai.")

    with st.expander("Tabel acuan Kelas A (bisa diedit)"):
        st.caption("Nilai bawaan mengikuti Excel acuan. Luas maks per APAR 100 m² lebih ketat daripada "
                   "angka NFPA 10 (1.045 m²); ubah di sini bila dasar perencanaan Anda berbeda.")
        tabel_ed = st.data_editor(
            ss.ap_tabel, hide_index=True, num_rows="fixed", disabled=[calc.C_KELAS], key="ap_tabel_ed",
            column_config={
                calc.C_MINA: st.column_config.NumberColumn("Daya padam min (A)", min_value=0.5, step=0.5, format="%g"),
                calc.C_PERA: st.column_config.NumberColumn("Luas per unit A (m²)", min_value=1, step=1, format="%g"),
                calc.C_MAKS: st.column_config.NumberColumn("Luas maks per APAR (m²)", min_value=1, step=1, format="%g"),
                calc.C_JARAK: st.column_config.NumberColumn("Jarak tempuh maks (m)", min_value=1, step=1, format="%g"),
            },
        )
        ss.ap_tabel = calc.normalisasi_tabel(tabel_ed)

    # ---- 4. Hasil
    h = calc.hitung(ss.ap_lantai, ss.ap_kelas, ss.ap_rating, ss.ap_jarak, ss.ap_tabel)
    section_title("4. Hasil Perhitungan")
    st.markdown(header_proyek_html(_proyek()), unsafe_allow_html=True)
    for c in h["catatan"]:
        st.warning(c)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Kebutuhan APAR", "-" if h["total"] is None else f"{h['total']} buah")
    m2.metric("Rating dipakai", f"{h['rating_a']:g}-A", help=f"Minimum disyaratkan {h['min_a']:g}-A ({h['status_rating']})")
    m3.metric("Cakupan per APAR", f"{h['cakupan']:g} m²")
    m4.metric("Jarak tempuh maks", f"{h['jarak_pakai']:g} m")

    st.markdown("**Ukuran APAR dan Penempatannya untuk Bahaya Kebakaran Kelas A**")
    st.markdown(tabel_kelas_a_html(ss.ap_tabel, ss.ap_kelas), unsafe_allow_html=True)
    st.markdown(catatan_tabel_html(), unsafe_allow_html=True)

    st.markdown("**Perhitungan Jumlah APAR**")
    st.markdown(hitung_html(h), unsafe_allow_html=True)
    for i in h["info"]:
        st.caption(f"ℹ️ {i}")

    st.markdown("**Rekomendasi APAR**")
    st.markdown(rekomendasi_html(ss.ap_jenis, ss.ap_kap, ss.ap_rating, h), unsafe_allow_html=True)
    st.caption("Dasar APAR tidak boleh kurang dari 15 cm di atas permukaan lantai (PER.04/MEN/1980). "
               "Tempatkan APAR pada jalur yang mudah dilihat dan dijangkau.")

    # ---- 5. Unduh / ekspor
    section_title("5. Unduh / Ekspor")
    ekspor_ui.ekspor_apar(_proyek(), _entri(), ss.ap_tabel, h)

    # ---- simpan otomatis
    ss.ap_cache = {k: ss[k] for k in WIDGET_KEYS}
    storage.save(KEY, {
        "proyek": _proyek(), "kelas": ss.ap_kelas, "jenis": ss.ap_jenis, "kapasitas": ss.ap_kap,
        "rating": ss.ap_rating, "jarak": float(ss.ap_jarak),
        "tabel": storage.df_to_records(ss.ap_tabel), "lantai": storage.df_to_records(ss.ap_lantai),
    })
    st.caption("💾 Data tersimpan otomatis di folder data/")
    st.button("↺ Reset ke data awal", on_click=_reset, key="ap_reset")
