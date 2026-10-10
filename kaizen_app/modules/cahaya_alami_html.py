"""Modul Pencahayaan Alami - tampilan HTML (memakai sistem desain bersama)."""
from __future__ import annotations

import base64
from html import escape

from modules import desain as ds
from modules.cahaya_alami_calc import KURANG, OK, TANPA, TERBUKA, fmt_id, kesimpulan, pct, pct_bersih
from modules.cahaya_alami_denah import denah_png


def _a(x, d=2) -> str:
    return "–" if x is None or x != x else fmt_id(x, d)


def _sel(x) -> str:
    if x is None or x != x:
        return "–"
    return ("+" if x >= 0 else "−") + fmt_id(abs(x), 3 if abs(x) < 0.1 else 2)


def _sek_dasar(h, data) -> str:
    return (ds.sec(1, "Dasar Perhitungan")
            + '<div class="card"><b>Rasio Luas Bukaan terhadap Luas Lantai</b>'
              f'<div class="formula">Rasio = Aj / Ar &nbsp;≥&nbsp; {pct_bersih(h["ambang"])}'
              '<small>Aj = Σ (lebar × tinggi × jumlah × faktor efektif) &nbsp;·&nbsp; Ar = P × L</small></div>'
              '<div class="legend"><b>Aj</b><span>luas bukaan cahaya / jendela (m²)</span>'
              '<b>Ar</b><span>luas lantai ruangan (m²)</span>'
              f'<b>Minimum</b><span>{pct_bersih(h["ambang"])} dari luas lantai (Aj minimum = ambang × Ar)</span></div></div>'
              f'<div class="note">{escape(data["catatan_metode"])}</div>')


def _sek_bukaan(h) -> str:
    b = h["bukaan"]
    if b.empty:
        return ds.sec(2, "Daftar Bukaan") + '<div class="note">Belum ada bukaan.</div>'
    rows = "".join(
        f'<tr><td class="c">{i}</td><td><b>{escape(r.Ruangan)}</b></td><td>{escape(r.Jenis)}</td>'
        f'<td class="n">{fmt_id(r.W)} × {fmt_id(r.H)}</td><td class="c">{r.n}</td><td class="n">{fmt_id(r.f)}</td>'
        f'<td class="n"><b>{fmt_id(r.Aj, 3)}</b></td></tr>' for i, r in enumerate(b.itertuples(), start=1))
    return (ds.sec(2, "Daftar Bukaan (Aj)")
            + '<table class="t"><tr><th>No</th><th>Ruangan</th><th>Jenis bukaan</th><th>Lebar × Tinggi (m)</th><th>Jumlah</th>'
              f'<th>Faktor efektif</th><th>Aj (m²)</th></tr>{rows}'
              f'<tr class="tot"><td colspan="6">TOTAL Aj</td><td class="n">{fmt_id(b["Aj"].sum(), 3)}</td></tr></table>')


def _sek_rasio(h) -> str:
    t, thr = h["tabel"], h["ambang"]
    o = [ds.sec(3, "Perhitungan Rasio per Ruangan")]
    o.append('<table class="t"><tr><th>No</th><th>Nama Ruangan</th><th>Ar: P × L (m)</th><th>Ar (m²)</th><th>Bukaan</th><th>Aj (m²)</th>'
             '<th>Rasio Aj/Ar</th><th>Aj minimum (m²)</th><th>Selisih (m²)</th><th>Terhadap ambang</th><th>Keterangan</th></tr>')
    for lt, grp in t.groupby("Lantai", sort=False):
        o.append(f'<tr class="tot"><td colspan="11">{escape(lt.upper())}</td></tr>')
        for i, r in enumerate(grp.itertuples(), start=1):
            dim = f"{r.P:g} × {r.L:g}" if r.P == r.P and r.P else "–"
            rasio_thd = (r.rasio / thr) if r.rasio is not None and r.rasio == r.rasio else None
            o.append(f'<tr><td class="c">{i}</td><td><b>{escape(r.Ruangan)}</b></td><td class="c">{dim}</td>'
                     f'<td class="n">{_a(r.Ar)}</td><td class="c">{r.nb if r.status != TERBUKA else "–"}</td>'
                     f'<td class="n">{_a(r.Aj, 3)}</td><td class="n"><b>{pct(r.rasio) if rasio_thd is not None else "–"}</b></td>'
                     f'<td class="n">{_a(r.aj_min, 3)}</td><td class="n">{_sel(r.selisih)}</td>'
                     f'<td>{ds.gauge_target(rasio_thd) if rasio_thd is not None else ""}</td><td class="c">{ds.chip(r.status)}</td></tr>')
    o.append(f'<tr class="tot"><td colspan="3">TOTAL (ruang tertutup)</td><td class="n">{fmt_id(h["ar_total"])}</td><td></td>'
             f'<td class="n">{fmt_id(h["aj_total"], 3)}</td><td class="n">{pct(h["rasio_total"]) if h["rasio_total"] else "–"}</td>'
             '<td colspan="4"></td></tr></table>')
    return "".join(o)


