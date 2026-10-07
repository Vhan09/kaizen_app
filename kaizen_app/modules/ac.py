"""Modul 3 - Kebutuhan AC.

Dua metode perhitungan:
  - Standar Calculation : rumus pendekatan dari sheet 'AC STANDART'
  - Full Calculation    : rumus dasar + beban orang, lampu, dan peralatan

Dipanggil dari app.py:  "Modul 3 ❄️ Kebutuhan AC": ac.render
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from modules import ac_calc, ac_excel, ac_html
from modules.ac_calc import MODE_FULL, MODE_STANDAR

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.cache_data(show_spinner="Membuat PDF...")
def _buat_pdf(hasil_standar, hasil_full, data: dict, proyek: dict, orang_dasar: float, faktor_lampu: float):
    from modules import ekspor_pdf
    return ekspor_pdf.ac_pdf(hasil_standar, hasil_full, data, proyek, orang_dasar, faktor_lampu)


def _landasan(data: dict) -> None:
    """Landasan perencanaan: ringkas di atas, rincian di expander."""
    kode = [s["kode"] for s in data["standar"]]
    st.markdown("**Landasan Perencanaan / SNI:** " + " · ".join(kode))
    with st.expander("Rincian SNI & standar HVAC yang menjadi acuan"):
        tabel = pd.DataFrame(data["standar"]).rename(
            columns={"kode": "Standar", "judul": "Judul / Ruang Lingkup", "peran": "Peran pada Modul Ini"})
        st.dataframe(tabel, hide_index=True, width="stretch")
        st.caption(data.get("catatan_standar", ""))


def _rumus(mode: str, data: dict, od: float, fl: float) -> None:
    p = data["konversi"]["pembagi"]
    if mode == MODE_STANDAR:
        st.latex(rf"Q\ (\text{{Btu/h}}) = \frac{{L \times W \times H \times I \times E}}{{{p}}}")
        st.latex(r"N_{AC} = \frac{Q}{\text{kapasitas AC terpilih (Btu/h)}}")
        st.caption("L, W, H dalam feet (1 m = 3,28 ft). I = faktor isolasi, E = faktor orientasi matahari.")
        return
    w2b = str(data["konversi"]["watt_ke_btu"]).replace(".", "{,}")
    st.latex(r"Q_{total} = Q_{dasar} + Q_{orang} + Q_{lampu} + Q_{peralatan}")
    st.latex(rf"Q_{{dasar}} = \frac{{L \times W \times H \times I \times E}}{{{p}}}")
    st.latex(rf"Q_{{orang}} = \max(0,\ n_{{orang}} - {od:g}) \times W_{{orang}} \times {w2b}")
    st.latex(rf"Q_{{lampu}} = n_{{lampu}} \times W_{{lampu}} \times {fl:g} \times {w2b}")
    st.latex(rf"Q_{{peralatan}} = W_{{peralatan}} \times {w2b}")
    st.latex(r"N_{AC} = \frac{Q_{total}}{\text{kapasitas AC terpilih (Btu/h)}}")
    st.caption("1 Watt = 3,412 Btu/h. W per orang mengikuti aktivitas (ASHRAE/ISO, 26 °C). "
               "Orang dasar dianggap sudah termasuk pada rumus dasar.")


def render():
    data = ac_calc.muat_data()

    st.title("❄️ Kebutuhan AC")
    st.caption("Estimasi kebutuhan pendinginan per ruangan. Pilih metode perhitungan di bawah; "
               "rumus yang dipakai ditampilkan agar bisa dicocokkan dengan Excel.")
    _landasan(data)

    # ---- pilih metode
    mode = st.radio("Metode perhitungan", [MODE_STANDAR, MODE_FULL], horizontal=True, key="ac_mode")
    if mode == MODE_STANDAR:
        st.info("**Standar Calculation** — rumus pendekatan dari file Excel (sheet AC STANDART): "
                "berdasarkan volume ruangan, isolasi, dan orientasi. Tidak memperhitungkan jumlah orang, "
                "lampu, dan peralatan.")
    else:
        st.info("**Full Calculation** — rumus dasar yang sama **ditambah** beban orang, lampu, dan peralatan "
                "elektronik di dalam ruangan. Belum mencakup beban selubung rinci (CLTD) dan udara segar.")

    # ---- asumsi Full
    fp = data["full"]
    od, fl = float(fp["orang_dasar"]), float(fp["faktor_lampu"])
    if mode == MODE_FULL:
        with st.expander("Asumsi Full Calculation"):
            c1, c2 = st.columns(2)
            od = c1.number_input("Orang yang sudah termasuk di rumus dasar", min_value=0.0, step=1.0,
                                 value=od, key="ac_od",
                                 help="Asumsi praktik umum (±2 orang). Isi 0 bila semua penghuni ingin dihitung terpisah.")
            fl = c2.number_input("Faktor lampu", min_value=0.5, step=0.05, value=fl, key="ac_fl",
                                 help="1,0 untuk LED. Untuk lampu TL dengan ballast biasanya sekitar 1,2.")
    else:
        od = float(st.session_state.get("ac_od", od))
        fl = float(st.session_state.get("ac_fl", fl))

    with st.expander("Rumus yang digunakan", expanded=True):
        _rumus(mode, data, od, fl)

    # ---- data proyek
    with st.expander("Data proyek (kop laporan)"):
        p = data["proyek"]
        c1, c2, c3 = st.columns(3)
        proyek = {
            "pekerjaan": c1.text_input("Pekerjaan", p["pekerjaan"], key="ac_pekerjaan"),
            "lokasi": c2.text_input("Lokasi", p["lokasi"], key="ac_lokasi"),
            "tahun": c3.text_input("Tahun", p["tahun"], key="ac_tahun"),
            "item": p["item"],
        }

    # ---- input ruangan (satu tabel untuk kedua metode)
    st.markdown("#### Data Ruangan")
    st.caption("Satu baris = satu ruangan. Kolom bertanda **(Full)** hanya dipakai pada Full Calculation. "
               "Nilai orang, lampu, dan peralatan pada contoh adalah ilustrasi — ganti dengan data sebenarnya.")
    input_df = st.data_editor(
        ac_calc.template_default(data),
        key="ac_inputs",
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "Lantai": st.column_config.TextColumn("Lantai", help="Contoh: Lantai 1"),
            "Nama Ruangan": st.column_config.TextColumn("Nama Ruangan"),
            "L (m)": st.column_config.NumberColumn("L (m)", min_value=0.0, step=0.05, format="%.2f"),
            "W (m)": st.column_config.NumberColumn("W (m)", min_value=0.0, step=0.05, format="%.2f"),
            "H (m)": st.column_config.NumberColumn("H (m)", min_value=0.0, step=0.05, format="%.2f"),
            "Isolasi (I)": st.column_config.SelectboxColumn(
                "Isolasi (I)", options=ac_calc.opsi_isolasi(data),
                help="Faktor isolasi posisi ruangan (10 / 14 / 18)."),
            "Orientasi (E)": st.column_config.SelectboxColumn(
                "Orientasi (E)", options=ac_calc.opsi_orientasi(data),
                help="Faktor orientasi matahari (Utara 16 … Barat 20)."),
            ac_calc.K_ORANG: st.column_config.NumberColumn(
                "Jumlah Orang (Full)", min_value=0, step=1, format="%d",
                help="Jumlah penghuni yang berada di ruangan bersamaan."),
            ac_calc.K_AKT: st.column_config.SelectboxColumn(
                "Aktivitas (Full)", options=ac_calc.opsi_aktivitas(data),
                help="Menentukan panas tubuh per orang (W)."),
            ac_calc.K_LAMPU_N: st.column_config.NumberColumn(
                "Jml Lampu (Full)", min_value=0, step=1, format="%d"),
            ac_calc.K_LAMPU_W: st.column_config.NumberColumn(
                "Watt/Lampu (Full)", min_value=0.0, step=1.0, format="%.0f"),
            ac_calc.K_ALAT: st.column_config.NumberColumn(
                "Peralatan W (Full)", min_value=0.0, step=10.0, format="%.0f",
                help="Total daya peralatan elektronik yang menyala bersamaan (TV, laptop, dll)."),
            "Jenis AC": st.column_config.SelectboxColumn(
                "Jenis AC", options=ac_calc.opsi_ac(data), help="Kapasitas AC yang dipilih."),
            "Jumlah AC": st.column_config.NumberColumn("Jumlah AC", min_value=0, step=1, format="%d"),
        },
    )

    hs = ac_calc.hitung(input_df, data, MODE_STANDAR, od, fl)
    hf = ac_calc.hitung(input_df, data, MODE_FULL, od, fl)
    if hs.empty:
        st.info("Isi minimal satu ruangan lengkap (nama, L, W, H, isolasi, orientasi, jenis AC).")
        return
    hasil = hf if mode == MODE_FULL else hs

    # ---- ringkasan
    m1, m2, m3 = st.columns(3)
    m1.metric("Jumlah Ruangan", f"{len(hasil)}")
    m2.metric(f"Total Kebutuhan Pendinginan ({'Full' if mode == MODE_FULL else 'Standar'})",
              f"{ac_calc.fmt_id(hasil['Btu'].sum(), 0)} Btu/h")
    m3.metric("Total Unit AC", f"{int(hasil['Jumlah'].sum())}")

    for _, r in hasil[hasil["Status"] == "Kurang"].iterrows():
        st.warning(f"{r['Ruangan']}: N (AC) = {ac_calc.fmt_id(r['N'], 3)} per {r['Jumlah']} unit "
                   f"{r['Jenis AC']} — kapasitas kurang. Rekomendasi: {r['Rekomendasi']}.")
    for _, r in hasil[hasil["Status"] == "Batas"].iterrows():
        st.info(f"{r['Ruangan']}: N (AC) = {ac_calc.fmt_id(r['N'], 3)} — sedikit di atas 1, "
                f"masih dalam toleransi. Rekomendasi bila ingin lebih aman: {r['Rekomendasi']}.")

    # ---- lembar perhitungan
    st.markdown(f"### Lembar Perhitungan Kapasitas AC — {mode}")
    st.iframe(ac_html.render_html(hasil, data, proyek, mode, od, fl),
              height=ac_html.tinggi_html(hasil, mode))

    # ---- rincian substitusi
    with st.expander("Rincian perhitungan per ruangan (substitusi rumus)"):
        pilih = st.selectbox("Ruangan", list(hasil["Ruangan"]), key="ac_pilih_ruang")
        baris = hasil[hasil["Ruangan"] == pilih].iloc[0]
        st.code(ac_calc.rincian_teks(baris, data, mode, od, fl), language=None)

    # ---- perbandingan
    st.markdown("#### Perbandingan Standar vs Full")
    bandingan = ac_calc.perbandingan(hs, hf)
    st.dataframe(
        bandingan, hide_index=True, width="stretch",
        column_config={
            "Standar (Btu/h)": st.column_config.NumberColumn(format="%.0f"),
            "Full (Btu/h)": st.column_config.NumberColumn(format="%.0f"),
            "Selisih (Btu/h)": st.column_config.NumberColumn(format="%+.0f"),
            "Selisih (%)": st.column_config.NumberColumn(format="%+.1f%%"),
        },
    )
    st.caption("Full ≥ Standar selama ada beban orang di atas orang dasar, lampu, atau peralatan. "
               "Rekomendasi = PK terkecil yang kapasitasnya mencukupi kebutuhan.")

    # ---- rekap untuk modul SLD
    st.markdown("#### Rekap Jenis AC (acuan untuk Modul Beban Listrik / SLD)")
    rekap = ac_calc.rekap_ac(hasil, data)
    st.dataframe(rekap[rekap["Unit"] > 0], hide_index=True, width="stretch")
    st.caption("Jenis dan jumlah AC mengikuti pilihan di tabel input. Daya/unit diambil dari kolom AC pada sheet SLD "
               "(1/2 PK = 390 W, 3/4 PK = 620 W, 1 PK = 750 W); ubah di data/ac.json bila perlu.")

    # ---- unduh (Excel berisi kedua sheet: AC STANDART & AC FULL)
    xlsx = ac_excel.build_excel(hs, hf, data, proyek, od, fl)
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("Unduh Excel (.xlsx)", xlsx, "Kebutuhan_AC.xlsx",
                       mime=XLSX_MIME, on_click="ignore")
    if d2.button("Siapkan PDF"):
        try:
            pdf = _buat_pdf(hs, hf, data, proyek, od, fl)
            d2.download_button("Unduh PDF", pdf, "Kebutuhan_AC.pdf",
                               mime="application/pdf", on_click="ignore")
        except Exception as err:
            d2.error(f"Gagal membuat PDF: {err}")
    st.caption("File Excel berisi dua sheet: AC STANDART dan AC FULL. PDF merangkum kedua metode.")

    # ---- keterangan
    with st.expander("Keterangan faktor dan referensi"):
        st.markdown(
            "- **E** (orientasi): " + ", ".join(f"{k} {v}" for k, v in data["orientasi"].items()) + "\n"
            "- **I** (isolasi): " + ", ".join(f"{v} = {k.lower()}" for k, v in data["isolasi"].items()) + "\n"
            f"- 1 meter = {data['konversi']['meter_ke_feet']} feet\n"
            "- **N (AC)** = Btu/h ruangan ÷ kapasitas AC terpilih; status *Cukup* bila N ÷ jumlah AC ≤ 1\n"
            "- Kapasitas: " + ", ".join(f"{a['label']} = {a['btu']:,} Btu/h" for a in data["ac"]) + "\n"
            "- W per orang: " + ", ".join(f"{a['label']} = {a['total']} W" for a in fp["aktivitas"])
        )
        st.caption(f"{fp['sumber_aktivitas']} · " + " · ".join(data.get("referensi", [])))
