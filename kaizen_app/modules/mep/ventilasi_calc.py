"""Perhitungan penghawaan alami & ventilasi mekanis (sheet 'Penghawaan Ruangan') - tanpa Streamlit.

Dasar: SNI 03-6572-2001 "Tata cara perancangan sistem ventilasi dan pengkondisian udara
pada bangunan gedung" (teks dibaca langsung dari dokumen standar):
  4.2    ruang yang layak ditempati harus punya ventilasi alami (4.3) ATAU ventilasi mekanis (4.4)
  4.3.2  ventilasi alami: bukaan tidak kurang dari 5% luas lantai ruangan, menghadap ruang luar /
         teras terbuka / ruang bersebelahan (4.3.3)
  4.3.3  ventilasi dari ruang bersebelahan: ruang yang diventilasi bukan kompartemen sanitasi (a.1)
  4.3.5  b.2 ruang berkloset yang tidak berhubungan dengan udara luar wajib exhaust mekanis
  4.4.1  Tabel 4.4.1 pertukaran udara/jam: kamar mandi/peturasan 10, dapur 20, lobi/koridor/tangga 4

Rumus:
  Av = jumlah x P x L (bukaan)        Ar = P x L (ruang)
  Syarat Av minimum = rasio x Ar      Selisih = Av - syarat
  V = Ar x T                          ACH = Q(m3/jam) / V     Q(m3/jam) = Q(m3/menit) x 60
"""
from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------- konstanta
JENIS_HUNIAN = "Ruang hunian"
JENIS_SANITASI = "Kamar mandi / WC"
JENIS_DAPUR = "Dapur"
JENIS_TANGGA = "Tangga / koridor"
JENIS_TERBUKA = "Ruang terbuka"
JENIS = [JENIS_HUNIAN, JENIS_SANITASI, JENIS_DAPUR, JENIS_TANGGA, JENIS_TERBUKA]

# ACH minimum ventilasi mekanis (SNI 03-6572-2001 Tabel 4.4.1). 0 = tidak ada acuan di SNI.
ACH_BAWAAN = {JENIS_HUNIAN: 0.0, JENIS_SANITASI: 10.0, JENIS_DAPUR: 20.0, JENIS_TANGGA: 4.0, JENIS_TERBUKA: 0.0}
ACH_KET = {
    JENIS_HUNIAN: "Tabel 4.4.1 tidak mengatur kamar tidur / ruang keluarga; isi bila ada acuan proyek",
    JENIS_SANITASI: "Tabel 4.4.1: kamar mandi, peturasan = 10 kali/jam",
    JENIS_DAPUR: "Tabel 4.4.1: dapur = 20 kali/jam",
    JENIS_TANGGA: "Tabel 4.4.1: lobi, koridor, tangga = 4 kali/jam",
    JENIS_TERBUKA: "Ruang terbuka tidak dihitung",
}

METODE = ["Alami", "Exhaust", "Alami + Exhaust"]
HADAP = ["Ruang luar", "Ruang bersebelahan"]

DASAR_SNI = "5% - SNI 03-6572-2001 pasal 4.3.2"
DASAR_10 = "10% - acuan konservatif (Excel acuan / rumah sehat)"
DASAR_KUSTOM = "Kustom"
DASAR_OPSI = [DASAR_SNI, DASAR_10, DASAR_KUSTOM]
DASAR_BAWAAN = DASAR_SNI
KUSTOM_BAWAAN = 5.0  # persen

ST_SESUAI = "Sesuai"
ST_EXH = "Sesuai (Exhaust)"
ST_TIDAK = "Tidak Sesuai"
ST_TERBUKA = "Ruang Terbuka"
ST_TINJAU = "Perlu Tinjauan"
ST_DATA = "Data Belum Lengkap"

C_LANTAI, C_NAMA, C_JENIS, C_METODE, C_HADAP = "Lantai", "Ruangan", "Jenis", "Metode", "Bukaan menghadap"
C_JML, C_VP, C_VL = "Jml bukaan", "P bukaan (m)", "L bukaan (m)"
C_RP, C_RL, C_T, C_Q = "P ruang (m)", "L ruang (m)", "T plafon (m)", "Q exhaust (m³/menit)"
KOLOM_RUANG = [C_LANTAI, C_NAMA, C_JENIS, C_METODE, C_HADAP, C_JML, C_VP, C_VL, C_RP, C_RL, C_T, C_Q]
NUM_RUANG = [C_JML, C_VP, C_VL, C_RP, C_RL, C_T, C_Q]
C_ACH_JENIS, C_ACH = "Jenis", "ACH minimum"

