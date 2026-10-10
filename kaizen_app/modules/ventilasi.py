"""Modul - Penghawaan Alami & Ventilasi Mekanis (sheet 'Penghawaan Ruangan')."""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules import ekspor_ui
from modules import ventilasi_calc as calc
from modules.ventilasi_html import (
    render as render_laporan, tinggi as tinggi_laporan,
)
from utils import storage
from utils.formatting import fmt_id
from utils.theme import info_simpan, section_title

KEY = "ventilasi"
BADGE = '<span class="badge-y">INPUT</span>'

# Nilai kotak isian yang harus selamat saat pindah menu (Streamlit membuang nilai widget
# yang tidak digambar), disimpan juga di ve_cache lalu dipulihkan.
WIDGET_KEYS = ["ve_pekerjaan", "ve_lokasi", "ve_tahun", "ve_item", "ve_dasar", "ve_kustom"]
KUSTOM_MIN, KUSTOM_MAKS = 0.5, 50.0

KOREKSI = [
    "**Batas ventilasi alami:** Excel memakai 10%. SNI 03-6572-2001 pasal 4.3.2 menyebut **5%** dari luas lantai "
    "ruangan. Angka 10% di SNI hanya ada pada pasal 4.3.3(b), yaitu bangunan kelas 5-9 yang meminjam ventilasi "
    "dari ruang bersebelahan. Pilihan 10% tetap tersedia sebagai acuan konservatif.",
    "**Keterangan diketik manual:** pada Excel kolom keterangan berupa teks, bukan rumus. Contoh Kamar Tidur Kecil: "
    "Av 0,54 m² kurang dari syarat 0,55 m² (selisih -0,01) pada basis 10%, tetapi tertulis \"Sesuai\". "
    "Sekarang status dihitung otomatis.",
    "**Tabel ACH:** angka di Excel (rumah tinggal 5-10, kamar tidur 3-6, dapur 10-15, kamar mandi 15-20) tidak "
    "terdapat dalam SNI 03-6572-2001. Diganti Tabel 4.4.1: kamar mandi / peturasan 10, dapur 20, "
    "lobi / koridor / tangga 4 kali per jam.",
    "**Cek exhaust:** Excel membandingkan dengan 20 kali/jam untuk kamar mandi, sedangkan SNI Tabel 4.4.1 "
    "mensyaratkan 10.",
    "**Aturan SNI yang ditambahkan:** arah bukaan (4.3.2 b), kompartemen sanitasi tidak boleh meminjam ventilasi "
    "ruang bersebelahan (4.3.3 a.1), dan ruang berkloset tanpa hubungan udara luar wajib exhaust (4.3.5 b.2).",
    "**Luas bukaan:** Excel menulis (2 × 0,47) × (2 × 1,2) = 2,256 m², setara 4 bukaan 0,47 × 1,2 m. "
    "Di aplikasi ditulis Jml = 4; pastikan keempatnya berupa bukaan yang dapat dibuka (kaca mati tidak dihitung).",
]


# ------------------------------------------------------------------ state
def _sanitasi() -> list[str]:
    ss = st.session_state
    pesan = []
    if ss.get("ve_dasar") not in calc.DASAR_OPSI:
        pesan.append(f"Dasar rasio '{ss.get('ve_dasar')}' tidak dikenal, dikembalikan ke {calc.DASAR_BAWAAN}.")
        ss["ve_dasar"] = calc.DASAR_BAWAAN
    try:
        v = float(ss.get("ve_kustom"))
        ok = KUSTOM_MIN <= v <= KUSTOM_MAKS
    except (TypeError, ValueError):
        v, ok = None, False
    if ok:
        ss["ve_kustom"] = v
    else:
        pesan.append(f"Rasio kustom {ss.get('ve_kustom')}% tidak wajar ({KUSTOM_MIN:g}-{KUSTOM_MAKS:g}%), "
                     f"dikembalikan ke {calc.KUSTOM_BAWAAN:g}%.")
        ss["ve_kustom"] = calc.KUSTOM_BAWAAN
    return pesan


def _init() -> list[str]:
    ss = st.session_state
    if "ve_ready" not in ss:
        _isi_awal()
    for k in WIDGET_KEYS:  # pulihkan nilai yang terhapus karena pindah menu
        if k not in ss:
            ss[k] = ss.ve_cache[k]
    return _sanitasi()


def _isi_awal() -> None:
    ss = st.session_state
    d = calc.muat_state(storage.load(KEY), storage.load("beban_listrik"))
    p = d["proyek"]
    ss.ve_pekerjaan, ss.ve_lokasi, ss.ve_tahun, ss.ve_item = p["pekerjaan"], p["lokasi"], p["tahun"], p["item"]
    ss.ve_dasar, ss.ve_kustom = d["dasar"], d["kustom"]
    ss.ve_ach, ss.ve_ruang = d["ach"], d["ruang"]
    ss.ve_ver = 0
    ss.ve_hapus = 0
    ss.ve_cache = {k: ss[k] for k in WIDGET_KEYS}
    ss.ve_ready = True


