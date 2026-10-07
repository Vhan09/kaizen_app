"""Modul AC - tabel HTML bergaya sheet 'AC STANDART' (tanpa Streamlit)."""
from __future__ import annotations

from html import escape

import pandas as pd

from modules.ac_calc import MODE_FULL, fmt_id

_CSS = """
<meta charset="utf-8">
<style>
 body{margin:0;font-family:Arial,sans-serif;background:#fff;color:#000}
 .wrap{overflow-x:auto;padding:8px}
 table{border-collapse:collapse;font-size:12px;white-space:nowrap}
 .info td{border:none;padding:1px 6px;text-align:left;font-size:12px}
 .info td.k{font-weight:700}
 .judul{font-weight:700;font-size:13px;margin:12px 0 6px}
 .t th,.t td{border:1px solid #444;padding:3px 8px;text-align:center}
 .t th{background:#f2f2f2;font-weight:600;white-space:normal;line-height:1.25;vertical-align:middle}
 .t td.w{white-space:normal}
 .t th.c-jenis{width:84px;min-width:84px;max-width:84px}
 .t th.c-konv{width:64px;min-width:64px;max-width:64px}
 .t th.c-n{width:48px;min-width:48px;max-width:48px}
 .t th.c-jml{width:70px;min-width:70px;max-width:70px}
 .t th.c-stat{width:72px;min-width:72px;max-width:72px}
 .t th.c-rek{width:88px;min-width:88px;max-width:88px}
 .t th.g{background:#e8eef7}
 .t td.l{text-align:left}
 .t tr.lt td{font-weight:700;background:#fafafa}
 .t tr.tot td{font-weight:700;background:#f2f2f2}
 .s-ok{background:#e6f4ea;color:#137333;font-weight:700}
 .s-bt{background:#fef7e0;color:#b06000;font-weight:700}
 .s-kr{background:#fce8e6;color:#c5221f;font-weight:700}
 .s-nl{color:#777}
 .rek{font-weight:700}
 .rumus{margin-top:10px;font-size:12px;line-height:1.6}
 .rumus b{display:inline-block;min-width:120px}
 .cat{font-style:italic;font-size:12px;margin-top:8px}
</style>
"""

_KELAS = {"Cukup": "s-ok", "Batas": "s-bt", "Kurang": "s-kr"}
_TH_AKHIR = (
    '<th rowspan="2" class="c-jenis">Jenis AC yang akan digunakan (PK)</th>'
    '<th rowspan="2" class="c-konv">Konversi (Btu/H)</th>'
    '<th rowspan="2" class="c-n">N (AC)</th>'
    '<th rowspan="2" class="c-jml">Jumlah AC Dalam Ruangan</th>'
    '<th rowspan="2" class="c-stat">Status</th>'
    '<th rowspan="2" class="c-rek">Rekomendasi AC</th>'
)


def _td(v, cls="") -> str:
    return f'<td class="{cls}">{v}</td>' if cls else f"<td>{v}</td>"


def _header(full: bool) -> tuple[str, int]:
    base = ('<tr><th rowspan="2">NO</th><th rowspan="2">NAMA RUANGAN</th>'
            '<th colspan="3">Dimensi Ruangan (meter)</th>'
            '<th colspan="2">FF</th>')
    if not full:
        h1 = (base + '<th rowspan="2">Total Btu/h</th>'
              + _TH_AKHIR + '</tr>')
        sub = ["L", "W", "H", "I (Insulasi)", "E (Kondisi)"]
        return h1 + "<tr>" + "".join(f"<th>{t}</th>" for t in sub) + "</tr>", 14
    h1 = (base + '<th rowspan="2">Beban Dasar (Btu/h)</th>'
          '<th colspan="4" class="g">ORANG</th><th colspan="3" class="g">LAMPU</th>'
          '<th colspan="2" class="g">PERALATAN</th><th rowspan="2">Total Btu/h</th>'
          + _TH_AKHIR + '</tr>')
    sub = ["L", "W", "H", "I (Insulasi)", "E (Kondisi)",
           "Jumlah", "Aktivitas", "W/orang", "Btu/h",
           "Jumlah", "W/lampu", "Btu/h", "Daya (W)", "Btu/h"]
    return h1 + "<tr>" + "".join(f"<th>{t}</th>" for t in sub) + "</tr>", 24


def _sel_dasar(r) -> str:
    return (_td(fmt_id(r["L_m"])) + _td(fmt_id(r["W_m"])) + _td(fmt_id(r["H_m"]))
            + _td(r["I"]) + _td(r["E"]))


def _sel_akhir(r) -> str:
    return (_td(escape(r["Jenis AC"])) + _td(fmt_id(r["Konversi"], 0)) + _td(fmt_id(r["N"], 3))
            + _td(r["Jumlah"]) + _td(escape(r["Status"]), _KELAS.get(r["Status"], "s-nl") + " w")
            + _td(escape(r["Rekomendasi"]), "rek w"))


