"""Perhitungan beban listrik (sheet 'SLD RUCON').

Rumus mengikuti Excel:
    Load (R)  = sum(jumlah_beban x watt_beban) + lain-lain
    Amp       = Load / Tegangan
    KA        = Load / (Tegangan x PF)
    VA puncak = Total Load x Faktor puncak
    Ampere    = VA puncak / Tegangan
    Daya nyata= VA puncak x PF
"""
from __future__ import annotations

import pandas as pd

from modules import akli_calc

N_BEBAN_DEFAULT = 10
QCOLS = [f"q{i}" for i in range(1, N_BEBAN_DEFAULT + 1)]  # kolom bawaan (q1..q10)
COL_ID = "ID"  # penanda tetap tiap armature -> kolom jumlahnya bernama q<ID>
BEBAN_COLS = [COL_ID, "Nama Beban", "Watt"]
COL_NAMA, COL_GRUP, COL_MCB, COL_KABEL, COL_KABEL_MANUAL, COL_LAIN = (
    "Nama Sirkuit", "No. Grup", "MCB (A)", "Kabel", "Kabel Manual", "Lain-lain (W)",
)
# COL_MCB_MANUAL   = MCB manual (opsional, 0 = kosong -> dipilih otomatis dari beban)
# COL_MCB_PAKAI    = MCB final dari beban + tabel AKLI
# COL_MCB          = salinan MCB final, hanya untuk tabel hasil (bukan input)
# COL_KAP          = kapasitas Watt (PF 0,8) pada MCB final, dari tabel AKLI
# COL_KABEL        = hasil akhir (otomatis dari AKLI, atau Kabel Manual bila diisi)
COL_MCB_MANUAL = "MCB Manual"
COL_MCB_PAKAI, COL_KAP = "MCB Pakai (AKLI)", "Kapasitas (W)"
BASE_COLS = [COL_NAMA, COL_GRUP, COL_MCB_MANUAL, COL_MCB_PAKAI, COL_KAP, COL_KABEL, COL_KABEL_MANUAL]
TEXT_COLS = [COL_NAMA, COL_KABEL, COL_KABEL_MANUAL]
NUM_BASE = [COL_GRUP, COL_MCB_MANUAL, COL_MCB_PAKAI, COL_KAP]


def sirkuit_cols(qcols) -> list[str]:
    return BASE_COLS + list(qcols) + [COL_LAIN]


SIRKUIT_COLS = sirkuit_cols(QCOLS)  # susunan bawaan

PROYEK_DEFAULT = {
    "pekerjaan": "PERENCANAAN PEMBANGUNAN RUMAH TINGGAL 2 LANTAI TYPE 55",
    "lokasi": "KOTA MAKASSAR",
    "tahun": "2026",
    "item": "PERHITUNGAN PENENTUAN KWH PADA RUMAH DENGAN ANALISA BEBAN PUNCAK PENGGUNAAN",
}
SISTEM_DEFAULT = {
    "tegangan": 220.0,
    "pf": 0.8,
    "faktor_puncak": 1.25,
    "grounding": "TN-S/TT",
    "res_grounding": "< 5 Ohm",
    "proteksi": "ELCB 30 mA",
}

BEBAN_DEFAULT = [
    ("DL 6 W", 6), ("DL 9 W", 9), ("DL 12 W", 12), ("DL 3 W", 3),
    ("EXHAUST", 30), ("STK", 100), ("POMPA", 300),
    ("AC 1/2 PK", 390), ("AC 3/4 PK", 620), ("AC 1 PK", 1000),
]


# ---------------------------------------------------------------- default data
def default_beban() -> pd.DataFrame:
    df = pd.DataFrame(BEBAN_DEFAULT, columns=["Nama Beban", "Watt"]).astype({"Watt": float})
    df.insert(0, COL_ID, range(1, len(df) + 1))
    return df


def qcols_of(beban: pd.DataFrame | None) -> list[str]:
    """Nama kolom jumlah-beban pada tabel sirkuit, mengikuti ID armature."""
    if beban is None:
        return list(QCOLS)
    return [f"q{int(i)}" for i in normalisasi_beban(beban)[COL_ID]]


