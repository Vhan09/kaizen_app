"""Tampilan HTML Modul Penghawaan Alami dan Ventilasi Mekanis."""
from __future__ import annotations

from html import escape

from modules import desain as ds
from modules.ventilasi_calc import (
    ST_DATA, ST_EXH, ST_SESUAI, ST_TERBUKA, ST_TIDAK, ST_TINJAU,
)
from utils.formatting import fmt_id

DASAR_STANDAR = [
    ("SNI 03-6572-2001, pasal 4.3.2",
     "Luas bukaan ventilasi alami sekurang-kurangnya 5% dari luas lantai ruangan."),
    ("SNI 03-6572-2001, pasal 4.3.3 & 4.3.5",
     "Ventilasi dari ruang bersebelahan perlu verifikasi khusus; kompartemen sanitasi tidak boleh "
     "mengandalkan ruang sebelah. Ruang berkloset tanpa hubungan udara luar perlu exhaust mekanis."),
    ("SNI 03-6572-2001, Tabel 4.4.1",
     "Acuan ventilasi mekanis: kamar mandi 10, dapur 20, dan lobi/koridor/tangga 4 kali pergantian udara per jam."),
]

_TONE = {
    ST_SESUAI: "MEMENUHI", ST_EXH: "MEMENUHI", ST_TIDAK: "KURANG",
    ST_TINJAU: "TINJAUAN", ST_DATA: "DATA BELUM LENGKAP", ST_TERBUKA: "AREA TERBUKA",
}


def status_kelas(status: str) -> str:
    return {
        ST_SESUAI: "ok", ST_EXH: "ok", ST_TIDAK: "no",
        ST_TINJAU: "warn", ST_DATA: "warn", ST_TERBUKA: "na",
    }.get(status, "na")


def _tone(status: str) -> str:
    return {
        ST_SESUAI: "good", ST_EXH: "good", ST_TIDAK: "bad",
        ST_TINJAU: "warn", ST_DATA: "warn", ST_TERBUKA: "mute",
    }.get(status, "warn")


def _status_chip(status: str) -> str:
    return ds.chip(_TONE.get(status, status.upper()))


def _n(x: float, digit: int = 2) -> str:
    return "-" if x is None else fmt_id(x, digit)


def _kpi(h: dict) -> str:
    c = h["hitungan"]
    memenuhi = c[ST_SESUAI] + c[ST_EXH]
    belum = c[ST_TIDAK] + c[ST_TINJAU] + c[ST_DATA]
    nilai = memenuhi / h["dinilai"] * 100 if h["dinilai"] else 0
    return ds.kpi([
        ("Ruang tertutup dinilai", str(h["dinilai"]), "ruang", "aqua"),
        ("Memenuhi", str(memenuhi), "ruang", "good"),
        ("Perlu tindak lanjut", str(belum), "ruang", "good" if belum == 0 else "bad"),
        ("Memenuhi saat ini", f"{fmt_id(nilai, 0)}", "% ruang", "good" if belum == 0 else "warn"),
    ])


def _dasar(h: dict) -> str:
    rasio = h["rasio"]
    cards = "".join(
        f'<div class="card"><b>{escape(title)}</b><div class="note">{escape(detail)}</div></div>'
        for title, detail in DASAR_STANDAR
    )
    return (
        ds.sec(1, "Dasar Penilaian")
        + f'<div class="formula">Syarat bukaan alami: <b>Av &ge; {fmt_id(rasio * 100, 1)}% &times; Ar</b>'
          '<small>Av = jumlah bukaan &times; tinggi &times; lebar &nbsp; &middot; &nbsp; Ar = panjang ruang &times; lebar ruang</small>'
          '</div><div class="two">'
        + cards + '</div>'
        + '<div class="note">Ruang yang dinilai dengan bukaan ke ruang bersebelahan tetap memerlukan verifikasi '
          'luas bukaan gabungan sesuai SNI. Pemeriksaan ACH menggunakan volume ruang dan debit exhaust yang diinput.</div>'
    )


