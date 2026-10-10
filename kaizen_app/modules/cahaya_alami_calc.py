"""Modul Pencahayaan Alami - perhitungan (tanpa Streamlit).

    Aj = sum(lebar x tinggi x jumlah x faktor efektif)    luas bukaan cahaya (m2)
    Ar = P x L                                            luas lantai ruangan (m2)
    Rasio = Aj / Ar        syarat: Rasio >= ambang (mis. 10%)
Rasio Aj/Ar adalah pemeriksaan awal; penilaian formal SNI 03-2396-2001 memakai faktor langit (FL).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "cahaya_alami.json"
OK, KURANG, TANPA, TERBUKA = "MEMENUHI", "KURANG", "TIDAK ADA BUKAAN", "AREA TERBUKA"
KR = ["Lantai", "Nama Ruangan", "P (m)", "L (m)", "Jenis Ruang"]
KB = ["Ruangan", "Jenis Bukaan", "Lebar (m)", "Tinggi (m)", "Jumlah", "Faktor Efektif"]


@lru_cache(maxsize=1)
def muat_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def fmt_id(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x: float, d: int = 1) -> str:
    return fmt_id(x * 100, d) + "%"


def pct_bersih(x: float) -> str:
    """0,1 -> 10% ; 0,125 -> 12,5%"""
    return (fmt_id(x * 100, 1).rstrip("0").rstrip(",")) + "%"


def _num(x) -> float:
    v = pd.to_numeric(x, errors="coerce")
    return 0.0 if pd.isna(v) else float(v)


def _txt(x) -> str:
    return "" if x is None or (not isinstance(x, str) and pd.isna(x)) else str(x).strip()


def opsi_ambang(data: dict) -> list[str]:
    return [a["label"] for a in data["ambang"]]


def saran_perbaikan(status: str, tambahan: float) -> tuple[str, str]:
    if status == TANPA:
        utama = (
            "Belum ada bukaan: survei dinding yang berbatasan dengan luar/halaman untuk "
            "menambah jendela, pintu kaca, atau bovenlicht yang menerima cahaya langsung. "
            "Jika tidak memungkinkan, evaluasi skylight, void/sumur cahaya, atau light tube "
            "yang terhubung ke langit; periksa struktur sebelum membuat bukaan."
        )
    elif status == KURANG:
        utama = (
            f"Target tambahan luas bukaan efektif sekitar {fmt_id(tambahan, 3)} m². "
            "Evaluasi memperbesar atau menambah jendela/pintu kaca pada sisi luar, atau "
            "menambah bovenlicht/skylight bila sesuai kondisi bangunan. Pastikan bukaan "
            "tidak terhalang dan konsultasikan perubahan struktur dengan tenaga ahli."
        )
    else:
        return "", ""

    pendukung = (
        "Untuk membantu cahaya yang sudah masuk: bersihkan kaca dan kurangi penghalang "
        "di luar tanpa mengabaikan panas/silau; gunakan warna terang dengan reflektansi "
        "baik pada plafon dan dinding, dan pertimbangkan light shelf atau permukaan pantul "
        "yang aman. Kaca/transom ke ruang lain dapat membantu sebagai cahaya pinjaman, "
        "tetapi tidak otomatis dihitung sebagai luas bukaan luar. Lampu buatan hanya "
        "penerangan pendukung, bukan pengganti pemenuhan pencahayaan alami."
    )
    return utama, pendukung


def template_ruang() -> pd.DataFrame:
    """Contoh dari cahaya_alami.xlsx (tabel ke-2: rasio Aj/Ar)."""
    t, o = "Ruang tertutup", "Area terbuka"
    b = [("Lantai Satu", "Kamar Mandi", 2, 1, t), ("Lantai Satu", "Ruang Makan & Dapur", 3.3, 2.2, t),
         ("Lantai Satu", "Ruang Keluarga", 3.3, 2.6, t), ("Lantai Satu", "Tangga", 3.7, 0.95, t),
         ("Lantai Satu", "Garasi", None, None, o), ("Lantai Satu", "Teras Depan", None, None, o),
         ("Lantai Satu", "Taman Belakang", None, None, o),
         ("Lantai Dua", "Kamar Tidur Kecil", 2.75, 2, t), ("Lantai Dua", "Kamar Mandi Kecil", 1.7, 1.4, t),
         ("Lantai Dua", "Kamar Mandi Utama", 1.75, 1.5, t), ("Lantai Dua", "Kamar Tidur Utama", 3.45, 3.15, t)]
    return pd.DataFrame(b, columns=KR)


def template_bukaan() -> pd.DataFrame:
    j = "Jendela"
    b = [("Kamar Mandi", j, 0.6, 0.4, 1, 1.0), ("Ruang Makan & Dapur", j, 1.2, 1.32, 1, 1.0),
         ("Ruang Keluarga", j, 2.4, 1.0, 1, 1.0), ("Tangga", j, 0.5, 3.0, 1, 1.0),
         ("Kamar Tidur Kecil", j, 0.6, 1.54, 1, 1.0), ("Kamar Mandi Kecil", j, 0.6, 0.4, 1, 1.0),
         ("Kamar Mandi Utama", j, 0.6, 0.4, 1, 1.0), ("Kamar Tidur Utama", j, 1.85, 1.8, 1, 1.0)]
    return pd.DataFrame(b, columns=KB)


def hitung(ruang: pd.DataFrame, bukaan: pd.DataFrame, data: dict, ambang: float) -> dict:
    # --- bukaan valid
    bk = []
    for _, r in bukaan.iterrows():
        nama, w, h = _txt(r.get("Ruangan")), _num(r.get("Lebar (m)")), _num(r.get("Tinggi (m)"))
        n = int(_num(r.get("Jumlah")) or 1)
        f = _num(r.get("Faktor Efektif")) or data["faktor_efektif_default"]
        if not nama or w <= 0 or h <= 0:
            continue
        bk.append({"Ruangan": nama, "Jenis": _txt(r.get("Jenis Bukaan")) or "Jendela", "W": w, "H": h, "n": n,
                   "f": min(f, 1.0), "Aj": w * h * n * min(f, 1.0)})
    b = pd.DataFrame(bk, columns=["Ruangan", "Jenis", "W", "H", "n", "f", "Aj"])
    aj_per = b.groupby("Ruangan")["Aj"].sum() if not b.empty else pd.Series(dtype=float)
    n_per = b.groupby("Ruangan")["n"].sum() if not b.empty else pd.Series(dtype=float)

    # --- ruangan
    rows, nama_ada, dobel = [], set(), []
    for _, r in ruang.iterrows():
        nama = _txt(r.get("Nama Ruangan"))
        if not nama:
            continue
        if nama in nama_ada:
            dobel.append(nama)
        nama_ada.add(nama)
        jenis = _txt(r.get("Jenis Ruang")) or "Ruang tertutup"
        p, l = _num(r.get("P (m)")), _num(r.get("L (m)"))
        ar = p * l if p > 0 and l > 0 else 0.0
        aj = float(aj_per.get(nama, 0.0))
        nb = int(n_per.get(nama, 0))
        if jenis == "Area terbuka":
            status, rasio = TERBUKA, None
        elif ar <= 0:
            continue
        else:
            rasio = aj / ar
            status = TANPA if aj <= 0 else (OK if rasio >= ambang - 1e-9 else KURANG)
        aj_min = ambang * ar if ar > 0 and jenis != "Area terbuka" else None
        tambahan = max(aj_min - aj, 0.0) if aj_min is not None else 0.0
        saran_utama, saran_pendukung = saran_perbaikan(status, tambahan)
        rows.append({"Lantai": _txt(r.get("Lantai")) or "-", "Ruangan": nama, "Jenis": jenis,
                     "P": p or None, "L": l or None, "Ar": ar or None, "Aj": aj if jenis != "Area terbuka" else None,
                     "nb": nb, "rasio": rasio, "aj_min": aj_min,
                     "selisih": (aj - aj_min) if aj_min is not None else None, "status": status,
                     "saran_utama": saran_utama, "saran_pendukung": saran_pendukung})
    t = pd.DataFrame(rows)
    if t.empty:
        return {"tabel": t, "bukaan": b, "ambang": ambang}

    dinilai = t[t["status"] != TERBUKA]
    rekap = t.assign(
        _dinilai=(t["status"] != TERBUKA).astype(int),
        _terbuka=(t["status"] == TERBUKA).astype(int),
        _ok=(t["status"] == OK).astype(int),
        _kurang=t["status"].isin([KURANG, TANPA]).astype(int),
    )
    lantai = (rekap.groupby("Lantai", sort=False)
              .agg(ruang=("_dinilai", "sum"), terbuka=("_terbuka", "sum"),
                   ar=("Ar", "sum"), aj=("Aj", "sum"), ok=("_ok", "sum"),
                   kurang=("_kurang", "sum")).reset_index())
    lantai["rasio"] = lantai["aj"] / lantai["ar"].replace(0, float("nan"))

    w = []
    for nm in sorted(set(b["Ruangan"]) - nama_ada) if not b.empty else []:
        w.append(f"Bukaan untuk “{nm}” diabaikan: nama ruangan tidak ada pada tabel ruangan.")
    for nm in dobel:
        w.append(f"Nama ruangan “{nm}” dipakai lebih dari sekali; bukaan dijumlahkan ke semua baris bernama sama.")
    for x in dinilai[dinilai["status"] == KURANG].itertuples():
        rasio, selisih = _num(x.rasio), _num(x.selisih)
        w.append(f"{x.Ruangan}: rasio {pct(rasio)} < {pct_bersih(ambang)}; "
                 f"tambah bukaan ±{fmt_id(-selisih, 3)} m².")
    for x in dinilai[dinilai["status"] == TANPA].itertuples():
        w.append(f"{x.Ruangan}: tidak ada bukaan cahaya; butuh minimal {fmt_id(_num(x.aj_min), 2)} m².")

    return {"tabel": t, "bukaan": b, "lantai": lantai, "ambang": ambang, "peringatan": w,
            "n_dinilai": len(dinilai), "n_ok": int((t["status"] == OK).sum()),
            "n_kurang": int(t["status"].isin([KURANG, TANPA]).sum()), "n_terbuka": int((t["status"] == TERBUKA).sum()),
            "ar_total": float(dinilai["Ar"].sum()), "aj_total": float(dinilai["Aj"].sum()),
            "rasio_total": float(dinilai["Aj"].sum() / dinilai["Ar"].sum()) if dinilai["Ar"].sum() else None,
            "tambahan": float(-dinilai.loc[dinilai["selisih"] < 0, "selisih"].sum())}


def kesimpulan(h: dict) -> str:
    if h["tabel"].empty or not h.get("n_dinilai"):
        return ""
    s = (f"Pemeriksaan pencahayaan alami dilakukan dengan rasio luas bukaan terhadap luas lantai (Aj/Ar) dengan ambang minimum "
         f"{pct_bersih(h['ambang'])}. Dari {h['n_dinilai']} ruangan tertutup, {h['n_ok']} ruangan memenuhi")
    if h["n_kurang"]:
        s += f" dan {h['n_kurang']} ruangan belum memenuhi (total tambahan bukaan ± {fmt_id(h['tambahan'], 3)} m²)"
    s += f". Rasio keseluruhan {pct(h['rasio_total'])}."
    if h["n_terbuka"]:
        s += f" {h['n_terbuka']} area terbuka (garasi, teras, taman) tidak dihitung."
    return s + " Penilaian formal SNI 03-2396-2001 (faktor langit) perlu dilakukan terpisah bila diminta."
