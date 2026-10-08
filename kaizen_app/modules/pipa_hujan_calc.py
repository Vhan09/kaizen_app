"""Modul Pipa Air Hujan - perhitungan (tanpa Streamlit).

1. Debit hujan (metode rasional, SNI 2415:2016)   Q = 0,00278 x C x I x A      (A dalam Ha, I mm/jam, Q m3/dt)
2. Pipa horizontal (SNI 8153:2015 Tabel 16)       luas dilayani <= luas maksimum pada kemiringan & intensitas
3. Pipa tegak / kolektor (SNI 8153:2015 Tabel 17) luas total <= kapasitas Tabel 17
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "pipa_hujan.json"
OK, TIDAK = "MEMENUHI", "TIDAK MEMENUHI"


@lru_cache(maxsize=1)
def muat_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def fmt_id(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ink(x) -> str:
    """3 -> 3\" ; 2.5 -> 2,5\""""
    return (f"{x:g}".replace(".", ",")) + '"'


def _num(x) -> float:
    v = pd.to_numeric(x, errors="coerce")
    return 0.0 if pd.isna(v) else float(v)


def _koef_limpasan(pilihan, data: dict) -> tuple[float, str]:
    if isinstance(pilihan, str):
        for opsi in data["koef_limpasan_pilihan"]["opsi"]:
            if opsi["id"] == pilihan:
                return float(opsi["nilai"]), opsi["permukaan"]
    return _num(pilihan), "Atap rumah"


def _txt(x) -> str:
    return "" if x is None or (not isinstance(x, str) and pd.isna(x)) else str(x).strip()


def template_atap(data: dict) -> pd.DataFrame:
    """Contoh dari Excel: atap 30,55 m2, C 0,95, 5 titik roof drain."""
    return pd.DataFrame([{"Bidang Atap": "Atap rumah", "Luas (m²)": 30.55,
                          "Koef. Limpasan (C)": data["koef_limpasan_pilihan"]["default"],
                          "Jumlah Roof Drain": 5}])


def parameter_default(data: dict) -> dict:
    return {"I": float(data["rasional"]["intensitas"]),
            "d_roof": 3.0, "d_cabang": 3.0, "s_cabang": 1, "d_gabung": 3.0, "s_gabung": 1,
            "d_tegak": 4.0}


# --------------------------------------------------------------- tabel 16
def kolom_intensitas(I: float, data: dict) -> tuple[int, float, bool]:
    """Kolom Tabel 16 yang dipakai = intensitas tabel terdekat di ATAS I. Return (indeks, nilai, di_luar_rentang)."""
    grid = data["tabel16"]["intensitas"]
    for i, g in enumerate(grid):
        if g >= I:
            return i, g, False
    return len(grid) - 1, grid[-1], True


def kapasitas(ukuran: float, kemiringan: int, I: float, data: dict) -> float | None:
    """Luas maksimum (m2) pipa horizontal. Bila I melebihi tabel: kapasitas ~ 1/I dari kolom terakhir."""
    t = data["tabel16"]["kemiringan"][str(int(kemiringan))]
    if ukuran not in data["ukuran_inci"]:
        return None
    row = data["ukuran_inci"].index(ukuran)
    idx, nilai, luar = kolom_intensitas(I, data)
    cap = float(t["luas"][row][idx])
    return cap * nilai / I if luar else cap


def debit_kapasitas(ukuran: float, kemiringan: int, data: dict) -> float | None:
    t = data["tabel16"]["kemiringan"][str(int(kemiringan))]
    if ukuran not in data["ukuran_inci"]:
        return None
    return t["debit"][data["ukuran_inci"].index(ukuran)]


def kapasitas_tegak(ukuran: float, I: float, data: dict) -> tuple[float | None, float | None]:
    """Kapasitas Tabel 17 pada intensitas tepat atau kolom berikutnya yang lebih tinggi."""
    tabel = data["tabel17"]
    if ukuran not in tabel["diameter_inci"] or I > tabel["intensitas"][-1]:
        return None, None
    idx = next(i for i, intensitas in enumerate(tabel["intensitas"]) if intensitas >= I)
    row = tabel["diameter_inci"].index(ukuran)
    return float(tabel["luas_m2"][row][idx]), float(tabel["intensitas"][idx])


