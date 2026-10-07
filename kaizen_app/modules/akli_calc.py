"""Tabel AKLI (daya tersedia, MCB, ukuran kabel) + aturan kabel otomatis.

Tanpa Streamlit supaya mudah diuji.

Aturan kabel otomatis untuk satu sirkuit (berdasarkan NAMA sirkuit + MCB):
  - nama mengandung stk / stopkontak / kontak / ac / pompa / spare  -> inti sesuai tabel (3)
  - nama mengandung lampu / lamp / dl / penerangan                  -> 2 inti
  - jika keduanya ada, stop kontak yang dipakai (3 inti, lebih aman)
  - ukuran mm2 diambil dari tabel AKLI: MCB sama, atau MCB terdekat di atasnya
  - BEBAN yang menentukan MCB: dipilih baris AKLI terkecil yang kapasitas
    Watt (PF 0,8)-nya cukup untuk beban sirkuit, lalu MCB dan kabel mengikuti baris itu
  - MCB Manual (opsional) berlaku sebagai MCB minimum; jika beban melebihi
    kapasitasnya, MCB dinaikkan otomatis
"""
from __future__ import annotations

import re

import pandas as pd

COLS = [
    "Fasa", "VA", "VA Pembulatan", "kVA", "Watt (PF 0,8)", "Gol",
    "MCB (A)", "Tegangan (V)", "Tipe Kabel", "Inti", "Ukuran (mm²)",
]
NUM = ["Fasa", "VA", "VA Pembulatan", "kVA", "Watt (PF 0,8)", "MCB (A)",
       "Tegangan (V)", "Inti", "Ukuran (mm²)"]

POLA_STOPKONTAK = re.compile(
    r"\b(stk|stopkontak|stop\s*kontak|kontak|ac|pompa|pump|spare|cadangan)\b", re.I
)
POLA_LAMPU = re.compile(r"\b(lampu|lamp|dl|downlight|penerangan|lighting)\b", re.I)

# MCB terkecil yang dipakai bila MCB Manual kosong (praktik rumah tinggal; ubah bila perlu)
MCB_MINIMAL = 4

# status hasil kabel otomatis
OK_LAMPU, OK_STK, TIDAK_DIKENAL, DI_LUAR, MCB_KOSONG = (
    "lampu", "stk", "tidak_dikenali", "di_luar_tabel", "mcb_kosong",
)


def default_tabel() -> pd.DataFrame:
    satu = [  # VA, kVA, Watt, MCB, mm2
        (450, 0.45, 360, 2, 2.5), (900, 0.9, 720, 4, 2.5),
        (1300, 1.3, 1040, 6, 2.5), (2200, 2.2, 1760, 10, 4),
        (3500, 3.5, 2800, 16, 4), (4400, 4.4, 3520, 20, 4),
        (5500, 5.5, 4400, 25, 4), (7700, 7.7, 6160, 35, 6),
        (11000, 11, 8800, 50, 6), (13900, 13.9, 11120, 63, 10),
    ]
    tiga = [  # VA, rounded, kVA, Watt, Gol, MCB, mm2
        (3949, 3900, 3.9, 3159, "TR", 6, 4), (6582, 6600, 6.6, 5265, "TR", 10, 4),
        (10531, 10600, 10.6, 8425, "TR", 16, 6), (13164, 13200, 13.2, 10531, "TR", 20, 10),
        (16454, 16500, 16.5, 13164, "TR", 25, 10), (23036, 23000, 23, 18429, "TR", 35, 16),
        (32909, 33000, 33, 26327, "TR", 50, 16), (41465, 41500, 41.5, 33172, "TR", 63, 25),
        (52654, 53000, 53, 42123, "TR", 80, 35), (65818, 66000, 66, 52654, "TR", 100, 50),
        (82272, 82500, 82.5, 65818, "TR", 125, 50), (105309, 105000, 105, 84247, "TR", 160, 70),
        (131636, 131000, 131, 105309, "TR", 200, 95), (148090, 147000, 147, 118472, "TR", 225, 95),
        (164545, 164000, 164, 131636, "TR", 250, 120), (197454, 197000, 197, 157963, "TR", 300, 150),
        (233654, 233000, 233, 186923, "TM", 355, 150), (279726, 279000, 279, 223781, "TM", 425, 240),
    ]
    rows = []
    for va, kva, w, mcb, mm in satu:
        rows.append([1, va, None, kva, w, "TR", mcb, 220, "NYY / NYM", 3, mm])
    for va, rd, kva, w, gol, mcb, mm in tiga:
        rows.append([3, va, rd, kva, w, gol, mcb, 380, "NYY / NYFGBY", 4, mm])
    return normalisasi(pd.DataFrame(rows, columns=COLS))


