"""Modul Resapan - tampilan HTML (memakai sistem desain bersama desain.py)."""
from __future__ import annotations

import base64
from html import escape

from modules import desain as ds
from modules.desain import chip, kpi, sec
from modules.resapan_calc import BELUM, OK, TIDAK, fmt_id, kesimpulan, opsi_ringkas
from modules.resapan_skema import skema_png

_TON = {OK: "good", TIDAK: "bad", BELUM: "warn"}


def _tbl(kolom, baris, tebal=(), kelas=None):
    """tabel generik: baris = list of list (sel sudah berupa html/teks)."""
    o = ['<table class="t"><tr>' + "".join(f"<th>{escape(k)}</th>" for k in kolom) + "</tr>"]
    for i, r in enumerate(baris):
        cls = ' class="tot"' if i in tebal else ""
        o.append(f"<tr{cls}>" + "".join(f"<td{(' class=' + chr(34) + kelas[j] + chr(34)) if kelas and kelas[j] else ''}>{c}</td>"
                                        for j, c in enumerate(r)) + "</tr>")
    return "".join(o) + "</table>"


def _sek_vab(h, data) -> str:
    v, P = h["vab"], h["P"]
    f = fmt_id
    o = [sec(1, "Volume Andil Banjir / Volume Wajib Kelola Air Hujan"),
         '<div class="card"><b>Rumus SNI 03-2453-2002 (1) · Permen PU 11/PRT/M/2014</b>'
         '<div class="formula">Vab = 0,855 × Σ(C × A) × R ÷ 1000'
         '<small>Vab = volume andil banjir (m³) · C = koefisien limpasan · A = luas bidang tadah (m²) · R = tinggi hujan harian (mm/hari = L/m²/hari)</small></div>'
         '<div class="note">Bila seluruh persil tertutup bangunan dan perkerasan, Vab sama dengan volume wajib kelola (Vwk). '
         'Bila ada pekarangan/ruang hijau yang menyerap, Vab hanya dihitung dari area bangunan dan perkerasan (taman tidak dihitung).</div></div>']
    rows = []
    for r in v["rinc"].itertuples():
        st = chip(OK) if r.dihitung else '<span class="chip mute">TIDAK DIHITUNG</span>'
        rows.append([escape(r.Permukaan), f(r.A), f(r.C), f(r.CA) if r.dihitung else "–", st])
    rows.append(["TOTAL bidang tadah", f(v["A_tadah"]), f(v["C_rata"]) + " (rata-rata)", f(v["CA"]), ""])
    o.append(_tbl(["Permukaan", "A (m²)", "C", "C × A", "Dalam Vab"], rows, tebal=(len(rows) - 1,), kelas=[None, "n", "n", "n", "c"]))
    o.append(f'<div class="formula">Vab = 0,855 × {f(v["CA"])} × {f(v["R"], 0)} ÷ 1000 = <b>{f(v["vab"], 3)} m³</b> = <b>{f(v["vab_L"], 0)} liter</b>'
             f'<small>R = {f(v["R"], 0)} mm/hari ({escape(data["hujan"]["kota"])}, dari Excel). {escape(data["hujan"]["catatan"])}</small></div>')
    o.append('<div class="card"><b>Pembanding aturan praktis (bukan SNI)</b>'
             f'<div class="formula">1 m³ resapan per {data["sni"]["rot_m2_per_m3"]} m² bidang tadah: {f(v["A_tadah"])} ÷ {data["sni"]["rot_m2_per_m3"]} = '
             f'<b>{f(v["rot_v"], 3)} m³</b></div>'
             '<div class="note">Satuan pada Excel “25 m³ luas atap” seharusnya m². Nilai ini jauh lebih kecil dari Vab SNI '
             f'({f(v["vab"], 3)} m³), jadi tidak dipakai sebagai dasar utama.</div></div>')
    return "".join(o)


def _sek_persyaratan(h) -> str:
    rows = [[escape(r["teks"]), escape(r["acuan"]), escape(r["ket"]), chip(r["status"])] for r in h["req"]]
    return (sec(2, "Persyaratan Teknis Lokasi (SNI 03-2453-2002)")
            + _tbl(["Persyaratan", "Acuan", "Keterangan", "Status"], rows, kelas=[None, None, None, "c"]))