PROYEK_BAWAAN = {
    "pekerjaan": "PERENCANAAN PEMBANGUNAN RUMAH TINGGAL 2 LANTAI TYPE 55",
    "lokasi": "KOTA MAKASSAR",
    "tahun": "2026",
    "item": "PERHITUNGAN PENGHAWAAN ALAMI PADA BANGUNAN",
}

TINGGI_BAWAAN = 3.0  # m


# ---------------------------------------------------------------- data bawaan
def _r(lantai, nama, jenis, metode, hadap, jml, vp, vl, rp, rl, t=TINGGI_BAWAAN, q=0.0) -> dict:
    return dict(zip(KOLOM_RUANG, [lantai, nama, jenis, metode, hadap, jml, vp, vl, rp, rl, t, q]))


def ruang_bawaan() -> pd.DataFrame:
    """Contoh dari Excel acuan. Catatan: Excel menulis (2*0,47)x(2*1,2) dan (2*0,55)x(2*1,05);
    hasilnya sama dengan 4 bukaan berukuran 0,47x1,2 dan 0,55x1,05, sehingga ditulis sebagai Jml = 4."""
    L1, L2 = "Lantai Satu", "Lantai Dua"
    rows = [
        _r(L1, "Kamar Mandi", JENIS_SANITASI, "Alami", "Ruang luar", 1, 0.4, 0.2, 2, 1),
        _r(L1, "Ruang Makan & Dapur", JENIS_DAPUR, "Alami", "Ruang luar", 4, 0.47, 1.2, 3.3, 2.2),
        _r(L1, "Ruang Keluarga", JENIS_HUNIAN, "Alami", "Ruang luar", 1, 0.5, 2.4, 3.3, 2.6),
        _r(L1, "Tangga", JENIS_TANGGA, "Alami", "Ruang luar", 0, 0, 0, 3.7, 0.95),
        _r(L1, "Garasi", JENIS_TERBUKA, "Alami", "Ruang luar", 0, 0, 0, 0, 0),
        _r(L1, "Teras Depan", JENIS_TERBUKA, "Alami", "Ruang luar", 0, 0, 0, 0, 0),
        _r(L1, "Taman Belakang", JENIS_TERBUKA, "Alami", "Ruang luar", 0, 0, 0, 0, 0),
        _r(L2, "Kamar Tidur Kecil", JENIS_HUNIAN, "Alami", "Ruang luar", 1, 1.35, 0.4, 2.75, 2),
        _r(L2, "Kamar Mandi Kecil", JENIS_SANITASI, "Alami", "Ruang luar", 1, 0.4, 0.2, 1.7, 1.4),
        _r(L2, "Kamar Mandi Utama", JENIS_SANITASI, "Exhaust", "Ruang luar", 0, 0, 0, 1.75, 1.5, q=8.1),
        _r(L2, "Kamar Tidur Utama", JENIS_HUNIAN, "Alami", "Ruang luar", 4, 0.55, 1.05, 3.45, 3.15),
    ]
    return normalisasi_ruang(pd.DataFrame(rows))


def ach_bawaan() -> pd.DataFrame:
    return pd.DataFrame({C_ACH_JENIS: JENIS, C_ACH: [ACH_BAWAAN[j] for j in JENIS]})


# ---------------------------------------------------------------- normalisasi
def normalisasi_ruang(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return normalisasi_ruang(pd.DataFrame([_r("Lantai Satu", "Ruangan 1", JENIS_HUNIAN, "Alami", "Ruang luar",
                                                  0, 0, 0, 0, 0)]))
    df = df.reindex(columns=KOLOM_RUANG).copy()
    for c in (C_LANTAI, C_NAMA):
        df[c] = df[c].fillna("").astype(str)
    df[C_JENIS] = df[C_JENIS].where(df[C_JENIS].isin(JENIS), JENIS_HUNIAN)
    df[C_METODE] = df[C_METODE].where(df[C_METODE].isin(METODE), "Alami")
    df[C_HADAP] = df[C_HADAP].where(df[C_HADAP].isin(HADAP), "Ruang luar")
    for c in NUM_RUANG:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).clip(lower=0).astype(float)
    return df.reset_index(drop=True)


def normalisasi_ach(df: pd.DataFrame | None) -> pd.DataFrame:
    """Selalu 5 baris sesuai JENIS; nilai kosong / negatif kembali ke bawaan."""
    if df is None or len(df) == 0 or C_ACH_JENIS not in df.columns:
        return ach_bawaan()
    dasar = {r[C_ACH_JENIS]: r[C_ACH] for _, r in df.iterrows()}
    nilai = []
    for j in JENIS:
        try:
            v = float(dasar.get(j, ACH_BAWAAN[j]))
        except (TypeError, ValueError):
            v = ACH_BAWAAN[j]
        nilai.append(v if v >= 0 and v == v else ACH_BAWAAN[j])
    return pd.DataFrame({C_ACH_JENIS: JENIS, C_ACH: nilai})


