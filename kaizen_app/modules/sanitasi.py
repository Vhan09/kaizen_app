"""Sanitasi & Air Bersih - empat tab: Air Bersih, Air Limbah, Air Kotor, Summary.

Setiap tab hanya menampilkan SNI/peraturan yang berkaitan; tab Summary menampilkan semuanya.
Dipanggil dari app.py:  "Modul N 🚿 Sanitasi & Air Bersih": sanitasi.render
(Resapan dikerjakan di modul tersendiri.)
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules import sanitasi_calc as sc
from modules import sanitasi_excel, sanitasi_html

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.cache_data(show_spinner="Membuat PDF...")
def _buat_pdf(xlsx_bytes: bytes):
    return sanitasi_excel.excel_ke_pdf(xlsx_bytes)


def _landasan(data: dict, kunci: str | None = None) -> None:
    """Daftar SNI/peraturan. kunci=None -> semua (Summary); selain itu hanya yang berkaitan dengan tab."""
    daftar = [s for s in data["standar"] if kunci is None or kunci in s["tab"]]
    st.markdown("**Landasan Perencanaan / SNI:** " + " · ".join(s["kode"] for s in daftar))
    with st.expander(f"Rincian SNI & peraturan ({len(daftar)})", expanded=kunci is None):
        tabel = pd.DataFrame(daftar)[["kode", "judul", "peran", "catatan"]]
        tabel.columns = ["Standar / Peraturan", "Judul", "Peran pada Modul Ini", "Catatan"]
        st.dataframe(tabel, hide_index=True, width="stretch")
        st.caption(data.get("catatan_standar", ""))


def _html(h, data, proyek, hanya=None, kop=False):
    components.html(sanitasi_html.render_html(h, data, proyek, hanya, kop),
                    height=sanitasi_html.tinggi_html(h, data, hanya, kop), scrolling=True)


def render():
    data = sc.muat_data()
    P0 = sc.parameter_default(data)
    sd = data["septik"]
    P = dict(P0)

    st.subheader("Sanitasi & Air Bersih")
    st.caption("Pilih tab: Air Bersih (kebutuhan air dan tandon), Air Limbah (grey water), Air Kotor "
               "(black water dan tangki septik), lalu Summary untuk rekap dan unduhan. "
               "Rumus ditampilkan agar bisa dicocokkan dengan Excel.")
    t_bersih, t_limbah, t_kotor, t_sum = st.tabs(["💧 Air Bersih", "🛁 Air Limbah", "🚽 Air Kotor", "📋 Summary"])

    # ============================================================ input (semua tab)
    with t_bersih:
        _landasan(data, "air_bersih")
        st.markdown("#### Kebutuhan Air Bersih")
        st.caption("Pilih fungsi bangunan; standar pemakaian air mengikuti SNI 03-7065-2005 Tabel 1. "
                   "Bangunan campuran (misal rumah + toko) bisa diisi lebih dari satu baris.")
        input_df = st.data_editor(
            sc.template_default(), key="san_penggunaan", num_rows="dynamic", width="stretch", hide_index=True,
            column_config={
                "Fungsi": st.column_config.SelectboxColumn("Fungsi Bangunan", options=sc.opsi_fungsi(data)),
                "Jumlah": st.column_config.NumberColumn(
                    "Jumlah (sesuai satuan standar)", min_value=0.0, step=1.0,
                    help="Contoh: jumlah penghuni, tempat tidur, siswa, kursi, atau m²."),
                "Keterangan": st.column_config.TextColumn("Keterangan"),
            },
        )
        a1, a2 = st.columns(2)
        P["faktor_puncak"] = a1.number_input("Faktor puncak (peak time)", 0.0, 2.0, float(P0["faktor_puncak"]),
                                             step=0.05, key="san_fp", help="Excel kamu memakai 30% (0,30).")
        P["pembulatan"] = a2.number_input("Pembulatan volume tandon ke atas, kelipatan (m³)", 0.01, 5.0,
                                          float(P0["pembulatan"]), step=0.05, key="san_bulat")

    with t_limbah:
        _landasan(data, "air_limbah")
        st.markdown("#### Air Limbah (Grey Water)")
        st.caption("Debit air limbah dihitung dari kebutuhan air pada tab Air Bersih, lalu dibagi menjadi "
                   "grey water (kamar mandi, cuci, dapur) dan black water (kakus).")
        b1, b2, b3 = st.columns(3)
        P["dasar"] = b1.selectbox("Dasar debit air limbah", [sc.DASAR_PUNCAK, sc.DASAR_RATA], key="san_dasar")
        P["faktor_limbah"] = b2.number_input("Faktor air limbah (% dari debit dasar)", 0.1, 1.0,
                                             float(P0["faktor_limbah"]), step=0.05, key="san_fl",
                                             help="Excel: 100%. Acuan umum yang sering dipakai: 80%.")
        P["fraksi_black"] = b3.number_input("Fraksi black water (kakus)", 0.0, 1.0, float(P0["fraksi_black"]),
                                            step=0.05, key="san_fb", help="Excel: 20%.")

    with t_kotor:
        _landasan(data, "air_kotor")
        st.markdown("#### Air Kotor (Black Water) dan Tangki Septik")
        P["n_auto"] = st.checkbox("Jumlah pemakai diambil dari tabel Air Bersih (baris yang satuannya orang)",
                                  True, key="san_nauto")
        if not P["n_auto"]:
            P["n"] = st.number_input("Jumlah pemakai (orang)", 1, 10000, int(P0["n"]), step=1, key="san_n")
        s1, s2, s3 = st.columns(3)
        P["td"] = s1.number_input("Waktu detensi (hari)", 0.5, 10.0, float(P0["td"]), step=0.5, key="san_td",
                                  help=f"Rentang SNI: {sd['detensi_min']}–{sd['detensi_max']} hari.")
        P["ql"] = s2.number_input("Produksi lumpur (L/orang/tahun)", 1.0, 100.0, float(P0["ql"]), step=1.0,
                                  key="san_ql", help=f"Rentang SNI: {sd['lumpur_min']}–{sd['lumpur_max']}.")
        P["pp"] = s3.number_input("Periode pengurasan (tahun)", 1.0, 10.0, float(P0["pp"]), step=1.0,
                                  key="san_pp", help=f"Rentang SNI: {sd['pengurasan_min']}–{sd['pengurasan_max']} tahun.")
        s4, s5, s6 = st.columns(3)
        P["ambang"] = s4.number_input("Ambang bebas (m)", 0.0, 1.0, float(P0["ambang"]), step=0.05, key="san_amb")
        P["h_air"] = s5.number_input("Kedalaman air efektif (m)", 0.5, 4.0, float(P0["h_air"]), step=0.1, key="san_h")
        P["rasio"] = s6.number_input("Rasio panjang : lebar", 1.0, 5.0, float(P0["rasio"]), step=0.5, key="san_rasio")

    with t_sum:
        _landasan(data, None)
        with st.expander("Data proyek (kop laporan)"):
            p = data["proyek"]
            c1, c2, c3 = st.columns(3)
            proyek = {
                "pekerjaan": c1.text_input("Pekerjaan", p["pekerjaan"], key="san_pekerjaan"),
                "lokasi": c2.text_input("Lokasi", p["lokasi"], key="san_lokasi"),
                "tahun": c3.text_input("Tahun", p["tahun"], key="san_tahun"),
                "item": p["item"],
            }

    # ============================================================ hitung
    h = sc.hitung_semua(input_df, data, P)
    if h["rinc"].empty:
        for t in (t_bersih, t_limbah, t_kotor, t_sum):
            with t:
                st.info("Isi minimal satu baris fungsi bangunan dengan jumlah lebih dari 0 pada tab Air Bersih.")
        return
    f = sc.fmt_id

    # ============================================================ hasil per tab
    with t_bersih:
        m1, m2, m3 = st.columns(3)
        m1.metric("Kebutuhan Air Harian", f"{f(h['q_harian'], 0)} L/hari")
        m2.metric("Q Rencana (+ faktor puncak)", f"{f(h['q_rencana'], 0)} L/hari")
        m3.metric("Volume Tandon Rencana", f"{f(h['vol_rencana'], 2)} m³")
        _html(h, data, None, ["air_bersih"])
        with st.expander("Rumus yang digunakan", expanded=True):
            st.latex(r"Q_{harian} = \sum \left(\text{jumlah} \times \text{standar pemakaian air}\right)")
            st.latex(rf"Q_{{rencana}} = Q_{{harian}} \times (1 + {P['faktor_puncak']:g})")
            st.latex(r"V_{tandon} = \lceil Q_{rencana} / 1000 \rceil \ \text{(dibulatkan ke atas, kelipatan pembulatan)}")

    with t_limbah:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Air Limbah", f"{f(h['limbah_total'], 1)} L/hari")
        m2.metric("Grey Water", f"{f(h['grey'], 1)} L/hari")
        m3.metric("Black Water", f"{f(h['black'], 1)} L/hari")
        _html(h, data, None, ["air_limbah"])
        with st.expander("Rumus yang digunakan", expanded=True):
            st.latex(r"Q_{limbah} = Q_{dasar} \times f_{limbah}")
            st.latex(r"Q_{black} = Q_{limbah} \times f_{black}; \qquad Q_{grey} = Q_{limbah} - Q_{black}")

    with t_kotor:
        for w in h["peringatan"]:
            st.warning(w)
        m1, m2, m3 = st.columns(3)
        m1.metric("Black Water", f"{f(h['black'], 1)} L/hari")
        m2.metric("Tangki Septik Tercampur", f"{f(h['tc']['v_total'], 2)} m³")
        m3.metric("Tangki Septik Terpisah", f"{f(h['tp']['v_total'], 2)} m³")
        st.info(f"Pembanding contoh SNI untuk black water: {data['air_limbah']['black_water_l_org_hari']} L/orang/hari × "
                f"{h['n']:g} orang = {f(h['cek_black_sni'], 1)} L/hari (hitungan di atas: {f(h['black'], 1)} L/hari).")
        _html(h, data, None, ["air_kotor"])
        st.caption("Dimensi tangki adalah estimasi dari volume. Ukuran minimum, jumlah ruang, dan detail konstruksi "
                   "tetap mengikuti SNI 2398:2017.")
        with st.expander("Rumus yang digunakan", expanded=True):
            st.latex(r"V_{air} = \frac{Q_{limbah} \times t_d}{1000}; \qquad V_{lumpur} = \frac{QL \times n \times PP}{1000}")
            st.latex(r"A = \frac{V_{air} + V_{lumpur}}{h_{air}}; \qquad V_{tangki} = V_{air} + V_{lumpur} + (A \times h_{ambang})")
            st.caption("td = waktu detensi (hari), QL = produksi lumpur (L/orang/tahun), PP = periode pengurasan (tahun), "
                       "n = jumlah pemakai. Tercampur: grey + black water; terpisah: black water saja.")

    with t_sum:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Air Bersih Harian", f"{f(h['q_harian'], 0)} L/hari")
        m2.metric("Volume Tandon", f"{f(h['vol_rencana'], 2)} m³")
        m3.metric("Total Air Limbah", f"{f(h['limbah_total'], 0)} L/hari")
        m4.metric("Tangki Septik", f"{f(h['tc']['v_total'], 2)} m³")
        for w in h["peringatan"]:
            st.warning(w)
        st.markdown("### Lembar Perhitungan Sanitasi dan Air Bersih")
        _html(h, data, proyek, None, True)

        xlsx = sanitasi_excel.build_excel(h, data, proyek)
        d1, d2, _ = st.columns([1, 1, 3])
        d1.download_button("Unduh Excel (.xlsx)", xlsx, "Sanitasi_Air.xlsx", mime=XLSX_MIME, on_click="ignore")
        if d2.button("Siapkan PDF"):
            pdf = _buat_pdf(xlsx)
            if pdf:
                d2.download_button("Unduh PDF", pdf, "Sanitasi_Air.pdf", mime="application/pdf", on_click="ignore")
            else:
                d2.warning("PDF butuh LibreOffice terpasang di komputer ini.")
        st.caption("File Excel berisi rumus hidup, tabel pemakaian air SNI, dan daftar SNI/peraturan (3 sheet).")

        with st.expander("Tabel pemakaian air (SNI 03-7065-2005 Tabel 1)"):
            tabel = pd.DataFrame(data["pemakaian_air"])[["fungsi", "nilai", "satuan"]]
            tabel.columns = ["Penggunaan gedung", "Pemakaian air", "Satuan"]
            st.dataframe(tabel, hide_index=True, width="stretch")
            st.caption(f"{data['sumber_tabel']}. {data['catatan_tabel']}")
