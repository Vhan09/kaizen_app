"""Opsi + nilai standar untuk Data Sistem (grounding & proteksi kebocoran).

Tanpa Streamlit. Nilai default bisa diubah di sini.
Catatan: batas resistansi 5 Ohm mengikuti praktik umum rumah tinggal (PUIL) dan
sheet Excel asli. Cek pasal PUIL 2020 yang berlaku saat dipakai untuk dokumen PBG.
"""
from __future__ import annotations

import re

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