def rasio_dari(dasar: str, kustom_persen: float) -> float:
    if dasar == DASAR_10:
        return 0.10
    if dasar == DASAR_KUSTOM:
        try:
            return min(max(float(kustom_persen), 0.0), 100.0) / 100.0
        except (TypeError, ValueError):
            return KUSTOM_BAWAAN / 100.0
    return 0.05


# ---------------------------------------------------------------- perhitungan
def _status(jenis, metode, adj, ar, vol, alami_txt, exh_txt) -> str:
    """Logika status (sama persis dengan rumus pada file Excel)."""
    if jenis == JENIS_TERBUKA:
        return ST_TERBUKA
    if ar <= 0:
        return ST_DATA
    if "Exhaust" in metode and vol <= 0:
        return ST_DATA
    sanitasi = jenis == JENIS_SANITASI
    s_alami = ""
    if alami_txt == "Ya" and not (sanitasi and adj):
        s_alami = ST_TINJAU if adj else ST_SESUAI
    if metode == "Exhaust":
        return ST_EXH if exh_txt == "Ya" else ST_TIDAK
    if metode == "Alami + Exhaust":
        if s_alami == ST_SESUAI:
            return ST_SESUAI
        if exh_txt == "Ya":
            return ST_EXH
        return s_alami or ST_TIDAK
    return s_alami or ST_TIDAK


def _g(x: float, nd: int = 3) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def _keterangan(b: dict) -> str:
    st, jenis, metode = b["status"], b["jenis"], b["metode"]
    sanitasi = jenis == JENIS_SANITASI
    adj = b["hadap"] == "Ruang bersebelahan"
    if st == ST_TERBUKA:
        return "Ruang terbuka: tidak memerlukan perhitungan ventilasi (SNI 4.3.2 b)."
    if st == ST_DATA:
        return "Lengkapi dimensi ruang (dan tinggi plafon bila memakai exhaust)."
    if st == ST_SESUAI:
        return f"Av {_g(b['av'])} m² ≥ syarat {_g(b['av_min'])} m² (rasio {_g(b['rasio'] * 100, 1)}%)."
    if st == ST_TINJAU:
        return ("Ventilasi diambil dari ruang bersebelahan: pastikan memenuhi SNI 03-6572-2001 pasal 4.3.3 "
                "(bukaan ruang sebelah memadai terhadap gabungan luas kedua ruang).")
    if st == ST_EXH:
        if b["ach_min"] > 0:
            return f"ACH {_g(b['ach'], 1)} ≥ {_g(b['ach_min'], 0)} kali/jam (SNI Tabel 4.4.1)."
        return f"ACH {_g(b['ach'], 1)} kali/jam (SNI tidak memberi acuan ACH untuk jenis ini)."
    # ST_TIDAK
    if metode == "Exhaust":
        pesan = f"ACH {_g(b['ach'], 1)} kurang dari {_g(b['ach_min'], 0)} kali/jam"
        return pesan + (f"; Q minimum {_g(b['q_min'], 0)} m³/jam." if b["q_min"] > 0 else ".")
    if sanitasi and adj and b["alami_txt"] == "Ya":
        return ("Kompartemen sanitasi tidak boleh mengambil ventilasi dari ruang bersebelahan "
                "(SNI 4.3.3 a.1): arahkan bukaan ke ruang luar atau pasang exhaust.")
    if b["av"] <= 0:
        pesan = "Tidak ada bukaan ventilasi."
    else:
        pesan = f"Av {_g(b['av'])} m² kurang {_g(b['tambah'])} m² dari syarat {_g(b['av_min'])} m²."
    pesan += f" Tambah bukaan ≥ {_g(b['tambah'])} m²"
    if b["q_min"] > 0 and b["vol"] > 0:
        pesan += f" atau pasang exhaust ≥ {_g(b['q_min'], 0)} m³/jam (SNI Tabel 4.4.1)."
    else:
        pesan += "."
    return pesan


