"""Ekspor ke PDF - tanpa Streamlit (memakai reportlab).

Tabel SLD otomatis memakai kertas A4 landscape, atau A3 landscape bila kolom
armature banyak. Pangkat (mm²) ditulis dengan tag <super> agar tampil benar.
"""
from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, PageBreak, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules import akli_calc
from modules import standar_listrik as std
from modules.beban_listrik_calc import COL_GRUP, COL_KABEL, COL_LAIN, COL_MCB, COL_NAMA
from utils.formatting import fmt_id

NAVY = colors.HexColor("#1F3864")
KUNING = colors.HexColor("#FFF200")
HIJAU = colors.HexColor("#00B050")
CATATAN = colors.HexColor("#FFF9C4")
ABU = colors.HexColor("#EEF2F8")
GARIS = colors.HexColor("#8C96A3")


# ------------------------------------------------------------------ helper
def _teks(s) -> str:
    """Teks aman untuk Paragraph; pangkat 2 jadi <super>."""
    return escape(str(s)).replace("²", "<super>2</super>")


def _gaya(nama: str, ukuran: float, **kw) -> ParagraphStyle:
    font_name = kw.pop("fontName", "Helvetica")
    leading = kw.pop("leading", ukuran + 1.8)
    return ParagraphStyle(nama, fontName=font_name, fontSize=ukuran, leading=leading, **kw)


def _kaki(judul: str):
    def gambar(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#555555"))
        w, _ = doc.pagesize
        canvas.drawString(doc.leftMargin, 8 * mm, f"Kaizen PBG - {judul}")
        canvas.drawRightString(w - doc.rightMargin, 8 * mm,
                               f"Dicetak {datetime.now():%d-%m-%Y %H:%M}  |  Halaman {doc.page}")
        canvas.restoreState()
    return gambar


def _g(x) -> str:
    """Angka ala Indonesia tanpa nol berlebih: 2,5 / 0,45 / 13,9."""
    return f"{float(x):g}".replace(".", ",")


# ------------------------------------------------------------------ AKLI
def _tabel_akli(sub: pd.DataFrame, g_head: ParagraphStyle, lebar_total: float, ukuran: float) -> Table:
    kol = [k for k in akli_calc.COLS if k != "Fasa"]
    judul = {"VA": "VA", "VA Pembulatan": "VA<br/>Pembulatan", "kVA": "kVA",
             "Watt (PF 0,8)": "Watt<br/>(PF 0,8)", "Gol": "GOL", "MCB (A)": "MCB / MCCB<br/>(A)",
             "Tegangan (V)": "V", "Tipe Kabel": "Type Kabel", "Inti": "Inti",
             "Ukuran (mm²)": "Ukuran<br/>(mm<super>2</super>)"}
    rows = [[Paragraph(judul[k], g_head) for k in kol]]
    for _, r in sub.iterrows():
        baris = []
        for k in kol:
            v = r[k]
            if k in ("Gol", "Tipe Kabel"):
                baris.append(str(v))
            elif pd.isna(v):
                baris.append("")
            elif k in ("VA", "VA Pembulatan", "Watt (PF 0,8)"):
                baris.append(fmt_id(v))
            elif k in ("MCB (A)", "Tegangan (V)", "Inti"):
                baris.append(fmt_id(v))
            else:
                baris.append(_g(v))
        rows.append(baris)
    bobot = {"VA": 1.0, "VA Pembulatan": 1.2, "kVA": 0.8, "Watt (PF 0,8)": 1.1, "Gol": 0.6,
             "MCB (A)": 1.1, "Tegangan (V)": 0.7, "Tipe Kabel": 1.5, "Inti": 0.6, "Ukuran (mm²)": 1.1}
    tot = sum(bobot[k] for k in kol)
    t = Table(rows, colWidths=[lebar_total * bobot[k] / tot for k in kol], repeatRows=1)
    gaya = [
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), ukuran),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), KUNING), ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            gaya.append(("BACKGROUND", (0, i), (-1, i), ABU))
    t.setStyle(TableStyle(gaya))
    return t


