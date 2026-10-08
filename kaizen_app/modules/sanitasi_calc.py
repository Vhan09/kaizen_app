"""Modul Sanitasi & Air Bersih - perhitungan (tanpa Streamlit).

1. Kebutuhan air bersih   : Q harian = sum(jumlah x standar SNI 03-7065-2005 Tabel 1)
                            Q rencana = Q harian x (1 + faktor puncak)
2. Air limbah             : total = Q dasar x faktor limbah ; black = total x fraksi black ; grey = total - black
3. Tangki septik (SNI 2398:2017)
        V air    = Q limbah x waktu detensi
        V lumpur = QL x n x periode pengurasan
        V total  = V air + V lumpur + ambang bebas
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sanitasi.json"

DASAR_PUNCAK = "Q dengan faktor puncak (seperti Excel)"
DASAR_RATA = "Q rata-rata harian"


@lru_cache(maxsize=1)
def muat_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def opsi_fungsi(data: dict) -> list[str]:
    return [r["fungsi"] for r in data["pemakaian_air"]]


def _txt(x) -> str:
    return "" if x is None or (not isinstance(x, str) and pd.isna(x)) else str(x).strip()


def _num(x) -> float:
    v = pd.to_numeric(x, errors="coerce")
    return 0.0 if pd.isna(v) else float(v)


def fmt_id(x: float, d: int = 2) -> str:
    """4270 -> 4.270,00"""
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def bulat_atas(x: float, langkah: float) -> float:
    if langkah <= 0:
        return x
    return round(math.ceil(round(x / langkah, 9)) * langkah, 6)


def template_default() -> pd.DataFrame:
    """Contoh dari Excel: rumah tinggal, 4 penghuni."""
    return pd.DataFrame([{"Fungsi": "Rumah tinggal", "Jumlah": 4, "Keterangan": "Penghuni rumah"}])


def parameter_default(data: dict) -> dict:
    s, ab, al = data["septik"], data["air_bersih"], data["air_limbah"]
    return {
        "faktor_puncak": ab["faktor_puncak"], "pembulatan": ab["pembulatan_m3"], "dasar": DASAR_PUNCAK,
        "faktor_limbah": al["faktor_limbah"], "fraksi_black": al["fraksi_black"],
        "n_auto": True, "n": 4,
        "td": s["waktu_detensi_hari"], "ql": s["lumpur_l_org_thn"], "pp": s["pengurasan_thn"],
        "ambang": s["ambang_bebas_m"], "h_air": s["kedalaman_air_m"], "rasio": s["rasio_pl"],
    }


# --------------------------------------------------------------- tangki septik
def _septik(q_l_hari: float, n: float, P: dict) -> dict:
    td, ql, pp = P["td"], P["ql"], P["pp"]
    v_air = q_l_hari * td / 1000
    v_lumpur = ql * n * pp / 1000
    v_basah = v_air + v_lumpur
    luas = v_basah / P["h_air"] if P["h_air"] > 0 else 0.0
    lebar = math.sqrt(luas / P["rasio"]) if luas > 0 and P["rasio"] > 0 else 0.0
    panjang = P["rasio"] * lebar
    v_ambang = luas * P["ambang"]
    return {
        "q": q_l_hari, "v_air": v_air, "v_lumpur": v_lumpur, "v_basah": v_basah,
        "luas": luas, "lebar": lebar, "panjang": panjang,
        "v_ambang": v_ambang, "v_total": v_basah + v_ambang, "tinggi": P["h_air"] + P["ambang"],
    }


# ---------------------------------------------------------------- hitung semua
def hitung_semua(df: pd.DataFrame, data: dict, P: dict) -> dict:
    fx = {r["fungsi"]: r for r in data["pemakaian_air"]}
    baris = []
    for _, r in df.iterrows():
        f, jml = _txt(r.get("Fungsi")), _num(r.get("Jumlah"))
        if f not in fx or jml <= 0:
            continue
        info = fx[f]
        baris.append({"Fungsi": f, "Jumlah": jml, "Satuan": info["per"], "Standar": info["nilai"],
                      "Q": jml * info["nilai"], "orang": info["orang"], "Keterangan": _txt(r.get("Keterangan"))})
    rinc = pd.DataFrame(baris, columns=["Fungsi", "Jumlah", "Satuan", "Standar", "Q", "orang", "Keterangan"])

    q_harian = float(rinc["Q"].sum())
    q_rencana = q_harian * (1 + P["faktor_puncak"])
    vol_m3 = q_rencana / 1000
    vol_rencana = bulat_atas(vol_m3, P["pembulatan"])

    q_dasar = q_rencana if P["dasar"] == DASAR_PUNCAK else q_harian
    limbah_total = q_dasar * P["faktor_limbah"]
    black = limbah_total * P["fraksi_black"]
    grey = limbah_total - black

    n_orang = float(rinc.loc[rinc["orang"], "Jumlah"].sum()) if not rinc.empty else 0.0
    n = n_orang if P["n_auto"] else float(P["n"])

    tc = _septik(limbah_total, n, P)     # sistem tercampur (grey + black)
    tp = _septik(black, n, P)            # sistem terpisah (black water saja)

    d = data["septik"]
    peringatan = []
    if not d["detensi_min"] <= P["td"] <= d["detensi_max"]:
        peringatan.append(f"Waktu detensi {P['td']:g} hari di luar rentang {d['detensi_min']}–{d['detensi_max']} hari.")
    if not d["lumpur_min"] <= P["ql"] <= d["lumpur_max"]:
        peringatan.append(f"Produksi lumpur {P['ql']:g} L/orang/tahun di luar rentang {d['lumpur_min']}–{d['lumpur_max']}.")
    if not d["pengurasan_min"] <= P["pp"] <= d["pengurasan_max"]:
        peringatan.append(f"Periode pengurasan {P['pp']:g} tahun di luar rentang {d['pengurasan_min']}–{d['pengurasan_max']}.")

    return {
        "rinc": rinc, "q_harian": q_harian, "q_rencana": q_rencana, "vol_m3": vol_m3, "vol_rencana": vol_rencana,
        "q_dasar": q_dasar, "limbah_total": limbah_total, "black": black, "grey": grey,
        "n": n, "n_orang": n_orang, "tc": tc, "tp": tp,
        "cek_black_sni": data["air_limbah"]["black_water_l_org_hari"] * n,
        "peringatan": peringatan, "P": P,
    }


# --------------------------------------------------- seksi untuk tabel HTML/UI
def susun_seksi(h: dict, data: dict) -> list[dict]:
    """Setiap seksi: judul, kolom, baris (list), tebal (indeks baris tebal)."""
    P, f = h["P"], fmt_id
    s = []

    rows = [[i + 1, r.Fungsi, f(r.Jumlah, 0 if float(r.Jumlah).is_integer() else 2), r.Satuan,
             f(r.Standar, 0), f(r.Q, 0)] for i, r in enumerate(h["rinc"].itertuples())]
    rows += [
        ["", "Total Q harian (rata-rata)", "", "", "", f(h["q_harian"], 0)],
        ["", f"Q rencana = Q harian × (1 + {f(P['faktor_puncak'] * 100, 0)}%)", "", "", "L/hari", f(h["q_rencana"], 0)],
        ["", "Q rencana", "", "", "m³/hari", f(h["vol_m3"], 3)],
        ["", f"VOLUME TANDON RENCANA (dibulatkan ke atas, kelipatan {f(P['pembulatan'], 2)} m³)", "", "", "m³",
         f(h["vol_rencana"], 2)],
    ]
    n = len(h["rinc"])
    s.append({"judul": "1. Kebutuhan Air Bersih (SNI 03-7065-2005 Tabel 1 · SNI 8153:2015)", "kunci": "air_bersih",
              "kolom": ["No", "Fungsi Bangunan", "Jumlah", "Satuan", "Standar (L/satuan/hari)", "Q (L/hari)"],
              "baris": rows, "tebal": [n, n + 3]})

    s.append({"judul": "2. Air Limbah (Pembagian Grey Water dan Black Water)", "kunci": "air_limbah",
              "kolom": ["Uraian", "Rumus", "Nilai", "Satuan"],
              "baris": [
                  ["Dasar perhitungan", P["dasar"], f(h["q_dasar"], 0), "L/hari"],
                  ["Total air limbah", f"Q dasar × {f(P['faktor_limbah'] * 100, 0)}%", f(h["limbah_total"], 1), "L/hari"],
                  ["Black water (kakus)", f"Total × {f(P['fraksi_black'] * 100, 0)}%", f(h["black"], 1), "L/hari"],
                  ["Grey water (kamar mandi, cuci, dapur)", "Total − Black water", f(h["grey"], 1), "L/hari"],
              ], "tebal": [1]})

    tc, tp = h["tc"], h["tp"]
    sp = data["septik"]
    s.append({"judul": "3. Air Kotor (Black Water) dan Tangki Septik (SNI 2398:2017)", "kunci": "air_kotor",
              "kolom": ["Uraian", "Rumus", "Tercampur", "Terpisah", "Satuan"],
              "baris": [
                  ["Jumlah pemakai (n)", "dari tabel / input", f(h["n"], 0), f(h["n"], 0), "orang"],
                  ["Debit air limbah masuk", "tercampur: grey+black; terpisah: black", f(tc["q"], 1), f(tp["q"], 1), "L/hari"],
                  ["Volume air", f"Q × waktu detensi ({P['td']:g} hari)", f(tc["v_air"], 3), f(tp["v_air"], 3), "m³"],
                  ["Volume lumpur", f"QL ({P['ql']:g}) × n × PP ({P['pp']:g} thn)", f(tc["v_lumpur"], 3), f(tp["v_lumpur"], 3), "m³"],
                  ["Volume basah", "V air + V lumpur", f(tc["v_basah"], 3), f(tp["v_basah"], 3), "m³"],
                  ["Luas denah", f"V basah / kedalaman air ({P['h_air']:g} m)", f(tc["luas"], 3), f(tp["luas"], 3), "m²"],
                  ["Lebar", f"√(Luas / rasio P:L = {P['rasio']:g})", f(tc["lebar"], 2), f(tp["lebar"], 2), "m"],
                  ["Panjang", "rasio × Lebar", f(tc["panjang"], 2), f(tp["panjang"], 2), "m"],
                  ["Volume ambang bebas", f"Luas × {P['ambang']:g} m", f(tc["v_ambang"], 3), f(tp["v_ambang"], 3), "m³"],
                  ["VOLUME TOTAL TANGKI", "V basah + V ambang bebas", f(tc["v_total"], 3), f(tp["v_total"], 3), "m³"],
                  ["Tinggi total", "kedalaman air + ambang bebas", f(tc["tinggi"], 2), f(tp["tinggi"], 2), "m"],
              ], "tebal": [9]})

    s.append({"judul": "4. Rekap", "kunci": "rekap",
              "kolom": ["Keterangan", "Jumlah", "Satuan"],
              "baris": [
                  ["Penghuni / pemakai", f(h["n"], 0), "orang"],
                  ["Jumlah pemakaian air harian", f(h["q_harian"], 0), "L/hari"],
                  ["Jumlah pemakaian air harian", f(h["q_harian"] / 1000, 3), "m³/hari"],
                  [f"Penggunaan peak time air harian {f(P['faktor_puncak'] * 100, 0)}%",
                   f(h["q_harian"] / 1000 * P["faktor_puncak"], 3), "m³/hari"],
                  ["VOLUME TOTAL", f(h["vol_m3"], 3), "m³"],
                  ["VOLUME TANDON RENCANA", f(h["vol_rencana"], 2), "m³"],
                  ["VOLUME TANGKI SEPTIK (tercampur)", f(tc["v_total"], 2), "m³"],
              ], "tebal": [4, 5, 6]})
    return s