def _reset() -> None:
    ss = st.session_state
    for k in [k for k in ss.keys() if k.startswith("ve_")]:
        del ss[k]
    storage.delete(KEY)


def _tambah_ruang() -> None:
    ss = st.session_state
    r = ss.ve_ruang
    baru = pd.DataFrame([{
        calc.C_LANTAI: r[calc.C_LANTAI].iloc[-1] if len(r) else "Lantai Satu",
        calc.C_NAMA: f"Ruangan {len(r) + 1}", calc.C_JENIS: calc.JENIS_HUNIAN, calc.C_METODE: "Alami",
        calc.C_HADAP: "Ruang luar", calc.C_JML: 0.0, calc.C_VP: 0.0, calc.C_VL: 0.0,
        calc.C_RP: 0.0, calc.C_RL: 0.0, calc.C_T: calc.TINGGI_BAWAAN, calc.C_Q: 0.0,
    }])
    ss.ve_ruang = calc.normalisasi_ruang(pd.concat([r, baru], ignore_index=True))
    ss.ve_ver += 1


def _hapus_ruang() -> None:
    ss = st.session_state
    if len(ss.ve_ruang) <= 1:
        return
    idx = int(ss.get("ve_hapus", 0))
    ss.ve_ruang = ss.ve_ruang.drop(index=idx).reset_index(drop=True)
    ss.ve_hapus = 0
    ss.ve_ver += 1


def _proyek() -> dict:
    ss = st.session_state
    return {"pekerjaan": ss.ve_pekerjaan, "lokasi": ss.ve_lokasi, "tahun": ss.ve_tahun, "item": ss.ve_item}