def ukuran_minimum(luas: float, kemiringan: int, I: float, data: dict) -> float | None:
    for u in data["ukuran_inci"]:
        cap = kapasitas(u, kemiringan, I, data)
        if cap is not None and cap >= luas:
            return u
    return None


def _cek(luas: float, ukuran: float, kemiringan: int, I: float, q_ls: float, data: dict) -> dict:
    cap = kapasitas(ukuran, kemiringan, I, data)
    rasio = luas / cap if cap else float("inf")
    deb = debit_kapasitas(ukuran, kemiringan, data)
    return {"luas": luas, "ukuran": ukuran, "kemiringan": kemiringan, "kapasitas": cap, "rasio": rasio,
            "status": OK if cap and luas <= cap else TIDAK, "minimum": ukuran_minimum(luas, kemiringan, I, data),
            "q_ls": q_ls, "debit_kap": deb}


# ---------------------------------------------------------------- hitung
def hitung(atap_df: pd.DataFrame, data: dict, P: dict) -> dict:
    k = data["rasional"]["konstanta"]
    I = P["I"]
    zona = []
    for _, r in atap_df.iterrows():
        nama = _txt(r.get("Bidang Atap"))
        A = _num(r.get("Luas (m²)"))
        C, permukaan = _koef_limpasan(r.get("Koef. Limpasan (C)"), data)
        n = int(_num(r.get("Jumlah Roof Drain")))
        if not nama or A <= 0 or not 0 < C <= 1 or n < 1:
            continue
        ha = A / 10000
        q_m3 = k * C * I * ha
        zona.append({"Bidang": nama, "Permukaan": permukaan, "A": A, "Ha": ha, "C": C, "n": n,
                     "Q_m3s": q_m3, "Q_Ls": q_m3 * 1000,
                     "A_drain": A / n, "Q_drain_Ls": q_m3 * 1000 / n})
    z = pd.DataFrame(zona, columns=["Bidang", "Permukaan", "A", "Ha", "C", "n", "Q_m3s", "Q_Ls",
                                    "A_drain", "Q_drain_Ls"])

    A_tot = float(z["A"].sum())
    Q_m3 = float(z["Q_m3s"].sum())
    Q_Ls = Q_m3 * 1000
    n_tot = int(z["n"].sum())
    C_rata = float((z["C"] * z["A"]).sum() / A_tot) if A_tot else 0.0

    idx, I_tabel, luar = kolom_intensitas(I, data)
    if z.empty:
        return {"zona": z, "A_tot": 0.0, "Q_m3": 0.0, "Q_Ls": 0.0, "n_tot": 0, "C_rata": 0.0, "I": I, "I_tabel": I_tabel,
                "luar": luar, "cabang": None, "gabung": None, "tegak": None, "peringatan": [], "P": P}

    worst = z.sort_values("A_drain", kind="stable").iloc[-1]
    cabang = _cek(float(worst["A_drain"]), P["d_cabang"], P["s_cabang"], I, float(worst["Q_drain_Ls"]), data)
    cabang["bidang"] = worst["Bidang"]
    gabung = _cek(A_tot, P["d_gabung"], P["s_gabung"], I, Q_Ls, data)

    cap_t, I_tabel17 = kapasitas_tegak(P["d_tegak"], I, data)
    tegak = {"ukuran": P["d_tegak"], "luas": A_tot, "q_ls": Q_Ls, "I_tabel": I_tabel17,
             "kapasitas": cap_t, "rasio": A_tot / cap_t if cap_t else None,
             "status": (OK if A_tot <= cap_t else TIDAK) if cap_t is not None else "DI LUAR TABEL"}

    w = []
    if cap_t is None:
        w.append(f"Intensitas {I:g} mm/jam melebihi rentang Tabel 17 (maks. {data['tabel17']['intensitas'][-1]:g}); "
                 "kapasitas pipa tegak tidak diekstrapolasi.")
    if luar:
        w.append(f"Intensitas {I:g} mm/jam melebihi rentang Tabel 16 (maks. {I_tabel:g}); kapasitas diperkirakan "
                 f"proporsional 1/I (ekstrapolasi, cek ulang ke SNI).")
    if cabang["status"] == TIDAK:
        w.append(f"Pipa cabang Ø{ink(P['d_cabang'])} tidak memenuhi; ukuran minimum: "
                 f"{('Ø' + ink(cabang['minimum'])) if cabang['minimum'] else 'di luar Tabel 16'}.")
    if gabung["status"] == TIDAK:
        w.append(f"Pipa horizontal gabungan Ø{ink(P['d_gabung'])} tidak memenuhi; ukuran minimum: "
                 f"{('Ø' + ink(gabung['minimum'])) if gabung['minimum'] else 'di luar Tabel 16'}.")
    if P["d_gabung"] < P["d_cabang"]:
        w.append("Diameter pipa gabungan lebih kecil dari pipa cabang — periksa kembali.")
    if P["d_tegak"] < P["d_gabung"]:
        w.append("Diameter pipa tegak lebih kecil dari pipa horizontal gabungan — periksa kembali.")

    return {"zona": z, "A_tot": A_tot, "Q_m3": Q_m3, "Q_Ls": Q_Ls, "n_tot": n_tot, "C_rata": C_rata,
            "I": I, "I_tabel": I_tabel, "idx": idx, "luar": luar,
            "cabang": cabang, "gabung": gabung, "tegak": tegak, "peringatan": w, "P": P,
            "ok_semua": cabang["status"] == OK and gabung["status"] == OK and tegak["status"] == OK}