def _sek_rekap(h) -> str:
    lt, t = h["lantai"], h["tabel"]
    o = [ds.sec(4, "Rekap per Lantai")]
    o.append('<table class="t"><tr><th>Lantai</th><th>Ruang tertutup</th><th>Area terbuka</th><th>Luas lantai (m²)</th>'
             '<th>Luas bukaan (m²)</th><th>Rasio</th><th>Memenuhi</th><th>Kurang</th></tr>' + "".join(
                 f'<tr><td><b>{escape(r.Lantai)}</b></td><td class="c">{int(r.ruang)}</td><td class="c">{int(r.terbuka)}</td>'
                 f'<td class="n">{fmt_id(r.ar)}</td><td class="n">{fmt_id(r.aj, 3)}</td><td class="n"><b>{pct(r.rasio) if r.rasio == r.rasio else "–"}</b></td>'
                 f'<td class="c">{int(r.ok)}</td><td class="c">{int(r.kurang)}</td></tr>' for r in lt.itertuples())
             + f'<tr class="tot"><td>TOTAL</td><td class="c">{h["n_dinilai"]}</td><td class="c">{h["n_terbuka"]}</td>'
               f'<td class="n">{fmt_id(h["ar_total"])}</td><td class="n">{fmt_id(h["aj_total"], 3)}</td>'
               f'<td class="n">{pct(h["rasio_total"]) if h["rasio_total"] else "–"}</td><td class="c">{h["n_ok"]}</td>'
               f'<td class="c">{h["n_kurang"]}</td></tr></table>')
    bad = t[t["status"].isin([KURANG, TANPA])]
    o.append(ds.sec(5, "Tambahan Bukaan yang Diperlukan"))
    if bad.empty:
        o.append('<div class="concl">Semua ruangan tertutup sudah memenuhi ambang; tidak ada tambahan bukaan.</div>')
    else:
        o.append('<table class="t"><tr><th>Ruangan</th><th>Ar (m²)</th><th>Aj sekarang (m²)</th><th>Aj minimum (m²)</th>'
                 '<th>Tambahan (m²)</th><th>Status</th></tr>' + "".join(
                     f'<tr><td><b>{escape(r.Ruangan)}</b></td><td class="n">{_a(r.Ar)}</td><td class="n">{_a(r.Aj, 3)}</td>'
                     f'<td class="n">{_a(r.aj_min, 3)}</td><td class="n"><b>{fmt_id(-r.selisih, 3)}</b></td>'
                     f'<td class="c">{ds.chip(r.status)}</td></tr>' for r in bad.itertuples())
                 + f'<tr class="tot"><td colspan="4">TOTAL TAMBAHAN</td><td class="n">{fmt_id(h["tambahan"], 3)}</td><td></td></tr></table>')
    return "".join(o)


