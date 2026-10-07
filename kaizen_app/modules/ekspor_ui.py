"""Tombol unduh Excel & PDF (Streamlit).

Pembuat file dipanggil lewat fungsi kecil agar library (xlsxwriter, reportlab)
baru dimuat saat dibutuhkan. Jika library belum terpasang atau pembuatan gagal,
halaman tetap jalan dan hanya menampilkan peringatan.
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME_PDF = "application/pdf"


def _buat(fn):
    """Jalankan pembuat file. Return (bytes, None) atau (None, pesan)."""
    try:
        return fn(), None
    except ImportError as err:
        return None, (f"Library untuk unduh belum terpasang ({err}). "
                      "Jalankan: pip install -r requirements.txt, lalu jalankan ulang aplikasi.")
    except Exception as err:  # ekspor tidak boleh merusak halaman
        return None, f"Gagal membuat file: {err}"


def _tombol(nama_dasar: str, buat_xlsx, buat_pdf, key: str) -> None:
    stempel = datetime.now().strftime("%Y%m%d")
    c1, c2 = st.columns(2)
    for kolom, label, fn, ext, mime in (
        (c1, "⬇️ Unduh Excel (.xlsx)", buat_xlsx, "xlsx", MIME_XLSX),
        (c2, "⬇️ Unduh PDF", buat_pdf, "pdf", MIME_PDF),
    ):
        data, pesan = _buat(fn)
        if data is None:
            kolom.warning(pesan)
        else:
            kolom.download_button(
                label, data=data, file_name=f"{nama_dasar}_{stempel}.{ext}",
                mime=mime, key=f"{key}_{ext}",
            )


def ekspor_sld(proyek, sistem, labels, out, induk, catatan, tabel_akli) -> None:
    def xlsx():
        from modules import ekspor_xlsx
        return ekspor_xlsx.sld_xlsx(proyek, sistem, labels, out, induk, catatan, tabel_akli)

    def pdf():
        from modules import ekspor_pdf
        return ekspor_pdf.sld_pdf(proyek, sistem, labels, out, induk, catatan)

    _tombol("SLD_Beban_Listrik", xlsx, pdf, "dl_sld")
    st.caption(
        "Excel berisi sheet SLD dan AKLI dengan rumus hidup: ubah sel kuning, "
        "Load, total, VA, Ampere, dan saran kabel induk menghitung ulang. "
        "MCB UP dan Cable berupa nilai hasil aplikasi."
    )


def ekspor_akli(tabel) -> None:
    def xlsx():
        from modules import ekspor_xlsx
        return ekspor_xlsx.akli_xlsx(tabel)

    def pdf():
        from modules import ekspor_pdf
        return ekspor_pdf.akli_pdf(tabel)

    _tombol("Tabel_AKLI", xlsx, pdf, "dl_akli")