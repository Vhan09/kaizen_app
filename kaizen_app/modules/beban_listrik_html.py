"""Tabel hasil beban listrik dalam tampilan mirip Excel (tanpa Streamlit)."""
from __future__ import annotations

import html

from utils.formatting import fmt_id
from modules.beban_listrik_calc import COL_GRUP, COL_KABEL, COL_LAIN, COL_MCB, COL_NAMA

e = html.escape


def header_proyek_html(proyek: dict) -> str:
    baris = [
        ("PEKERJAAN", proyek["pekerjaan"]),
        ("LOKASI", proyek["lokasi"]),
        ("TAHUN", proyek["tahun"]),
        ("ITEM PEKERJAAN", proyek["item"]),
    ]
    isi = "".join(
        f'<tr><td class="k">{k}</td><td>: {e(str(v))}</td></tr>' for k, v in baris
    )
    return f'<table class="proj">{isi}</table>'


def data_sistem_html(sistem: dict) -> str:
    """Tabel 'DATA SISTEM' seperti di Excel (nilai ikut pilihan input)."""
    baris = [
        ("Tegangan Sistem", f"{fmt_id(sistem['tegangan'])} V"),
        ("Sistem Grounding", sistem["grounding"]),
        ("Resistansi Grounding Max", sistem["res_grounding"]),
        ("Proteksi Kebocoran", sistem["proteksi"]),
    ]
    isi = "".join(
        f'<tr><td class="l">{e(k)}</td><td class="l b">{e(str(v))}</td></tr>'
        for k, v in baris
    )
    return (
        '<div class="xl-wrap"><table class="xl" style="width:auto;min-width:380px">'
        '<thead><tr><th>Sistem</th><th>Nilai</th></tr></thead>'
        f"<tbody>{isi}</tbody></table></div>"
    )


def tabel_html(nama_beban: list[str], hitung_out: dict, sistem: dict, induk: dict | None = None) -> str:
    h = hitung_out["hasil"]
    watt = hitung_out["watt"]
    qcols = hitung_out["qcols"]
    n = len(qcols)
    n_depan = 6  # Nama, Grup, MCB, KA, Load, Cable (sebelum kolom R)

    o = ['<div class="xl-wrap"><table class="xl"><thead>']
    o.append(
        '<tr><th rowspan="3">Nama Sirkuit</th><th rowspan="3">Grouping<br>Number</th>'
        '<th colspan="3">Circuit Breaker</th><th colspan="2">Grouping Power</th>'
        f'<th colspan="{n}">BEBAN</th><th rowspan="3">Lain-lain<br>(W)</th></tr>'
    )
    o.append(
        '<tr><th rowspan="2">MCB UP</th><th rowspan="2">KA</th>'
        '<th rowspan="2">Load</th>'
        '<th rowspan="2">Cable</th><th rowspan="2">R</th>'
        + "".join(f'<th class="y">{e(nm)}</th>' for nm in nama_beban)
        + "</tr>"
    )
    o.append("<tr>" + "".join(f'<th class="y">{fmt_id(w)}</th>' for w in watt) + "</tr>")
    o.append("</thead><tbody>")

    for _, r in h.iterrows():
        o.append("<tr>")
        o.append(f'<td class="l">{e(r[COL_NAMA])}</td>')
        o.append(f"<td>{fmt_id(r[COL_GRUP])}</td>")
        o.append(f"<td>{fmt_id(r[COL_MCB])}</td>")
        o.append(f"<td>{fmt_id(r['ka'], 2)}</td>")
        o.append(f"<td>{fmt_id(r['load'])}</td>")
        o.append(f"<td>{e(r[COL_KABEL])}</td>")
        o.append(f'<td class="b">{fmt_id(r["load"])}</td>')
        for c in qcols:
            o.append(f"<td>{fmt_id(r[c], 0, kosong_jika_nol=True)}</td>")
        o.append(f"<td>{fmt_id(r[COL_LAIN], 0, kosong_jika_nol=True)}</td>")
        o.append("</tr>")

    # Baris total (hijau seperti di Excel)
    o.append(f'<tr><td colspan="{n_depan}" class="l b">TOTAL LOAD</td>')
    o.append(f'<td class="b">{fmt_id(hitung_out["total_load"])}</td>')
    for t in hitung_out["total_qty"]:
        o.append(f'<td class="g">{fmt_id(t)}</td>')
    o.append(f'<td class="g">{fmt_id(hitung_out["total_lain"])}</td></tr>')

    span_note = n + 1
    o.append(
        f'<tr><td colspan="{n_depan}" class="l b">VA (BEBAN PUNCAK WORST CASE SCENARIO)</td>'
        f'<td class="b">{fmt_id(hitung_out["va"])} VA</td>'
        f'<td colspan="{span_note}" class="note">Catatan : Semua Elektronik Nyala Bersamaan '
        f'(faktor puncak x{fmt_id(sistem["faktor_puncak"], 2)})</td></tr>'
    )
    o.append(
        f'<tr><td colspan="{n_depan}" class="l b">AMPERE</td>'
        f'<td class="b">{fmt_id(hitung_out["ampere"], 2)} A</td>'
        f'<td colspan="{span_note}" class="note">Catatan : Ampere = VA / tegangan '
        f'({fmt_id(sistem["tegangan"])} V)</td></tr>'
    )
    if induk is not None:  # saran kabel induk untuk beban keseluruhan (dari tabel AKLI)
        if induk.get("ok"):
            nilai = e(induk["teks"])
            ket = (f'Catatan : Mengacu tabel AKLI 1 fasa - daya tersedia {fmt_id(induk["va_tersedia"])} VA, '
                   f'MCB induk {fmt_id(induk["mcb"])} A, {e(induk["tipe"])}')
        else:
            nilai = "-"
            ket = (f'Catatan : Beban puncak {fmt_id(hitung_out["va"])} VA melebihi tabel AKLI 1 fasa '
                   f'(maks {fmt_id(induk["va_maks"])} VA), pertimbangkan sistem 3 fasa')
        o.append(
            f'<tr><td colspan="{n_depan}" class="l b">SARAN UKURAN KABEL INDUK (BEBAN KESELURUHAN)</td>'
            f'<td class="b">{nilai}</td>'
            f'<td colspan="{span_note}" class="note">{ket}</td></tr>'
        )
    o.append("</tbody></table></div>")
    return "".join(o)


def catatan_html(hitung_out: dict) -> str:
    return (
        '<div class="notes"><b>Catatan :</b><br>'
        "Pertimbangan penggunaan daya sesuai aturan keamanan 80% dari VA<br>"
        f"Total daya dalam satu bangunan dengan semua elektronik menyala "
        f"<b>{fmt_id(hitung_out['total_load'])} W</b><br>"
        f"Total Daya Semu (VA) dalam bangunan "
        f"<b>{fmt_id(hitung_out['va'])} VA</b></div>"
    )