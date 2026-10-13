
"""Core calculations and validation for ARS-01: Luas & Intensitas Bangunan."""

from typing import Any


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def validate_inputs(inputs: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Does not decide legal compliance."""
    errors: list[str] = []
    warnings: list[str] = []

    land = _as_float(inputs.get("land_area_m2"), -1)
    footprint = _as_float(inputs.get("footprint_area_m2"), -1)
    green = _as_float(inputs.get("green_area_m2"), -1)
    floors = inputs.get("floor_areas_m2", [])
    manual_total = inputs.get("total_floor_area_manual_m2")

    if land <= 0:
        errors.append("Luas lahan harus lebih besar dari 0 m².")
    if footprint < 0:
        errors.append("Luas tapak bangunan tidak boleh negatif.")
    if green < 0:
        errors.append("Luas area hijau tidak boleh negatif.")
    if land > 0 and footprint > land:
        errors.append("Luas tapak bangunan tidak boleh melebihi luas lahan.")
    if land > 0 and green > land:
        errors.append("Luas area hijau tidak boleh melebihi luas lahan.")
    if land > 0 and footprint + green > land + 1e-9:
        warnings.append("Luas tapak + area hijau melebihi luas lahan. Periksa kemungkinan tumpang tindih atau input area.")
    if not isinstance(floors, list) or not floors:
        errors.append("Masukkan minimal satu nilai luas lantai.")
    else:
        for i, area in enumerate(floors, start=1):
            if _as_float(area, -1) < 0:
                errors.append(f"Luas lantai tingkat {i} tidak boleh negatif.")
    if manual_total is not None and _as_float(manual_total, -1) < 0:
        errors.append("Luas total lantai manual tidak boleh negatif.")

    limits = inputs.get("limits", {})
    for key in ("max_kdb_percent", "max_klb", "min_kdh_percent"):
        if key not in limits:
            errors.append(f"Batas {key} belum diisi.")
    if _as_float(limits.get("max_kdb_percent"), -1) < 0 or _as_float(limits.get("max_kdb_percent"), -1) > 100:
        errors.append("Batas maksimum KDB harus berada pada rentang 0–100%.")
    if _as_float(limits.get("min_kdh_percent"), -1) < 0 or _as_float(limits.get("min_kdh_percent"), -1) > 100:
        errors.append("Batas minimum KDH harus berada pada rentang 0–100%.")
    if _as_float(limits.get("max_klb"), -1) < 0:
        errors.append("Batas maksimum KLB tidak boleh negatif.")

    if manual_total is not None and floors:
        if abs(_as_float(manual_total) - sum(_as_float(x) for x in floors)) > 0.01:
            warnings.append("Luas total manual berbeda dari jumlah luas per tingkat. Hasil memakai luas total manual.")
    return errors, warnings


def calculate_ars01(inputs: dict) -> dict:
    """Calculate KDB, KLB, KDH and input-limit checks.

    KDB (%) = footprint / land area * 100
    KLB (-) = total counted floor area / land area
    KDH (%) = qualifying green area / land area * 100

    Local rules may define included/excluded floor areas and qualifying green areas
    differently. Those definitions must be checked against the project regulations.
    """
    errors, _warnings = validate_inputs(inputs)
    if errors:
        raise ValueError("Input tidak valid: " + " ".join(errors))

    land = float(inputs["land_area_m2"])
    footprint = float(inputs["footprint_area_m2"])
    green = float(inputs["green_area_m2"])
    floor_areas = [float(x) for x in inputs["floor_areas_m2"]]
    manual_total = inputs.get("total_floor_area_manual_m2")
    total_floor = float(manual_total) if manual_total is not None else sum(floor_areas)
    limits = inputs["limits"]

    kdb = footprint / land * 100.0
    klb = total_floor / land
    kdh = green / land * 100.0
    max_kdb = float(limits["max_kdb_percent"])
    max_klb = float(limits["max_klb"])
    min_kdh = float(limits["min_kdh_percent"])

    return {
        "land_area_m2": round(land, 3),
        "footprint_area_m2": round(footprint, 3),
        "total_floor_area_m2": round(total_floor, 3),
        "green_area_m2": round(green, 3),
        "remaining_land_m2": round(land - footprint, 3),
        "kdb_percent": round(kdb, 4),
        "klb": round(klb, 4),
        "kdh_percent": round(kdh, 4),
        "formulas": {
            "KDB_percent": "luas_tapak_bangunan / luas_lahan * 100",
            "KLB": "total_luas_lantai_yang_dihitung / luas_lahan",
            "KDH_percent": "luas_area_hijau_yang_memenuhi_definisi / luas_lahan * 100"
        },
        "limits_used": {
            "max_kdb_percent": max_kdb,
            "max_klb": max_klb,
            "min_kdh_percent": min_kdh
        },
        "checks": {
            "kdb_pass": kdb <= max_kdb + 1e-9,
            "klb_pass": klb <= max_klb + 1e-9,
            "kdh_pass": kdh >= min_kdh - 1e-9
        }
    }