def _sek_sumur(h, data, bentuk: str, no: int) -> str:
    s = h[bentuk]
    P, v = h["P"], h["vab"]
    f = fmt_id
    judul = "Sumur Resapan Berpenampang Lingkaran" if bentuk == "lingkaran" else "Sumur Resapan Berpenampang Persegi"
    o = [sec(no, f"{judul} — {s['dim']}")]
    if bentuk == "lingkaran":
        d_ = P["D"]
        ge = [("Luas alas", "A alas = ¼ π D²", f"¼ × π × {f(d_)}²", f(s["a_alas"], 3), "m²"),
              ("Luas dinding", "A dinding = π D H", f"π × {f(d_)} × {f(s['H'])}", f(s["a_dinding"], 3), "m²")]
    else:
        ge = [("Luas alas", "A alas = P × L", f"{f(P['P'])} × {f(P['L'])}", f(s["a_alas"], 3), "m²"),
              ("Luas dinding", "A dinding = 2 (P + L) H", f"2 × ({f(P['P'])} + {f(P['L'])}) × {f(s['H'])}", f(s["a_dinding"], 3), "m²")]
    if s["kedap"]:
        ket_k = [("K alas (Kv)", "K = permeabilitas vertikal", f"{f(P['k_cmjam'])} cm/jam × 24 ÷ 100", f(s["kv"], 3), "m/hari"),
                 ("A total (alas saja)", "dinding kedap", "A alas", f(s["a_total"], 3), "m²"),
                 ("K rata-rata", "dinding kedap → K = Kv", "–", f(s["k_rata"], 3), "m/hari")]
    else:
        ket_k = [("K alas (Kv)", "Kv = K tanah", f"{f(P['k_cmjam'])} cm/jam × 24 ÷ 100", f(s["kv"], 3), "m/hari"),
                 ("K dinding (Kh)", f"Kh = {f(P['rasio_kh'], 1)} × Kv", f"{f(P['rasio_kh'], 1)} × {f(s['kv'], 3)}", f(s["kh"], 3), "m/hari"),
                 ("A total", "A alas + A dinding", f"{f(s['a_alas'], 3)} + {f(s['a_dinding'], 3)}", f(s["a_total"], 3), "m²"),
                 ("K rata-rata (3)", "(Kv·A alas + Kh·A dinding) / A total",
                  f"({f(s['kv'], 3)}×{f(s['a_alas'], 3)} + {f(s['kh'], 3)}×{f(s['a_dinding'], 3)}) / {f(s['a_total'], 3)}", f(s["k_rata"], 3), "m/hari")]
    baris = [
        ["(1)", "Volume andil banjir", "Vab", f"dari bagian 1", f(v["vab"], 3), "m³"],
        ["", "Durasi hujan efektif", "te = 0,9 × R^0,92 / 60", f"0,9 × {f(v['R'], 0)}^0,92 / 60", f(s["te"], 3), "jam"],
    ] + [["", a, b, c, d, e] for a, b, c, d, e in ge] + [["", a, b, c, d, e] for a, b, c, d, e in ket_k] + [
        ["(2)", "Volume meresap", "Vrsp = te/24 × A total × K rata-rata",
         f"{f(s['te'], 3)}/24 × {f(s['a_total'], 3)} × {f(s['k_rata'], 3)}", f(s["v_rsp"], 3), "m³"],
        ["(4)", "Volume storasi", "V storasi = Vab − Vrsp", f"{f(v['vab'], 3)} − {f(s['v_rsp'], 3)}", f(s["v_sto"], 3), "m³"],
        ["(5)", "Kedalaman total", "H total = V storasi / A alas", f"{f(s['v_sto'], 3)} / {f(s['a_alas'], 3)}", f(s["h_total"], 2), "m"],
        ["(6)", "Jumlah sumur", "n = H total / H rencana", f"{f(s['h_total'], 2)} / {f(s['H'])}", f(s["n_raw"], 2), "buah"],
        ["", "JUMLAH SUMUR (dibulatkan ke atas)", "N = ⌈n⌉", f"⌈{f(s['n_raw'], 2)}⌉", f"<b>{s['n']}</b>", "buah"],
    ]
    o.append(_tbl(["SNI", "Uraian", "Rumus", "Substitusi", "Hasil", "Satuan"],
                  [[escape(str(c)) if i not in (4,) or "<b>" not in str(c) else c for i, c in enumerate(r)] for r in baris],
                  tebal=(len(baris) - 1,), kelas=[None, None, None, None, "n", "c"]))
    rasio = s["rasio_kap"]
    status = OK if rasio >= 1 else TIDAK
    o.append('<div class="note"><b>Kontrol kapasitas</b> (tambahan): kapasitas = N × (volume tampung + Vrsp) dibandingkan dengan Vab.</div>')
    o.append(_tbl(["Volume tampung / unit", "Vrsp / unit", "Kapasitas total", "Vab", "Rasio kapasitas / Vab", "Pemakaian", "Status"],
                  [[f"{f(s['v_unit'], 3)} m³", f"{f(s['v_rsp'], 3)} m³", f"{f(s['kap'], 3)} m³", f"{f(v['vab'], 3)} m³",
                    f"{rasio * 100:.0f}%", ds.gauge_target(rasio), chip(status)]], kelas=["n", "n", "n", "n", "n", None, "c"]))
    o.append('<div class="note">Mengikuti pasal 5 SNI 03-2453-2002. Pada contoh SNI, K rata-rata tertulis 0,857 sedangkan perhitungan '
             'berbobot luas memberi 0,907; modul memakai rata-rata berbobot luas. Kontrol kapasitas umumnya ≥ 100% karena Vrsp '
             'dihitung dari satu sumur sedangkan N sumur meresap bersamaan; asumsi Kh = 2 × Kv mengikuti contoh SNI.</div>')
    return "".join(o)