def normalisasi(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return default_tabel()
    df = df.reindex(columns=COLS).copy()
    for c in NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ("Gol", "Tipe Kabel"):
        df[c] = df[c].fillna("").astype(str)
    return df.reset_index(drop=True)


def muat(saved: dict | None) -> pd.DataFrame:
    if saved and saved.get("tabel"):
        return normalisasi(pd.DataFrame(saved["tabel"]))
    return default_tabel()


# ------------------------------------------------------------------ pencarian
def cari_baris(tabel: pd.DataFrame, mcb: float, fasa: int = 1, watt_min: float = 0.0):
    """Baris AKLI pertama dengan MCB >= mcb dan kapasitas Watt >= watt_min.

    None jika tidak ada. mcb <= 0 berarti tanpa batas bawah MCB."""
    t = tabel[(tabel["Fasa"] == fasa) & tabel["MCB (A)"].notna()
              & tabel["Ukuran (mm²)"].notna()]
    if watt_min and watt_min > 0:
        t = t[t["Watt (PF 0,8)"].notna() & (t["Watt (PF 0,8)"] >= watt_min)]
    t = t.sort_values("MCB (A)")
    cocok = t[t["MCB (A)"] >= max(float(mcb or 0), 0.0)]
    return None if cocok.empty else cocok.iloc[0]


def deteksi_jenis(nama: str) -> str | None:
    nama = nama or ""
    if POLA_STOPKONTAK.search(nama):
        return OK_STK
    if POLA_LAMPU.search(nama):
        return OK_LAMPU
    return None


def fmt_kabel(inti: int, mm2: float) -> str:
    return f"{int(inti)}x{mm2:g} mm²".replace(".", ",")


def pilih_sirkuit(nama: str, mcb_manual: float, beban_w: float,
                  tabel: pd.DataFrame, fasa: int = 1, mcb_min: float = MCB_MINIMAL) -> dict:
    """Tentukan MCB pakai, kapasitas, dan kabel untuk satu sirkuit.

    mcb_manual : MCB manual (0 = kosong -> dipilih dari beban, minimal mcb_min)
    beban_w    : beban sirkuit dalam Watt
    Return dict: teks, status, mcb_pakai, kapasitas, mcb_dasar, kap_dasar
    """
    manual = float(mcb_manual or 0)
    beban_w = float(beban_w or 0)
    batas_bawah = manual if manual > 0 else float(mcb_min)
    dasar = cari_baris(tabel, manual, fasa) if manual > 0 else None   # menurut MCB manual saja
    baris = cari_baris(tabel, batas_bawah, fasa, watt_min=beban_w)    # sesuai beban
    if baris is None:
        return {"teks": "", "status": DI_LUAR, "mcb_pakai": manual, "kapasitas": 0.0,
                "mcb_dasar": None if dasar is None else float(dasar["MCB (A)"]),
                "kap_dasar": None}

    jenis = deteksi_jenis(nama)
    mm2 = float(baris["Ukuran (mm²)"])
    if jenis == OK_LAMPU:
        teks, status = fmt_kabel(2, mm2), OK_LAMPU
    else:
        inti = int(baris["Inti"]) if pd.notna(baris["Inti"]) else 3
        teks = fmt_kabel(inti, mm2)
        status = OK_STK if jenis == OK_STK else TIDAK_DIKENAL  # cadangan: 3 inti, ditandai
    return {
        "teks": teks, "status": status,
        "mcb_pakai": float(baris["MCB (A)"]),
        "kapasitas": float(baris["Watt (PF 0,8)"]) if pd.notna(baris["Watt (PF 0,8)"]) else 0.0,
        "mcb_dasar": None if dasar is None else float(dasar["MCB (A)"]),
        "kap_dasar": None if dasar is None or pd.isna(dasar["Watt (PF 0,8)"])
        else float(dasar["Watt (PF 0,8)"]),
    }


def kabel_otomatis(nama: str, mcb: float, tabel: pd.DataFrame, fasa: int = 1) -> tuple[str, str]:
    """Versi lama (tanpa beban): hanya menurut MCB. Return (teks kabel, status)."""
    if not mcb or mcb <= 0:
        return "", MCB_KOSONG
    r = pilih_sirkuit(nama, mcb, 0.0, tabel, fasa)
    return r["teks"], r["status"]