def baris_sirkuit(nama="", grup=1, mcb=0, manual="", q=None, lain=0, qcols=None) -> dict:
    """mcb = MCB manual (0 = otomatis dari beban); manual = Kabel Manual."""
    qcols = list(qcols) if qcols is not None else list(QCOLS)
    r = {COL_NAMA: nama, COL_GRUP: grup, COL_MCB_MANUAL: mcb, COL_KABEL: "", COL_KABEL_MANUAL: manual}
    for c in qcols:
        r[c] = 0
    for idx, val in (q or {}).items():
        r[qcols[idx]] = val
    r[COL_LAIN] = lain
    return r


def default_sirkuit() -> pd.DataFrame:
    # Contoh diambil dari sheet 'SLD 1 Fasa' (index beban: 0=DL6 1=DL9 2=DL12
    # 3=DL3 4=Exhaust 5=STK 6=Pompa 7=AC1/2 8=AC3/4 9=AC1)
    rows = [
        baris_sirkuit("LAMPU LT.1", 1, q={0: 2, 1: 1, 2: 7, 3: 3}),
        baris_sirkuit("STK LT.1", 2, q={5: 4}),
        baris_sirkuit("STK LT.1", 3, q={5: 2, 6: 1}),
        baris_sirkuit("STK AC LT.1", 5, q={8: 1}),
        baris_sirkuit("LAMPU LT.2", 1, q={0: 3, 1: 2, 2: 3, 4: 1}),
        baris_sirkuit("STK LT.2", 2, q={5: 3}),
        baris_sirkuit("STK AC LT.2", 3, q={7: 1}),
        baris_sirkuit("STK AC LT.2", 4, q={7: 1}),
        baris_sirkuit("SPARE LT. 1", 5, lain=200),
        baris_sirkuit("SPARE LT. 2", 5, lain=200),
    ]
    return normalisasi_sirkuit(pd.DataFrame(rows))