def _rumus_html(full: bool, data: dict, od: float, fl: float) -> str:
    p = data["konversi"]["pembagi"]
    w2b = str(data["konversi"]["watt_ke_btu"]).replace(".", ",")
    ft = str(data["konversi"]["meter_ke_feet"]).replace(".", ",")
    if not full:
        return (f'<div class="rumus"><b>Rumus:</b> Btu/h = (L × W × H × I × E) / {p} &nbsp;&nbsp; '
                f'(L, W, H dikonversi ke feet: 1 m = {ft} ft) &nbsp;|&nbsp; N (AC) = Btu/h ÷ kapasitas AC terpilih</div>')
    return (
        '<div class="rumus">'
        f'<div><b>Q dasar</b> = (L × W × H × I × E) / {p} &nbsp; (L, W, H dalam feet: 1 m = {ft} ft)</div>'
        f'<div><b>Q orang</b> = max(0; n orang − {fmt_id(od, 0)}) × W/orang × {w2b}</div>'
        f'<div><b>Q lampu</b> = n lampu × W/lampu × {fmt_id(fl)} × {w2b}</div>'
        f'<div><b>Q peralatan</b> = W peralatan × {w2b}</div>'
        '<div><b>Q total</b> = Q dasar + Q orang + Q lampu + Q peralatan &nbsp;|&nbsp; '
        'N (AC) = Q total ÷ kapasitas AC terpilih</div></div>'
    )


def render_html(hasil: pd.DataFrame, data: dict, proyek: dict, mode: str,
                orang_dasar: float | None = None, faktor_lampu: float | None = None) -> str:
    full = mode == MODE_FULL
    od = data["full"]["orang_dasar"] if orang_dasar is None else orang_dasar
    fl = data["full"]["faktor_lampu"] if faktor_lampu is None else faktor_lampu

    h = [_CSS, '<div class="wrap"><table class="info">']
    for k, v in (("PEKERJAAN :", proyek.get("pekerjaan", "")), ("LOKASI :", proyek.get("lokasi", "")),
                 ("TAHUN :", proyek.get("tahun", "")), ("ITEM PEKERJAAN :", proyek.get("item", ""))):
        h.append(f'<tr><td class="k">{k}</td><td>: {escape(str(v))}</td></tr>')
    h.append("</table>")
    h.append(f'<div class="judul">Metode Estimasi Kebutuhan Pendinginan Ruangan — {escape(mode)}</div>')

    head, n_kol = _header(full)
    h.append('<table class="t">' + head)

    for no, (lantai, grup) in enumerate(hasil.groupby("Lantai", sort=False), start=1):
        h.append(f'<tr class="lt"><td>{no}</td><td class="l">{escape(lantai)}</td>'
                 f'<td colspan="{n_kol - 2}"></td></tr>')
        for _, r in grup.iterrows():
            row = '<tr><td></td>' + _td(escape(r["Ruangan"]), "l") + _sel_dasar(r)
            if full:
                row += (_td(fmt_id(r["Q_dasar"]))
                        + _td(fmt_id(r["Orang"], 0)) + _td(escape(r["Aktivitas"])) + _td(r["W_org"])
                        + _td(fmt_id(r["Q_orang"]))
                        + _td(fmt_id(r["N_lampu"], 0)) + _td(fmt_id(r["W_lampu"], 0)) + _td(fmt_id(r["Q_lampu"]))
                        + _td(fmt_id(r["W_alat"], 0)) + _td(fmt_id(r["Q_alat"])))
            row += _td(fmt_id(r["Btu"])) + _sel_akhir(r) + "</tr>"
            h.append(row)

    s = hasil.sum(numeric_only=True)
    if full:
        tot = (f'<tr class="tot"><td colspan="7">TOTAL</td><td>{fmt_id(s["Q_dasar"])}</td>'
               f'<td>{fmt_id(s["Orang"], 0)}</td><td></td><td></td><td>{fmt_id(s["Q_orang"])}</td>'
               f'<td>{fmt_id(s["N_lampu"], 0)}</td><td></td><td>{fmt_id(s["Q_lampu"])}</td>'
               f'<td>{fmt_id(s["W_alat"], 0)}</td><td>{fmt_id(s["Q_alat"])}</td>'
               f'<td>{fmt_id(s["Btu"])}</td><td colspan="3"></td><td>{int(s["Jumlah"])}</td><td></td><td></td></tr>')
    else:
        tot = (f'<tr class="tot"><td colspan="7">TOTAL</td><td>{fmt_id(s["Btu"])}</td>'
               f'<td colspan="3"></td><td>{int(s["Jumlah"])}</td><td></td><td></td></tr>')
    h.append(tot + "</table>")
    h.append(_rumus_html(full, data, od, fl))
    if full:
        h.append(f'<div class="cat">Nilai W/orang: {escape(data["full"]["sumber_aktivitas"])}. '
                 f'Orang dasar (sudah termasuk di rumus dasar) = {fmt_id(od, 0)}.</div>')
    if data.get("catatan"):
        h.append(f'<div class="cat">“{escape(data["catatan"])}”</div>')
    h.append("</div>")
    return "".join(h)


def tinggi_html(hasil: pd.DataFrame, mode: str = "") -> int:
    """Perkiraan tinggi iframe untuk components.html."""
    n_lantai = hasil["Lantai"].nunique()
    ekstra = 110 if mode == MODE_FULL else 50
    return 250 + ekstra + 28 * (len(hasil) + n_lantai + 1)