def akli_pdf(tabel: pd.DataFrame) -> bytes:
    t = akli_calc.normalisasi(tabel).sort_values(["Fasa", "MCB (A)"], kind="stable")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=14 * mm, bottomMargin=16 * mm,
                            title="Tabel AKLI", author="Kaizen PBG")
    lebar = doc.width
    g_judul = _gaya("judul", 14, fontName="Helvetica-Bold", spaceAfter=2)
    g_sub = _gaya("sub", 8, textColor=colors.HexColor("#555555"), spaceAfter=8)
    g_sec = _gaya("sec", 10, fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=4)
    g_head = _gaya("head", 8, fontName="Helvetica-Bold", alignment=TA_CENTER)

    isi = [Paragraph("TABEL AKLI - DAYA TERSEDIA, MCB / MCCB, DAN UKURAN KABEL", g_judul),
           Paragraph("Sumber: tabel AKLI yang tersimpan di aplikasi Kaizen PBG", g_sub)]
    for fasa, nama in ((1, "1 FASA - 220 V"), (3, "3 FASA - 380 V")):
        sub = t[t["Fasa"] == fasa]
        if sub.empty:
            continue
        isi.append(Paragraph(nama, g_sec))
        isi.append(_tabel_akli(sub, g_head, lebar, 8))
        isi.append(Spacer(1, 6))
    doc.build(isi, onFirstPage=_kaki("Tabel AKLI"), onLaterPages=_kaki("Tabel AKLI"))
    return buf.getvalue()


