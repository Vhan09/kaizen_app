"""Streamlit interface for the ARS-01 building-area calculation."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from modules.arsitektur import luas_bangunan as calc
from modules.arsitektur import luas_bangunan_excel, luas_bangunan_pdf
from utils import storage
from utils.formatting import fmt_id

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "arsitektur" / "arsitektur.json"
_STORAGE_KEY = "luas_bangunan_arsitektur"
_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _load_data() -> dict:
    try:
        return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Gagal membaca konfigurasi Arsitektur di {_DATA_PATH}: {exc}") from exc


def _load_saved() -> dict:
    saved = storage.load(_STORAGE_KEY, {}, domain="arsitektur")
    if not isinstance(saved, dict):
        return {}
    return saved


def _floor_areas(frame: pd.DataFrame) -> list[float]:
    if frame.empty:
        return []
    values = pd.to_numeric(frame["Luas lantai (m²)"], errors="coerce")
    return [-1.0 if pd.isna(value) else float(value) for value in values]


def render(
    *,
    embedded: bool = False,
    land_area_m2: float | None = None,
    regulation_limits: dict[str, float | None] | None = None,
    project_name: str = "",
    project_location: str = "",
) -> None:
    data = _load_data()
    saved = _load_saved()
    limits_default = data.get("example_limits", {})
    project_default = saved.get("project", {})

    if not embedded:
        st.title("Luas & Intensitas Bangunan")
    st.caption(
        "Perhitungan luas lahan, luas tapak, luas lantai, KDB, KLB, dan KDH. "
        "Gunakan batas yang telah diverifikasi untuk lokasi dan jenis bangunan."
    )
    st.warning(
        "Nilai batas bawaan hanya contoh antarmuka, bukan standar universal atau "
        "pernyataan kepatuhan regulasi."
    )

    with st.expander("Data proyek (kop laporan)", expanded=True):
        c1, c2, c3 = st.columns(3)
        project = {
            "pekerjaan": c1.text_input(
                "Pekerjaan",
                project_default.get("pekerjaan", project_name),
                key="ars_luas_pekerjaan",
            ),
            "lokasi": c2.text_input(
                "Lokasi",
                project_default.get("lokasi", project_location),
                key="ars_luas_lokasi",
            ),
            "tahun": c3.text_input(
                "Tahun", project_default.get("tahun", ""), key="ars_luas_tahun"
            ),
        }

    st.markdown("### Data lahan dan bangunan")
    left, right = st.columns(2)
    with left:
        land_area = st.number_input(
            "Luas lahan (m²)",
            min_value=0.0,
            value=float(saved.get("land_area_m2", land_area_m2 or 0.0)),
            step=1.0,
            key="ars_luas_lahan",
        )
        footprint_area = st.number_input(
            "Luas tapak bangunan (m²)",
            min_value=0.0,
            value=float(saved.get("footprint_area_m2", 0.0)),
            step=1.0,
            key="ars_luas_tapak",
            help="Luas proyeksi tapak bangunan yang digunakan untuk menghitung KDB.",
        )
    with right:
        green_area = st.number_input(
            "Luas area hijau untuk KDH (m²)",
            min_value=0.0,
            value=float(saved.get("green_area_m2", 0.0)),
            step=1.0,
            key="ars_luas_hijau",
            help="Gunakan definisi area yang memenuhi KDH menurut ketentuan lokasi.",
        )
        manual_enabled = st.checkbox(
            "Gunakan total luas lantai manual",
            value=saved.get("total_floor_area_manual_m2") is not None,
            key="ars_luas_total_manual_enabled",
            help="Aktifkan jika total perhitungan luas lantai perlu dikoreksi menurut definisi setempat.",
        )
        if manual_enabled:
            manual_total = st.number_input(
                "Total luas lantai manual (m²)",
                min_value=0.0,
                value=float(saved.get("total_floor_area_manual_m2") or 0.0),
                step=1.0,
                key="ars_luas_total_manual",
            )
        else:
            manual_total = None

    stored_floor_areas = saved.get("floor_areas_m2", data.get("default_floor_areas_m2", []))
    if not isinstance(stored_floor_areas, list) or not stored_floor_areas:
        stored_floor_areas = [0.0]
    floor_frame = pd.DataFrame(
        {"Luas lantai (m²)": [float(value) for value in stored_floor_areas]}
    )
    floor_frame.index = [f"Tingkat {index}" for index in range(1, len(floor_frame) + 1)]
    floor_editor = st.data_editor(
        floor_frame,
        key="ars_luas_lantai_editor",
        num_rows="dynamic",
        hide_index=False,
        width="stretch",
        column_config={
            "Luas lantai (m²)": st.column_config.NumberColumn(
                "Luas lantai (m²)", min_value=0.0, step=1.0, format="%.2f"
            )
        },
    )
    floor_areas = _floor_areas(floor_editor)

    st.markdown("### Batas untuk pemeriksaan")
    st.caption(
        "Silakan ubah sesuai ketentuan tata ruang yang telah diverifikasi. "
        "Perbandingan hasil hanya terhadap nilai yang Anda masukkan."
    )
    b1, b2, b3 = st.columns(3)
    saved_limits = saved.get("limits", {})
    regulation_limits = regulation_limits or {}
    limits = {
        "max_kdb_percent": b1.number_input(
            "Batas maksimum KDB (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(saved_limits.get(
                "max_kdb_percent",
                regulation_limits.get("max_kdb_percent")
                if regulation_limits.get("max_kdb_percent") is not None
                else limits_default.get("max_kdb_percent", 60.0),
            )),
            step=1.0,
            key="ars_luas_batas_kdb",
        ),
        "max_klb": b2.number_input(
            "Batas maksimum KLB",
            min_value=0.0,
            value=float(saved_limits.get(
                "max_klb",
                regulation_limits.get("max_klb")
                if regulation_limits.get("max_klb") is not None
                else limits_default.get("max_klb", 1.2),
            )),
            step=0.1,
            key="ars_luas_batas_klb",
        ),
        "min_kdh_percent": b3.number_input(
            "Batas minimum KDH (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(saved_limits.get(
                "min_kdh_percent",
                regulation_limits.get("min_kdh_percent")
                if regulation_limits.get("min_kdh_percent") is not None
                else limits_default.get("min_kdh_percent", 10.0),
            )),
            step=1.0,
            key="ars_luas_batas_kdh",
        ),
    }

    inputs = {
        "land_area_m2": land_area,
        "footprint_area_m2": footprint_area,
        "green_area_m2": green_area,
        "floor_areas_m2": floor_areas,
        "total_floor_area_manual_m2": manual_total,
        "limits": limits,
    }
    payload = {"project": project, **inputs}
    if not storage.save(_STORAGE_KEY, payload, domain="arsitektur"):
        st.error("Data Arsitektur gagal disimpan. Periksa izin tulis pada folder data/arsitektur/.")
    else:
        st.caption("Data input tersimpan otomatis di folder data/arsitektur/.")

    errors, warnings = calc.validate_inputs(inputs)
    for warning in warnings:
        st.warning(warning)
    if errors:
        for error in errors:
            st.error(error)
        st.info("Lengkapi input yang valid untuk menampilkan hasil dan menyiapkan laporan.")
        return

    result = calc.calculate_ars01(inputs)
    st.markdown("### Hasil perhitungan")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("KDB", f"{fmt_id(result['kdb_percent'], 2)}%")
    m2.metric("KLB", fmt_id(result["klb"], 4))
    m3.metric("KDH", f"{fmt_id(result['kdh_percent'], 2)}%")
    m4.metric(
        "Luas lantai dihitung",
        f"{fmt_id(result['total_floor_area_m2'], 2)} m²",
    )

    check_labels = [
        ("KDB", result["checks"]["kdb_pass"], "batas maksimum"),
        ("KLB", result["checks"]["klb_pass"], "batas maksimum"),
        ("KDH", result["checks"]["kdh_pass"], "batas minimum"),
    ]
    check_columns = st.columns(3)
    for column, (label, passed, comparison) in zip(check_columns, check_labels):
        if passed:
            column.success(f"{label}: memenuhi {comparison} yang diinput")
        else:
            column.warning(f"{label}: melewati {comparison} yang diinput")

    with st.expander("Rumus yang digunakan", expanded=True):
        st.latex(r"\mathrm{KDB} = \frac{\text{luas tapak bangunan}}{\text{luas lahan}} \times 100\%")
        st.latex(r"\mathrm{KLB} = \frac{\text{total luas lantai yang dihitung}}{\text{luas lahan}}")
        st.latex(r"\mathrm{KDH} = \frac{\text{area hijau yang memenuhi definisi}}{\text{luas lahan}} \times 100\%")

    st.markdown("### Laporan")
    xlsx = luas_bangunan_excel.build_excel(inputs, result, project, data.get("notes", []))
    pdf = luas_bangunan_pdf.build_pdf(inputs, result, project, data.get("notes", []))
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button(
        "Unduh Excel (.xlsx)",
        xlsx,
        "Luas_Intensitas_Bangunan.xlsx",
        mime=_XLSX_MIME,
        on_click="ignore",
    )
    d2.download_button(
        "Unduh PDF",
        pdf,
        "Luas_Intensitas_Bangunan.pdf",
        mime="application/pdf",
        on_click="ignore",
    )

    with st.expander("Catatan dan batasan perhitungan"):
        for note in data.get("notes", []):
            st.markdown(f"- {note}")
        st.caption(
            "Definisi luas, batas KDB/KLB/KDH, dan ketentuan yang berlaku perlu "
            "dikonfirmasi untuk lokasi proyek. Hasil ini bukan penetapan kepatuhan hukum."
        )
