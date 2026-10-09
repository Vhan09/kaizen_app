"""Modul Titik Lampu - perhitungan (tanpa Streamlit).

    A = P x L                         luas ruangan (m2)
    Phi = W x (lm/W)                  fluks cahaya satu lampu (lumen)
    N = (E x A) / (Phi x LLF x CU x n)   jumlah armatur; dibulatkan KE ATAS
    E tercapai = N x Phi x LLF x CU x n / A
E = tingkat pencahayaan target (lux) dari SNI 6197:2020 Tabel 1 (atau isian manual).
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "titik_lampu.json"
LAINNYA = "Lainnya (isi E manual)"

K = ["Lantai", "Nama Ruangan", "P (m)", "L (m)", "Jenis Ruangan", "E Manual (lux)", "Jenis Lampu", "Watt (W)",
     "lm/W Manual", "n (lampu/armatur)", "Titik Manual"]


@lru_cache(maxsize=1)
def muat_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def fmt_id(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _num(x) -> float:
    v = pd.to_numeric(x, errors="coerce")
    return 0.0 if pd.isna(v) else float(v)


def _txt(x) -> str:
    return "" if x is None or (not isinstance(x, str) and pd.isna(x)) else str(x).strip()


def label_lux(e: dict) -> str:
    return f"{e['fungsi']} — {e['kelompok']} ({e['lux']} lux)"


def opsi_ruangan(data: dict) -> list[str]:
    return [label_lux(e) for e in data["lux"]] + [LAINNYA]


def opsi_lampu(data: dict) -> list[str]:
    return [x["label"] for x in data["lampu"]]


def _cari_lux(label, data: dict):
    for e in data["lux"]:
        if label == label_lux(e):
            return e
    return None


def template_default(data: dict) -> pd.DataFrame:
    """Contoh dari Excel (titik_lampu.xlsx). Jenis ruangan dipetakan ke Tabel 1 SNI 6197:2020."""
    L = {e["fungsi"]: label_lux(e) for e in data["lux"] if e["kelompok"] == "Rumah Tinggal"}
    inb, outb = "DL inbow", "DL outbow"
    b = [
        ("Lantai Satu", "Kamar Mandi", 2, 1.25, L["Kamar mandi"], None, inb, 9, None, 1, None),
        ("Lantai Satu", "Ruang Makan & Dapur", 2.85, 3.75, L["Dapur"], None, inb, 12, None, 1, None),
        ("Lantai Satu", "Ruang keluarga", 2.15, 3.75, L["Ruang keluarga"], None, inb, 12, None, 1, None),
        ("Lantai Satu", "Tangga", 3, 1.85, L["Tangga"], None, inb, 6, None, 1, None),
        ("Lantai Satu", "Garasi", 4, 3.85, L["Garasi"], None, outb, 12, None, 1, None),
        ("Lantai Satu", "Teras depan", 2.875, 1, L["Teras"], None, inb, 6, None, 1, None),
        ("Lantai Satu", "Taman Belakang", 2, 1.25, LAINNYA, 100, inb, 3, None, 1, None),
        ("Lantai Dua", "Kamar Tidur Non Utama", 2.15, 3, L["Kamar tidur"], None, inb, 12, None, 1, None),
        ("Lantai Dua", "Kamar Mandi Non Utama", 1.55, 2, L["Kamar mandi"], None, inb, 9, None, 1, None),
        ("Lantai Dua", "Kamar Mandi Utama", 1.65, 2, L["Kamar mandi"], None, inb, 9, None, 1, None),
        ("Lantai Dua", "Kamar Tidur Utama", 3.3, 3.7, L["Kamar tidur"], None, inb, 12, None, 1, None),
        ("Lantai Dua", "Koridor Kecil", 1.05, 1.15, LAINNYA, 100, inb, 6, None, 1, None),
        ("Lantai Dua", "Outdoor Kamar Utama", None, None, LAINNYA, 100, inb, 6, None, 1, 1),
    ]
    return pd.DataFrame(b, columns=K)


def parameter_default(data: dict) -> dict:
    p = data["parameter"]
    return {"llf": p["llf"], "cu": p["cu"]}


def bulat_atas(x: float) -> int:
    return int(math.ceil(round(x, 9)))


# --------------------------------------------------------------- hitung
def hitung(df: pd.DataFrame, data: dict, P: dict) -> dict:
    llf, cu = P["llf"], P["cu"]
    lmw_kat = {x["label"]: x["lmw"] for x in data["lampu"]}
    baris = []
    for _, r in df.iterrows():
        nama = _txt(r.get("Nama Ruangan"))
        p, l, w = _num(r.get("P (m)")), _num(r.get("L (m)")), _num(r.get("Watt (W)"))
        jl = _txt(r.get("Jenis Lampu"))
        manual = int(_num(r.get("Titik Manual")))
        std = _cari_lux(r.get("Jenis Ruangan"), data)
        e = _num(r.get("E Manual (lux)")) or (std["lux"] if std else 0.0)
        if not nama or w <= 0 or jl not in lmw_kat:
            continue
        A = p * l if p > 0 and l > 0 else 0.0
        if not (A > 0 and e > 0) and manual <= 0:
            continue
        lmw = _num(r.get("lm/W Manual")) or lmw_kat[jl]
        n = int(_num(r.get("n (lampu/armatur)")) or data["parameter"]["n"])
        phi = w * lmw
        eff = phi * llf * cu * n
        req = e * A
        raw = req / eff if A > 0 and e > 0 and eff > 0 else None
        pembulatan = max(1, bulat_atas(raw)) if raw is not None else None
        titik = manual if manual > 0 else pembulatan
        e_cap = titik * eff / A if A > 0 else None
        if A <= 0 or e <= 0:
            status = "MANUAL"
        else:
            status = "MEMENUHI" if e_cap >= e - 1e-6 else "KURANG"
        daya = titik * w * n
        baris.append({
            "Lantai": _txt(r.get("Lantai")) or "-", "Ruangan": nama, "P": p or None, "L": l or None, "A": A or None,
            "JenisR": std["fungsi"] if std else "Lainnya", "Kelompok": std["kelompok"] if std else "–",
            "Ra": std["ra"] if std else None, "E": e or None, "Lampu": jl, "W": w, "lmw": lmw, "n": n, "phi": phi,
            "eff": eff, "req": req if A > 0 and e > 0 else None, "raw": raw, "bulat": pembulatan,
            "manual": manual or None, "titik": int(titik), "e_cap": e_cap, "status": status,
            "daya": daya, "wm2": daya / A if A > 0 else None, "label_lampu": f"{jl} {w:g} W",
        })
    t = pd.DataFrame(baris)
    if t.empty:
        return {"tabel": t, "P": P}

    lantai = (t.groupby("Lantai", sort=False)
              .agg(ruang=("Ruangan", "count"), area=("A", "sum"), titik=("titik", "sum"), daya=("daya", "sum"))
              .reset_index())
    daya_ber = t[t["A"].fillna(0) > 0].groupby("Lantai", sort=False)["daya"].sum()
    lantai["wm2"] = lantai["Lantai"].map(daya_ber).fillna(0) / lantai["area"].replace(0, float("nan"))
    pivot = (t.pivot_table(index="label_lampu", columns="Lantai", values="titik", aggfunc="sum", fill_value=0)
             .reindex(columns=list(lantai["Lantai"])))
    pivot["Total"] = pivot.sum(axis=1)
    kurang = t[t["status"] == "KURANG"]

    w = []
    if not 0 < llf <= 1 or not 0 < cu <= 1:
        w.append("LLF dan CU harus di antara 0 dan 1.")
    pr = data["parameter"]
    if not pr["llf_min"] <= llf <= pr["llf_max"]:
        w.append(f"LLF {llf:g} di luar rentang yang dipakai pada Excel ({pr['llf_min']}–{pr['llf_max']}).")
    if not pr["cu_min"] <= cu <= pr["cu_max"]:
        w.append(f"CU {cu:g} di luar rentang pada Excel ({pr['cu_min']:.0%}–{pr['cu_max']:.0%}).")
    for x in kurang.itertuples():
        w.append(f"{x.Ruangan}: titik manual {x.titik} menghasilkan {fmt_id(x.e_cap, 0)} lux < target {fmt_id(x.E, 0)} lux.")
    tidak_std = t[t["JenisR"] == "Lainnya"]
    return {"tabel": t, "lantai": lantai, "pivot": pivot, "P": P, "peringatan": w,
            "titik_total": int(t["titik"].sum()), "daya_total": float(t["daya"].sum()),
            "area_total": float(t["A"].fillna(0).sum()), "n_ruang": len(t),
            "wm2": (float(t.loc[t["A"] > 0, "daya"].sum() / t["A"].sum()) if (t["A"].fillna(0) > 0).any() else None),
            "n_kurang": len(kurang), "n_manual": int((t["status"] == "MANUAL").sum()),
            "lainnya": list(tidak_std["Ruangan"])}


def kesimpulan(h: dict) -> str:
    t = h["tabel"]
    if t.empty:
        return ""
    s = (f"Perhitungan jumlah titik lampu menggunakan metode lumen (N = E × A / (Φ × LLF × CU × n)) dengan LLF "
         f"{fmt_id(h['P']['llf'])} dan CU {fmt_id(h['P']['cu'])}. Pada {h['n_ruang']} ruangan dibutuhkan "
         f"{h['titik_total']} titik lampu dengan daya terpasang {fmt_id(h['daya_total'], 0)} W "
         f"(± {fmt_id(h['wm2'], 1) if h['wm2'] else '–'} W/m² pada ruangan berdimensi). ")
    if h["n_kurang"] == 0:
        s += "Seluruh ruangan dengan data dimensi memenuhi tingkat pencahayaan target."
    else:
        s += f"{h['n_kurang']} ruangan masih di bawah target karena titik manual; periksa kembali."
    if h["n_manual"]:
        s += f" {h['n_manual']} ruangan memakai titik manual tanpa dimensi."
    return s