def _sek_saran(h) -> str:
    bad = h["tabel"][h["tabel"]["status"].isin([KURANG, TANPA])]
    o = [ds.sec(6, "Saran Penanganan untuk Bangunan yang Sudah Terbangun")]
    if bad.empty:
        o.append('<div class="concl">Tidak ada ruang tertutup yang memerlukan saran retrofit berdasarkan ambang ini.</div>')
    else:
        o.append('<table class="t"><tr><th>Ruang</th><th>Status</th><th>Saran utama</th><th>Faktor pendukung</th></tr>')
        for r in bad.itertuples():
            o.append(
                f'<tr><td><b>{escape(r.Ruangan)}</b></td><td class="c">{ds.chip(r.status)}</td>'
                f'<td>{escape(r.saran_utama)}</td><td>{escape(r.saran_pendukung)}</td></tr>'
            )
        o.append("</table>")
    o.append(
        '<div class="note">Saran ini merupakan opsi awal, bukan jaminan memenuhi standar. '
        'Rasio Aj/Ar hanya pemeriksaan awal; verifikasi faktor langit sesuai SNI 03-2396-2001, '
        'kondisi panas/silau, privasi, kebocoran, dan keamanan struktur dengan tenaga ahli. '
        'Bukaan ke ruang dalam atau pantulan cahaya tidak otomatis dihitung sebagai bukaan luar.</div>'
    )
    return "".join(o)


def _kpi(h) -> str:
    return ds.kpi([
        ("Ruang tertutup dinilai", f"{h['n_dinilai']}", "ruang", "aqua"),
        ("Memenuhi", f"{h['n_ok']}", "ruang", "good"),
        ("Belum memenuhi", f"{h['n_kurang']}", "ruang", "good" if h["n_kurang"] == 0 else "bad"),
        ("Rasio keseluruhan", pct(h["rasio_total"]) if h["rasio_total"] else "–", f"min {pct_bersih(h['ambang'])}", ""),
    ])


def _kesimpulan(h) -> str:
    tone = "" if h["n_kurang"] == 0 else "bad"
    return ds.sec(7, "Kesimpulan") + f'<div class="concl {tone}">{escape(kesimpulan(h))}</div>'


def render(h: dict, data: dict, proyek: dict | None, bagian: str) -> str:
    """bagian: hitung | rekap | ringkasan | lembar"""
    b = []
    if bagian in ("hitung", "rekap", "ringkasan"):
        b.append(_kpi(h))
    if bagian in ("hitung", "ringkasan", "lembar"):
        b.append(ds.peringatan(h["peringatan"]))
    if bagian == "lembar":
        b.append(ds.kop(proyek or {}))
    if bagian in ("hitung", "lembar"):
        b += [_sek_dasar(h, data), _sek_bukaan(h), _sek_rasio(h)]
    if bagian in ("rekap", "lembar"):
        b.append(_sek_rekap(h))
    if bagian in ("hitung", "rekap", "ringkasan", "lembar"):
        b.append(_sek_saran(h))
    if bagian == "ringkasan":
        b.append('<img class="dg" alt="Perbandingan luas bukaan dan luas lantai" src="data:image/png;base64,'
                 f'{base64.b64encode(denah_png(h)).decode()}">')
    if bagian in ("ringkasan", "lembar"):
        b.append(_kesimpulan(h))
    return ds.CSS + '<div class="wrap">' + "".join(b) + "</div>"


def tinggi(h: dict, bagian: str) -> int:
    n, nl, nb = len(h["tabel"]), len(h["lantai"]), len(h["bukaan"])
    return {"hitung": 620 + 38 * (n + nl + nb) + 40 * len(h["peringatan"]) + 240 * h["n_kurang"],
            "rekap": 760 + 40 * (nl + h["n_kurang"]) + 240 * h["n_kurang"],
            "ringkasan": 1450 + 240 * h["n_kurang"] + 40 * len(h["peringatan"]),
            "lembar": 1700 + 40 * (n + nl + nb + h["n_kurang"]) + 240 * h["n_kurang"]
            + 40 * len(h["peringatan"])}[bagian]