def kesimpulan(h: dict, data: dict) -> str:
    """Kalimat penutup seperti pada Excel, dibuat dinamis."""
    P, I = h["P"], h["I"]
    if h["cabang"] is None:
        return ""
    c, g, t = h["cabang"], h["gabung"], h["tegak"]
    awal = (f"Penentuan ukuran roof drain dan pipa air hujan dilakukan berdasarkan luas bidang atap efektif "
            f"({fmt_id(h['A_tot'])} m²), intensitas hujan rencana {I:g} mm/jam, dan ketentuan SNI 8153:2015. ")
    if c["status"] == OK and g["status"] == OK:
        hasil = (f"Hasil evaluasi menunjukkan bahwa pipa cabang Ø{ink(c['ukuran'])} (melayani {fmt_id(c['luas'])} m² < "
                 f"{fmt_id(c['kapasitas'], 0)} m²) dan pipa horizontal gabungan Ø{ink(g['ukuran'])} (melayani "
                 f"{fmt_id(g['luas'])} m² < {fmt_id(g['kapasitas'], 0)} m²) mampu melayani luas bidang atap rencana.")
    else:
        bad = []
        if c["status"] != OK:
            bad.append(f"pipa cabang Ø{ink(c['ukuran'])} (min. Ø{ink(c['minimum']) if c['minimum'] else '—'})")
        if g["status"] != OK:
            bad.append(f"pipa horizontal gabungan Ø{ink(g['ukuran'])} (min. Ø{ink(g['minimum']) if g['minimum'] else '—'})")
        hasil = "Hasil evaluasi menunjukkan " + " dan ".join(bad) + " belum memenuhi persyaratan kapasitas."
    if t["status"] == "DI LUAR TABEL":
        hasil += f" Intensitas hujan berada di luar rentang Tabel 17 untuk pipa tegak Ø{ink(t['ukuran'])}; kapasitas belum dapat dicek."
    elif t["status"] == OK:
        hasil += f" Pipa tegak Ø{ink(t['ukuran'])} memenuhi kapasitas Tabel 17."
    else:
        hasil += f" Pipa tegak Ø{ink(t['ukuran'])} belum memenuhi kapasitas Tabel 17."
    return awal + hasil
