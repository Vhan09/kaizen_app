"""Modul Titik Lampu - tampilan HTML (memakai sistem desain bersama)."""
from __future__ import annotations

import base64
from html import escape

from modules import desain as ds
from modules.desain import chip, gauge_target, kpi, sec
from modules.titik_lampu_calc import fmt_id, kesimpulan
from modules.titik_lampu_denah import denah_png


def _angka(x, d=2) -> str:
    return "–" if x is None or x != x else fmt_id(x, d)


def _sek_rumus() -> str:
    return (sec(1, "Dasar Perhitungan")
            + '<div class="card"><b>Metode Lumen (SNI 03-6575-2001 · SNI 6197:2020)</b>'
              '<div class="formula">N = (E × A) / (Φ × LLF × CU × n)<small>Φ = W × (lm/W) &nbsp;·&nbsp; A = P × L '
              '&nbsp;·&nbsp; jumlah titik dibulatkan ke atas</small></div>'
              '<div class="legend"><b>N</b><span>jumlah armatur lampu (titik)</span>'
              '<b>E</b><span>kuat penerangan / target penerangan (lux)</span>'
              '<b>P, L, A</b><span>panjang, lebar (m), luas ruangan (m²)</span>'
              '<b>Φ</b><span>fluks cahaya satu lampu (lumen); W = daya lampu (watt); lm/W = luminous efficacy</span>'
              '<b>LLF</b><span>light loss factor / faktor cahaya rugi</span>'
              '<b>CU</b><span>coefficient of utilization / faktor penambahan cahaya</span>'
              '<b>n</b><span>jumlah lampu dalam 1 armatur</span></div></div>')


def _sek_tabel(h) -> str:
    t, P = h["tabel"], h["P"]
    o = [sec(2, "Perhitungan Titik Lampu per Ruangan"),
         f'<div class="note">LLF = <b>{fmt_id(P["llf"])}</b> · CU = <b>{fmt_id(P["cu"])}</b>. '
         'Kolom “E tercapai” = titik × Φ × LLF × CU × n ÷ A.</div>']
    o.append('<table class="t"><tr><th>No</th><th>Nama Ruangan</th><th>P × L (m)</th><th>A (m²)</th><th>Jenis Ruangan</th>'
             '<th>E (lux)</th><th>Lampu</th><th>Φ (lm)</th><th>Φ×LLF×CU×n (lm)</th><th>E × A (lm)</th><th>N hitung</th>'
             '<th>Titik</th><th>E tercapai (lux)</th><th>Terhadap target</th><th>Status</th></tr>')
    for lt, grp in t.groupby("Lantai", sort=False):
        o.append(f'<tr class="tot"><td colspan="15">{escape(lt.upper())}</td></tr>')
        for i, r in enumerate(grp.itertuples(), start=1):
            dim = f"{r.P:g} × {r.L:g}" if r.A == r.A and r.A else "–"
            rasio = (r.e_cap / r.E) if (r.e_cap == r.e_cap and r.E == r.E and r.E) else None
            ket = " <small>(manual)</small>" if (r.manual == r.manual and r.manual) else ""
            o.append(f'<tr><td class="c">{i}</td><td><b>{escape(r.Ruangan)}</b></td><td class="c">{dim}</td>'
                     f'<td class="n">{_angka(r.A)}</td><td>{escape(r.JenisR)}</td>'
                     f'<td class="n">{_angka(r.E, 0)}</td><td>{escape(r.Lampu)} {r.W:g} W</td>'
                     f'<td class="n">{fmt_id(r.phi, 0)}</td><td class="n">{fmt_id(r.eff, 0)}</td>'
                     f'<td class="n">{_angka(r.req, 0)}</td><td class="n">{_angka(r.raw)}</td>'
                     f'<td class="c"><b>{r.titik}</b>{ket}</td><td class="n">{_angka(r.e_cap, 0)}</td>'
                     f'<td>{gauge_target(rasio)}</td><td class="c">{chip(r.status)}</td></tr>')
    o.append(f'<tr class="tot"><td colspan="3">TOTAL</td><td class="n">{fmt_id(h["area_total"])}</td><td colspan="7"></td>'
             f'<td class="c">{h["titik_total"]}</td><td colspan="3" class="n">Daya terpasang {fmt_id(h["daya_total"], 0)} W</td></tr></table>')
    return "".join(o)


