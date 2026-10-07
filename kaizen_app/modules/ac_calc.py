"""Modul AC - perhitungan (tanpa Streamlit, aman dites terpisah).

Dua metode:
  Standar Calculation : Q = (L x W x H x I x E) / 60                 (L, W, H dalam feet)
  Full Calculation    : Q = Q_dasar + Q_orang + Q_lampu + Q_peralatan
        Q_dasar      = (L x W x H x I x E) / 60
        Q_orang      = max(0, n_orang - n_orang_dasar) x W_per_orang x 3,412
        Q_lampu      = n_lampu x W_lampu x F_lampu x 3,412
        Q_peralatan  = W_peralatan x 3,412
  N (AC) = Q / kapasitas AC terpilih (Btu/h)
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "ac.json"

MODE_STANDAR = "Standar Calculation"
MODE_FULL = "Full Calculation"

K_ORANG = "Jumlah Orang (Full)"
K_AKT = "Aktivitas (Full)"
K_LAMPU_N = "Jml Lampu (Full)"
K_LAMPU_W = "Watt/Lampu (Full)"
K_ALAT = "Peralatan W (Full)"

KOLOM = ["Lantai", "Nama Ruangan", "L (m)", "W (m)", "H (m)", "Isolasi (I)", "Orientasi (E)",
         K_ORANG, K_AKT, K_LAMPU_N, K_LAMPU_W, K_ALAT, "Jenis AC", "Jumlah AC"]


@lru_cache(maxsize=1)
def muat_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- pilihan
def opsi_isolasi(data: dict) -> list[str]:
    return [f"{k} ({v})" for k, v in data["isolasi"].items()]


def opsi_orientasi(data: dict) -> list[str]:
    return [f"{k} ({v})" for k, v in data["orientasi"].items()]


def opsi_ac(data: dict) -> list[str]:
    return [a["label"] for a in data["ac"]]


def opsi_aktivitas(data: dict) -> list[str]:
    return [a["label"] for a in data["full"]["aktivitas"]]


def _nilai(label, mapping: dict):
    """'Barat (20)' -> 20 ; None kalau label tidak dikenal."""
    if not isinstance(label, str):
        return None
    for k, v in mapping.items():
        if label == f"{k} ({v})":
            return v
    return None


def _txt(x) -> str:
    return "" if x is None or (not isinstance(x, str) and pd.isna(x)) else str(x).strip()


def _num(x) -> float:
    v = pd.to_numeric(x, errors="coerce")
    return 0.0 if pd.isna(v) else float(v)


def fmt_id(x: float, d: int = 2) -> str:
    """Format angka gaya Indonesia: 6.587,01"""
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------------------------- data awal
def template_default(data: dict) -> pd.DataFrame:
    """Contoh awal. L/W/H, isolasi, orientasi, dan jenis AC dari sheet 'AC STANDART'.
    Kolom (Full) hanyalah ILUSTRASI - ganti dengan data sebenarnya."""
    iso = {v: f"{k} ({v})" for k, v in data["isolasi"].items()}
    ori = {v: f"{k} ({v})" for k, v in data["orientasi"].items()}
    a = data["full"]["aktivitas"][0]["label"]
    baris = [
        ("Lantai 1", "R.keluarga",        5.00, 4.00, 2.8, iso[10], ori[20], 4, a, 4, 12, 150, "3/4 PK", 1),
        ("Lantai 2", "Kamar Tidur Kecil", 2.75, 2.00, 2.8, iso[14], ori[20], 1, a, 2,  9,  50, "1/2 PK", 1),
        ("Lantai 2", "Kamar Tidur Utama", 3.45, 3.15, 2.8, iso[14], ori[20], 2, a, 3, 12, 150, "1/2 PK", 1),
    ]
    return pd.DataFrame(baris, columns=KOLOM)


# ---------------------------------------------------------------- hitung
def rekomendasi(btu: float, jumlah: int, data: dict) -> str:
    """PK terkecil yang kapasitasnya (x jumlah unit) >= kebutuhan."""
    unit = max(1, int(jumlah))
    for a in sorted(data["ac"], key=lambda x: x["btu"]):
        if a["btu"] * unit >= btu:
            return a["label"]
    return f"> {max(data['ac'], key=lambda x: x['btu'])['label']} (tambah unit)"


def hitung(df: pd.DataFrame, data: dict, mode: str = MODE_STANDAR,
           orang_dasar: float | None = None, faktor_lampu: float | None = None) -> pd.DataFrame:
    """Baris yang belum lengkap otomatis dilewati."""
    k = data["konversi"]
    ft, pembagi, w2b = k["meter_ke_feet"], k["pembagi"], k["watt_ke_btu"]
    fp = data["full"]
    od = fp["orang_dasar"] if orang_dasar is None else orang_dasar
    fl = fp["faktor_lampu"] if faktor_lampu is None else faktor_lampu
    full = mode == MODE_FULL
    tol = data.get("toleransi_n", 0.0)
    btu_pk = {a["label"]: a["btu"] for a in data["ac"]}
    watt_akt = {a["label"]: a["total"] for a in fp["aktivitas"]}
    akt_default = fp["aktivitas"][0]["label"]

    hasil = []
    for _, r in df.iterrows():
        nama = _txt(r.get("Nama Ruangan"))
        L, W, H = (pd.to_numeric(r.get(c), errors="coerce") for c in ("L (m)", "W (m)", "H (m)"))
        i_val = _nilai(r.get("Isolasi (I)"), data["isolasi"])
        e_val = _nilai(r.get("Orientasi (E)"), data["orientasi"])
        jenis = r.get("Jenis AC")
        if (not nama or any(pd.isna(x) or x <= 0 for x in (L, W, H))
                or i_val is None or e_val is None or jenis not in btu_pk):
            continue

        jumlah = int(_num(r.get("Jumlah AC")))
        lf, wf, hf = L * ft, W * ft, H * ft
        q_dasar = lf * wf * hf * i_val * e_val / pembagi

        orang = akt = w_org = n_lampu = w_lampu = w_alat = 0
        q_orang = q_lampu = q_alat = 0.0
        if full:
            orang = _num(r.get(K_ORANG))
            akt = _txt(r.get(K_AKT))
            akt = akt if akt in watt_akt else akt_default
            w_org = watt_akt[akt]
            q_orang = max(0.0, orang - od) * w_org * w2b
            n_lampu, w_lampu = _num(r.get(K_LAMPU_N)), _num(r.get(K_LAMPU_W))
            q_lampu = n_lampu * w_lampu * fl * w2b
            w_alat = _num(r.get(K_ALAT))
            q_alat = w_alat * w2b

        btu = q_dasar + q_orang + q_lampu + q_alat
        n_ac = btu / btu_pk[jenis]
        if jumlah <= 0:
            status = "Isi jumlah AC"
        else:
            rasio = n_ac / jumlah
            status = "Cukup" if rasio <= 1 else ("Batas" if rasio <= 1 + tol else "Kurang")

        hasil.append({
            "Lantai": _txt(r.get("Lantai")) or "-", "Ruangan": nama,
            "L_m": float(L), "W_m": float(W), "H_m": float(H),
            "L_ft": lf, "W_ft": wf, "H_ft": hf, "I": i_val, "E": e_val,
            "Q_dasar": q_dasar,
            "Orang": orang, "Aktivitas": akt or "-", "W_org": w_org, "Q_orang": q_orang,
            "N_lampu": n_lampu, "W_lampu": w_lampu, "Q_lampu": q_lampu,
            "W_alat": w_alat, "Q_alat": q_alat,
            "Btu": btu, "Jenis AC": jenis, "Konversi": btu_pk[jenis],
            "N": n_ac, "Jumlah": jumlah, "Status": status,
            "Rekomendasi": rekomendasi(btu, jumlah, data),
        })
    return pd.DataFrame(hasil)


def rekap_ac(hasil: pd.DataFrame, data: dict) -> pd.DataFrame:
    """Jumlah unit per jenis AC + estimasi daya (acuan untuk Modul SLD)."""
    baris = []
    for a in data["ac"]:
        unit = int(hasil.loc[hasil["Jenis AC"] == a["label"], "Jumlah"].sum()) if not hasil.empty else 0
        watt = a.get("watt")
        baris.append({"Jenis AC": a["label"], "Unit": unit,
                      "Daya/unit (W)": watt, "Total (W)": unit * watt if watt else None})
    return pd.DataFrame(baris)


def perbandingan(hs: pd.DataFrame, hf: pd.DataFrame) -> pd.DataFrame:
    """Standar vs Full per ruangan (baris keduanya sejajar karena sumber input sama)."""
    out = pd.DataFrame({
        "Ruangan": hs["Ruangan"],
        "Standar (Btu/h)": hs["Btu"],
        "Full (Btu/h)": hf["Btu"],
    })
    out["Selisih (Btu/h)"] = out["Full (Btu/h)"] - out["Standar (Btu/h)"]
    out["Selisih (%)"] = out["Selisih (Btu/h)"] / out["Standar (Btu/h)"] * 100
    out["Rek. Standar"] = hs["Rekomendasi"]
    out["Rek. Full"] = hf["Rekomendasi"]
    return out


# ---------------------------------------------------- rincian substitusi
def rincian_teks(r: pd.Series, data: dict, mode: str,
                 orang_dasar: float | None = None, faktor_lampu: float | None = None) -> str:
    """Substitusi angka ke rumus untuk satu ruangan (supaya mudah dicocokkan dengan Excel)."""
    fp = data["full"]
    od = fp["orang_dasar"] if orang_dasar is None else orang_dasar
    fl = fp["faktor_lampu"] if faktor_lampu is None else faktor_lampu
    w2b = data["konversi"]["watt_ke_btu"]
    f = fmt_id
    p = data["konversi"]["pembagi"]

    t = [f"{r['Ruangan']}  —  {mode}", "",
         f"Q dasar    = (L × W × H × I × E) / {p}",
         f"           = ({f(r['L_ft'])} × {f(r['W_ft'])} × {f(r['H_ft'])} × {r['I']} × {r['E']}) / {p}",
         f"           = {f(r['Q_dasar'])} Btu/h"]
    if mode == MODE_FULL:
        t += ["",
              f"Q orang    = max(0; n orang − orang dasar) × W/orang × {str(w2b).replace('.', ',')}",
              f"           = max(0; {f(r['Orang'], 0)} − {f(od, 0)}) × {r['W_org']} × {str(w2b).replace('.', ',')}",
              f"           = {f(r['Q_orang'])} Btu/h",
              "",
              f"Q lampu    = n lampu × W/lampu × F lampu × {str(w2b).replace('.', ',')}",
              f"           = {f(r['N_lampu'], 0)} × {f(r['W_lampu'], 0)} × {f(fl)} × {str(w2b).replace('.', ',')}",
              f"           = {f(r['Q_lampu'])} Btu/h",
              "",
              f"Q alat     = W peralatan × {str(w2b).replace('.', ',')}",
              f"           = {f(r['W_alat'], 0)} × {str(w2b).replace('.', ',')}",
              f"           = {f(r['Q_alat'])} Btu/h",
              "",
              "Q total    = Q dasar + Q orang + Q lampu + Q alat",
              f"           = {f(r['Q_dasar'])} + {f(r['Q_orang'])} + {f(r['Q_lampu'])} + {f(r['Q_alat'])}",
              f"           = {f(r['Btu'])} Btu/h"]
    t += ["",
          f"N (AC)     = Q / kapasitas AC = {f(r['Btu'])} / {f(r['Konversi'], 0)} ({r['Jenis AC']})",
          f"           = {f(r['N'], 3)}   →  status: {r['Status']}   |   rekomendasi: {r['Rekomendasi']}"]
    return "\n".join(t)
