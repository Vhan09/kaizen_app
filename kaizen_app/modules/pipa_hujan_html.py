"""Modul Pipa Air Hujan - tampilan HTML (sistem desain: kartu, KPI, gauge, tabel bernomor)."""
from __future__ import annotations

import base64
from html import escape

from modules.pipa_hujan_calc import OK, TIDAK, fmt_id, ink, kesimpulan
from modules.pipa_hujan_diagram import diagram_png

_CSS = """
<meta charset="utf-8">
<style>
 :root{--ink:#1B2A3A;--navy:#0F3D63;--blue:#2A7AB0;--aqua:#35B6C9;--soft:#EAF3F9;--line:#D5E1EB;
       --grey:#6B7C8C;--good:#1E8E5A;--warn:#C77700;--bad:#C0392B}
 *{box-sizing:border-box}
 body{margin:0;font-family:'Segoe UI',system-ui,-apple-system,Arial,sans-serif;color:var(--ink);background:#fff;font-size:13px}
 .wrap{padding:6px 4px 10px}
 .kop{display:grid;grid-template-columns:auto 1fr;gap:3px 14px;border-left:5px solid var(--navy);background:var(--soft);
      border-radius:0 12px 12px 0;padding:10px 16px;margin-bottom:14px}
 .kop b{color:var(--navy);font-size:11px;letter-spacing:.06em}
 .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:10px;margin:4px 0 12px}
 .kpi{border:1px solid var(--line);border-left:5px solid var(--navy);border-radius:12px;padding:9px 14px}
 .kpi .l{font-size:11px;color:var(--grey)}
 .kpi .v{font-size:22px;font-weight:700;line-height:1.25;font-variant-numeric:tabular-nums}
 .kpi .v small{font-size:12px;font-weight:600;color:var(--grey);margin-left:3px}
 .kpi.good{border-left-color:var(--good)}.kpi.warn{border-left-color:var(--warn)}.kpi.bad{border-left-color:var(--bad)}.kpi.aqua{border-left-color:var(--aqua)}
 h3.sec{font-size:15px;color:var(--navy);margin:20px 0 8px;display:flex;align-items:center;gap:10px}
 h3.sec .no{background:var(--navy);color:#fff;border-radius:50%;width:24px;height:24px;display:inline-flex;align-items:center;
            justify-content:center;font-size:12px}
 .card{border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:8px 0}
 .formula{background:var(--soft);border-radius:10px;padding:10px 16px;margin:8px 0;font-family:'Cambria Math','Times New Roman',serif;font-size:16px}
 .formula small{display:block;font-family:'Segoe UI',Arial,sans-serif;font-size:12px;color:var(--grey);margin-top:4px}
 .legend{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;font-size:12px;color:var(--grey);margin-top:6px}
 .legend b{color:var(--ink)}
 table{border-collapse:separate;border-spacing:0;width:100%;font-size:12.5px}
 table.t{border:1px solid var(--line);border-radius:10px;overflow:hidden}
 table.t th{background:var(--navy);color:#fff;font-weight:600;padding:7px 10px;text-align:center;border-right:1px solid #2b5a82}
 table.t th:last-child{border-right:none}
 table.t td{padding:6px 10px;border-top:1px solid var(--line);border-right:1px solid #EEF3F7;font-variant-numeric:tabular-nums}
 table.t td:last-child{border-right:none}
 table.t tr:nth-child(even) td{background:#F8FBFD}
 table.t td.n{text-align:right}table.t td.c{text-align:center}
 table.t tr.tot td{background:var(--soft);font-weight:700}
 table.t tr.sel td{background:#FFF6DA;font-weight:700}
 table.t tr.min td:first-child{box-shadow:inset 4px 0 0 var(--good)}
 table.t td.hl,table.t th.hl{background:#DDF1F5;color:#0B5A66;font-weight:700}
 table.t th.hl{background:#127A88;color:#fff}
 table.t tr.sel td.hl{background:#FFE9A8}
 .t17-wrap{overflow-x:auto;margin-top:8px}.t17{min-width:1120px}
 .chip{display:inline-block;border-radius:999px;padding:2px 11px;font-size:11px;font-weight:700;color:#fff;white-space:nowrap}
 .chip.good{background:var(--good)}.chip.bad{background:var(--bad)}.chip.warn{background:var(--warn)}
 .gauge{height:8px;background:#E6EDF3;border-radius:4px;overflow:hidden;min-width:90px}
 .gauge span{display:block;height:100%;border-radius:4px}
 .gl{display:flex;align-items:center;gap:8px}.gl em{font-style:normal;font-size:11px;color:var(--grey);min-width:34px;text-align:right}
 .note{font-size:12px;color:var(--grey);margin:6px 2px}
 .pr{background:#FFF6DA;border:1px solid #F0D58A;color:#8A5A00;border-radius:10px;padding:7px 12px;margin:6px 0;font-size:12.5px}
 .concl{border-left:5px solid var(--good);background:#F1FAF5;border-radius:0 12px 12px 0;padding:12px 18px;line-height:1.6;margin:8px 0}
 .concl.bad{border-left-color:var(--bad);background:#FDF3F2}
 .concl.warn{border-left-color:var(--warn);background:#FFF9EC}
 img.dg{width:100%;max-width:1500px;border-radius:14px;display:block}
 .two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
 @media(max-width:760px){.two{grid-template-columns:1fr}}
</style>
"""