def _sek_biopori(h, data, no: int) -> str:
    b, v, P = h["biopori"], h["vab"], h["P"]
    f = fmt_id
    o = [sec(no, f"Resapan Biopori — Pipa Ø {f(b['d'] * 100, 1)} cm × {f(b['t'], 2)} m")]
    o.append(_tbl(["Uraian", "Rumus", "Substitusi", "Hasil", "Satuan"], [
        ["Jari-jari", "r = d / 2", f"{f(b['d'], 4)} / 2", f(b["d"] / 2, 4), "m"],
        ["Volume satu lubang", "V = π r² t", f"π × {f(b['d'] / 2, 4)}² × {f(b['t'])}", f(b["v_lubang"], 5), "m³"],
        ["", "", "", f(b["v_lubang"] * 1000, 2), "liter"],
        ["Volume meresap / lubang (adaptasi SNI)", "Vrsp = te/24 × A total × K rata-rata",
         f"{f(v['te'], 3)}/24 × {f(b['a_dinding'] + b['a_alas'], 4)} × {f(b['k_rata'], 3)}", f(b["v_rsp"], 5), "m³"],
        ["Kapasitas satu lubang", "V + Vrsp", f"{f(b['v_lubang'], 5)} + {f(b['v_rsp'], 5)}", f(b["v_total"], 5), "m³"],
    ], kelas=[None, None, None, "n", "c"]))
    o.append(sec(no + 1, "Jumlah Lubang Biopori"))
    rows = [
        ["A", "Metode volume (konservatif, seperti Excel)", "N = Vab / V lubang", f"{f(v['vab'], 3)} / {f(b['v_lubang'], 5)}",
         f"{f(v['vab'] / b['v_lubang'], 1)}", f"<b>{b['n1']}</b>", f"Rp {f(b['biaya1'], 0)}"],
        ["B", "Dengan peresapan (adaptasi SNI 03-2453-2002)", "N = Vab / (V + Vrsp)", f"{f(v['vab'], 3)} / {f(b['v_total'], 5)}",
         f"{f(v['vab'] / b['v_total'], 1)}", f"<b>{b['n2']}</b>", f"Rp {f(b['biaya2'], 0)}"],
    ]
    if b["n3"]:
        rows.append(["C", "Brata & Nelistya (2008)", "N = I × A / P",
                     f"{f(P['I_jam'], 1)} × {f(v['A_tadah'])} / {f(P['P_lph'], 1)}", "–", f"<b>{b['n3']}</b>", f"Rp {f(b['n3'] * b['harga'], 0)}"])
    else:
        rows.append(["C", "Brata & Nelistya (2008)", "N = I × A / P", "isi intensitas hujan (mm/jam) dan laju peresapan (L/jam)", "–", "–", "–"])
    rows.append(["·", "Pembanding aturan praktis (bukan SNI)", "N = (A/25) / V lubang",
                 f"({f(v['A_tadah'])}/25) / {f(b['v_lubang'], 5)}", f"{f(v['rot_v'] / b['v_lubang'], 1)}", f"{b['n_rot']}", f"Rp {f(b['n_rot'] * b['harga'], 0)}"])
    o.append(_tbl(["", "Metode", "Rumus", "Substitusi", "N (hitung)", "N (dibulatkan)", f"Estimasi biaya @ Rp {f(b['harga'], 0)}"], rows,
                  kelas=[None, None, None, None, "n", "c", "n"]))
    o.append('<div class="note">Biopori tidak diatur dalam SNI 03-2453-2002; metode A mengabaikan peresapan sehingga sangat konservatif, '
             'metode B menerapkan persamaan SNI pada lubang kecil. Biaya adalah estimasi indikatif dari harga satuan yang diisi.</div>')
    return "".join(o)