def _meter(rasio: float, warna: str) -> str:
    lebar = min(max(rasio / 1.5, 0), 1) * 100
    return (
        '<div class="gl"><div class="gauge"><span '
        f'style="width:{lebar:.0f}%;background:var(--{warna})"></span></div>'
        f'<em>{fmt_id(rasio * 100, 0)}%</em></div>'
    )


def _tabel_alami(h: dict) -> str:
    out = [ds.sec(2, "Hasil Perhitungan per Ruangan")]
    out.append(
        '<div style="overflow-x:auto"><table class="t"><tr>'
        '<th>Lantai</th><th>Ruangan</th><th>Metode</th><th>Ar (m&sup2;)</th>'
        '<th>Av (m&sup2;)</th><th>Minimum (m&sup2;)</th><th>Selisih (m&sup2;)</th>'
        '<th>Pemenuhan</th><th>Status</th></tr>'
    )
    for b in h["baris"]:
        if b["status"] == ST_TERBUKA:
            cells = (
                f'<td colspan="5" class="c" style="color:var(--grey)">Tidak memerlukan '
                'perhitungan ventilasi ruang tertutup</td>'
            )
        else:
            persen = b["av"] / b["av_min"] if b["av_min"] > 0 else 0
            selisih = b["selisih"]
            tanda = "+" if selisih >= 0 else "−"
            cells = (
                f'<td class="n">{_n(b["ar"], 3)}</td><td class="n">{_n(b["av"], 3)}</td>'
                f'<td class="n">{_n(b["av_min"], 3)}</td>'
                f'<td class="n">{tanda}{fmt_id(abs(selisih), 3)}</td>'
                f'<td>{_meter(persen, _tone(b["status"]))}</td>'
            )
        out.append(
            f'<tr><td>{escape(b["lantai"])}</td><td><b>{escape(b["nama"])}</b></td>'
            f'<td class="c">{escape(b["metode"])}</td>{cells}'
            f'<td class="c">{_status_chip(b["status"])}</td></tr>'
        )
    out.append("</table></div>")
    out.append(
        '<div class="note">Selisih positif berarti luas bukaan memenuhi ambang rasio yang dipilih; '
        'selisih negatif menunjukkan tambahan luas bukaan efektif yang dibutuhkan. Ruang terbuka tidak dinilai.</div>'
    )
    return "".join(out)


def _tabel_exhaust(h: dict) -> str:
    out = [ds.sec(3, "Pemeriksaan Exhaust Mekanis")]
    if not h["exhaust"]:
        return "".join(out) + '<div class="concl">Belum ada ruang yang menggunakan metode exhaust.</div>'
    out.append(
        '<div style="overflow-x:auto"><table class="t"><tr><th>Ruangan</th><th>Volume (m&sup3;)</th>'
        '<th>Debit input (m&sup3;/menit)</th><th>ACH aktual</th><th>ACH minimum</th>'
        '<th>Debit minimum (m&sup3;/jam)</th><th>Status</th></tr>'
    )
    for b in h["exhaust"]:
        out.append(
            f'<tr><td><b>{escape(b["nama"])}</b></td><td class="n">{_n(b["vol"], 3)}</td>'
            f'<td class="n">{_n(b["q_menit"], 2)}</td><td class="n"><b>{_n(b["ach"], 1)}</b></td>'
            f'<td class="n">{_n(b["ach_min"], 0)}</td><td class="n">{_n(b["q_min"], 1)}</td>'
            f'<td class="c">{_status_chip(b["status"])}</td></tr>'
        )
    out.append("</table></div>")
    out.append(
        '<div class="note">ACH = debit (m&sup3;/jam) &divide; volume ruang. Debit minimum berasal dari '
        'ACH minimum &times; volume; pastikan kapasitas aktual kipas sesuai spesifikasi pabrikan.</div>'
    )
    return "".join(out)