# ------------------------------------------------------------------ SLD
def sld_pdf(proyek: dict, sistem: dict, labels: list[str], out: dict,
            induk: dict | None, catatan: list[str]) -> bytes:
    hasil, qcols, watt = out["hasil"], out["qcols"], out["watt"]
    n, m = len(qcols), len(hasil)

    # kertas: A4 landscape, atau A3 bila kolom armature banyak
    tetap = [64, 46, 32, 34, 36, 54, 40]  # Nama, Grup, MCB, KA, Load, Cable, R
    lain = 40
    margin = 12 * mm
    pagesize = landscape(A4)
    if (pagesize[0] - 2 * margin - sum(tetap) - lain) / max(n, 1) < 31:
        pagesize = landscape(A3)
    lebar_tersedia = pagesize[0] - 2 * margin
    ukuran = 7 if pagesize == landscape(A4) else 8.5
    w_arm = max(22.0, (lebar_tersedia - sum(tetap) - lain) / max(n, 1))
    widths = tetap + [w_arm] * n + [lain]
    if sum(widths) > lebar_tersedia:  # sangat banyak kolom: kecilkan proporsional
        skala = lebar_tersedia / sum(widths)
        widths = [w * skala for w in widths]
        ukuran = max(5.0, ukuran * skala)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=pagesize, leftMargin=margin, rightMargin=margin,
                            topMargin=12 * mm, bottomMargin=15 * mm,
                            title="Perhitungan Kebutuhan Listrik (SLD)", author="Kaizen PBG")

    g_judul = _gaya("judul", 14, fontName="Helvetica-Bold", spaceAfter=2)
    g_sub = _gaya("sub", 8, textColor=colors.HexColor("#555555"), spaceAfter=6)
    g_kecil = _gaya("kecil", 8.5, alignment=TA_LEFT)
    g_kecil_b = _gaya("kecil_b", 8.5, fontName="Helvetica-Bold")
    g_h = _gaya("h", ukuran, fontName="Helvetica-Bold", alignment=TA_CENTER, textColor=colors.white)
    g_hy = _gaya("hy", ukuran, fontName="Helvetica-Bold", alignment=TA_CENTER)
    g_c = _gaya("c", ukuran, alignment=TA_CENTER)
    g_cl = _gaya("cl", ukuran, alignment=TA_LEFT)
    g_note = _gaya("note", ukuran, fontName="Helvetica-Oblique", alignment=TA_LEFT)
    g_lb = _gaya("lb", ukuran, fontName="Helvetica-Bold", alignment=TA_LEFT)

    isi = [Paragraph("PERHITUNGAN KEBUTUHAN LISTRIK (SLD)", g_judul),
           Paragraph("Dibuat dari aplikasi Kaizen PBG", g_sub)]

    # ---- identitas proyek
    ident = Table([[Paragraph(k, g_kecil_b), Paragraph(": " + _teks(v), g_kecil)] for k, v in [
        ("PEKERJAAN", proyek["pekerjaan"]), ("LOKASI", proyek["lokasi"]),
        ("TAHUN", proyek["tahun"]), ("ITEM PEKERJAAN", proyek["item"])]],
        colWidths=[34 * mm, lebar_tersedia - 34 * mm], hAlign="LEFT")
    ident.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    isi += [ident, Spacer(1, 6)]

    # ---- data sistem
    ds = [[Paragraph("Sistem", _gaya("dh", 8.5, fontName="Helvetica-Bold", textColor=colors.white)),
           Paragraph("Nilai", _gaya("dh2", 8.5, fontName="Helvetica-Bold", textColor=colors.white))]]
    for k, v in [("Tegangan Sistem", f"{fmt_id(sistem['tegangan'])} V"),
                 ("Faktor Daya (PF)", fmt_id(sistem["pf"], 2)),
                 ("Faktor Beban Puncak", fmt_id(sistem["faktor_puncak"], 2)),
                 ("Sistem Grounding", sistem["grounding"]),
                 ("Resistansi Grounding Max", sistem["res_grounding"]),
                 ("Proteksi Kebocoran", sistem["proteksi"])]:
        ds.append([Paragraph(_teks(k), g_kecil), Paragraph(_teks(v), g_kecil_b)])
    t_ds = Table(ds, colWidths=[48 * mm, 40 * mm], hAlign="LEFT")
    t_ds.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
                              ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    isi += [t_ds, Spacer(1, 6)]

    # ---- landasan perencanaan kelistrikan
    g_sni = _gaya("sni_header", 7, fontName="Helvetica-Bold", alignment=TA_CENTER,
                  textColor=colors.white, leading=8)
    g_sni_cell = _gaya("sni_cell", 6.5, leading=8)
    isi.append(Paragraph("LANDASAN PERENCANAAN / SNI KELISTRIKAN", _gaya("sni_title", 10, fontName="Helvetica-Bold", spaceAfter=4)))
    sni_rows = [[Paragraph(label, g_sni) for label in ("Kategori", "Nomor", "Judul", "Status dan relevansi untuk SLD")]]
    for item in std.LANDASAN_SLD + std.LANDASAN_PELENGKAP_SLD:
        status_relevansi = f"{item['status']}<br/>{_teks(item['relevansi'])}"
        sni_rows.append([
            Paragraph(_teks(item["kategori"]), g_sni_cell),
            Paragraph(_teks(item["kode"]), g_sni_cell),
            Paragraph(_teks(item["judul"]), g_sni_cell),
            Paragraph(status_relevansi, g_sni_cell),
        ])
    sni_table = Table(sni_rows, colWidths=[25 * mm, 34 * mm, 78 * mm, lebar_tersedia - 137 * mm],
                      repeatRows=1, hAlign="LEFT")
    sni_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.35, GARIS),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ABU]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    isi.extend([
        sni_table,
        Spacer(1, 3),
        Paragraph(
            f"{_teks(std.CATATAN_LANDASAN_SLD)}<br/>"
            f'Sumber: <link href="{std.BSN_PUIL_URL}" color="#1F3864">Katalog PUIL BSN</link> · '
            f'<link href="{std.BSN_41_2025_URL}" color="#1F3864">SNI 0225-4-41:2025</link> · '
            f'<link href="{std.BSN_9_2020_URL}" color="#1F3864">SNI 0225-9:2020</link> · '
            f'<link href="{std.AKLI_URL}" color="#1F3864">AKLI</link> · '
            f'<link href="{std.NEC_URL}" color="#1F3864">NFPA 70/NEC</link>', g_sub),
        Spacer(1, 6),
    ])

    # ---- tabel utama
    nc = 8 + n  # jumlah kolom
    C_LAIN = 7 + n
    kosong = [""] * nc
    h0, h1, h2 = list(kosong), list(kosong), list(kosong)
    h0[0], h0[1] = Paragraph("Nama Sirkuit", g_h), Paragraph("Grouping<br/>Number", g_h)
    h0[2], h0[5], h0[7] = Paragraph("Circuit Breaker", g_h), Paragraph("Grouping Power", g_h), Paragraph("BEBAN", g_h)
    h0[C_LAIN] = Paragraph("Lain-lain<br/>(W)", g_h)
    for c, tk in zip(range(2, 7), ["MCB UP", "KA", "Load", "Cable", "R"]):
        h1[c] = Paragraph(tk, g_h)
    for i in range(n):
        h1[7 + i] = Paragraph(_teks(labels[i]), g_hy)
        h2[7 + i] = Paragraph(fmt_id(watt[i]), g_hy)
    rows = [h0, h1, h2]

    for _, r in hasil.iterrows():
        baris = [Paragraph(_teks(r[COL_NAMA]), g_cl), fmt_id(r[COL_GRUP]), fmt_id(r[COL_MCB]),
                 fmt_id(r["ka"], 2), fmt_id(r["load"]), Paragraph(_teks(r[COL_KABEL]), g_c),
                 Paragraph(f"<b>{fmt_id(r['load'])}</b>", g_c)]
        baris += [fmt_id(r[q], 0, kosong_jika_nol=True) for q in qcols]
        baris.append(fmt_id(r[COL_LAIN], 0, kosong_jika_nol=True))
        rows.append(baris)

    rt = 3 + m
    tot = [Paragraph("TOTAL LOAD", g_lb)] + [""] * 5 + [Paragraph(f"<b>{fmt_id(out['total_load'])}</b>", g_c)]
    tot += [fmt_id(x) for x in out["total_qty"]] + [fmt_id(out["total_lain"])]
    rows.append(tot)

    def baris_ringkas(label, nilai, catatan_txt):
        b = [Paragraph(label, g_lb)] + [""] * 5 + [Paragraph(f"<b>{_teks(nilai)}</b>", g_c)]
        b += [Paragraph(_teks(catatan_txt), g_note)] + [""] * n
        return b

    rows.append(baris_ringkas("VA (BEBAN PUNCAK WORST CASE SCENARIO)", f"{fmt_id(out['va'])} VA",
                              f"Catatan : Semua Elektronik Nyala Bersamaan (faktor puncak x{fmt_id(sistem['faktor_puncak'], 2)})"))
    rows.append(baris_ringkas("AMPERE", f"{fmt_id(out['ampere'], 2)} A",
                              f"Catatan : Ampere = VA / tegangan ({fmt_id(sistem['tegangan'])} V)"))
    ada_induk = induk is not None
    if ada_induk:
        if induk.get("ok"):
            nilai = induk["teks"]
            ket = (f"Catatan : Mengacu tabel AKLI 1 fasa - daya tersedia {fmt_id(induk['va_tersedia'])} VA, "
                   f"MCB induk {fmt_id(induk['mcb'])} A, {induk['tipe']}")
        else:
            nilai = "-"
            ket = (f"Catatan : Beban puncak {fmt_id(out['va'])} VA melebihi tabel AKLI 1 fasa "
                   f"(maks {fmt_id(induk['va_maks'])} VA), pertimbangkan sistem 3 fasa")
        rows.append(baris_ringkas("SARAN UKURAN KABEL INDUK (BEBAN KESELURUHAN)", nilai, ket))
    r_akhir = len(rows) - 1

    tb = Table(rows, colWidths=widths, repeatRows=3)
    st = [
        ("FONTNAME", (0, 3), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 3), (-1, -1), ukuran),
        ("ALIGN", (1, 3), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        # header
        ("BACKGROUND", (0, 0), (-1, 2), NAVY),
        ("BACKGROUND", (7, 1), (6 + n, 2), KUNING),
        ("SPAN", (0, 0), (0, 2)), ("SPAN", (1, 0), (1, 2)), ("SPAN", (2, 0), (4, 0)),
        ("SPAN", (5, 0), (6, 0)), ("SPAN", (7, 0), (6 + n, 0)), ("SPAN", (C_LAIN, 0), (C_LAIN, 2)),
    ]
    for c in range(2, 7):
        st.append(("SPAN", (c, 1), (c, 2)))
    if n == 1:  # SPAN 1 sel tidak diperlukan
        st = [s for s in st if s != ("SPAN", (7, 0), (6 + n, 0))]
    # kolom R & total
    st.append(("BACKGROUND", (6, 3), (6, 2 + m), ABU))
    # baris total (hijau) + ringkasan
    st += [("SPAN", (0, rt), (5, rt)), ("BACKGROUND", (0, rt), (6, rt), ABU),
           ("BACKGROUND", (7, rt), (C_LAIN, rt), HIJAU), ("TEXTCOLOR", (7, rt), (C_LAIN, rt), colors.white),
           ("FONTNAME", (7, rt), (C_LAIN, rt), "Helvetica-Bold")]
    for rr in range(rt + 1, r_akhir + 1):
        st += [("SPAN", (0, rr), (5, rr)), ("SPAN", (7, rr), (C_LAIN, rr)),
               ("BACKGROUND", (0, rr), (6, rr), ABU), ("BACKGROUND", (7, rr), (C_LAIN, rr), CATATAN)]
    tb.setStyle(TableStyle(st))
    isi.append(tb)

    # ---- catatan bawah tabel (satu blok utuh, tidak terpotong antar halaman)
    g_cat = _gaya("cat", 8.5, spaceAfter=1)
    blok = [Paragraph("<b>Catatan :</b>", g_cat),
            Paragraph("Pertimbangan penggunaan daya sesuai aturan keamanan 80% dari VA", g_cat),
            Paragraph(f"Total daya dalam satu bangunan dengan semua elektronik menyala "
                      f"<b>{fmt_id(out['total_load'])} W</b>", g_cat),
            Paragraph(f"Total Daya Semu (VA) dalam bangunan <b>{fmt_id(out['va'])} VA</b>", g_cat)]
    if catatan:
        blok += [Spacer(1, 6), Paragraph("<b>Catatan penyesuaian MCB &amp; kabel :</b>", g_cat)]
        blok += [Paragraph("- " + _teks(c), g_cat) for c in catatan]
    isi += [Spacer(1, 6), KeepTogether(blok)]

    doc.build(isi, onFirstPage=_kaki("Perhitungan Kebutuhan Listrik (SLD)"),
              onLaterPages=_kaki("Perhitungan Kebutuhan Listrik (SLD)"))
    return buf.getvalue()


