"""Perhitungan kebutuhan APAR (sheet 'Apar') - tanpa Streamlit.

Aturan hitung:
  Cakupan 1 APAR      = min(luas lantai maks per APAR, rating-A x luas lantai per unit A)
  Jumlah APAR/lantai  = luas lantai / cakupan, dibulatkan ke atas (minimal 1 tiap lantai)
  Jarak tempuh dipakai = yang terkecil antara tabel dan batas regulasi
"""
from __future__ import annotations

import math

import pandas as pd

KELAS = ["Ringan", "Sedang", "Berat"]
C_KELAS = "Kelas"
C_MINA = "Daya padam min (A)"
C_PERA = "Luas per unit A (m²)"
C_MAKS = "Luas maks per APAR (m²)"
C_JARAK = "Jarak tempuh maks (m)"
KOLOM_TABEL = [C_KELAS, C_MINA, C_PERA, C_MAKS, C_JARAK]

# (daya padam min [A], luas per unit A [m2], luas maks per APAR [m2], jarak tempuh [m])
# 278/139/93 m2 = 3000/1500/1000 ft2 (tabel kelas A, NFPA 10 / SNI). Luas maks per APAR
# memakai 100 m2 sesuai Excel acuan (NFPA 10 asli: 1.045 m2, jadi 100 m2 lebih ketat).
TABEL_BAWAAN = {
    "Ringan": (2, 278, 100, 23),
    "Sedang": (2, 139, 100, 23),
    "Berat": (4, 93, 100, 23),
}
JARAK_REGULASI_BAWAAN = 15.0

C_LANTAI, C_LUAS = "Lantai", "Luas (m²)"
LUAS_BAWAAN = 60.0

JENIS = {
    "APAR DCP": "umumnya kelas A, B, C (tipe serbaguna ABC; tipe BC tidak untuk kelas A)",
    "APAR Foam": "umumnya kelas A, B",
    "APAR Air": "umumnya kelas A saja (tidak untuk listrik / cairan mudah terbakar)",
    "APAR CO2": "umumnya kelas B, C (tidak punya rating A)",
}
JENIS_BAWAAN = "APAR DCP"
KAPASITAS_BAWAAN = "3 kg"
RATING_BAWAAN = "2A:10BC"
KELAS_BAWAAN = "Ringan"

PROYEK_BAWAAN = {
    "pekerjaan": "PERENCANAAN PEMBANGUNAN RUMAH TINGGAL 2 LANTAI TYPE 55",
    "lokasi": "KOTA MAKASSAR",
    "tahun": "2026",
    "item": "PERHITUNGAN KEBUTUHAN APAR PADA BANGUNAN",
}

CATATAN_TABEL = [
    "Sampai dengan 2 APAR jenis air, setiap kemampuan 1-A dapat digunakan untuk memenuhi "
    "persyaratan kemampuan satu APAR 2-A.",
    "Dua APAR jenis air dengan kapasitas 9 liter (2½ gallon) dapat digunakan untuk memenuhi "
    "persyaratan 1 APAR dengan kemampuan 4-A.",
    "Ukuran minimal APAR untuk bahaya kebakaran terdaftar harus disediakan dengan dasar tabel di atas. "
    "APAR harus ditempatkan sehingga jarak tempuh maksimumnya tidak melebihi seperti ditentukan "
    "dalam tabel yang dipakai.",
]


# ---------------------------------------------------------------- data bawaan
def tabel_bawaan() -> pd.DataFrame:
    rows = [[k, *TABEL_BAWAAN[k]] for k in KELAS]
    return pd.DataFrame(rows, columns=KOLOM_TABEL).astype(
        {C_MINA: float, C_PERA: float, C_MAKS: float, C_JARAK: float}
    )


def lantai_bawaan() -> pd.DataFrame:
    return pd.DataFrame([{C_LANTAI: "Lantai 1", C_LUAS: LUAS_BAWAAN}])


# ---------------------------------------------------------------- normalisasi
def normalisasi_tabel(df: pd.DataFrame | None) -> pd.DataFrame:
    """Selalu 3 baris (Ringan, Sedang, Berat); nilai kosong / <= 0 diganti nilai bawaan."""
    if df is None or len(df) == 0 or C_KELAS not in df.columns:
        return tabel_bawaan()
    dasar = {r[C_KELAS]: r for _, r in df.iterrows()}
    rows = []
    for k in KELAS:
        r = dasar.get(k)
        baris = [k]
        for i, kol in enumerate(KOLOM_TABEL[1:]):
            bawaan = float(TABEL_BAWAAN[k][i])
            try:
                v = float(r[kol]) if r is not None else bawaan
            except (TypeError, ValueError):
                v = bawaan
            baris.append(v if v > 0 and v == v else bawaan)
        rows.append(baris)
    return pd.DataFrame(rows, columns=KOLOM_TABEL)