def _sek_rekap(h) -> str:
    lt, pv = h["lantai"], h["pivot"]
    total = max(1, h["titik_total"])
    o = [sec(3, "Rekap per Lantai")]
    o.append('<table class="t"><tr><th>Lantai</th><th>Ruangan</th><th>Luas (m²)</th><th>Titik lampu</th><th>Porsi titik</th>'
             '<th>Daya (W)</th><th>W/m²</th></tr>' + "".join(
                 f'<tr><td><b>{escape(r.Lantai)}</b></td><td class="c">{r.ruang}</td><td class="n">{fmt_id(r.area)}</td>'
                 f'<td class="c"><b>{r.titik}</b></td><td>{ds.gauge(r.titik / total)}</td>'
                 f'<td class="n">{fmt_id(r.daya, 0)}</td><td class="n">{_angka(r.wm2, 1)}</td></tr>' for r in lt.itertuples())
             + f'<tr class="tot"><td>TOTAL</td><td class="c">{h["n_ruang"]}</td><td class="n">{fmt_id(h["area_total"])}</td>'
               f'<td class="c">{h["titik_total"]}</td><td></td><td class="n">{fmt_id(h["daya_total"], 0)}</td>'
               f'<td class="n">{_angka(h["wm2"], 1)}</td></tr></table>')
    o.append(sec(4, "Rekap per Jenis Lampu (acuan untuk Modul Beban Listrik / SLD)"))
    kolom = list(pv.columns)
    o.append('<table class="t"><tr><th>Jenis lampu</th>' + "".join(f"<th>{escape(str(k))}</th>" for k in kolom) + "</tr>"
             + "".join('<tr><td><b>' + escape(str(idx)) + "</b></td>" + "".join(
                 f'<td class="c">{int(v) if v else "–"}</td>' for v in row) + "</tr>" for idx, row in pv.iterrows())
             + '<tr class="tot"><td>TOTAL</td>' + "".join(f'<td class="c">{int(pv[k].sum())}</td>' for k in kolom) + "</tr></table>")
    o.append('<div class="note">Angka titik per watt dapat dicocokkan dengan kolom DL pada Modul Beban Listrik (SLD): '
             'DL 3 W, 6 W, 9 W, dan 12 W.</div>')
    return "".join(o)


def _kpi_utama(h) -> str:
    return kpi([
        ("Total titik lampu", f"{h['titik_total']}", "titik", "aqua"),
        ("Daya terpasang", fmt_id(h["daya_total"], 0), "W", ""),
        ("Ruangan", f"{h['n_ruang']}", "ruang", ""),
        ("Di bawah target", f"{h['n_kurang']}", "ruang", "good" if h["n_kurang"] == 0 else "bad"),
    ])


def _kesimpulan(h) -> str:
    tone = "" if h["n_kurang"] == 0 else "bad"
    return sec(5, "Kesimpulan") + f'<div class="concl {tone}">{escape(kesimpulan(h))}</div>'


def render(h: dict, data: dict, proyek: dict | None, bagian: str) -> str:
    """bagian: hitung | rekap | ringkasan | lembar"""
    b = []
    if bagian in ("hitung", "rekap", "ringkasan"):
        b.append(_kpi_utama(h))
    if bagian in ("hitung", "ringkasan", "lembar"):
        b.append(ds.peringatan(h["peringatan"]))
    if bagian == "lembar":
        b.append(ds.kop(proyek or {}))
    if bagian in ("hitung", "lembar"):
        b.append(_sek_rumus())
        b.append(_sek_tabel(h))
    if bagian in ("rekap", "lembar"):
        b.append(_sek_rekap(h))
    if bagian == "ringkasan":
        b.append(f'<img class="dg" alt="Denah skematik titik lampu" src="data:image/png;base64,'
                 f'{base64.b64encode(denah_png(h)).decode()}">')
        b.append('<div class="note">Denah skematik: sebaran titik hanya ilustrasi kebutuhan jumlah, bukan gambar teknis penempatan.</div>')
    if bagian in ("ringkasan", "lembar"):
        b.append(_kesimpulan(h))
    return ds.CSS + '<div class="wrap">' + "".join(b) + "</div>"


def tinggi(h: dict, bagian: str) -> int:
    n = len(h["tabel"]); nl = len(h["lantai"])
    return {"hitung": 640 + 40 * (n + nl), "rekap": 600 + 40 * (nl + len(h["pivot"])),
            "ringkasan": 1450, "lembar": 1500 + 40 * (n + nl)}[bagian]
