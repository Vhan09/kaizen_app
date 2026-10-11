"""Modul Resapan - perhitungan (tanpa Streamlit).

SNI 03-2453-2002 pasal 5:
  (1) Vab   = 0,855 x C x A x R                 R = tinggi hujan harian (mm/hari = L/m2/hari) -> /1000 untuk m3
  (2) Vrsp  = (te / 24) x A_total x K_rata      te = 0,9 x R^0,92 / 60 (jam)
  (3) K_rata = (K_alas x A_alas + K_dinding x A_dinding) / A_total      (K_dinding = Kh = 2 x Kv)
  (4) V_storasi = Vab - Vrsp
  (5) H_total = V_storasi / A_alas        (6) n = H_total / H_rencana
Lingkaran : A_alas = pi D^2/4 ; A_dinding = pi D H        Persegi : A_alas = P L ; A_dinding = 2 (P+L) H
Biopori   : (a) volume saja N = Vab / V_lubang (konservatif, seperti Excel); (b) adaptasi SNI dgn peresapan;
            (c) Brata & Nelistya N = I A / P (bila I dan P diisi).
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "resapan.json"
OK, TIDAK, BELUM = "MEMENUHI", "TIDAK MEMENUHI", "BELUM DICEK"
KP = ["Permukaan", "Luas (m²)"]


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


def bulat_atas(x: float) -> int:
    return int(math.ceil(round(x, 9)))


def opsi_permukaan(data: dict) -> list[str]:
    return [p["nama"] for p in data["permukaan"]]


def template_permukaan() -> pd.DataFrame:
    return pd.DataFrame([{"Permukaan": "Atap beton", "Luas (m²)": 28.67}])


def parameter_default(data: dict) -> dict:
    s = data["sni"]
    return {
        "R": data["hujan"]["R24"], "taman": False, "k_cmjam": s["k_default_cm_jam"], "rasio_kh": s["rasio_kh_kv"],
        "mat": 0.0, "kedap": False,
        "D": data["sumur"]["lingkaran"]["D"], "H1": data["sumur"]["lingkaran"]["H"],
        "P": data["sumur"]["persegi"]["P"], "L": data["sumur"]["persegi"]["L"], "H2": data["sumur"]["persegi"]["H"],
        "d_bio": data["biopori"]["d"], "t_bio": data["biopori"]["t"], "harga": data["biopori"]["harga"],
        "I_jam": 0.0, "P_lph": 0.0,
        "cek": {"datar": False, "tak_tercemar": False, "pondasi": False, "sumur_air": False, "septik": False, "perda": False},
    }


# --------------------------------------------------------------------- Vab
def hitung_vab(df: pd.DataFrame, data: dict, P: dict) -> dict:
    kat = {p["nama"]: p for p in data["permukaan"]}
    baris = []
    for _, r in df.iterrows():
        n, a = _txt(r.get("Permukaan")), _num(r.get("Luas (m²)"))
        if n not in kat or a <= 0:
            continue
        p = kat[n]
        dihitung = p["tadah"] or P["taman"]
        baris.append({"Permukaan": n, "A": a, "C": p["c"], "CA": p["c"] * a, "dihitung": dihitung})
    rinc = pd.DataFrame(baris, columns=["Permukaan", "A", "C", "CA", "dihitung"])
    h = rinc[rinc["dihitung"]] if not rinc.empty else rinc
    a_tadah = float(h["A"].sum()) if not h.empty else 0.0
    ca = float(h["CA"].sum()) if not h.empty else 0.0
    R = P["R"]
    vab = data["sni"]["faktor_vab"] * ca * R / 1000
    rot_v = a_tadah / data["sni"]["rot_m2_per_m3"]
    return {"rinc": rinc, "A_tadah": a_tadah, "CA": ca, "C_rata": ca / a_tadah if a_tadah else 0.0, "R": R,
            "vab": vab, "vab_L": vab * 1000, "rot_v": rot_v, "te": te_jam(R, data)}


def te_jam(R: float, data: dict) -> float:
    s = data["sni"]
    return s["te_koef"] * (R ** s["te_pangkat"]) / 60


# ------------------------------------------------------------------ sumur
def _k_rata(k_alas, k_dinding, a_alas, a_dinding, kedap):
    if kedap:
        return k_alas, a_alas, a_alas
    at = a_alas + a_dinding
    return (k_alas * a_alas + k_dinding * a_dinding) / at, at, a_alas


def _g(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def sumur(bentuk: str, vab_m3: float, te: float, P: dict, data: dict) -> dict:
    kv = P["k_cmjam"] * 24 / 100                      # m/hari
    kh = kv * P["rasio_kh"]
    if bentuk == "lingkaran":
        D, H = P["D"], P["H1"]
        a_alas, a_dinding = math.pi * D ** 2 / 4, math.pi * D * H
        dim = f"Ø {_g(D)} m × {_g(H)} m"
    else:
        Pp, L, H = P["P"], P["L"], P["H2"]
        a_alas, a_dinding = Pp * L, 2 * (Pp + L) * H
        dim = f"{_g(Pp)} × {_g(L)} m × {_g(H)} m"
    k_rata, a_total, _ = _k_rata(kv, kh, a_alas, a_dinding, P["kedap"])
    v_rsp = te / 24 * a_total * k_rata
    v_sto = vab_m3 - v_rsp
    h_total = v_sto / a_alas if a_alas else 0.0
    n_raw = h_total / H if H else 0.0
    n = max(1, bulat_atas(n_raw)) if n_raw > 0 else 1
    v_unit = a_alas * H
    kap = n * (v_unit + v_rsp)
    return {"bentuk": bentuk, "dim": dim, "H": H, "kv": kv, "kh": kh, "a_alas": a_alas, "a_dinding": a_dinding,
            "a_total": a_total, "k_rata": k_rata, "te": te, "v_rsp": v_rsp, "v_sto": v_sto, "h_total": h_total,
            "n_raw": n_raw, "n": n, "v_unit": v_unit, "kap": kap, "rasio_kap": kap / vab_m3 if vab_m3 else None,
            "v_tampung": n * v_unit, "kedap": P["kedap"]}


# ----------------------------------------------------------------- biopori
def biopori(vab_m3: float, a_tadah: float, te: float, P: dict, data: dict) -> dict:
    d, t = P["d_bio"], P["t_bio"]
    v_l = math.pi * (d / 2) ** 2 * t
    a_alas, a_dinding = math.pi * d ** 2 / 4, math.pi * d * t
    kv = P["k_cmjam"] * 24 / 100
    k_rata, a_total, _ = _k_rata(kv, kv * P["rasio_kh"], a_alas, a_dinding, False)
    v_rsp = te / 24 * a_total * k_rata
    n1 = bulat_atas(vab_m3 / v_l) if v_l else 0
    n2 = bulat_atas(vab_m3 / (v_l + v_rsp)) if v_l else 0
    n_rot = bulat_atas((a_tadah / data["sni"]["rot_m2_per_m3"]) / v_l) if v_l else 0
    n3 = None
    if P["I_jam"] > 0 and P["P_lph"] > 0:
        n3 = bulat_atas(P["I_jam"] * a_tadah / P["P_lph"])
    b = data["biopori"]
    w = []
    if not b["d_min"] <= d <= b["d_maks"]:
        w.append(f"Diameter {fmt_id(d * 100, 1)} cm di luar acuan {b['d_min'] * 100:g}–{b['d_maks'] * 100:g} cm.")
    if t > b["t_acuan"] + 1e-9:
        w.append(f"Kedalaman {_g(t)} m melebihi acuan sekitar {b['t_acuan'] * 100:g} cm; periksa muka air tanah dan kelayakan pemasangan.")
    if P["mat"] > 0 and t >= P["mat"]:
        w.append(f"Kedalaman biopori {t:g} m sama atau lebih dalam dari muka air tanah ({_g(P['mat'])} m).")
    return {"d": d, "t": t, "v_lubang": v_l, "a_alas": a_alas, "a_dinding": a_dinding, "k_rata": k_rata, "v_rsp": v_rsp,
            "v_total": v_l + v_rsp, "n1": n1, "n2": n2, "n3": n3, "n_rot": n_rot, "biaya1": n1 * P["harga"],
            "biaya2": n2 * P["harga"], "harga": P["harga"], "peringatan": w, "luas_serap_1": a_dinding + a_alas}


# --------------------------------------------------------------- persyaratan
def persyaratan(P: dict, data: dict) -> list[dict]:
    s = data["sni"]
    k = P["k_cmjam"]
    c = P["cek"]
    mat = P["mat"]
    hmax = max(P["H1"], P["H2"])

    def man(ok):
        return OK if ok else BELUM

    return [
        {"teks": f"Permeabilitas tanah ≥ {s['k_min_cm_jam']:g} cm/jam", "acuan": "SNI 03-2453-2002 pasal 4.2",
         "status": OK if k >= s["k_min_cm_jam"] else TIDAK, "ket": f"K = {fmt_id(k, 2)} cm/jam ({fmt_id(k * 24 / 100, 3)} m/hari)"},
        {"teks": f"Muka air tanah ≥ {s['mat_min']:g} m pada musim hujan", "acuan": "SNI 03-2453-2002 pasal 4.2",
         "status": (OK if mat >= s["mat_min"] else TIDAK) if mat > 0 else BELUM,
         "ket": f"MAT = {fmt_id(mat, 2)} m" if mat > 0 else "isi kedalaman muka air tanah"},
        {"teks": "Kedalaman sumur rencana < muka air tanah", "acuan": "SNI 03-2453-2002 pasal 5.2",
         "status": (OK if hmax < mat else TIDAK) if mat > 0 else BELUM,
         "ket": f"H rencana maks. {fmt_id(hmax, 2)} m" if mat > 0 else "isi kedalaman muka air tanah"},
        {"teks": "Lahan relatif datar", "acuan": "SNI 03-2453-2002 pasal 4.1", "status": man(c["datar"]), "ket": "konfirmasi lapangan"},
        {"teks": "Air yang masuk adalah air hujan tidak tercemar", "acuan": "SNI 03-2453-2002 pasal 4.1", "status": man(c["tak_tercemar"]), "ket": "konfirmasi desain"},
        {"teks": f"Jarak ke pondasi bangunan ≥ {s['jarak'][1]['m']} m", "acuan": "SNI 03-2453-2002 Tabel 1", "status": man(c["pondasi"]), "ket": "ukur tepi ke tepi"},
        {"teks": f"Jarak ke sumur air bersih / sumur resapan lain ≥ {s['jarak'][0]['m']} m", "acuan": "SNI 03-2453-2002 Tabel 1", "status": man(c["sumur_air"]), "ket": "ukur tepi ke tepi"},
        {"teks": f"Jarak ke bidang/sumur resapan tangki septik ≥ {s['jarak'][2]['m']} m", "acuan": "SNI 03-2453-2002 Tabel 1", "status": man(c["septik"]), "ket": "ukur tepi ke tepi"},
        {"teks": "Memenuhi peraturan daerah setempat", "acuan": "SNI 03-2453-2002 pasal 4.1", "status": man(c["perda"]), "ket": "konfirmasi dinas"},
    ]


# ------------------------------------------------------------------- semua
def hitung_semua(df: pd.DataFrame, data: dict, P: dict) -> dict:
    v = hitung_vab(df, data, P)
    if v["A_tadah"] <= 0:
        return {"vab": v, "kosong": True, "P": P}
    sl = sumur("lingkaran", v["vab"], v["te"], P, data)
    sp = sumur("persegi", v["vab"], v["te"], P, data)
    bp = biopori(v["vab"], v["A_tadah"], v["te"], P, data)
    req = persyaratan(P, data)
    w = list(bp["peringatan"])
    for s, nama in ((sl, "lingkaran"), (sp, "persegi")):
        if s["v_sto"] <= 0:
            w.append(f"Sumur {nama}: peresapan selama hujan sudah melebihi Vab; dipakai minimal 1 sumur.")
        if s["n_raw"] > 0 and s["n"] - s["n_raw"] < 1e-9 and False:
            pass
    return {"vab": v, "lingkaran": sl, "persegi": sp, "biopori": bp, "req": req, "P": P, "kosong": False,
            "peringatan": w, "req_tidak": sum(1 for r in req if r["status"] == TIDAK),
            "req_belum": sum(1 for r in req if r["status"] == BELUM)}


def opsi_ringkas(h: dict) -> pd.DataFrame:
    v, sl, sp, bp = h["vab"], h["lingkaran"], h["persegi"], h["biopori"]
    baris = [
        ("Sumur resapan lingkaran", sl["dim"], sl["n"], sl["v_tampung"], sl["kap"], sl["kap"] / v["vab"]),
        ("Sumur resapan persegi", sp["dim"], sp["n"], sp["v_tampung"], sp["kap"], sp["kap"] / v["vab"]),
        ("Biopori — metode volume", f"Ø {fmt_id(bp['d'] * 100, 1)} cm × {_g(bp['t'])} m", bp["n1"], bp["n1"] * bp["v_lubang"],
         bp["n1"] * bp["v_lubang"], bp["n1"] * bp["v_lubang"] / v["vab"]),
        ("Biopori — dengan peresapan", f"Ø {fmt_id(bp['d'] * 100, 1)} cm × {_g(bp['t'])} m", bp["n2"], bp["n2"] * bp["v_lubang"],
         bp["n2"] * bp["v_total"], bp["n2"] * bp["v_total"] / v["vab"]),
    ]
    return pd.DataFrame(baris, columns=["Opsi", "Dimensi", "N", "V_tampung", "Kapasitas", "Rasio"])


def kesimpulan(h: dict) -> str:
    if h["kosong"]:
        return ""
    v, sl, sp, bp = h["vab"], h["lingkaran"], h["persegi"], h["biopori"]
    s = (f"Volume andil banjir (Vab) dihitung dengan rumus SNI 03-2453-2002 dan Permen PU 11/PRT/M/2014: "
         f"Vab = 0,855 × {fmt_id(v['CA'])} × {fmt_id(v['R'], 0)} mm/hari ÷ 1000 = {fmt_id(v['vab'], 3)} m³ "
         f"(luas tadah {fmt_id(v['A_tadah'])} m²). Kebutuhan resapan: {sl['n']} sumur lingkaran ({sl['dim']}), "
         f"atau {sp['n']} sumur persegi ({sp['dim']}), atau {bp['n1']} lubang biopori bila hanya memperhitungkan volume "
         f"({bp['n2']} lubang bila memperhitungkan peresapan). ")
    if h["req_tidak"]:
        s += f"{h['req_tidak']} persyaratan teknis tidak terpenuhi. "
    elif h["req_belum"]:
        s += f"{h['req_belum']} persyaratan teknis lokasi masih perlu dikonfirmasi. "
    return s + "Pembanding aturan praktis 1 m³ resapan per 25 m² bidang tadah bukan bagian SNI."