def _solusi(b: dict) -> tuple[str, str]:
    if b["status"] == ST_DATA:
        missing = []
        if b["ar"] <= 0:
            missing.append("panjang dan lebar ruang")
        if "Exhaust" in b["metode"] and b["vol"] <= 0:
            missing.append("tinggi plafon untuk menghitung volume")
        if "Exhaust" in b["metode"] and b["q_menit"] <= 0:
            missing.append("debit exhaust dari spesifikasi kipas")
        return (
            "Lengkapi " + ("; ".join(missing) if missing else "dimensi ruang") + " lalu periksa ulang hasil.",
            "Masukkan ukuran bersih ruang dan debit aktual, bukan kapasitas perkiraan.",
        )
    if b["status"] == ST_TINJAU:
        return (
            "Verifikasi luas bukaan ruang ini bersama ruang sebelah terhadap luas gabungan keduanya sebelum "
            "menyatakan memenuhi.",
            "Pastikan ruang sebelah bukan kompartemen sanitasi. Jika verifikasi tidak dapat dilakukan, arahkan "
            "bukaan langsung ke ruang luar atau gunakan exhaust.",
        )
    if b["metode"] == "Exhaust":
        kurang = max(b["q_min"] - b["q_jam"], 0)
        return (
            f"Naikkan debit exhaust sedikitnya {fmt_id(b['q_min'], 1)} m&sup3;/jam "
            f"(tambahan sekitar {fmt_id(kurang, 1)} m&sup3;/jam) agar mencapai ACH minimum.",
            "Pilih kipas berdasarkan debit pada tekanan kerja dan jalur duct aktual; ukur ulang setelah pemasangan.",
        )
    if b["jenis"] == "Kamar mandi / WC" and b["hadap"] == "Ruang bersebelahan":
        return (
            "Jangan mengandalkan bukaan dari ruang bersebelahan untuk kompartemen sanitasi; buat bukaan ke ruang "
            "luar atau sediakan exhaust mekanis.",
            f"Jika memakai exhaust, targetkan sekurang-kurangnya {fmt_id(b['q_min'], 1)} m&sup3;/jam "
            "berdasarkan volume ruang dan ACH acuan.",
        )
    tambah = max(b["av_min"] - b["av"], 0)
    utama = f"Tambahkan luas bukaan efektif sekurang-kurangnya {fmt_id(tambah, 3)} m&sup2;."
    bila_exhaust = (
        f"Alternatifnya, sediakan exhaust minimal {fmt_id(b['q_min'], 1)} m&sup3;/jam bila ACH "
        "ruangan memiliki acuan."
        if b["q_min"] > 0 and b["vol"] > 0 else
        "Pastikan setiap bukaan benar-benar dapat dibuka dan menghadap sumber udara yang sesuai."
    )
    return utama, bila_exhaust


def _saran(h: dict) -> str:
    out = [ds.sec(4, "Saran Penanganan per Ruangan")]
    if not h["perbaikan"]:
        return "".join(out) + '<div class="concl">Semua ruang tertutup memenuhi dasar yang dipilih; tidak ada tindak lanjut otomatis.</div>'
    out.append(
        '<div style="overflow-x:auto"><table class="t"><tr><th>Ruangan</th><th>Status</th>'
        '<th>Temuan dan tindakan utama</th><th>Alternatif / hal yang perlu diverifikasi</th></tr>'
    )
    for b in h["perbaikan"]:
        utama, pendukung = _solusi(b)
        out.append(
            f'<tr><td><b>{escape(b["lantai"])}<br>{escape(b["nama"])}</b></td>'
            f'<td class="c">{_status_chip(b["status"])}</td>'
            f'<td>{escape(b["ket"])}<br><br><b>Saran:</b> {utama}</td>'
            f'<td>{pendukung}</td></tr>'
        )
    out.append("</table></div>")
    out.append(
        '<div class="note">Saran adalah langkah awal berdasarkan data yang dimasukkan, bukan pengganti '
        'verifikasi lapangan atau persetujuan tenaga ahli. Perhitungkan privasi, hujan, keamanan, kebisingan, '
        'hambatan aliran, dan kondisi bukaan sebelum menentukan solusi.</div>'
    )
    return "".join(out)