# ---------------------------------------------------------------- normalisasi
def normalisasi_beban(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return default_beban()
    df = df.copy()
    if COL_ID not in df.columns:  # data lama: ID = urutan baris (cocok dengan q1..q10)
        df[COL_ID] = range(1, len(df) + 1)
    df = df.reindex(columns=BEBAN_COLS)
    df["Nama Beban"] = df["Nama Beban"].fillna("").astype(str)
    df["Watt"] = pd.to_numeric(df["Watt"], errors="coerce").fillna(0).astype(float)
    ids = pd.to_numeric(df[COL_ID], errors="coerce")
    berikut = int(ids.max()) + 1 if ids.notna().any() else 1
    terpakai, hasil = set(), []
    for v in ids:
        if pd.isna(v) or int(v) <= 0 or int(v) in terpakai:
            v = berikut
            berikut += 1
        terpakai.add(int(v))
        hasil.append(int(v))
    df[COL_ID] = hasil
    return df.reset_index(drop=True)


def normalisasi_sirkuit(df: pd.DataFrame | None, qcols=None) -> pd.DataFrame:
    qcols = list(qcols) if qcols is not None else list(QCOLS)
    cols = sirkuit_cols(qcols)
    if df is None or len(df) == 0:
        return pd.DataFrame([baris_sirkuit("SIRKUIT 1", qcols=qcols)]).reindex(columns=cols)
    df = df.reindex(columns=cols).copy()
    for c in TEXT_COLS:
        df[c] = df[c].fillna("").astype(str)
    for c in NUM_BASE + qcols + [COL_LAIN]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(float)
    return df.reset_index(drop=True)


def muat_state(saved: dict | None) -> dict:
    saved = saved or {}
    beban = pd.DataFrame(saved["beban"]) if saved.get("beban") else None
    beban = normalisasi_beban(beban)
    qcols = qcols_of(beban)
    sirkuit = pd.DataFrame(saved["sirkuit"]) if saved.get("sirkuit") else default_sirkuit()
    return {
        "proyek": {**PROYEK_DEFAULT, **saved.get("proyek", {})},
        "sistem": {**SISTEM_DEFAULT, **saved.get("sistem", {})},
        "beban": beban,
        "sirkuit": normalisasi_sirkuit(sirkuit, qcols),
    }


# ---------------------------------------------------------------- kabel otomatis
def beban_per_sirkuit(sirkuit: pd.DataFrame, beban: pd.DataFrame | None):
    """Beban tiap sirkuit dalam Watt (jumlah x watt + lain-lain)."""
    qcols = qcols_of(beban)
    df = normalisasi_sirkuit(sirkuit, qcols)
    watt = normalisasi_beban(beban)["Watt"].to_numpy() if beban is not None else [0.0] * len(qcols)
    return df[qcols].to_numpy() @ watt + df[COL_LAIN].to_numpy()


def isi_kabel(sirkuit: pd.DataFrame, tabel_akli: pd.DataFrame,
              beban: pd.DataFrame | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Tentukan MCB pakai, kapasitas, dan kabel dari tabel AKLI.

    - MCB dipilih dari BEBAN: baris AKLI terkecil yang kapasitas Watt-nya cukup
      (minimal akli_calc.MCB_MINIMAL), kabel mengikuti baris itu.
    - MCB Manual (jika diisi) menjadi MCB minimum; naik otomatis bila beban melebihi.
    - Kabel Manual (jika diisi) menang atas kabel otomatis.
    Return (df baru, daftar catatan untuk pengguna).
    """
    df = normalisasi_sirkuit(sirkuit, qcols_of(beban))
    load = beban_per_sirkuit(df, beban)
    catatan, kabel, mcb_pakai, kapasitas = [], [], [], []
    for i, r in df.iterrows():
        mcb = float(r[COL_MCB_MANUAL])
        w = float(load[i])
        h = akli_calc.pilih_sirkuit(r[COL_NAMA], mcb, w, tabel_akli)
        label = f"Baris {i + 1} '{r[COL_NAMA]}'"
        status = h["status"]

        mcb_pakai.append(h["mcb_pakai"])
        kapasitas.append(h["kapasitas"])
        manual = r[COL_KABEL_MANUAL].strip()
        kabel.append(manual or h["teks"] or "-")

        if status == akli_calc.DI_LUAR:
            catatan.append(f"{label}: beban {w:,.0f} W di luar tabel AKLI 1 fasa "
                           "(maks 63 A). Isi 'Kabel Manual'.")
            continue
        dasar, kap_dasar = h["mcb_dasar"], h.get("kap_dasar")
        if mcb > 0 and dasar is not None and h["mcb_pakai"] > dasar:
            catatan.append(
                f"{label}: beban {w:,.0f} W melebihi kapasitas MCB manual {dasar:g} A "
                f"({(kap_dasar or 0):,.0f} W di tabel AKLI), dinaikkan ke MCB {h['mcb_pakai']:g} A.")
        elif mcb > 0 and dasar is not None and dasar != mcb:
            catatan.append(f"{label}: MCB manual {mcb:g} A tidak ada di tabel AKLI, "
                           f"dipakai {dasar:g} A.")
        if not manual and status == akli_calc.TIDAK_DIKENAL:
            catatan.append(f"{label}: nama tidak dikenali (bukan lampu/stopkontak/AC/pompa), "
                           f"dipakai {h['teks']}. Isi 'Kabel Manual' jika berbeda.")
    df[COL_MCB_PAKAI] = mcb_pakai
    df[COL_KAP] = kapasitas
    df[COL_KABEL] = kabel
    return df, catatan


# ---------------------------------------------------------------- perhitungan
def hitung(beban: pd.DataFrame, sirkuit: pd.DataFrame, sistem: dict) -> dict:
    beban = normalisasi_beban(beban)
    qcols = qcols_of(beban)
    sirkuit = normalisasi_sirkuit(sirkuit, qcols)

    v = float(sistem.get("tegangan") or 0)
    pf = float(sistem.get("pf") or 0)
    fp = float(sistem.get("faktor_puncak") or 0)

    watt = beban["Watt"].to_numpy()
    qty = sirkuit[qcols]
    load = qty.to_numpy() @ watt + sirkuit[COL_LAIN].to_numpy()

    hasil = sirkuit.copy()
    # tabel hasil menampilkan MCB final (jika sudah dihitung dari AKLI)
    hasil[COL_MCB] = hasil[COL_MCB_PAKAI].where(hasil[COL_MCB_PAKAI] > 0, hasil[COL_MCB_MANUAL])
    hasil["load"] = load
    hasil["amp"] = load / v if v else 0.0
    hasil["ka"] = load / (v * pf) if v and pf else 0.0

    total_load = float(load.sum())
    va = total_load * fp
    return {
        "hasil": hasil,
        "watt": watt,
        "qcols": qcols,
        "total_qty": qty.sum().to_numpy(),
        "total_lain": float(sirkuit[COL_LAIN].sum()),
        "total_load": total_load,
        "va": va,
        "ampere": va / v if v else 0.0,
        "daya_nyata": va * pf,
    }