_TONE = {OK: "good", TIDAK: "bad", "BELUM DICEK": "warn", "DI LUAR TABEL": "warn"}


def _chip(status: str) -> str:
    return f'<span class="chip {_TONE.get(status, "warn")}">{escape(status)}</span>'


def _gauge(rasio: float | None) -> str:
    if rasio is None:
        return '<div class="gl"><div class="gauge"></div><em>–</em></div>'
    tone = "var(--good)" if rasio <= 0.8 else ("var(--warn)" if rasio <= 1 else "var(--bad)")
    w = min(rasio, 1.25) / 1.25 * 100
    return (f'<div class="gl"><div class="gauge"><span style="width:{w:.0f}%;background:{tone}"></span></div>'
            f'<em>{rasio * 100:.0f}%</em></div>')


def _kpi(items) -> str:
    out = ['<div class="kpis">']
    for label, nilai, unit, tone in items:
        out.append(f'<div class="kpi {tone}"><div class="l">{escape(label)}</div>'
                   f'<div class="v">{nilai}<small>{escape(unit)}</small></div></div>')
    return "".join(out) + "</div>"


def _sec(no: int, judul: str) -> str:
    return f'<h3 class="sec"><span class="no">{no}</span>{escape(judul)}</h3>'


def _kop(proyek: dict) -> str:
    rows = [("PEKERJAAN", proyek.get("pekerjaan", "")), ("LOKASI", proyek.get("lokasi", "")),
            ("TAHUN", proyek.get("tahun", "")), ("ITEM PEKERJAAN", proyek.get("item", ""))]
    return '<div class="kop">' + "".join(f"<b>{k}</b><span>{escape(str(v))}</span>" for k, v in rows) + "</div>"


def _peringatan(h) -> str:
    return "".join(f'<div class="pr">⚠ {escape(w)}</div>' for w in h["peringatan"])