def hitung(ruang: pd.DataFrame, rasio: float, ach_tabel: pd.DataFrame) -> dict:
    ruang = normalisasi_ruang(ruang)
    ach_map = {r[C_ACH_JENIS]: float(r[C_ACH]) for _, r in normalisasi_ach(ach_tabel).iterrows()}
    rasio = float(rasio)
    baris = []
    for _, r in ruang.iterrows():
        jenis, metode, hadap = r[C_JENIS], r[C_METODE], r[C_HADAP]
        av = r[C_JML] * r[C_VP] * r[C_VL]
        ar = r[C_RP] * r[C_RL]
        vol = ar * r[C_T]
        q_jam = r[C_Q] * 60.0
        ach = q_jam / vol if vol > 0 else 0.0
        ach_min = ach_map.get(jenis, 0.0)
        av_min = rasio * ar
        selisih = av - av_min
        alami_txt = "-" if ar <= 0 else ("Ya" if round(selisih, 6) >= 0 else "Tidak")
        if q_jam <= 0:
            exh_txt = "-"
        elif vol <= 0:
            exh_txt = "Tidak"
        else:
            exh_txt = "Ya" if (ach_min <= 0 or round(ach - ach_min, 6) >= 0) else "Tidak"
        status = _status(jenis, metode, hadap == "Ruang bersebelahan", ar, vol, alami_txt, exh_txt)
        tambah = (-selisih if (ar > 0 and round(selisih, 6) < 0 and status == ST_TIDAK and metode != "Exhaust")
                  else 0.0)
        b = {
            "lantai": r[C_LANTAI], "nama": r[C_NAMA], "jenis": jenis, "metode": metode, "hadap": hadap,
            "jml": r[C_JML], "vp": r[C_VP], "vl": r[C_VL], "av": av,
            "rp": r[C_RP], "rl": r[C_RL], "ar": ar, "rasio": av / ar if ar > 0 else 0.0,
            "av_min": av_min, "selisih": selisih, "alami_txt": alami_txt,
            "t": r[C_T], "vol": vol, "q_menit": r[C_Q], "q_jam": q_jam, "ach": ach,
            "ach_min": ach_min, "q_min": ach_min * vol, "exh_txt": exh_txt,
            "status": status, "tambah": tambah,
        }
        b["ket"] = _keterangan(b)
        baris.append(b)

    hitungan = {s: sum(1 for b in baris if b["status"] == s)
                for s in (ST_SESUAI, ST_EXH, ST_TIDAK, ST_TINJAU, ST_TERBUKA, ST_DATA)}
    return {
        "rasio": rasio, "baris": baris, "hitungan": hitungan,
        "dinilai": len(baris) - hitungan[ST_TERBUKA],
        "kelompok": kelompok(baris),
        "exhaust": [b for b in baris if "Exhaust" in b["metode"] and b["jenis"] != JENIS_TERBUKA],
        "perbaikan": [b for b in baris if b["status"] in (ST_TIDAK, ST_TINJAU, ST_DATA)],
    }


def kelompok(baris: list[dict]) -> list[tuple[str, list[dict]]]:
    """Kelompokkan per lantai, urutan kemunculan dipertahankan."""
    hasil: dict[str, list[dict]] = {}
    for b in baris:
        hasil.setdefault(b["lantai"].strip() or "Tanpa Lantai", []).append(b)
    return list(hasil.items())


def bandingkan(ruang: pd.DataFrame, ach_tabel: pd.DataFrame) -> list[dict]:
    """Rekap kepatuhan bila dasar rasio 5% (SNI) dibanding 10% (konservatif)."""
    hasil = []
    for nama, rasio in (("5% (SNI 03-6572-2001 pasal 4.3.2)", 0.05), ("10% (acuan konservatif)", 0.10)):
        h = hitung(ruang, rasio, ach_tabel)
        c = h["hitungan"]
        hasil.append({"dasar": nama, "rasio": rasio, "sesuai": c[ST_SESUAI] + c[ST_EXH], "tidak": c[ST_TIDAK],
                      "tinjau": c[ST_TINJAU], "terbuka": c[ST_TERBUKA], "dinilai": h["dinilai"]})
    return hasil


# ---------------------------------------------------------------- muat state
def muat_state(saved: dict | None, saved_listrik: dict | None = None) -> dict:
    saved = saved or {}
    dasar = dict(PROYEK_BAWAAN)
    for k in ("pekerjaan", "lokasi", "tahun"):
        v = ((saved_listrik or {}).get("proyek") or {}).get(k)
        if v:
            dasar[k] = v
    try:
        kustom = float(saved.get("kustom", KUSTOM_BAWAAN))
    except (TypeError, ValueError):
        kustom = KUSTOM_BAWAAN
    return {
        "proyek": {**dasar, **(saved.get("proyek") or {})},
        "dasar": saved.get("dasar") if saved.get("dasar") in DASAR_OPSI else DASAR_BAWAAN,
        "kustom": kustom,
        "ach": normalisasi_ach(pd.DataFrame(saved["ach"]) if saved.get("ach") else None),
        "ruang": normalisasi_ruang(pd.DataFrame(saved["ruang"]) if saved.get("ruang") else ruang_bawaan()),
    }