def _rekap(h: dict, banding: list[dict]) -> str:
    out = [ds.sec(5, "Rekap Status per Lantai")]
    rows = []
    for lantai, daftar in h["kelompok"]:
        tertutup = [b for b in daftar if b["status"] != ST_TERBUKA]
        memenuhi = sum(b["status"] in (ST_SESUAI, ST_EXH) for b in tertutup)
        perlu = len(tertutup) - memenuhi
        rows.append(
            f'<tr><td><b>{escape(lantai)}</b></td><td class="c">{len(tertutup)}</td>'
            f'<td class="c">{sum(b["status"] == ST_TERBUKA for b in daftar)}</td>'
            f'<td class="c">{memenuhi}</td><td class="c">{perlu}</td></tr>'
        )
    out.append(
        '<table class="t"><tr><th>Lantai</th><th>Ruang tertutup</th><th>Ruang terbuka</th>'
        '<th>Memenuhi</th><th>Perlu tindak lanjut</th></tr>' + "".join(rows) + "</table>"
    )
    out.append(ds.sec(6, "Perbandingan Dasar Rasio"))
    out.append(
        '<table class="t"><tr><th>Dasar rasio</th><th>Ruang dinilai</th><th>Memenuhi</th>'
        '<th>Tidak sesuai</th><th>Perlu tinjauan</th><th>Terbuka</th></tr>'
        + "".join(
            f'<tr><td><b>{escape(b["dasar"])}</b></td><td class="c">{b["dinilai"]}</td>'
            f'<td class="c">{b["sesuai"]}</td><td class="c">{b["tidak"]}</td>'
            f'<td class="c">{b["tinjau"]}</td><td class="c">{b["terbuka"]}</td></tr>'
            for b in banding
        )
        + "</table>"
    )
    return "".join(out)


def _kesimpulan(h: dict) -> str:
    c = h["hitungan"]
    perlu = c[ST_TIDAK] + c[ST_TINJAU] + c[ST_DATA]
    if not h["dinilai"]:
        pesan = "Belum ada ruang tertutup yang dapat dinilai. Lengkapi data ruang untuk mendapatkan hasil."
    elif perlu:
        pesan = (
            f"{h['dinilai']} ruang tertutup dinilai; {c[ST_SESUAI] + c[ST_EXH]} memenuhi dan {perlu} "
            "memerlukan tindak lanjut. Lihat saran per ruang sebelum menyimpulkan kepatuhan."
        )
    else:
        pesan = f"Semua {h['dinilai']} ruang tertutup memenuhi dasar yang dipilih pada pemeriksaan awal ini."
    return ds.sec(7, "Kesimpulan") + f'<div class="concl {"bad" if perlu else ""}">{escape(pesan)}</div>'


def render(h: dict, proyek: dict | None, bagian: str, banding: list[dict] | None = None) -> str:
    """Buat laporan bergaya Modul 8 untuk bagian hitung, rekap, atau ringkasan."""
    isi = [ds.CSS, '<div class="wrap">', _kpi(h)]
    if bagian in ("hitung", "ringkasan"):
        isi.append(_dasar(h))
    if bagian in ("hitung", "ringkasan"):
        isi.extend([_tabel_alami(h), _tabel_exhaust(h)])
    if bagian in ("rekap", "ringkasan"):
        isi.append(_rekap(h, banding or []))
    if bagian in ("rekap", "ringkasan"):
        isi.append(_saran(h))
    if bagian == "ringkasan":
        if proyek:
            isi.append(ds.sec(8, "Identitas Proyek"))
            isi.append(ds.kop(proyek))
        isi.append(_kesimpulan(h))
    isi.append("</div>")
    return "".join(isi)


def tinggi(h: dict, bagian: str) -> int:
    baris = len(h["baris"])
    saran = len(h["perbaikan"])
    if bagian == "hitung":
        return max(900, 560 + 90 * baris + 75 * len(h["exhaust"]))
    if bagian == "rekap":
        return max(850, 480 + 165 * saran + 50 * len(h["kelompok"]))
    return max(1500, 1100 + 110 * baris + 180 * saran + 60 * len(h["exhaust"]))
