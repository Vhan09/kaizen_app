"""Tampilan HTML modul APAR (tanpa Streamlit)."""
from __future__ import annotations

import html

from modules.apar_calc import (C_JARAK, C_KELAS, C_MAKS, C_MINA, C_PERA, CATATAN_TABEL, KELAS)
from utils.formatting import fmt_id

e = html.escape

DASAR_PERATURAN = [
    ("Permenaker No. PER.04/MEN/1980",
     "Syarat-syarat pemasangan dan pemeliharaan Alat Pemadam Api Ringan (APAR)."),
    ("Permen PU No. 26/PRT/M/2008",
     "Persyaratan teknis sistem proteksi kebakaran pada bangunan gedung dan lingkungan."),
    ("SNI 03-3987-1995",
     "Tata cara perencanaan, pemasangan, dan pemeliharaan APAR untuk pencegahan bahaya "
     "kebakaran pada bangunan rumah dan gedung."),
]


def _n(x) -> str:
    """Angka ringkas ala Indonesia: 278 / 2,5 / 1.045."""
    x = float(x)
    return fmt_id(x, 0 if x == int(x) else 1)


def peraturan_html(jarak_regulasi: float) -> str:
    kartu = "".join(
        f'<div class="card"><div class="t">{e(t)}</div><div class="d">{e(d)}</div></div>'
        for t, d in DASAR_PERATURAN
    )
    return (
        f'<div class="card-row">{kartu}</div>'
        '<div class="callout">Persyaratan proteksi dapat dipenuhi dengan APAR berkemampuan lebih tinggi, '
        f'asalkan jarak tempuh ke APAR yang lebih besar tidak melebihi <b>{_n(jarak_regulasi)} m</b> '
        f'(jarak antar APAR {_n(jarak_regulasi)} meter) dan jumlah kebutuhan APAR mengikuti tabel di bawah ini.</div>'
    )


def tabel_kelas_a_html(tabel, terpilih: str) -> str:
    """Tabel 'Ukuran APAR dan penempatannya untuk bahaya kebakaran Kelas A'; kolom terpilih disorot."""
    nilai = {r[C_KELAS]: r for _, r in tabel.iterrows()}

    def sel(k: str) -> str:
        return " sel" if k == terpilih else ""

    kepala = (
        '<thead><tr><th rowspan="2">No</th><th rowspan="2">Kriteria</th>'
        '<th colspan="3">Hunian bahaya kebakaran</th></tr><tr>'
        + "".join(f'<th class="{sel(k).strip()}">{k}</th>' for k in KELAS) + "</tr></thead>"
    )
    # (judul, kolom, format, penanda catatan per kelas)
    baris = [
        ("Daya padam minimum APAR tunggal", C_MINA, lambda v: f"{_n(v)}-A", {"Ringan": "1", "Sedang": "1", "Berat": "2"}),
        ("Luas lantai maksimum per unit A", C_PERA, lambda v: f"{_n(v)} m²", {}),
        ("Luas lantai maksimum per APAR", C_MAKS, lambda v: f"{_n(v)} m²", {k: "3" for k in KELAS}),
        ("Jarak tempuh maksimum ke APAR", C_JARAK, lambda v: f"{_n(v)} m", {k: "3" for k in KELAS}),
    ]
    isi = []
    for i, (judul, kol, fmt, penanda) in enumerate(baris, start=1):
        sel_td = "".join(
            f'<td class="b{sel(k)}">{fmt(nilai[k][kol])}'
            + (f"<sup>({penanda[k]})</sup>" if k in penanda else "") + "</td>"
            for k in KELAS
        )
        isi.append(f'<tr><td>{i}</td><td class="l">{e(judul)}</td>{sel_td}</tr>')
    return f'<div class="xl-wrap"><table class="xl apar">{kepala}<tbody>{"".join(isi)}</tbody></table></div>'


def catatan_tabel_html() -> str:
    butir = "".join(f"<li>{e(t)}</li>" for t in CATATAN_TABEL)
    return f'<div class="notes"><b>Catatan:</b><ol style="margin:.2rem 0 0 1.2rem;padding:0">{butir}</ol></div>'


def hitung_html(h: dict) -> str:
    """Tabel perhitungan jumlah APAR per lantai."""
    kepala = (
        "<thead><tr><th>No</th><th>Lantai / Area</th><th>Luas Lantai</th>"
        "<th>Cakupan per APAR</th><th>Luas ÷ Cakupan</th><th>Jumlah APAR</th></tr></thead>"
    )
    isi = []
    for i, r in enumerate(h["lantai"], start=1):
        jumlah = "-" if r["jumlah"] is None else f'{r["jumlah"]} buah'
        cak = "-" if h["cakupan"] <= 0 else f"{_n(h['cakupan'])} m²"
        rasio = "-" if h["cakupan"] <= 0 else fmt_id(r["rasio"], 2)
        isi.append(
            f'<tr><td>{i}</td><td class="l">{e(r["lantai"] or "-")}</td><td>{_n(r["luas"])} m²</td>'
            f'<td>{cak}</td><td>{rasio}</td><td class="b">{jumlah}</td></tr>'
        )
    total = "-" if h["total"] is None else f'{h["total"]} buah'
    isi.append(
        f'<tr><td colspan="2" class="l b">TOTAL KEBUTUHAN APAR</td><td class="b">{_n(h["total_luas"])} m²</td>'
        f'<td></td><td></td><td class="g">{total}</td></tr>'
    )
    isi.append(
        '<tr><td colspan="6" class="note">Catatan : Kebutuhan jumlah APAR = Luas lantai ÷ Cakupan per APAR, '
        'dibulatkan ke atas (minimal 1 APAR pada tiap lantai yang berisi).</td></tr>'
    )
    return f'<div class="xl-wrap"><table class="xl">{kepala}<tbody>{"".join(isi)}</tbody></table></div>'


def rekomendasi_html(jenis: str, kapasitas: str, rating: str, h: dict) -> str:
    """Kartu rekomendasi ala Excel: jenis, kapasitas, rating, jarak tempuh, jumlah."""
    total = "-" if h["total"] is None else f'{h["total"]} buah'
    baris = [
        ("Jenis", jenis), ("Kapasitas", kapasitas), ("Rating", rating),
        ("Maks jarak tempuh", f"{_n(h['jarak_pakai'])} m"),
    ]
    isi = "".join(f'<tr><td class="l">{e(k)}</td><td class="l b">{e(str(v))}</td></tr>' for k, v in baris)
    isi += f'<tr><td class="l b">Jumlah APAR yang dibutuhkan</td><td class="g">{total}</td></tr>'
    return (
        '<div class="xl-wrap"><table class="xl" style="width:auto;min-width:380px">'
        f'<thead><tr><th>Rekomendasi APAR</th><th>Nilai</th></tr></thead><tbody>{isi}</tbody></table></div>'
    )
