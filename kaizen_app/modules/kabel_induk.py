"""Saran kabel induk (feeder) untuk beban keseluruhan, dari tabel AKLI.

Tanpa Streamlit. Dasar pemilihan: beban puncak (VA) dibandingkan dengan kolom
"Besaran daya yang tersedia (VA)" pada tabel AKLI. Dipilih baris terkecil yang
dayanya cukup; MCB induk dan ukuran kabel mengikuti baris itu.
"""
from __future__ import annotations

import pandas as pd

from modules.akli_calc import fmt_kabel


def saran(va_puncak: float, tabel: pd.DataFrame, fasa: int = 1) -> dict:
    """Return dict.

    ok=True  : teks (mis. '3x6 mm²'), mcb, va_tersedia, tipe, va_maks
    ok=False : beban melebihi tabel (atau tabel kosong); va_maks = daya terbesar di tabel
    """
    t = tabel[
        (tabel["Fasa"] == fasa)
        & tabel["VA"].notna()
        & tabel["MCB (A)"].notna()
        & tabel["Ukuran (mm²)"].notna()
    ].sort_values("VA")
    if t.empty:
        return {"ok": False, "va_maks": 0.0}

    va_maks = float(t["VA"].max())
    cocok = t[t["VA"] >= float(va_puncak or 0)]
    if cocok.empty:
        return {"ok": False, "va_maks": va_maks}

    r = cocok.iloc[0]
    inti = int(r["Inti"]) if pd.notna(r["Inti"]) else 3
    return {
        "ok": True,
        "teks": fmt_kabel(inti, float(r["Ukuran (mm²)"])),
        "mcb": float(r["MCB (A)"]),
        "va_tersedia": float(r["VA"]),
        "tipe": str(r["Tipe Kabel"]).strip(),
        "va_maks": va_maks,
    }