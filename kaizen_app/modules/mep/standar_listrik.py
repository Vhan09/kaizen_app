"""Opsi + nilai standar untuk Data Sistem (grounding & proteksi kebocoran).

Tanpa Streamlit. Nilai default bisa diubah di sini.
Catatan: batas resistansi 5 Ohm mengikuti praktik umum rumah tinggal (PUIL) dan
sheet Excel asli. Cek pasal PUIL 2020 yang berlaku saat dipakai untuk dokumen PBG.
"""
from __future__ import annotations

import re

BSN_PUIL_URL = "https://pesta.bsn.go.id/produk/index?key=Puil"
BSN_41_2025_URL = "https://pesta.bsn.go.id/produk/detail/02254412025-sni0225-4-41:2025"
BSN_9_2020_URL = "https://pesta.bsn.go.id/produk/detail/12953-sni0225-92020"
AKLI_URL = "https://akli.org/index.php"
NEC_URL = "https://www.nfpa.org/codes-and-standards/nfpa-70-standard-development/70"

LANDASAN_SLD = [
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-2:2020",
		"judul": "PUIL 2020 Bagian 2: Desain instalasi listrik",
		"status": "Berlaku (katalog BSN)",
		"relevansi": "Acuan utama desain instalasi dan single-line diagram; karakteristik suplai, beban, sirkit, dan perlindungan.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-3:2020",
		"judul": "PUIL 2020 Bagian 3: Asesmen karakteristik umum",
		"status": "Berlaku (katalog BSN)",
		"relevansi": "Asesmen karakteristik suplai dan instalasi yang menjadi masukan rancangan.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-4-41:2025",
		"judul": "PUIL 2020 Bagian 4-41: Proteksi keselamatan terhadap kejut listrik",
		"status": "Berlaku; edisi 2025",
		"relevansi": "Pemilihan tindakan proteksi terhadap kejut listrik, termasuk rancangan sirkit dan proteksi arus sisa.",
		"url": BSN_41_2025_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-4-41:2020",
		"judul": "PUIL 2020 Bagian 4-41: Proteksi terhadap kejut listrik (IEC 60364-4-41:2017, MOD)",
		"status": "Berlaku (katalog BSN; edisi terdahulu juga tercantum)",
		"relevansi": "Edisi 2020 untuk rujukan dokumen lama; konfirmasikan edisi yang diminta proyek karena edisi 2025 juga tercatat berlaku.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-4-42:2020",
		"judul": "PUIL 2020 Bagian 4-42: Proteksi terhadap efek termal",
		"status": "Berlaku (katalog BSN)",
		"relevansi": "Proteksi instalasi dari bahaya termal dan risiko kebakaran akibat listrik.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-4-43:2020",
		"judul": "PUIL 2020 Bagian 4-43: Proteksi terhadap arus lebih (IEC 60364-4-43:2008, MOD)",
		"status": "Berlaku (katalog BSN)",
		"relevansi": "Acuan koordinasi beban, penghantar, dan pemutus/proteksi arus lebih.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-4-44:2020",
		"judul": "PUIL 2020 Bagian 4-44: Proteksi terhadap gangguan voltase dan elektromagnetik",
		"status": "Berlaku (katalog BSN)",
		"relevansi": "Pertimbangan gangguan voltase, termasuk koordinasi proteksi tegangan lebih.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-5-51:2020",
		"judul": "PUIL 2020 Bagian 5-51: Pemilihan dan pemasangan peralatan listrik – Aturan bersama",
		"status": "Berlaku (katalog BSN)",
		"relevansi": "Pemilihan peralatan listrik sesuai pengaruh eksternal dan kondisi penggunaan.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-5-52:2020",
		"judul": "PUIL 2020 Bagian 5-52: Pemilihan dan pemasangan sistem perkawatan",
		"status": "Berlaku (katalog BSN)",
		"relevansi": "Pemilihan jenis/ukuran kabel dan cara pemasangan; lengkapi desain dengan metode instalasi dan faktor koreksi yang sesuai.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-5-525:2025",
		"judul": "PUIL 2020 Bagian 5-525: Batas jatuh tegangan pada instalasi konsumen",
		"status": "Berlaku; edisi 2025",
		"relevansi": "Pemeriksaan jatuh tegangan sirkit; relevan untuk panjang dan ukuran kabel pada SLD.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-5-54:2020",
		"judul": "PUIL 2020 Bagian 5-54: Susunan pembumian dan konduktor proteksi",
		"status": "Berlaku (katalog BSN)",
		"relevansi": "Acuan susunan grounding, konduktor proteksi (PE), dan ikatan proteksi.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-6:2020",
		"judul": "PUIL 2020 Bagian 6: Verifikasi",
		"status": "Berlaku (katalog BSN)",
		"relevansi": "Verifikasi dan pengujian instalasi setelah pemasangan; menjadi bagian pemeriksaan rancangan dan serah terima.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "SNI PUIL",
		"kode": "SNI 0225-9:2020",
		"judul": "PUIL 2020 Bagian 9: Pengusahaan instalasi listrik",
		"status": "Berlaku (katalog BSN)",
		"relevansi": "Ketentuan pengusahaan instalasi listrik; bukan tabel kapasitas MCB/kabel.",
		"url": BSN_9_2020_URL,
	},
]