def _sek_ringkasan(h, data) -> str:
    t = opsi_ringkas(h)
    f = fmt_id
    rows = [[f"<b>{escape(r.Opsi)}</b>", escape(r.Dimensi), f"<b>{r.N}</b>", f"{f(r.V_tampung, 2)} m³", f"{f(r.Kapasitas, 2)} m³",
             ds.gauge_target(r.Rasio)] for r in t.itertuples()]
    return (sec(9, "Perbandingan Opsi Resapan")
            + _tbl(["Opsi", "Dimensi unit", "Jumlah unit", "Volume tampung total", "Kapasitas total", "Kapasitas / Vab"], rows,
                   kelas=[None, None, "c", "n", "n", None]))


def _kpi(h) -> str:
    v, sl, sp, bp = h["vab"], h["lingkaran"], h["persegi"], h["biopori"]
    return kpi([
        ("Volume andil banjir (Vab)", fmt_id(v["vab"], 3), "m³", "aqua"),
        ("Sumur lingkaran", f"{sl['n']}", "unit", "good" if sl["rasio_kap"] >= 1 else "bad"),
        ("Sumur persegi", f"{sp['n']}", "unit", "good" if sp["rasio_kap"] >= 1 else "bad"),
        ("Biopori (volume / peresapan)", f"{bp['n1']} / {bp['n2']}", "lubang", "warn"),
    ])


def _kesimpulan(h) -> str:
    tone = "bad" if h["req_tidak"] else ("warn" if h["req_belum"] else "")
    return sec(10, "Kesimpulan") + f'<div class="concl {tone}">{escape(kesimpulan(h))}</div>'


def render(h: dict, data: dict, proyek: dict | None, bagian: str) -> str:
    """bagian: vab | lingkaran | persegi | biopori | ringkasan | lembar"""
    b = []
    if bagian in ("vab", "lingkaran", "persegi", "biopori", "ringkasan"):
        b.append(_kpi(h))
    if bagian in ("lingkaran", "persegi", "biopori", "ringkasan", "lembar"):
        b.append(ds.peringatan(h["peringatan"]))
    if bagian == "lembar":
        b.append(ds.kop(proyek or {}))
    if bagian in ("vab", "lembar"):
        b += [_sek_vab(h, data), _sek_persyaratan(h)]
    if bagian in ("lingkaran", "lembar"):
        b.append(_sek_sumur(h, data, "lingkaran", 3))
    if bagian in ("persegi", "lembar"):
        b.append(_sek_sumur(h, data, "persegi", 5 if bagian == "lembar" else 3))
    if bagian in ("biopori", "lembar"):
        b.append(_sek_biopori(h, data, 7 if bagian == "lembar" else 3))
    if bagian in ("ringkasan", "lembar"):
        if bagian == "ringkasan":
            b.append('<img class="dg" alt="Skema opsi resapan" src="data:image/png;base64,'
                     f'{base64.b64encode(skema_png(h)).decode()}">')
        b.append(_sek_ringkasan(h, data))
        b.append(_kesimpulan(h))
    return ds.CSS + '<div class="wrap">' + "".join(b) + "</div>"


def tinggi(h: dict, bagian: str) -> int:
    nw = 40 * len(h["peringatan"])
    return {"vab": 1180 + 36 * len(h["vab"]["rinc"]), "lingkaran": 1050 + nw, "persegi": 1050 + nw, "biopori": 900 + nw,
            "ringkasan": 1000 + nw, "lembar": 4700 + nw}[bagian]