# ------------------------------------------------------------------- seksi
def _sek_debit(h, data) -> str:
    k = str(data["rasional"]["konstanta"]).replace(".", ",")
    z = h["zona"]
    o = [_sec(1, "Dasar Perhitungan")]
    o.append('<div class="card"><b>Metode : Rumus Rasional</b>'
             f'<div class="formula">Q = {k} × C × I × A</div>'
             '<div class="legend"><b>Q</b><span>debit air hujan (m³/dt)</span><b>C</b><span>koefisien limpasan</span>'
             '<b>I</b><span>intensitas hujan (mm/jam)</span><b>A</b><span>luas atap / daerah tangkapan (Ha)</span></div></div>')

    o.append(_sec(2, "Data Curah Hujan"))
    o.append('<table class="t"><tr><th>Parameter</th><th>Nilai</th><th>Sat</th></tr>'
             f'<tr><td>Intensitas Hujan (I)</td><td class="n">{fmt_id(h["I"], 0 if float(h["I"]).is_integer() else 1)}</td><td class="c">mm/jam</td></tr>'
             f'<tr><td>Koef. Limpasan (C){" (rata-rata tertimbang)" if len(z) > 1 else ""}</td><td class="n">{fmt_id(h["C_rata"])}</td><td class="c">–</td></tr>'
             f'<tr><td>Luas Atap (A)</td><td class="n">{fmt_id(h["A_tot"])}</td><td class="c">m²</td></tr>'
             f'<tr><td>Luas Atap (A)</td><td class="n">{fmt_id(h["A_tot"] / 10000, 6)}</td><td class="c">Ha</td></tr></table>')
    o.append('<div class="note">Rincian per bidang atap:</div><table class="t"><tr><th>Bidang Atap</th>'
             '<th>Permukaan</th><th>A (m²)</th><th>C</th><th>Roof drain</th></tr>' + "".join(
                 f'<tr><td>{escape(r.Bidang)}</td><td>{escape(r.Permukaan)}</td><td class="n">{fmt_id(r.A)}</td>'
                 f'<td class="n">{fmt_id(r.C)}</td><td class="c">{r.n}</td></tr>' for r in z.itertuples()) + "</table>")

    o.append(_sec(3, "Analisa Perhitungan Teknis"))
    for r in z.itertuples():
        etiket = f"{escape(r.Bidang)}: " if len(z) > 1 else ""
        o.append(f'<div class="formula">{etiket}Q = {k} × {fmt_id(r.C)} × {fmt_id(h["I"], 0)} × {fmt_id(r.Ha, 6)}'
                 f' = <b>{fmt_id(r.Q_m3s, 5)} m³/dt</b> = <b>{fmt_id(r.Q_Ls)} L/dt</b></div>')
    if len(z) > 1:
        o.append(f'<div class="formula">Q total = <b>{fmt_id(h["Q_m3"], 5)} m³/dt</b> = <b>{fmt_id(h["Q_Ls"])} L/dt</b></div>')
    return "".join(o)


def _t16(h, data, kem: int, pilih: float | None, minimum: float | None) -> str:
    t = data["tabel16"]
    grid, idx = t["intensitas"], h["idx"]
    kd = t["kemiringan"][str(kem)]
    head = ("<tr><th>Ø pipa (inci)</th><th>Debit (L/dt)</th>" + "".join(
        f'<th class="{"hl" if i == idx else ""}">{fmt_id(g, 1)}<br><small>mm/jam</small></th>' for i, g in enumerate(grid)) + "</tr>")
    rows = []
    for r, u in enumerate(data["ukuran_inci"]):
        cls = " ".join(x for x, ok in (("sel", u == pilih), ("min", u == minimum)) if ok)
        deb = kd["debit"][r]
        dtxt = (fmt_id(deb, 2) + ("*" if kem == 1 else "")) if deb is not None else "–"
        cells = "".join(f'<td class="n {"hl" if i == idx else ""}">{fmt_id(v, 0)}</td>' for i, v in enumerate(kd["luas"][r]))
        rows.append(f'<tr class="{cls}"><td class="c"><b>{ink(u)}</b></td><td class="n">{dtxt}</td>{cells}</tr>')
    cap = (f'<div class="note">Luas bidang datar horizontal maksimum (m²) pada kemiringan <b>{kem}%</b>. '
           f'Kolom yang dipakai: <b>{fmt_id(h["I_tabel"], 1)} mm/jam</b> (terdekat di atas I = {fmt_id(h["I"], 0)}). '
           'Baris kuning = ukuran dipilih; garis hijau = ukuran minimum yang memenuhi.</div>')
    return cap + f'<table class="t">{head}{"".join(rows)}</table>'


def _baris_cek(nama, c) -> str:
    mn = f"Ø{ink(c['minimum'])}" if c["minimum"] else "di luar tabel"
    return (f'<tr><td><b>{nama}</b></td><td class="n">{fmt_id(c["luas"])}</td><td class="c">Ø{ink(c["ukuran"])}</td>'
            f'<td class="c">{c["kemiringan"]} %</td><td class="n">{fmt_id(c["kapasitas"], 0)}</td>'
            f'<td>{_gauge(c["rasio"])}</td><td class="c">{_chip(c["status"])}</td><td class="c">{mn}</td></tr>')