# ------------------------------------------------------------------ AC
def ac_pdf(hasil_standar: pd.DataFrame, hasil_full: pd.DataFrame, data: dict,
           proyek: dict, orang_dasar: float, faktor_lampu: float) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A3), leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=16 * mm,
                            title="Kebutuhan AC", author="Kaizen PBG")
    judul = _gaya("ac_judul", 16, fontName="Helvetica-Bold", spaceAfter=3)
    sub = _gaya("ac_sub", 8.5, textColor=colors.HexColor("#555555"), spaceAfter=8)
    bagian = _gaya("ac_bagian", 11, fontName="Helvetica-Bold", spaceBefore=7, spaceAfter=5)
    normal = _gaya("ac_normal", 8)
    kecil = _gaya("ac_kecil", 7, leading=8.5)
    header = _gaya("ac_header", 7, fontName="Helvetica-Bold", textColor=colors.white,
                   alignment=TA_CENTER, leading=8)

    def paragraph(value, style=normal):
        return Paragraph(_teks(value).replace("\n", "<br/>"), style)

    def table(headers, rows, weights, font_size=7, bold_rows=()):
        widths = [doc.width * weight / sum(weights) for weight in weights]
        contents = [[paragraph(value, header) for value in headers]]
        contents.extend([[paragraph(value, kecil) for value in row] for row in rows])
        result = Table(contents, colWidths=widths, repeatRows=1, hAlign="LEFT")
        styles = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("GRID", (0, 0), (-1, -1), 0.35, GARIS),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        for index in range(2, len(contents), 2):
            styles.append(("BACKGROUND", (0, index), (-1, index), ABU))
        for index in bold_rows:
            styles.extend([
                ("BACKGROUND", (0, index + 1), (-1, index + 1), ABU),
                ("FONTNAME", (0, index + 1), (-1, index + 1), "Helvetica-Bold"),
            ])
        result.setStyle(TableStyle(styles))
        return result

    info_rows = [[paragraph(label, _gaya(f"ac_meta_{i}", 8, fontName="Helvetica-Bold")),
                  paragraph(proyek.get(key, "") or "-")]
                 for i, (label, key) in enumerate((
                     ("Pekerjaan", "pekerjaan"), ("Lokasi", "lokasi"),
                     ("Tahun", "tahun"), ("Item pekerjaan", "item")))]
    info = Table(info_rows, colWidths=[32 * mm, doc.width - 32 * mm], hAlign="LEFT")
    info.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("TOPPADDING", (0, 0), (-1, -1), 1),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))

    isi: list[Flowable] = [Paragraph("KEBUTUHAN AC", judul),
                           Paragraph("Laporan perhitungan Standar dan Full Calculation", sub),
                           info, Spacer(1, 5)]
    standar = data.get("standar", [])
    if standar:
        isi.append(Paragraph("Landasan Perencanaan / SNI", bagian))
        isi.append(table(
            ["Standar", "Judul / Ruang Lingkup", "Peran"],
            [[s.get("kode", ""), s.get("judul", ""), s.get("peran", "")] for s in standar],
            [1.2, 3.5, 2.3], 7,
        ))

    def rows_standar(hasil):
        rows = []
        for _, r in hasil.iterrows():
            rows.append([
                f"{r['Lantai']}\n{r['Ruangan']}",
                f"{fmt_id(r['L_m'], 2)} × {fmt_id(r['W_m'], 2)} × {fmt_id(r['H_m'], 2)}",
                fmt_id(r["I"], 0), fmt_id(r["E"], 0), fmt_id(r["Btu"], 0),
                r["Jenis AC"], fmt_id(r["Jumlah"], 0), fmt_id(r["N"], 3),
                r["Status"], r["Rekomendasi"],
            ])
        if not hasil.empty:
            rows.append(["TOTAL", "", "", "", fmt_id(hasil["Btu"].sum(), 0), "",
                         fmt_id(hasil["Jumlah"].sum(), 0), "", "", ""])
        return rows

    isi.append(Paragraph("Standar Calculation", bagian))
    isi.append(Paragraph("Q = (L × W × H × I × E) / pembagi; dimensi dikonversi ke feet.", sub))
    isi.append(table(
        ["Lantai / Ruangan", "Dimensi (m)", "I", "E", "Kebutuhan (Btu/h)",
         "Jenis AC", "Unit", "N (AC)", "Status", "Rekomendasi"],
        rows_standar(hasil_standar), [2.0, 1.8, 0.45, 0.45, 1.25, 0.9, 0.5, 0.65, 0.8, 1.1],
    ))

    isi.append(PageBreak())
    isi.append(Paragraph("Full Calculation", bagian))
    isi.append(Paragraph(
        f"Q total = Q dasar + Q orang + Q lampu + Q peralatan. "
        f"Orang dasar: {fmt_id(orang_dasar, 0)}; faktor lampu: {fmt_id(faktor_lampu, 2)}.", sub))
    rows_full = []
    for _, r in hasil_full.iterrows():
        rows_full.append([
            f"{r['Lantai']}\n{r['Ruangan']}",
            f"{fmt_id(r['L_m'], 2)} × {fmt_id(r['W_m'], 2)} × {fmt_id(r['H_m'], 2)}",
            fmt_id(r["Q_dasar"], 0), fmt_id(r["Orang"], 0), fmt_id(r["Q_orang"], 0),
            f"{fmt_id(r['N_lampu'], 0)} × {fmt_id(r['W_lampu'], 0)}", fmt_id(r["Q_lampu"], 0),
            fmt_id(r["W_alat"], 0), fmt_id(r["Q_alat"], 0), fmt_id(r["Btu"], 0),
            r["Jenis AC"], fmt_id(r["Jumlah"], 0), fmt_id(r["N"], 3),
            r["Status"], r["Rekomendasi"],
        ])
    if not hasil_full.empty:
        rows_full.append([
            "TOTAL", "", fmt_id(hasil_full["Q_dasar"].sum(), 0),
            fmt_id(hasil_full["Orang"].sum(), 0), fmt_id(hasil_full["Q_orang"].sum(), 0), "",
            fmt_id(hasil_full["Q_lampu"].sum(), 0), fmt_id(hasil_full["W_alat"].sum(), 0),
            fmt_id(hasil_full["Q_alat"].sum(), 0), fmt_id(hasil_full["Btu"].sum(), 0), "",
            fmt_id(hasil_full["Jumlah"].sum(), 0), "", "", "",
        ])
    isi.append(table(
        ["Lantai / Ruangan", "Dimensi (m)", "Q Dasar", "Orang", "Q Orang", "Lampu (jml × W)",
         "Q Lampu", "Alat (W)", "Q Alat", "Total (Btu/h)", "Jenis AC", "Unit", "N", "Status", "Rekomendasi"],
        rows_full, [2.0, 1.8, 0.9, 0.5, 0.85, 1.0, 0.85, 0.65, 0.8, 1.0, 0.8, 0.45, 0.6, 0.7, 0.95],
    ))
    isi.append(Spacer(1, 7))
    isi.append(Paragraph(
        "Catatan: estimasi ini mengikuti rumus dan asumsi yang ditampilkan pada aplikasi. "
        "Periksa kembali data ruangan, beban internal, dan kapasitas unit sebelum digunakan untuk perencanaan.", kecil))
    doc.build(isi, onFirstPage=_kaki("Kebutuhan AC"), onLaterPages=_kaki("Kebutuhan AC"))
    return buf.getvalue()