LANDASAN_PELENGKAP_SLD = [
	{
		"kategori": "Rujukan pelengkap",
		"kode": "PUIL 2011 dan amendemen yang tercantum di katalog BSN",
		"judul": "Edisi terdahulu Persyaratan Umum Instalasi Listrik",
		"status": "Sebagian amendemen masih tercantum Berlaku di katalog BSN",
		"relevansi": "Untuk menelusuri dokumen lama atau ketika edisi ini disebut eksplisit dalam persyaratan proyek. Jangan gabungkan persyaratan berbeda tanpa kajian.",
		"url": BSN_PUIL_URL,
	},
	{
		"kategori": "Rujukan pelengkap",
		"kode": "Tabel AKLI pada aplikasi Kaizen PBG",
		"judul": "Acuan praktis VA/daya tersedia, MCB/MCCB, dan rekomendasi kabel",
		"status": "Referensi asosiasi/aplikasi; bukan SNI",
		"relevansi": "Dipakai aplikasi untuk rekomendasi awal MCB dan kabel. Verifikasi kemampuan hantar arus, cara pemasangan, faktor koreksi, proteksi, dan produk terhadap PUIL serta data pabrikan.",
		"url": AKLI_URL,
	},
	{
		"kategori": "Rujukan pelengkap",
		"kode": "NFPA 70 (NEC)",
		"judul": "National Electrical Code – kode instalasi listrik Amerika Serikat",
		"status": "Pembanding internasional; bukan SNI dan tidak otomatis menjadi persyaratan di Indonesia",
		"relevansi": "Gunakan hanya jika spesifikasi kontrak/yurisdiksi proyek secara eksplisit meminta NEC; untuk dokumen PBG Indonesia utamakan SNI/PUIL dan peraturan Indonesia.",
		"url": NEC_URL,
	},
]

CATATAN_LANDASAN_SLD = (
	"Status katalog dicek 8 Oktober 2026 pada katalog BSN. Status ‘Berlaku’ pada katalog tidak dengan sendirinya "
	"menetapkan edisi kontraktual proyek; pastikan edisi yang diwajibkan instansi PBG/pemilik. PUIL mengadopsi "
	"sejumlah bagian IEC 60364 dengan modifikasi (MOD). Tabel AKLI di aplikasi adalah alat bantu, bukan pengganti "
	"perhitungan desain sesuai PUIL, data pabrikan, dan verifikasi instalasi."
)

# sistem grounding -> nilai standar yang terisi otomatis + keterangan singkat
GROUNDING = {
	"TN-S": {
		"res": "< 5 Ohm",
		"ket": "Penghantar netral (N) dan pembumian (PE) terpisah di seluruh instalasi.",
	},
	"TN-C-S": {
		"res": "< 5 Ohm",
		"ket": "N dan PE menyatu (PEN) di sisi sumber, terpisah di dalam instalasi.",
	},
	"TT": {
		"res": "< 5 Ohm",
		"ket": "Pembumian instalasi terpisah dari pembumian sumber; proteksi memakai RCD.",
	},
	"TN-S/TT": {
		"res": "< 5 Ohm",
		"ket": "Mengikuti sheet Excel asli (TN-S atau TT).",
	},
}
GROUNDING_DEFAULT = "TN-S/TT"

RES_OPSI = ["< 1 Ohm", "< 3 Ohm", "< 5 Ohm", "< 10 Ohm"]

PROTEKSI_TIPE = ["ELCB", "RCCB"]
PROTEKSI_MA = [10, 30, 100, 300]
PROTEKSI_TIPE_DEFAULT = "ELCB"
PROTEKSI_MA_DEFAULT = 30
PROTEKSI_KET = {
	10: "Sensitivitas sangat tinggi (area basah / khusus).",
	30: "Standar perlindungan manusia pada rumah tinggal.",
	100: "Perlindungan peralatan / kebakaran, kurang aman untuk manusia.",
	300: "Perlindungan kebakaran / proteksi utama, bukan untuk manusia.",
}


def res_default(grounding: str) -> str:
	return GROUNDING.get(grounding, GROUNDING[GROUNDING_DEFAULT])["res"]


def teks_proteksi(tipe: str, ma: int) -> str:
	return f"{tipe} {int(ma)} mA"


def parse_proteksi(teks: str | None) -> tuple[str, int]:
	"""'ELCB 30 mA' -> ('ELCB', 30). Jika tidak cocok, kembalikan default."""
	m = re.match(r"\s*(ELCB|RCCB)\s*(\d+)\s*mA", teks or "", re.I)
	if m and m.group(1).upper() in PROTEKSI_TIPE and int(m.group(2)) in PROTEKSI_MA:
		return m.group(1).upper(), int(m.group(2))
	return PROTEKSI_TIPE_DEFAULT, PROTEKSI_MA_DEFAULT