# ------------------------------------------------------------------ halaman
def render() -> None:
    pesan_koreksi = _init()
    ss = st.session_state

    st.subheader("Kebutuhan Ventilasi")
    st.caption("Periksa kecukupan bukaan alami dan debit exhaust per ruang. Hasil dilengkapi alasan status "
               "serta tindakan yang dapat ditindaklanjuti.")
    for m in pesan_koreksi:
        st.warning(m)

    t_hitung, t_rekap, t_sum = st.tabs(["📝 Perhitungan", "📊 Rekap", "📋 Summary"])

    with t_hitung:
        section_title("1. Dasar Standar & Parameter")
        st.markdown(f"{BADGE} **Dasar rasio ventilasi alami**", unsafe_allow_html=True)
        p1, p2 = st.columns([2, 1])
        p1.selectbox("Rasio minimum bukaan terhadap luas lantai", calc.DASAR_OPSI, key="ve_dasar",
                     help="Bawaan 5% sesuai teks SNI 03-6572-2001 pasal 4.3.2. Pilih 10% bila ingin acuan lebih ketat.")
        if ss.ve_dasar == calc.DASAR_KUSTOM:
            p2.number_input("Rasio kustom (%)", min_value=KUSTOM_MIN, max_value=KUSTOM_MAKS, step=0.5,
                            key="ve_kustom")
        else:
            p2.metric("Rasio yang dipakai", f"{fmt_id(calc.rasio_dari(ss.ve_dasar, ss.ve_kustom) * 100, 1)}%")
        rasio = calc.rasio_dari(ss.ve_dasar, ss.ve_kustom)

        with st.expander("Tabel ACH minimum ventilasi mekanis (bisa diedit)"):
            st.caption("Nilai bawaan mengikuti SNI 03-6572-2001 Tabel 4.4.1. Nilai 0 berarti SNI tidak memberi acuan.")
            ach_ed = st.data_editor(
                ss.ve_ach, hide_index=True, num_rows="fixed", disabled=[calc.C_ACH_JENIS], key="ve_ach_ed",
                column_config={
                    calc.C_ACH_JENIS: st.column_config.TextColumn("Jenis ruang"),
                    calc.C_ACH: st.column_config.NumberColumn(
                        "ACH minimum (kali/jam)", min_value=0, step=1, format="%g"),
                },
            )
            ss.ve_ach = calc.normalisasi_ach(ach_ed)
            for jenis in calc.JENIS:
                st.caption(f"• {jenis}: {calc.ACH_KET[jenis]}")

        section_title("2. Data Ruangan")
        st.markdown(f"{BADGE} Isi dimensi, metode ventilasi, bukaan, dan debit exhaust bila digunakan.",
                    unsafe_allow_html=True)
        ruang_ed = st.data_editor(
            ss.ve_ruang, hide_index=True, num_rows="fixed", key=f"ve_ruang_ed_{ss.ve_ver}",
            column_config={
                calc.C_LANTAI: st.column_config.TextColumn("Lantai", width="small", help="Pengelompokan tabel hasil"),
                calc.C_NAMA: st.column_config.TextColumn("Nama Ruangan", width="medium"),
                calc.C_JENIS: st.column_config.SelectboxColumn(
                    "Jenis", options=calc.JENIS, required=True, width="medium"),
                calc.C_METODE: st.column_config.SelectboxColumn(
                    "Metode", options=calc.METODE, required=True),
                calc.C_HADAP: st.column_config.SelectboxColumn(
                    "Bukaan menghadap", options=calc.HADAP, required=True,
                    help="SNI 4.3.2 b: ruang luar / teras terbuka, atau ruang bersebelahan (pasal 4.3.3)"),
                calc.C_JML: st.column_config.NumberColumn("Jml bukaan", min_value=0, step=1, format="%g"),
                calc.C_VP: st.column_config.NumberColumn("P bukaan (m)", min_value=0, step=0.05, format="%g"),
                calc.C_VL: st.column_config.NumberColumn("L bukaan (m)", min_value=0, step=0.05, format="%g"),
                calc.C_RP: st.column_config.NumberColumn("P ruang (m)", min_value=0, step=0.05, format="%g"),
                calc.C_RL: st.column_config.NumberColumn("L ruang (m)", min_value=0, step=0.05, format="%g"),
                calc.C_T: st.column_config.NumberColumn(
                    "T plafon (m)", min_value=0, step=0.1, format="%g",
                    help="Dipakai untuk volume ruang pada hitungan exhaust"),
                calc.C_Q: st.column_config.NumberColumn(
                    "Q exhaust (m³/menit)", min_value=0, step=0.5, format="%g",
                    help="Debit exhaust dari spesifikasi pabrikan"),
            },
        )
        ss.ve_ruang = calc.normalisasi_ruang(ruang_ed)
        a1, a2, a3 = st.columns([1, 2, 1])
        a1.button("➕ Tambah ruangan", on_click=_tambah_ruang)
        a2.selectbox(
            "Hapus ruangan", options=list(range(len(ss.ve_ruang))),
            format_func=lambda i: (
                f"{i + 1}. {ss.ve_ruang.loc[i, calc.C_LANTAI]} - "
                f"{ss.ve_ruang.loc[i, calc.C_NAMA] or '(kosong)'}"
            ),
            key="ve_hapus", label_visibility="collapsed",
        )
        a3.button("🗑️ Hapus ruangan", on_click=_hapus_ruang)
        st.caption("Av = jumlah × P bukaan × L bukaan. Ar = P ruang × L ruang. "
                   "Hitungan luas bukaan hanya mencakup bagian yang benar-benar dapat mengalirkan udara.")

    # ---- hasil dihitung dari masukan yang sama untuk seluruh tab
    h = calc.hitung(ss.ve_ruang, rasio, ss.ve_ach)
    banding = calc.bandingkan(ss.ve_ruang, ss.ve_ach)

    with t_hitung:
        components.html(
            render_laporan(h, None, "hitung"),
            height=tinggi_laporan(h, "hitung"), scrolling=True,
        )
        with st.expander("Rumus dan cara membaca hasil"):
            st.latex(r"A_v = n \times P_v \times L_v;\qquad A_r = P_r \times L_r")
            st.latex(rf"A_{{v,min}} = {fmt_id(rasio * 100, 1)}\% \times A_r;\qquad ACH = \frac{{Q_{{exhaust}} \times 60}}{{A_r \times T}}")
            st.caption("Rasio bukaan digunakan untuk pemeriksaan awal. Ruang yang mengambil udara dari ruang "
                       "bersebelahan perlu pemeriksaan bukaan gabungan; untuk kompartemen sanitasi gunakan "
                       "bukaan luar atau exhaust.")

    with t_rekap:
        components.html(
            render_laporan(h, None, "rekap", banding),
            height=tinggi_laporan(h, "rekap"), scrolling=True,
        )

    with t_sum:
        with st.expander("Identitas proyek"):
            p = st.columns(2)
            p[0].text_input("Pekerjaan", key="ve_pekerjaan")
            p[1].text_input("Lokasi", key="ve_lokasi")
            p[0].text_input("Tahun", key="ve_tahun")
            p[1].text_input("Item Pekerjaan", key="ve_item")
        proyek = _proyek()
        components.html(
            render_laporan(h, proyek, "ringkasan", banding),
            height=tinggi_laporan(h, "ringkasan"), scrolling=True,
        )
        section_title("8. Unduh / Ekspor")
        entri = {"dasar": ss.ve_dasar, "rasio": rasio, "ach": ss.ve_ach, "ruang": ss.ve_ruang, "banding": banding}
        ekspor_ui.ekspor_ventilasi(proyek, entri, h)
        with st.expander("Catatan koreksi terhadap Excel acuan"):
            for k in KOREKSI:
                st.markdown(f"- {k}")

    # ---- simpan otomatis
    ss.ve_cache = {k: ss[k] for k in WIDGET_KEYS}
    tersimpan = storage.save(KEY, {
        "proyek": _proyek(), "dasar": ss.ve_dasar, "kustom": float(ss.ve_kustom),
        "ach": storage.df_to_records(ss.ve_ach), "ruang": storage.df_to_records(ss.ve_ruang),
    })
    info_simpan(tersimpan, KEY)
    st.button("↺ Reset ke data awal", on_click=_reset, key="ve_reset")