# -------------------------------------------------------------- sanitasi
def sanitasi_pdf(h: dict, data: dict, proyek: dict) -> bytes:
    from modules import sanitasi_calc

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=16 * mm,
                            title="Sanitasi dan Air Bersih", author="Kaizen PBG")
    judul = _gaya("san_judul", 16, fontName="Helvetica-Bold", spaceAfter=3)
    sub = _gaya("san_sub", 8.5, textColor=colors.HexColor("#555555"), spaceAfter=7)
    bagian = _gaya("san_bagian", 10, fontName="Helvetica-Bold", spaceBefore=7, spaceAfter=4)
    normal = _gaya("san_normal", 7.5, leading=9)
    kecil = _gaya("san_kecil", 6.8, leading=8)
    header = _gaya("san_header", 7, fontName="Helvetica-Bold", textColor=colors.white,
                   alignment=TA_CENTER, leading=8)

    def paragraph(value, style=normal):
        return Paragraph(_teks(value).replace("\n", "<br/>"), style)

    isi: list[Flowable] = [Paragraph("SANITASI & AIR BERSIH", judul),
                           Paragraph("Laporan perhitungan kebutuhan air, air limbah, tangki septik, dan resapan", sub)]
    meta = [[paragraph(label, _gaya(f"san_meta_{i}", 7.5, fontName="Helvetica-Bold")),
             paragraph(proyek.get(key, "") or "-")]
            for i, (label, key) in enumerate((
                ("Pekerjaan", "pekerjaan"), ("Lokasi", "lokasi"),
                ("Tahun", "tahun"), ("Item pekerjaan", "item")))]
    meta_table = Table(meta, colWidths=[30 * mm, doc.width - 30 * mm], hAlign="LEFT")
    meta_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    isi.extend([meta_table, Spacer(1, 5)])

    standards = data.get("standar", [])
    if standards:
        isi.append(Paragraph("Landasan Perencanaan / SNI", bagian))
        standard_rows = [[paragraph("Standar", header), paragraph("Judul", header), paragraph("Peran", header)]]
        standard_rows.extend([[paragraph(s.get("kode", ""), kecil), paragraph(s.get("judul", ""), kecil),
                               paragraph(s.get("peran", ""), kecil)] for s in standards])
        standard_table = Table(standard_rows,
                               colWidths=[doc.width * 0.18, doc.width * 0.42, doc.width * 0.40],
                               repeatRows=1, hAlign="LEFT")
        standard_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.35, GARIS),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        isi.append(standard_table)
    if data.get("catatan_standar"):
        isi.append(Paragraph(_teks(data["catatan_standar"]), kecil))

    for section in sanitasi_calc.susun_seksi(h, data):
        isi.append(Paragraph(_teks(section["judul"]), bagian))
        headers = section["kolom"]
        widths_by_count = {
            3: [2.2, 1.0, 1.0],
            4: [1.8, 3.2, 1.2, 0.8],
            5: [1.6, 3.0, 1.2, 1.2, 0.8],
            6: [0.4, 2.0, 0.8, 1.2, 1.4, 1.0],
        }
        weights = widths_by_count.get(len(headers), [1.0] * len(headers))
        widths = [doc.width * weight / sum(weights) for weight in weights]
        rows = [[paragraph(value, header) for value in headers]]
        rows.extend([[paragraph(value, kecil) for value in row] for row in section["baris"]])
        tbl = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        styles = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.35, GARIS),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (2, 1), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        for row_index in range(2, len(rows), 2):
            styles.append(("BACKGROUND", (0, row_index), (-1, row_index), ABU))
        for row_index in section.get("tebal", []):
            styles.extend([
                ("BACKGROUND", (0, row_index + 1), (-1, row_index + 1), ABU),
                ("FONTNAME", (0, row_index + 1), (-1, row_index + 1), "Helvetica-Bold"),
            ])
        tbl.setStyle(TableStyle(styles))
        isi.extend([tbl, Spacer(1, 3)])

    for warning in h.get("peringatan", []):
        isi.append(Paragraph("Peringatan: " + _teks(warning), normal))
    isi.append(Spacer(1, 5))
    isi.append(Paragraph(
        "Catatan: hasil merupakan estimasi perencanaan. Verifikasi kondisi lapangan, uji perkolasi, "
        "serta persyaratan SNI dan peraturan yang berlaku sebelum pelaksanaan.", kecil))
    doc.build(isi, onFirstPage=_kaki("Sanitasi & Air Bersih"),
              onLaterPages=_kaki("Sanitasi & Air Bersih"))
    return buf.getvalue()