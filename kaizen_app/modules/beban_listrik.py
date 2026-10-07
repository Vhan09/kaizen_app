"""Modul 1 - Perhitungan Kebutuhan Listrik (sheet 'SLD RUCON')."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from modules import akli
from modules import beban_listrik_calc as calc
from modules import kabel_induk
from modules import standar_listrik as std
from modules.beban_listrik_html import (
    catatan_html, data_sistem_html, header_proyek_html, tabel_html,
)
from utils import storage
from utils.formatting import fmt_id
from utils.theme import section_title

KEY = "beban_listrik"
BADGE = '<span class="badge-y">INPUT</span>'

# Kotak isian (widget) yang nilainya harus selamat saat pindah menu.
# Streamlit menghapus nilai widget yang tidak digambar pada satu putaran halaman,
# jadi nilainya kita simpan juga di bl_cache lalu dipulihkan.
WIDGET_KEYS = [
    "bl_pekerjaan", "bl_lokasi", "bl_tahun", "bl_item",
    "bl_v", "bl_pf", "bl_fp",
    "bl_grounding", "bl_resg", "bl_prot_tipe", "bl_prot_ma",
]

# batas wajar parameter sistem: (min, maks, nilai standar, nama)
BATAS = {
    "bl_v": (100.0, 1000.0, 220.0, "Tegangan sistem (V)"),
    "bl_pf": (0.5, 1.0, 0.8, "Faktor daya (PF)"),
    "bl_fp": (1.0, 3.0, 1.25, "Faktor beban puncak"),
}


# ------------------------------------------------------------------ state
def _sanitasi() -> list[str]:
    """Kembalikan parameter yang tidak wajar (mis. 1 V sisa data rusak) ke nilai standar."""
    ss = st.session_state
    pesan = []
    for k, (lo, hi, standar, nama) in BATAS.items():
        try:
            v = float(ss.get(k))
            ok = lo <= v <= hi
        except (TypeError, ValueError):
            v, ok = None, False
        if ok:
            ss[k] = v
        else:
            pesan.append(f"{nama} = {ss.get(k)} tidak wajar (batas {lo:g}-{hi:g}), "
                         f"dikembalikan ke {standar:g}. Silakan cek lagi.")
            ss[k] = standar
    return pesan


def _init() -> list[str]:
    ss = st.session_state
    if "bl_ready" not in ss:
        _isi_awal()
    # pulihkan nilai kotak isian yang terhapus karena pindah menu
    for k in WIDGET_KEYS:
        if k not in ss:
            ss[k] = ss.bl_cache[k]
    return _sanitasi()


def _isi_awal() -> None:
    ss = st.session_state
    d = calc.muat_state(storage.load(KEY))
    p, s = d["proyek"], d["sistem"]
    ss.bl_pekerjaan, ss.bl_lokasi = p["pekerjaan"], p["lokasi"]
    ss.bl_tahun, ss.bl_item = p["tahun"], p["item"]
    ss.bl_v, ss.bl_pf, ss.bl_fp = s["tegangan"], s["pf"], s["faktor_puncak"]
    ss.bl_grounding = s["grounding"] if s["grounding"] in std.GROUNDING else std.GROUNDING_DEFAULT
    ss.bl_resg = s["res_grounding"] if s["res_grounding"] in std.RES_OPSI else std.res_default(ss.bl_grounding)
    tipe, ma = std.parse_proteksi(s.get("proteksi"))
    ss.bl_prot_tipe = s.get("proteksi_tipe") if s.get("proteksi_tipe") in std.PROTEKSI_TIPE else tipe
    ss.bl_prot_ma = s.get("proteksi_ma") if s.get("proteksi_ma") in std.PROTEKSI_MA else ma
    ss.bl_beban = d["beban"]
    ss.bl_sirkuit, _ = calc.isi_kabel(d["sirkuit"], akli.ambil_tabel(), d["beban"])
    ss.bl_ver = 0
    ss.bl_verb = 0
    ss.bl_hapus = 0
    ss.bl_hapus_b = 0
    ss.bl_cache = {k: ss[k] for k in WIDGET_KEYS}
    ss.bl_ready = True


def _reset() -> None:
    ss = st.session_state
    for k in [k for k in ss.keys() if k.startswith("bl_")]:
        del ss[k]
    storage.delete(KEY)


def _tambah_beban() -> None:
    """Tambah jenis beban (armature) baru + kolom jumlahnya di tabel sirkuit."""
    ss = st.session_state
    b = ss.bl_beban
    baru = pd.DataFrame([{
        calc.COL_ID: int(b[calc.COL_ID].max()) + 1 if len(b) else 1,
        "Nama Beban": f"Armature {len(b) + 1}",
        "Watt": 0.0,
    }])
    ss.bl_beban = calc.normalisasi_beban(pd.concat([b, baru], ignore_index=True))
    ss.bl_sirkuit, _ = calc.isi_kabel(ss.bl_sirkuit, akli.ambil_tabel(), ss.bl_beban)
    ss.bl_verb += 1
    ss.bl_ver += 1


def _hapus_beban() -> None:
    """Hapus jenis beban terpilih + kolom jumlahnya di tabel sirkuit."""
    ss = st.session_state
    if len(ss.bl_beban) <= 1:
        return
    idx = int(ss.get("bl_hapus_b", 0))
    ss.bl_beban = calc.normalisasi_beban(ss.bl_beban.drop(index=idx).reset_index(drop=True))
    ss.bl_sirkuit, _ = calc.isi_kabel(ss.bl_sirkuit, akli.ambil_tabel(), ss.bl_beban)
    ss.bl_hapus_b = 0
    ss.bl_verb += 1
    ss.bl_ver += 1


def _tambah_sirkuit() -> None:
    ss = st.session_state
    n = len(ss.bl_sirkuit) + 1
    baru = pd.DataFrame([calc.baris_sirkuit(f"SIRKUIT {n}")])
    ss.bl_sirkuit, _ = calc.isi_kabel(
        pd.concat([ss.bl_sirkuit, baru], ignore_index=True),
        akli.ambil_tabel(), ss.bl_beban,
    )
    ss.bl_ver += 1


def _hapus_sirkuit() -> None:
    ss = st.session_state
    if len(ss.bl_sirkuit) <= 1:
        return
    idx = int(ss.bl_hapus)
    ss.bl_sirkuit = ss.bl_sirkuit.drop(index=idx).reset_index(drop=True)
    ss.bl_hapus = 0
    ss.bl_ver += 1


def _sync_sirkuit() -> None:
    """Dipanggil saat sel diedit: terapkan edit lebih dulu, lalu hitung kabel AKLI,
    sehingga kolom Kabel di editor langsung ikut berubah."""
    ss = st.session_state
    delta = ss.get(f"bl_sirkuit_ed_{ss.bl_ver}")
    if not isinstance(delta, dict):
        return
    df = ss.bl_sirkuit.copy()
    for r, perubahan in delta.get("edited_rows", {}).items():
        for kolom, nilai in perubahan.items():
            if kolom in df.columns and int(r) < len(df):
                df.at[int(r), kolom] = nilai
    ss.bl_sirkuit, _ = calc.isi_kabel(df, akli.ambil_tabel(), ss.bl_beban)


def _pilih_grounding() -> None:
    """Saat sistem grounding diganti, resistansi maks ikut terisi sesuai standar."""
    ss = st.session_state
    ss.bl_resg = std.res_default(ss.bl_grounding)


def _proyek() -> dict:
    ss = st.session_state
    return {
        "pekerjaan": ss.bl_pekerjaan, "lokasi": ss.bl_lokasi,
        "tahun": ss.bl_tahun, "item": ss.bl_item,
    }


def _sistem() -> dict:
    ss = st.session_state
    return {
        "tegangan": ss.bl_v, "pf": ss.bl_pf, "faktor_puncak": ss.bl_fp,
        "grounding": ss.bl_grounding, "res_grounding": ss.bl_resg,
        "proteksi": std.teks_proteksi(ss.bl_prot_tipe, ss.bl_prot_ma),
        "proteksi_tipe": ss.bl_prot_tipe, "proteksi_ma": ss.bl_prot_ma,
    }


# ------------------------------------------------------------------ halaman
def render() -> None:
    pesan_koreksi = _init()
    ss = st.session_state

    st.title("⚡ Perhitungan Kebutuhan Listrik")
    st.caption("Analisa beban puncak penggunaan - kolom kuning diisi manual, sisanya otomatis.")
    for m in pesan_koreksi:
        st.warning(m)

    # ---- 1. Data proyek & sistem (input)
    section_title("1. Data Proyek & Sistem")
    st.markdown(f"{BADGE} Isi data proyek dan parameter sistem", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.text_input("Pekerjaan", key="bl_pekerjaan")
    c2.text_input("Lokasi", key="bl_lokasi")
    c1.text_input("Tahun", key="bl_tahun")
    c2.text_input("Item Pekerjaan", key="bl_item")

    s1, s2, s3 = st.columns(3)
    s1.number_input("Tegangan sistem (V)", min_value=100.0, max_value=1000.0, step=1.0, key="bl_v")
    s2.number_input("Faktor daya (PF)", min_value=0.5, max_value=1.0, step=0.05, key="bl_pf")
    s3.number_input("Faktor beban puncak", min_value=1.0, max_value=3.0, step=0.05, key="bl_fp")
    g1, g2, g3, g4 = st.columns(4)
    g1.selectbox(
        "Sistem grounding", list(std.GROUNDING.keys()),
        key="bl_grounding", on_change=_pilih_grounding,
    )
    g2.selectbox(
        "Resistansi grounding maks", std.RES_OPSI, key="bl_resg",
        help="Terisi otomatis sesuai sistem grounding, tetap bisa diganti",
    )
    g3.selectbox("Proteksi kebocoran", std.PROTEKSI_TIPE, key="bl_prot_tipe")
    g4.selectbox("Sensitivitas (mA)", std.PROTEKSI_MA, key="bl_prot_ma")
    st.caption(
        f"{std.GROUNDING[ss.bl_grounding]['ket']}  |  "
        f"{std.teks_proteksi(ss.bl_prot_tipe, ss.bl_prot_ma)}: {std.PROTEKSI_KET[ss.bl_prot_ma]}"
    )

    # ---- 2. Input beban
    section_title("2. Input Beban")
    st.markdown(f"{BADGE} **A. Jenis beban (armature) & daya (Watt)** - header kuning di Excel", unsafe_allow_html=True)
    beban_ed = st.data_editor(
        ss.bl_beban,
        hide_index=True,
        num_rows="fixed",
        key=f"bl_beban_ed_{ss.bl_verb}",
        column_config={
            calc.COL_ID: None,
            "Nama Beban": st.column_config.TextColumn("Nama Beban", help="Nama kolom beban"),
            "Watt": st.column_config.NumberColumn("Watt", min_value=0, step=1, format="%d"),
        },
    )
    ss.bl_beban = calc.normalisasi_beban(beban_ed)
    # watt beban berubah -> MCB & kabel ikut dihitung ulang sebelum tabel sirkuit digambar
    ss.bl_sirkuit, _ = calc.isi_kabel(ss.bl_sirkuit, akli.ambil_tabel(), ss.bl_beban)

    a1, a2, a3 = st.columns([1, 2, 1])
    a1.button("➕ Tambah armature", on_click=_tambah_beban)
    a2.selectbox(
        "Hapus armature",
        options=list(range(len(ss.bl_beban))),
        format_func=lambda i: f"{i + 1}. {ss.bl_beban.loc[i, 'Nama Beban'] or '(kosong)'}",
        key="bl_hapus_b",
        label_visibility="collapsed",
    )
    a3.button("🗑️ Hapus armature", on_click=_hapus_beban)

    st.markdown(f"{BADGE} **B. Jumlah beban per sirkuit**", unsafe_allow_html=True)
    labels = [
        (nm.strip() or f"Beban {i + 1}") for i, nm in enumerate(ss.bl_beban["Nama Beban"])
    ]
    qcols = calc.qcols_of(ss.bl_beban)
    cfg = {
        calc.COL_NAMA: st.column_config.TextColumn("Nama Sirkuit", width="medium"),
        calc.COL_GRUP: st.column_config.NumberColumn("No. Grup", min_value=1, step=1, format="%d"),
        calc.COL_MCB_MANUAL: st.column_config.NumberColumn(
            "MCB Manual", min_value=0, step=1, format="%d",
            help="Opsional. 0 = MCB dipilih otomatis dari beban (Tabel AKLI). "
                 "Isi bila ingin MCB minimum tertentu; naik otomatis jika beban melebihi.",
        ),
        # kolom hasil disembunyikan: detailnya ada di tabel "3. Hasil Perhitungan"
        calc.COL_MCB_PAKAI: None,
        calc.COL_KAP: None,
        calc.COL_KABEL: None,
        calc.COL_KABEL_MANUAL: None,
        calc.COL_LAIN: st.column_config.NumberColumn(
            "Lain-lain (W)", min_value=0, step=1, format="%d",
            help="Beban tetap manual, contoh spare 200 W",
        ),
    }
    for q, lb in zip(qcols, labels):
        cfg[q] = st.column_config.NumberColumn(lb, min_value=0, step=1, format="%d")

    sirkuit_ed = st.data_editor(
        ss.bl_sirkuit,
        hide_index=True,
        num_rows="fixed",
        column_config=cfg,
        key=f"bl_sirkuit_ed_{ss.bl_ver}",
        on_change=_sync_sirkuit,
    )
    ss.bl_sirkuit, catatan_kabel = calc.isi_kabel(
        sirkuit_ed, akli.ambil_tabel(), ss.bl_beban
    )
    st.caption("MCB dan kabel dipilih otomatis dari beban menurut Tabel AKLI (MCB Manual 0 = otomatis). "
               "Hasilnya ada di bagian 3.")

    k1, k2, k3 = st.columns([1, 2, 1])
    k1.button("➕ Tambah sirkuit", on_click=_tambah_sirkuit)
    k2.selectbox(
        "Hapus sirkuit",
        options=list(range(len(ss.bl_sirkuit))),
        format_func=lambda i: f"{i + 1}. {ss.bl_sirkuit.loc[i, calc.COL_NAMA]}",
        key="bl_hapus",
        label_visibility="collapsed",
    )
    k3.button("🗑️ Hapus terpilih", on_click=_hapus_sirkuit)

    # ---- 3. Hasil
    out = calc.hitung(ss.bl_beban, ss.bl_sirkuit, _sistem())

    section_title("3. Hasil Perhitungan")
    st.markdown(header_proyek_html(_proyek()), unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Load", f"{fmt_id(out['total_load'])} W")
    m2.metric("Beban Puncak", f"{fmt_id(out['va'])} VA")
    m3.metric("Arus Puncak", f"{fmt_id(out['ampere'], 2)} A")

    st.markdown("**Data Sistem**")
    st.markdown(data_sistem_html(_sistem()), unsafe_allow_html=True)
    st.markdown("**Tabel Perhitungan Kebutuhan Listrik**")
    induk = kabel_induk.saran(out["va"], akli.ambil_tabel())
    st.markdown(tabel_html(labels, out, _sistem(), induk), unsafe_allow_html=True)
    if catatan_kabel:
        with st.expander(f"Catatan penyesuaian MCB & kabel ({len(catatan_kabel)})"):
            for c in catatan_kabel:
                st.write(f"- {c}")
    st.markdown(catatan_html(out), unsafe_allow_html=True)

    grafik = pd.DataFrame(
        {"Load (W)": out["hasil"]["load"].to_numpy()},
        index=[
            f"{i + 1:02d} {nm}"
            for i, nm in enumerate(out["hasil"][calc.COL_NAMA])
        ],
    )
    st.markdown("**Load per sirkuit (W)**")
    st.bar_chart(grafik)

    # ---- simpan otomatis
    ss.bl_cache = {k: ss[k] for k in WIDGET_KEYS}
    storage.save(
        KEY,
        {
            "proyek": _proyek(),
            "sistem": _sistem(),
            "beban": storage.df_to_records(ss.bl_beban),
            "sirkuit": storage.df_to_records(ss.bl_sirkuit),
        },
    )
    st.caption("💾 Data tersimpan otomatis di folder data/")
    st.button("↺ Reset ke data awal", on_click=_reset)