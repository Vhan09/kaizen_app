"""Modul Sanitasi - tampilan HTML lembar perhitungan (tanpa Streamlit)."""
from __future__ import annotations

from html import escape

from modules.sanitasi_calc import susun_seksi

_CSS = """
<meta charset="utf-8">
<style>
 body{margin:0;font-family:Arial,sans-serif;background:#fff;color:#000}
 .wrap{overflow-x:auto;padding:8px}
 table{border-collapse:collapse;font-size:12px}
 .info td{border:none;padding:1px 6px;text-align:left}
 .info td.k{font-weight:700}
 .judul{font-weight:700;font-size:13px;margin:16px 0 6px}
 .t th,.t td{border:1px solid #444;padding:3px 8px;text-align:left;vertical-align:middle}
 .t th{background:#f2f2f2;font-weight:600;text-align:center;white-space:normal}
 .t td.n{text-align:right;white-space:nowrap}
 .t td.c{text-align:center}
 .t tr.b td{font-weight:700;background:#f2f2f2}
 .cat{font-style:italic;font-size:12px;margin-top:8px}
 .pr{background:#fef7e0;color:#b06000;border:1px solid #f0d58a;padding:4px 8px;margin:6px 0;font-size:12px}
</style>
"""


def _is_angka(s) -> bool:
    t = str(s).replace(".", "").replace(",", "").replace("-", "").replace("%", "").strip()
    return t.isdigit()


def render_html(h: dict, data: dict, proyek: dict, hanya: list[str] | None = None, kop: bool = True) -> str:
    """hanya = daftar kunci seksi yang ditampilkan (None = semua); kop=False menyembunyikan identitas proyek."""
    proyek = proyek or {}
    out = [_CSS, '<div class="wrap">']
    if kop:
        out.append('<table class="info">')
    for k, v in (("PEKERJAAN :", proyek.get("pekerjaan", "")), ("LOKASI :", proyek.get("lokasi", "")),
                 ("TAHUN :", proyek.get("tahun", "")), ("ITEM PEKERJAAN :", proyek.get("item", ""))):
        if kop:
            out.append(f'<tr><td class="k">{k}</td><td>: {escape(str(v))}</td></tr>')
    if kop:
        out.append("</table>")

    seksi = [x for x in susun_seksi(h, data) if hanya is None or x["kunci"] in hanya]
    if hanya is None or "air_kotor" in hanya:
        for p in h["peringatan"]:
            out.append(f'<div class="pr">⚠ {escape(p)}</div>')

    for sek in seksi:
        out.append(f'<div class="judul">{escape(sek["judul"])}</div><table class="t"><tr>')
        out.append("".join(f"<th>{escape(k)}</th>" for k in sek["kolom"]) + "</tr>")
        for i, row in enumerate(sek["baris"]):
            cls = ' class="b"' if i in sek["tebal"] else ""
            cells = []
            for j, v in enumerate(row):
                kelas = "c" if (j == 0 and _is_angka(v)) else ("n" if (j > 0 and _is_angka(v)) else "")
                cells.append(f'<td class="{kelas}">{escape(str(v))}</td>' if kelas else f"<td>{escape(str(v))}</td>")
            out.append(f"<tr{cls}>" + "".join(cells) + "</tr>")
        out.append("</table>")

    if hanya is None or "air_bersih" in hanya:
        out.append(f'<div class="cat">Sumber tabel pemakaian air: {escape(data["sumber_tabel"])}. '
                   f'{escape(data["catatan_tabel"])}</div>')
    out.append("</div>")
    return "".join(out)


def tinggi_html(h: dict, data: dict, hanya: list[str] | None = None, kop: bool = True) -> int:
    baris = sum(len(s["baris"]) + 2 for s in susun_seksi(h, data) if hanya is None or s["kunci"] in hanya)
    ekstra = (120 if kop else 40) + (30 * len(h["peringatan"]) if hanya is None or "air_kotor" in hanya else 0)
    return ekstra + 28 * baris
