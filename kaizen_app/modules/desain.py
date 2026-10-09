"""Sistem desain bersama untuk tampilan HTML modul (kartu KPI, label status, bar kapasitas, judul seksi)."""
from __future__ import annotations

from html import escape

CSS = """
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


TONE = {"MEMENUHI": "good", "TIDAK MEMENUHI": "bad", "KURANG": "bad", "MANUAL": "warn", "BELUM DICEK": "warn"}


def chip(status: str) -> str:
    return f'<span class="chip {TONE.get(status, "warn")}">{escape(status)}</span>'


def gauge(rasio: float | None) -> str:
    """Bar pemakaian/pemenuhan: rasio 1,0 = 100%."""
    if rasio is None:
        return '<div class="gl"><div class="gauge"></div><em>–</em></div>'
    tone = "var(--good)" if rasio <= 0.8 else ("var(--warn)" if rasio <= 1 else "var(--bad)")
    w = min(rasio, 1.25) / 1.25 * 100
    return (f'<div class="gl"><div class="gauge"><span style="width:{w:.0f}%;background:{tone}"></span></div>'
            f'<em>{rasio * 100:.0f}%</em></div>')


def gauge_target(rasio: float | None) -> str:
    """Bar pemenuhan target: >= 100% baik (hijau), < 100% buruk (merah)."""
    if rasio is None:
        return '<div class="gl"><div class="gauge"></div><em>–</em></div>'
    tone = "var(--good)" if rasio >= 1 else "var(--bad)"
    w = min(rasio, 2.0) / 2.0 * 100
    return (f'<div class="gl"><div class="gauge"><span style="width:{w:.0f}%;background:{tone}"></span></div>'
            f'<em>{rasio * 100:.0f}%</em></div>')


def kpi(items) -> str:
    out = ['<div class="kpis">']
    for label, nilai, unit, tone in items:
        out.append(f'<div class="kpi {tone}"><div class="l">{escape(label)}</div>'
                   f'<div class="v">{nilai}<small>{escape(unit)}</small></div></div>')
    return "".join(out) + "</div>"


def sec(no, judul: str) -> str:
    return f'<h3 class="sec"><span class="no">{no}</span>{escape(judul)}</h3>'


def kop(proyek: dict) -> str:
    rows = [("PEKERJAAN", proyek.get("pekerjaan", "")), ("LOKASI", proyek.get("lokasi", "")),
            ("TAHUN", proyek.get("tahun", "")), ("ITEM PEKERJAAN", proyek.get("item", ""))]
    return '<div class="kop">' + "".join(f"<b>{k}</b><span>{escape(str(v))}</span>" for k, v in rows) + "</div>"


def peringatan(daftar) -> str:
    return "".join(f'<div class="pr">⚠ {escape(w)}</div>' for w in daftar)