def _sek_horizontal(h, data) -> str:
    P, c, g, z = h["P"], h["cabang"], h["gabung"], h["zona"]
    o = [_sec(4, "Pipa Horizontal / Mendatar — SNI 8153:2015 Tabel 16")]
    o.append('<table class="t"><tr><th>Pipa</th><th>Luas dilayani (m²)</th><th>Ø</th><th>Kemiringan</th>'
             '<th>Kapasitas Tabel 16 (m²)</th><th>Pemakaian kapasitas</th><th>Status</th><th>Ø minimum</th></tr>'
             + _baris_cek("Cabang (per roof drain)", c) + _baris_cek("Horizontal gabungan", g) + "</table>")
    if c["debit_kap"]:
        tanda = "&lt;" if c["q_ls"] <= c["debit_kap"] else "&gt;"
        pembanding = (f' Pembanding debit: Q per roof drain {fmt_id(c["q_ls"], 3)} L/dt {tanda} debit kapasitas '
                      f'{fmt_id(c["debit_kap"], 2)} L/dt (Tabel 16{"*" if c["kemiringan"] == 1 else ""}).')
    else:
        pembanding = ""
    o.append(f'<div class="note">Pipa cabang dicek terhadap bidang atap dengan luas per roof drain terbesar '
             f'(<b>{escape(str(c["bidang"]))}</b>).{pembanding}</div>')

    o.append(_sec(5, "Catatan untuk Sistem Drainase Atap"))
    o.append('<table class="t"><tr><th>Bidang Atap</th><th>Luas (m²)</th><th>Roof drain</th><th>Luas per roof drain (m²)</th>'
             f'<th>Kapasitas Ø{ink(P["d_cabang"])} (m²)</th><th>Pemakaian kapasitas</th></tr>' + "".join(
                 f'<tr><td>{escape(r.Bidang)}</td><td class="n">{fmt_id(r.A)}</td><td class="c">Ø{ink(P["d_roof"])} × {r.n}</td>'
                 f'<td class="n"><b>{fmt_id(r.A_drain)}</b></td><td class="n">{fmt_id(c["kapasitas"], 0)}</td>'
                 f'<td>{_gauge(r.A_drain / c["kapasitas"])}</td></tr>' for r in z.itertuples()) + "</table>")
    r0 = z.iloc[0]
    o.append(f'<div class="formula">{fmt_id(r0.A)} m² ÷ {r0.n} roof drain = <b>{fmt_id(r0.A_drain)} m²</b> per cabang'
             f'&nbsp;&nbsp;({fmt_id(r0.A_drain)} {"&lt;" if r0.A_drain < c["kapasitas"] else "&gt;"} {fmt_id(c["kapasitas"], 0)})'
             f'<small>Roof drain PVC Ø{ink(P["d_roof"])} : {h["n_tot"]} titik · Pipa horizontal PVC Ø{ink(P["d_gabung"])}</small></div>')

    o.append('<div class="note"><b>Tabel referensi</b></div>')
    o.append(_t16(h, data, c["kemiringan"], c["ukuran"], c["minimum"]))
    if g["kemiringan"] != c["kemiringan"]:
        o.append(_t16(h, data, g["kemiringan"], g["ukuran"], g["minimum"]))
    if c["kemiringan"] == 1 or g["kemiringan"] == 1:
        o.append(f'<div class="note">* {escape(data["tabel16"]["catatan_debit"])}</div>')
    return "".join(o)


def _t17(h, data) -> str:
    tabel = data["tabel17"]
    intensitas_dipilih = h["tegak"]["I_tabel"]
    kolom_dipilih = tabel["intensitas"].index(intensitas_dipilih) if intensitas_dipilih is not None else None
    diameter_dipilih = tabel["diameter_inci"].index(h["tegak"]["ukuran"])
    headers = ["Ukuran pipa hujan", "Debit (L/dt)"]
    headers.extend(f'{fmt_id(nilai, 1 if not float(nilai).is_integer() else 0)} mm/jam'
                   for nilai in tabel["intensitas"])
    rows = ['<tr><th>' + '</th><th>'.join(headers[:2]) + '</th>' + ''.join(
        f'<th class="{"hl" if i == kolom_dipilih else ""}">{escape(header)}</th>'
        for i, header in enumerate(headers[2:])) + '</tr>']
    for i, diameter in enumerate(tabel["diameter_inci"]):
        cls = ' class="sel"' if i == diameter_dipilih else ""
        debit = f'{tabel["debit_ls"][i]:g}'.replace(".", ",")
        values = ''.join(f'<td class="n {"hl" if j == kolom_dipilih else ""}">{fmt_id(area, 0)}</td>'
                         for j, area in enumerate(tabel["luas_m2"][i]))
        rows.append(f'<tr{cls}><td class="c"><b>Ø{ink(diameter)}</b></td><td class="n">{debit}</td>{values}</tr>')
    sumber = escape(tabel["sumber"])
    catatan = escape(tabel["catatan"])
    return (f'<div class="note"><b>{sumber}</b> {catatan}</div>'
            f'<div class="t17-wrap"><table class="t t17">{"".join(rows)}</table></div>')