def normalisasi_lantai(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return lantai_bawaan()
    df = df.reindex(columns=[C_LANTAI, C_LUAS]).copy()
    df[C_LANTAI] = df[C_LANTAI].fillna("").astype(str)
    df[C_LUAS] = pd.to_numeric(df[C_LUAS], errors="coerce").fillna(0).clip(lower=0).astype(float)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------- rating
def rating_a(teks) -> float:
    """Ambil angka rating-A dari teks seperti '2A:10BC'.

    Aturan sama dengan rumus Excel: buang '-' dan spasi, ambil teks sebelum huruf A pertama
    sebagai angka. Tanpa huruf A / bukan angka -> 0.
    """
    s = str(teks or "").replace("-", "").replace(" ", "")
    i = s.upper().find("A")
    if i <= 0:
        return 0.0
    try:
        return float(s[:i].replace(",", "."))
    except ValueError:
        return 0.0


def bulat_atas(x: float) -> int:
    """Pembulatan ke atas dengan toleransi galat desimal (sama dengan ROUNDUP(ROUND(x,6),0))."""
    return int(math.ceil(round(x, 6)))


# ---------------------------------------------------------------- perhitungan
def hitung(lantai: pd.DataFrame, kelas: str, rating: str, jarak_regulasi: float,
           tabel: pd.DataFrame) -> dict:
    tabel = normalisasi_tabel(tabel)
    lantai = normalisasi_lantai(lantai)
    kelas = kelas if kelas in KELAS else KELAS_BAWAAN
    t = tabel[tabel[C_KELAS] == kelas].iloc[0]
    min_a, per_a, maks, jarak_tabel = (float(t[C_MINA]), float(t[C_PERA]),
                                       float(t[C_MAKS]), float(t[C_JARAK]))

    a = rating_a(rating)
    cakupan_rating = a * per_a
    cakupan = min(maks, cakupan_rating) if a > 0 else 0.0
    pembatas = "rating APAR" if (a > 0 and cakupan_rating < maks) else "luas lantai maksimum per APAR"
    reg = float(jarak_regulasi or 0)
    jarak = min(jarak_tabel, reg) if reg > 0 else jarak_tabel

    baris, total, bisa = [], 0, cakupan > 0
    for _, r in lantai.iterrows():
        luas = float(r[C_LUAS])
        rasio = luas / cakupan if cakupan > 0 else 0.0
        if luas <= 0:
            jumlah = 0
        elif cakupan > 0:
            jumlah = max(1, bulat_atas(rasio))
        else:
            jumlah = None
        baris.append({"lantai": r[C_LANTAI], "luas": luas, "rasio": rasio, "jumlah": jumlah})
        if jumlah is not None:
            total += jumlah

    if a <= 0:
        status = "Tidak ada rating A"
    elif a >= min_a:
        status = "Memenuhi"
    else:
        status = "Kurang dari minimum"

    catatan, info = [], []
    if a <= 0:
        catatan.append(f"Rating '{rating}' tidak memuat rating A, sehingga tidak berlaku untuk kebakaran "
                       "Kelas A dan jumlah APAR tidak dapat dihitung. Gunakan APAR yang memiliki rating A "
                       "(contoh DCP serbaguna 2A:10BC).")
    elif a < min_a:
        catatan.append(f"Rating {a:g}-A di bawah daya padam minimum {min_a:g}-A untuk hunian bahaya kebakaran "
                       f"{kelas.lower()}. Gunakan APAR dengan rating minimal {min_a:g}-A.")
    if cakupan > 0:
        info.append(f"Cakupan per APAR {cakupan:g} m², dibatasi oleh {pembatas}.")
    if 0 < reg < jarak_tabel:
        info.append(f"Jarak tempuh yang dipakai {jarak:g} m: batas regulasi {reg:g} m lebih ketat "
                    f"daripada tabel ({jarak_tabel:g} m).")

    return {
        "kelas": kelas, "min_a": min_a, "per_a": per_a, "maks": maks, "jarak_tabel": jarak_tabel,
        "rating_a": a, "cakupan_rating": cakupan_rating, "cakupan": cakupan, "pembatas": pembatas,
        "jarak_pakai": jarak, "status_rating": status, "memenuhi": status == "Memenuhi",
        "lantai": baris, "total_luas": float(lantai[C_LUAS].sum()),
        "total": total if bisa else None, "catatan": catatan, "info": info,
    }


# ---------------------------------------------------------------- muat / simpan
def muat_state(saved: dict | None, saved_listrik: dict | None = None) -> dict:
    """Gabungkan data tersimpan dengan bawaan. Data proyek bawaan diambil dari modul listrik."""
    saved = saved or {}
    dasar = dict(PROYEK_BAWAAN)
    for k in ("pekerjaan", "lokasi", "tahun"):
        v = ((saved_listrik or {}).get("proyek") or {}).get(k)
        if v:
            dasar[k] = v
    proyek = {**dasar, **(saved.get("proyek") or {})}
    try:
        jarak = float(saved.get("jarak", JARAK_REGULASI_BAWAAN))
    except (TypeError, ValueError):
        jarak = JARAK_REGULASI_BAWAAN
    return {
        "proyek": proyek,
        "kelas": saved.get("kelas") if saved.get("kelas") in KELAS else KELAS_BAWAAN,
        "jenis": saved.get("jenis") if saved.get("jenis") in JENIS else JENIS_BAWAAN,
        "kapasitas": str(saved.get("kapasitas", KAPASITAS_BAWAAN)),
        "rating": str(saved.get("rating", RATING_BAWAAN)),
        "jarak": jarak,
        "tabel": normalisasi_tabel(pd.DataFrame(saved["tabel"]) if saved.get("tabel") else None),
        "lantai": normalisasi_lantai(pd.DataFrame(saved["lantai"]) if saved.get("lantai") else None),
    }