def _sek_tegak(h, data) -> str:
    t, P = h["tegak"], h["P"]
    o = [_sec(6, "Pipa Kolektor Air Hujan Vertikal — SNI 8153:2015 Tabel 17")]
    kap = (fmt_id(t["kapasitas"], 0) + " m²") if t["kapasitas"] is not None else "di luar rentang tabel"
    o.append('<table class="t"><tr><th>Pipa</th><th>Ø</th><th>Luas dilayani (m²)</th><th>Debit (L/dt)</th>'
             '<th>Kapasitas Tabel 17 (m²)</th><th>Pemakaian kapasitas</th><th>Status</th></tr>'
             f'<tr><td><b>Kolektor vertikal</b></td><td class="c">Ø{ink(t["ukuran"])}</td><td class="n">{fmt_id(t["luas"])}</td>'
             f'<td class="n">{fmt_id(t["q_ls"])}</td><td class="n">{kap}</td><td>{_gauge(t["rasio"])}</td>'
             f'<td class="c">{_chip(t["status"])}</td></tr></table>')
    if t["I_tabel"] is not None:
        o.append(f'<div class="note">Kolom intensitas yang dipakai: <b>{fmt_id(t["I_tabel"], 1)} mm/jam</b> '
                 f'(terdekat di atas intensitas rencana {fmt_id(h["I"], 1)} mm/jam). Baris dan kolom terpilih disorot.</div>')
    o.append(_t17(h, data))
    return "".join(o)


def _sek_kesimpulan(h, data) -> str:
    teks = kesimpulan(h, data)
    tone = "" if h["ok_semua"] and h["tegak"]["status"] == OK else ("warn" if h["ok_semua"] else "bad")
    return _sec(7, "Kesimpulan") + f'<div class="concl {tone}">{escape(teks)}</div>'


def _kpi_utama(h) -> str:
    c, g = h["cabang"], h["gabung"]
    tone = lambda s: _TONE.get(s, "warn")
    return _kpi([
        ("Debit rencana", fmt_id(h["Q_Ls"]), "L/dt", "aqua"),
        ("Luas atap total", fmt_id(h["A_tot"]), "m²", ""),
        ("Luas per roof drain", fmt_id(c["luas"]), "m²", tone(c["status"])),
        ("Pipa horizontal", f"Ø{ink(g['ukuran'])}", g["status"].lower(), tone(g["status"])),
    ])


def diagram_html(h, data) -> str:
    b64 = base64.b64encode(diagram_png(h, data)).decode()
    return f'<img class="dg" alt="Skema sistem air hujan" src="data:image/png;base64,{b64}">'


# ------------------------------------------------------------------ render
def render(h: dict, data: dict, proyek: dict | None, bagian: str) -> str:
    """bagian: debit | horizontal | tegak | ringkasan | lembar"""
    body = []
    if bagian in ("debit", "horizontal", "tegak", "ringkasan"):
        body.append(_kpi_utama(h))
    if bagian in ("horizontal", "tegak", "ringkasan", "lembar"):
        body.append(_peringatan(h))
    if bagian == "lembar":
        body.append(_kop(proyek or {}))
    if bagian in ("debit", "lembar"):
        body.append(_sek_debit(h, data))
    if bagian in ("horizontal", "lembar"):
        body.append(_sek_horizontal(h, data))
    if bagian in ("tegak", "lembar"):
        body.append(_sek_tegak(h, data))
    if bagian in ("ringkasan", "lembar"):
        body.append(_sek_kesimpulan(h, data))
    if bagian == "ringkasan":
        body.insert(1, diagram_html(h, data))
    return _CSS + '<div class="wrap">' + "".join(body) + "</div>"


def tinggi(h: dict, bagian: str) -> int:
    nz = len(h["zona"])
    return {"debit": 640 + 48 * nz, "horizontal": 1230 + 40 * nz, "tegak": 600,
            "ringkasan": 760, "lembar": 2400 + 90 * nz}[bagian]
