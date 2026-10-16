"""Data and implementation for the Pre-Design residential planning module."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

DATA_DIR: Path = Path(
    os.environ.get("PREDESIGN_DATA_DIR")
    or Path(__file__).resolve().parents[2] / "data" / "arsitektur"
)
_FILES = (
    "sni_registry", "form_schema", "room_standards", "finishing_classes", "financial_params",
    "regulation_defaults", "site_rules", "structure_params", "building_physics",
    "utilities_params", "ottv_solar_factor",
)


def set_data_dir(path: str | os.PathLike) -> None:
    """Set the directory containing Predesign.json and clear the dataset cache."""
    global DATA_DIR
    DATA_DIR = Path(path)
    load.cache_clear()


@lru_cache(maxsize=None)
def load(name: str) -> dict[str, Any]:
    """Load one named dataset from the combined JSON file; do not mutate results."""
    if name not in _FILES:
        raise KeyError(f"Dataset tidak dikenal: {name!r}. Pilihan: {', '.join(_FILES)}")
    path = DATA_DIR / "Predesign.json"
    if not path.is_file():
        raise FileNotFoundError(f"{path} tidak ditemukan. Salin Predesign.json atau panggil set_data_dir().")
    with path.open("r", encoding="utf-8") as stream:
        datasets = json.load(stream)
    try:
        return datasets[name]
    except KeyError as exc:
        raise KeyError(f"Dataset {name!r} tidak ditemukan di {path}.") from exc


def room_catalog() -> dict[str, dict[str, Any]]:
    """Return a dictionary mapping room IDs to room definitions."""
    return {room["id"]: room for room in load("room_standards")["rooms"]}


def sni_lookup(doc_id: str) -> dict[str, Any]:
    for document in load("sni_registry")["documents"]:
        if document["id"] == doc_id:
            return document
    raise KeyError(doc_id)


def cite(*doc_ids: str) -> str:
    """Format document identifiers as short references."""
    out = []
    for doc_id in doc_ids:
        try:
            out.append(sni_lookup(doc_id)["number"])
        except KeyError:
            out.append(doc_id)
    return "; ".join(out)


"""Model data pre-design. Memetakan bagian slide ke dataset form_schema di Predesign.json."""

import dataclasses
import json
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from typing import Any, Optional


COMPASS8 = ("U", "TL", "T", "TG", "S", "BD", "B", "BL")
FINISHING = ("standar", "menengah", "atas")
PRIORITIES = ("Wajib", "Tinggi", "Sedang")


class _Serializable:
    """Mixin to_dict / from_dict yang mengabaikan kunci tak dikenal (toleran versi)."""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)  # type: ignore[arg-type]

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        names = {f.name for f in fields(cls)}  # type: ignore[arg-type]
        return cls(**{k: v for k, v in (data or {}).items() if k in names})


# ---------------------------------------------------------------- 1.1
@dataclass
class BuyerPersona(_Serializable):
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    household_size: Optional[int] = None
    children: Optional[int] = None
    household_type: Optional[str] = None
    occupations: list[str] = field(default_factory=list)
    monthly_income_idr: Optional[float] = None
    lifestyle_tags: list[str] = field(default_factory=list)
    aesthetic: Optional[str] = None
    price_sensitivity: Optional[str] = None
    cars: Optional[int] = None
    motorcycles: Optional[int] = None


# ---------------------------------------------------------------- 1.2
@dataclass
class ProductParameters(_Serializable):
    target_price_idr: Optional[float] = None
    target_price_min_idr: Optional[float] = None
    target_price_max_idr: Optional[float] = None
    max_construction_cost_per_m2_idr: Optional[float] = None  # KRITIS
    land_area_m2: Optional[float] = None
    target_gfa_m2: Optional[float] = None
    num_types: Optional[int] = None                           # KRITIS
    finishing_class: Optional[str] = None                     # KRITIS
    lot_width_m: Optional[float] = None
    lot_depth_m: Optional[float] = None

    def price_range(self) -> tuple[Optional[float], Optional[float]]:
        if self.target_price_min_idr and self.target_price_max_idr:
            return self.target_price_min_idr, self.target_price_max_idr
        return self.target_price_idr, self.target_price_idr


# ---------------------------------------------------------------- 1.3
@dataclass
class RoomProgramItem(_Serializable):
    room_id: str
    name: str = ""
    priority: str = "Sedang"
    approved: Optional[bool] = None      # True=centang, False=coret, None=belum diputuskan
    qty: int = 1
    area_m2: Optional[float] = None      # override luas per unit; None -> pakai rekomendasi kelas finishing
    question: str = ""
    answer: str = ""                     # jawaban atas 'note' slide
    note: str = ""


# ---------------------------------------------------------------- 2.1
@dataclass
class RegulationParams(_Serializable):
    kdb_pct: Optional[float] = None
    klb: Optional[float] = None
    gsb_front_m: Optional[float] = None
    gsj_from_axis_m: Optional[float] = None
    max_floors: Optional[int] = None
    max_height_m: Optional[float] = None
    kdh_pct: Optional[float] = None
    gsb_side_left_m: Optional[float] = None
    gsb_side_right_m: Optional[float] = None
    gsb_rear_m: Optional[float] = None
    source: str = ""
    confirmed: dict[str, bool] = field(default_factory=dict)  # kunci: kdb, klb, gsb, gsj, ktg, kdh


# ---------------------------------------------------------------- 2.2
@dataclass
class SiteConditions(_Serializable):
    front_orientation: Optional[str] = None
    topography: Optional[str] = None
    level_difference_m: Optional[float] = None
    best_view: str = ""
    best_view_direction: Optional[str] = None
    noise_sources: list[str] = field(default_factory=list)
    soil_condition: Optional[str] = None
    fill_thickness_m: Optional[float] = None
    fill_age_months: Optional[int] = None
    soil_tested: Optional[bool] = None
    vehicle_access_from: Optional[str] = None
    pln_entry_from: Optional[str] = None
    non_negotiables: list[str] = field(default_factory=list)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ottv_city: Optional[str] = None
    front_boundary_from_axis_m: Optional[float] = None  # jarak batas kavling depan ke as jalan (untuk cek GSJ)


@dataclass
class DecisionRecord(_Serializable):
    section_id: str
    decided: bool = False
    decision_text: str = ""
    decided_by: str = ""
    decided_at: str = ""


# ---------------------------------------------------------------- Project
@dataclass
class PreDesignProject:
    name: str = "Proyek Baru"
    location: str = ""
    session_date: str = field(default_factory=lambda: date.today().isoformat())
    persona: BuyerPersona = field(default_factory=BuyerPersona)
    product: ProductParameters = field(default_factory=ProductParameters)
    program: list[RoomProgramItem] = field(default_factory=list)
    regulation: RegulationParams = field(default_factory=RegulationParams)
    site: SiteConditions = field(default_factory=SiteConditions)
    decisions: list[DecisionRecord] = field(default_factory=list)
    schema_version: str = "0.1.0"

    # ---- program default dari template slide 1.3
    def init_default_program(self) -> None:
        self.program = [
            RoomProgramItem(
                room_id=r["id"], name=r["name"], priority=r["priority"], qty=r.get("default_qty", 1),
                question=r["question"], approved=None,
            )
            for r in load("room_standards")["rooms"]
        ]

    def room(self, room_id: str) -> Optional[RoomProgramItem]:
        return next((r for r in self.program if r.room_id == room_id), None)

    def decision(self, section_id: str) -> DecisionRecord:
        rec = next((d for d in self.decisions if d.section_id == section_id), None)
        if rec is None:
            rec = DecisionRecord(section_id=section_id)
            self.decisions.append(rec)
        return rec

    def record_decision(self, section_id: str, text: str, by: str = "") -> DecisionRecord:
        rec = self.decision(section_id)
        rec.decided, rec.decision_text, rec.decided_by = True, text, by
        rec.decided_at = datetime.now().isoformat(timespec="seconds")
        return rec

    # ---- kelengkapan form
    def _section_model(self, model_name: str):
        return {"BuyerPersona": self.persona, "ProductParameters": self.product,
                "RegulationParams": self.regulation, "SiteConditions": self.site}.get(model_name)

    @staticmethod
    def _filled(v: Any) -> bool:
        return not (v is None or v == "" or v == [] or v == {})

    def completeness(self) -> dict[str, dict[str, Any]]:
        """Persentase kelengkapan per seksi + daftar field kosong (khusus WAJIB & KRITIS)."""
        out: dict[str, dict[str, Any]] = {}
        for agenda in load("form_schema")["agendas"]:
            for sec in agenda["sections"]:
                obj = self._section_model(sec["model"])
                missing: list[str] = []
                req_total = 0
                for f in sec["fields"]:
                    if f["level"] not in ("WAJIB", "KRITIS"):
                        continue
                    if f["type"] == "room_list":
                        req_total += 1
                        if not self.program or any(r.approved is None for r in self.program if r.priority == "Wajib"):
                            missing.append("program ruang (ruang Wajib belum dikonfirmasi)")
                        continue
                    req_total += 1
                    if obj is None or not self._filled(getattr(obj, f["key"], None)):
                        missing.append(f["key"])
                done = req_total - len(missing)
                out[sec["id"]] = {
                    "title": sec["title"], "required": req_total, "filled": done,
                    "pct": round(100 * done / req_total, 1) if req_total else 100.0,
                    "missing": missing, "decided": self.decision(sec["id"]).decided if any(
                        d.section_id == sec["id"] for d in self.decisions) else False,
                }
        return out

    def critical_missing(self) -> list[str]:
        """Field KRITIS (oranye di slide 1.2) yang masih kosong."""
        crit = [f["key"] for a in load("form_schema")["agendas"] for s in a["sections"]
                for f in s["fields"] if f["level"] == "KRITIS"]
        return [k for k in crit if not self._filled(getattr(self.product, k, None))]

    # ---- serialisasi
    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PreDesignProject":
        return cls(
            name=d.get("name", "Proyek Baru"), location=d.get("location", ""),
            session_date=d.get("session_date", date.today().isoformat()),
            persona=BuyerPersona.from_dict(d.get("persona", {})),
            product=ProductParameters.from_dict(d.get("product", {})),
            program=[RoomProgramItem.from_dict(x) for x in d.get("program", [])],
            regulation=RegulationParams.from_dict(d.get("regulation", {})),
            site=SiteConditions.from_dict(d.get("site", {})),
            decisions=[DecisionRecord.from_dict(x) for x in d.get("decisions", [])],
            schema_version=d.get("schema_version", "0.1.0"),
        )

    @classmethod
    def from_json(cls, s: str) -> "PreDesignProject":
        return cls.from_dict(json.loads(s))

    @classmethod
    def load_file(cls, path: str) -> "PreDesignProject":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_json(fh.read())

    def save_file(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())


def validate_catalog_ids() -> None:
    """Sanity: id ruang unik (dipanggil oleh tes)."""
    ids = [r["id"] for r in load("room_standards")["rooms"]]
    assert len(ids) == len(set(ids)), "id ruang duplikat"
    assert set(room_catalog()) == set(ids)


"""Utilitas tapak: kompas 8 arah, rotasi muka bangunan, arah kiblat, aturan tanah (timbunan), kemiringan."""

import math
from typing import Optional


_COMPASS_ORDER = ["U", "TL", "T", "TG", "S", "BD", "B", "BL"]


def azimuth(code: str) -> int:
    return load("ottv_solar_factor")["_meta"]["azimuth_deg"][code]


def code_from_azimuth(az: float) -> str:
    idx = int(round((az % 360) / 45.0)) % 8
    return _COMPASS_ORDER[idx]


def facade_orientations(front: str) -> dict[str, str]:
    """Orientasi 4 muka dari arah hadap depan: depan, belakang, kanan (dilihat dari luar menghadap rumah), kiri."""
    a = azimuth(front)
    return {"depan": front, "kanan": code_from_azimuth(a + 90), "belakang": code_from_azimuth(a + 180),
            "kiri": code_from_azimuth(a - 90)}


def qibla_azimuth(lat_deg: float, lon_deg: float) -> float:
    """Azimuth awal great-circle ke Ka'bah (derajat dari Utara sejati, searah jarum jam)."""
    k = load("site_rules")["qibla"]
    phi1, phi2 = math.radians(lat_deg), math.radians(k["kaaba_lat"])
    dl = math.radians(k["kaaba_lon"] - lon_deg)
    y = math.sin(dl) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def terrain_class(level_diff_m: float) -> str:
    r = load("site_rules")["slope_rules"]
    if level_diff_m <= r["datar_max_diff_m"]:
        return "datar"
    if level_diff_m <= r["landai_max_diff_m"]:
        return "landai"
    return "miring"


def soil_rule(soil_condition: Optional[str]) -> dict:
    return load("site_rules")["soil_rules"].get(soil_condition or "tidak_diketahui",
                                                load("site_rules")["soil_rules"]["tidak_diketahui"])


def view_is_water(view_text: str) -> bool:
    kws = load("site_rules")["view_rules"]["water_body"]["keywords"]
    t = (view_text or "").lower()
    return any(k in t for k in kws)


def angular_difference(a: float, b: float) -> float:
    d = abs((a - b) % 360)
    return min(d, 360 - d)


"""Iklim & selubung: U-value, OTTV (SNI 6389:2020), posisi matahari, overhang, rekomendasi zoning.

Rumus:
    U = 1 / (Rsi + Σ(d_i/λ_i) + Rse)                                  [W/m2.K]
    OTTV_i = α·Uw·(1-WWR)·TDEk + Uf·WWR·ΔT + SC·WWR·SF               [W/m2]   (SNI 6389)
    OTTV   = Σ(A_i·OTTV_i) / Σ A_i      (A_i = luas dinding kotor muka-i)
    SC     = SCk x SCeff
    δ      = 23,45°·sin(360/365·(284+n))
    sin h  = sinφ·sinδ + cosφ·cosδ·cosω ,  ω = 15°·(jam surya - 12)
    VSA    = atan(tan h / cos γ)       γ = selisih azimuth matahari-normal muka
    bayangan overhang (tinggi) = P·tan(VSA) ;  tersinari fraksi = 1 - clamp((P·tanVSA - d)/H, 0, 1)
"""

import math
from dataclasses import dataclass, asdict
from typing import Iterable, Optional


ORIENT = ("U", "TL", "T", "TG", "S", "BD", "B", "BL")


# ------------------------------------------------------------------ U-value
def u_value(layers: Iterable[tuple[str, float]], *, rsi: Optional[float] = None, rse: Optional[float] = None) -> float:
    bp = load("building_physics")
    rsi = bp["surface_films_m2k_w"]["Rsi_wall"] if rsi is None else rsi
    rse = bp["surface_films_m2k_w"]["Rse_wall"] if rse is None else rse
    r = rsi + rse
    for mat, d in layers:
        m = bp["materials"][mat]
        r += m["r_equiv_m2k_w"] if "r_equiv_m2k_w" in m else d / m["lambda_w_mk"]
    return 1.0 / r


def wall_u(preset: str) -> float:
    return u_value([tuple(x) for x in load("building_physics")["wall_presets"][preset]["layers"]])


def tdek_indicative(mass_kg_m2: float) -> float:
    t = load("building_physics")["tdek_k_indicative"]
    if mass_kg_m2 < 125:
        return t["ringan_lt_125_kg_m2"]
    if mass_kg_m2 <= 250:
        return t["sedang_125_to_250_kg_m2"]
    return t["berat_gt_250_kg_m2"]


# ------------------------------------------------------------------ OTTV
def solar_factor(city: str, orientation: str) -> float:
    cities = load("ottv_solar_factor")["cities"]
    if city not in cities:
        raise KeyError(f"Kota {city!r} tidak ada di tabel SF; pakai kota terdekat: {', '.join(sorted(cities))}")
    return float(cities[city][orientation])


def ottv_facade(*, wwr: float, uw: float, tdek: float, alpha: float, uf: float, sc: float, sf: float,
                delta_t: Optional[float] = None) -> dict:
    dt = load("building_physics")["delta_t_k"] if delta_t is None else delta_t
    wall = alpha * uw * (1 - wwr) * tdek
    cond_glass = uf * wwr * dt
    solar = sc * wwr * sf
    return {"ottv_w_m2": round(wall + cond_glass + solar, 2), "wall_w_m2": round(wall, 2),
            "glass_conduction_w_m2": round(cond_glass, 2), "glass_solar_w_m2": round(solar, 2)}


@dataclass
class FacadeInput:
    side: str                # depan/kanan/belakang/kiri
    orientation: str         # U..BL
    gross_wall_area_m2: float
    wwr: float
    sc_eff: float = 1.0      # faktor naungan (1 = tanpa naungan)


def ottv_building(facades: list[FacadeInput], *, city: str, wall_preset: str = "bata_ringan_10",
                  glazing: str = "clear_6mm", alpha_name: str = "krem_muda") -> dict:
    bp = load("building_physics")
    uw = wall_u(wall_preset)
    tdek = tdek_indicative(bp["wall_presets"][wall_preset]["mass_kg_m2"])
    alpha = bp["solar_absorptance_alpha"][alpha_name]
    g = bp["glazing"][glazing]
    rows, num, den = [], 0.0, 0.0
    for f in facades:
        sf = solar_factor(city, f.orientation)
        r = ottv_facade(wwr=f.wwr, uw=uw, tdek=tdek, alpha=alpha, uf=g["U_w_m2k"], sc=g["SC"] * f.sc_eff, sf=sf)
        rows.append({"side": f.side, "orientation": f.orientation, "wwr": f.wwr, "sf": sf, **r})
        num += f.gross_wall_area_m2 * r["ottv_w_m2"]
        den += f.gross_wall_area_m2
    total = num / den if den else 0.0
    lim = load("ottv_solar_factor")["_meta"]["ottv_limit_w_m2"]
    return {"city": city, "uw": round(uw, 3), "tdek_k": tdek, "alpha": alpha, "glazing": glazing, "facades": rows,
            "ottv_w_m2": round(total, 2), "limit_w_m2": lim, "pass_indicator": total <= lim,
            "note": "TDEk indikatif; batas 35 W/m2 bukan syarat wajib rumah tinggal."}


def orientation_ranking(city: str) -> list[tuple[str, float]]:
    """Orientasi diurutkan dari SF terendah (paling sejuk) ke tertinggi (paling panas)."""
    c = load("ottv_solar_factor")["cities"][city]
    return sorted(((o, float(c[o])) for o in ORIENT), key=lambda x: x[1])


# ------------------------------------------------------------------ Matahari
def declination_deg(day_of_year: int) -> float:
    return 23.45 * math.sin(math.radians(360.0 / 365.0 * (284 + day_of_year)))


def solar_position(lat_deg: float, day_of_year: int, solar_hour: float) -> tuple[float, float]:
    """(altitude°, azimuth° dari Utara searah jarum jam). Mengembalikan altitude<0 bila di bawah horizon."""
    phi = math.radians(lat_deg)
    dec = math.radians(declination_deg(day_of_year))
    w = math.radians(15.0 * (solar_hour - 12.0))
    sin_h = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(w)
    h = math.asin(max(-1.0, min(1.0, sin_h)))
    if math.cos(h) < 1e-9:
        return math.degrees(h), 180.0
    cos_az = (math.sin(dec) - sin_h * math.sin(phi)) / (math.cos(h) * math.cos(phi))
    az = math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))
    if w > 0:
        az = 360.0 - az
    return math.degrees(h), az


def overhang_shaded_fraction(*, lat_deg: float, day_of_year: int, solar_hour: float, facade_az_deg: float,
                             overhang_m: float, gap_above_window_m: float, window_h_m: float) -> Optional[float]:
    """Fraksi tinggi jendela yang terbayang overhang horizontal. None bila matahari tidak mengenai muka."""
    alt, az = solar_position(lat_deg, day_of_year, solar_hour)
    if alt <= 1.0:
        return None
    gamma = angular_difference(az, facade_az_deg)
    if gamma >= 90.0:
        return None
    vsa = math.atan(math.tan(math.radians(alt)) / math.cos(math.radians(gamma)))
    shadow = overhang_m * math.tan(vsa)
    return max(0.0, min(1.0, (shadow - gap_above_window_m) / window_h_m))


def overhang_effectiveness(*, lat_deg: float, facade_orientation: str, overhang_m: float,
                           gap_above_window_m: float = 0.2, window_h_m: float = 1.2,
                           days: Iterable[int] = (80, 172, 266, 356), hours: Iterable[float] = tuple(range(8, 17))) -> dict:
    """Rata-rata fraksi terbayang, terbobot intensitas langsung (cosγ·sin h) — menghasilkan SCeff = 1 - fraksi."""
    az_f = azimuth(facade_orientation)
    wsum = fsum = 0.0
    for d in days:
        for h in hours:
            alt, az = solar_position(lat_deg, d, h)
            if alt <= 1.0:
                continue
            gamma = angular_difference(az, az_f)
            if gamma >= 90.0:
                continue
            w = math.cos(math.radians(gamma)) * math.sin(math.radians(alt))
            fr = overhang_shaded_fraction(lat_deg=lat_deg, day_of_year=d, solar_hour=h, facade_az_deg=az_f,
                                          overhang_m=overhang_m, gap_above_window_m=gap_above_window_m, window_h_m=window_h_m)
            if fr is None:
                continue
            wsum += w
            fsum += w * fr
    shaded = fsum / wsum if wsum else 0.0
    return {"facade": facade_orientation, "overhang_m": overhang_m, "shaded_fraction": round(shaded, 3),
            "sc_eff": round(1 - shaded, 3), "sun_on_facade_weight": round(wsum, 3)}


# ------------------------------------------------------------------ Rekomendasi
def zoning_advice(front: str, city: Optional[str] = None, view_direction: Optional[str] = None) -> list[str]:
    notes = load("building_physics")["orientation_notes"]
    out = []
    fac = facade_orientations(front)
    ranking = dict(orientation_ranking(city)) if city else {}
    for side, o in fac.items():
        txt = f"Muka {side} menghadap {o}: {notes[o]['advice']}"
        if ranking:
            txt += f" (SF {city} = {ranking[o]:.0f} W/m²)"
        out.append(txt)
    hot = [o for o in ("B", "BL", "BD") if o in fac.values()]
    if hot:
        out.append("Taruh zona servis (dapur, KM, tangga, gudang, carport) pada muka sisi barat sebagai buffer; ruang tidur/ruang tinggal di sisi U/S/T.")
    if view_direction:
        vd = view_direction
        if vd in ("B", "BL", "BD"):
            out.append(f"View terbaik ke {vd} bertabrakan dengan beban matahari sore: bukaan view lebar perlu overhang dalam/ sirip vertikal/ kaca low-E dan vegetasi pelindung.")
    return out


"""Pencahayaan alami/buatan & ventilasi per ruang.

Rumus:
    Lubang cahaya  ≥ 1/10 x A_lantai          (Kepmen 403/KPTS/M/2002)
    Lubang udara   ≥ 5%   x A_lantai          (Kepmen 403/KPTS/M/2002)
    RI (room index)= (P x L) / (h_m x (P + L)) , h_m = tinggi bidang kerja ke armatur
    N lampu        = (E x A) / (Φ x UF x MF)  (metode lumen, SNI 03-6575-2001)
    Q udara segar  = 0,8 m3/menit/orang       (Kepmen 403)
    ACH            = Q x 60 / V
"""

import math
from typing import Optional



def opening_requirements(floor_area_m2: float) -> dict:
    o = load("room_standards")["openings"]
    return {"daylight_min_m2": round(floor_area_m2 * o["daylight_opening_min_ratio"], 3),
            "ventilation_min_m2": round(floor_area_m2 * o["ventilation_opening_min_ratio"], 3)}


def check_openings(floor_area_m2: float, glazed_area_m2: float, operable_area_m2: float) -> dict:
    req = opening_requirements(floor_area_m2)
    return {**req, "daylight_ok": glazed_area_m2 + 1e-9 >= req["daylight_min_m2"],
            "ventilation_ok": operable_area_m2 + 1e-9 >= req["ventilation_min_m2"]}


def room_index(length_m: float, width_m: float, mount_height_m: float = 1.8) -> float:
    return length_m * width_m / (mount_height_m * (length_m + width_m))


def utilization_factor(ri: float) -> float:
    pts = load("building_physics")["lighting"]["utilization_factor_by_room_index"]
    if ri <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if ri <= x1:
            return y0 + (y1 - y0) * (ri - x0) / (x1 - x0)
    return pts[-1][1]


def lumen_method(lux: float, area_m2: float, lumen_per_lamp: float, ri: float, mf: Optional[float] = None) -> dict:
    lt = load("building_physics")["lighting"]
    mf = lt["maintenance_factor"] if mf is None else mf
    uf = utilization_factor(ri)
    n_exact = lux * area_m2 / (lumen_per_lamp * uf * mf)
    n = max(1, math.ceil(n_exact - 1e-9))
    return {"uf": round(uf, 3), "mf": mf, "lamps_exact": round(n_exact, 2), "lamps": n,
            "lux_achieved": round(n * lumen_per_lamp * uf * mf / area_m2, 1)}


def room_lighting(room_id: str, area_m2: float, width_m: Optional[float] = None, lamp_lm: Optional[float] = None) -> dict:
    spec = room_catalog()[room_id]
    lux = max(spec["lux"])
    width = width_m or math.sqrt(area_m2 / 1.4)
    length = area_m2 / width
    lamp = lamp_lm or load("building_physics")["lighting"]["luminaires"]["led_9w_lm"]
    ri = room_index(length, width)
    out = lumen_method(lux, area_m2, lamp, ri)
    out.update({"room": spec["name"], "target_lux": lux, "ri": round(ri, 2),
                "est_watt": round(out["lamps"] * 9, 0), "lpd_w_m2": round(out["lamps"] * 9 / area_m2, 2)})
    return out


def ventilation_check(volume_m3: float, occupants: int, effective_ach: Optional[float] = None) -> dict:
    v = load("building_physics")["ventilation"]
    q_min = v["fresh_air_m3_min_per_person"] * occupants           # m3/menit
    ach_req = q_min * 60 / volume_m3
    out = {"required_flow_m3_min": round(q_min, 2), "required_ach": round(ach_req, 2),
           "volume_per_person_m3": round(volume_m3 / max(1, occupants), 2),
           "volume_per_person_ok": volume_m3 / max(1, occupants) >= v["air_volume_m3_per_person"]}
    if effective_ach is not None:
        out["ach_ok"] = effective_ach >= ach_req
    return out


def program_openings(project) -> list[dict]:
    """Tabel kebutuhan bukaan (m2) per ruang dari program disetujui (luas rekomendasi/override)."""
    res = compute_program(project)
    cat = room_catalog()
    rows = []
    for ln in res.lines:
        spec = cat.get(ln.room_id)
        if not spec or not spec.get("needs_daylight") and not spec.get("wet"):
            continue
        req = opening_requirements(ln.unit_area_m2)
        rows.append({"room": ln.name, "qty": ln.qty, "area_m2": ln.unit_area_m2, **req,
                     "needs_cross_vent": spec.get("needs_cross_vent", False)})
    return rows


"""Keuangan produk (slide 1.2): dari harga jual ke batas biaya konstruksi/m², dan keterjangkauan KPR.

A. Batas biaya konstruksi (residual / backward):
    P_net     = P / (1 + PPN)                     bila harga jual sudah termasuk PPN
    Rev       = P_net x (1 - komisi - biaya_jual - PPh_final)
    Biaya_maks= Rev x (1 - margin)
    Tanah_unit= (Harga_tanah_bruto/m2 / NTG) x Luas_kavling
    B_konstr  = Biaya_maks - Tanah_unit - Prasarana_unit - Perizinan - Overhead - Biaya_keuangan
    Konstr/m2 = B_konstr / (1 + kontingensi) / GFA
B. KPR (anuitas):
    Pokok = P x (1 - DP%)
    r     = bunga_tahunan/12 ; n = tenor x 12
    Angsuran = Pokok x r / (1 - (1 + r)^-n)       (r=0 → Pokok/n)
    Penghasilan_min = Angsuran / DSR
Semua tarif = default terverifikasi lemah (lihat dataset financial_params di Predesign.json).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional



# ------------------------------------------------------------------ A
@dataclass
class CostSolveInputs:
    price_idr: float
    gfa_m2: float
    land_area_m2: float
    land_price_gross_per_m2_idr: float
    ntg_ratio: Optional[float] = None
    infrastructure_per_unit_idr: float = 0.0
    permits_legal_per_unit_idr: float = 0.0
    overhead_pct_of_price: float = 4.0
    marketing_pct_of_price: float = 3.0
    finance_cost_pct_of_price: float = 2.0
    target_margin_pct: float = 12.0
    contingency_pct: Optional[float] = None
    price_includes_ppn: bool = True
    ppn_pct: Optional[float] = None
    pph_final_pct: Optional[float] = None


@dataclass
class CostSolveResult:
    price_net_idr: float
    revenue_idr: float
    max_total_cost_idr: float
    land_cost_idr: float
    infrastructure_idr: float
    permits_idr: float
    overhead_idr: float
    marketing_idr: float
    finance_idr: float
    construction_budget_idr: float
    construction_budget_after_contingency_idr: float
    max_construction_per_m2_idr: float
    land_share_of_price: float
    construction_share_of_price: float
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def solve_max_construction_cost(inp: CostSolveInputs) -> CostSolveResult:
    fp = load("financial_params")
    ppn = (fp["taxes"]["ppn_effective_pct"] if inp.ppn_pct is None else inp.ppn_pct) / 100.0
    pph = (fp["taxes"]["pph_final_seller_pct"] if inp.pph_final_pct is None else inp.pph_final_pct) / 100.0
    ntg = inp.ntg_ratio or fp["net_to_gross_land_ratio"]["default"]
    cont = (fp["contingency_default_pct"] if inp.contingency_pct is None else inp.contingency_pct) / 100.0
    if inp.gfa_m2 <= 0 or inp.price_idr <= 0:
        raise ValueError("price_idr dan gfa_m2 harus > 0")

    p_net = inp.price_idr / (1 + ppn) if inp.price_includes_ppn else inp.price_idr
    marketing = p_net * inp.marketing_pct_of_price / 100
    overhead = p_net * inp.overhead_pct_of_price / 100
    finance = p_net * inp.finance_cost_pct_of_price / 100
    pph_amt = p_net * pph
    revenue = p_net - marketing - pph_amt
    max_total = revenue * (1 - inp.target_margin_pct / 100)
    land = inp.land_price_gross_per_m2_idr / ntg * inp.land_area_m2
    budget = max_total - land - inp.infrastructure_per_unit_idr - inp.permits_legal_per_unit_idr - overhead - finance
    after_cont = budget / (1 + cont)
    per_m2 = after_cont / inp.gfa_m2
    warn = []
    if budget <= 0:
        warn.append("Anggaran konstruksi ≤ 0: harga jual tidak menutup tanah+prasarana+margin. Naikkan harga/turunkan biaya tanah.")
    land_share = land / inp.price_idr
    cons_share = after_cont / inp.price_idr
    chk = load("finishing_classes")["price_ratio_checks"]
    if land_share > chk["max_land_share_of_price"]:
        warn.append(f"Porsi tanah {land_share:.0%} > {chk['max_land_share_of_price']:.0%} harga jual (indikatif).")
    return CostSolveResult(round(p_net), round(revenue), round(max_total), round(land), inp.infrastructure_per_unit_idr,
                           inp.permits_legal_per_unit_idr, round(overhead), round(marketing), round(finance), round(budget),
                           round(after_cont), round(per_m2), round(land_share, 4), round(cons_share, 4), warn)


def classify_cost_per_m2(cost_per_m2: float) -> str:
    """Padankan biaya/m2 ke kelas finishing (indikatif, lihat dataset finishing_classes)."""
    cls = load("finishing_classes")["classes"]
    if cost_per_m2 < cls["standar"]["cost_per_m2_idr"]["low"]:
        return "di bawah standar"
    for k in ("standar", "menengah", "atas"):
        if cost_per_m2 <= cls[k]["cost_per_m2_idr"]["high"]:
            return k
    return "di atas kelas atas"


def construction_cost_estimate(gfa_m2: float, finishing: str, *, fill_soil: bool = False,
                               covered_outdoor_m2: float = 0.0, outdoor_factor: float = 0.5) -> dict:
    """Perkiraan biaya konstruksi dari benchmark kelas finishing (low/mid/high), termasuk kontingensi."""
    fc = load("finishing_classes")
    c = fc["classes"][finishing]["cost_per_m2_idr"]
    area_eq = gfa_m2 + covered_outdoor_m2 * outdoor_factor
    cont = fc["contingency_pct"][finishing] + (fc["contingency_pct"]["extra_if_fill_soil"] if fill_soil else 0)
    out = {"equivalent_area_m2": round(area_eq, 2), "contingency_pct": cont}
    for k in ("low", "mid", "high"):
        base = area_eq * c[k]
        out[k] = {"base_idr": round(base), "with_contingency_idr": round(base * (1 + cont / 100))}
    return out


def breakdown(total_idr: float) -> dict[str, tuple[float, float]]:
    """Alokasi tipikal biaya konstruksi per kelompok pekerjaan (rentang Rp) dari dataset finishing_classes."""
    b = load("finishing_classes")["cost_breakdown_typical_pct"]
    return {k: (round(total_idr * v[0] / 100), round(total_idr * v[1] / 100))
            for k, v in b.items() if isinstance(v, list)}


# ------------------------------------------------------------------ B
def annuity_payment(principal: float, annual_rate_pct: float, years: float) -> float:
    n = int(round(years * 12))
    if n <= 0:
        raise ValueError("tenor harus > 0")
    r = annual_rate_pct / 100.0 / 12.0
    if abs(r) < 1e-12:
        return principal / n
    return principal * r / (1 - (1 + r) ** (-n))


@dataclass
class KprResult:
    price_idr: float
    down_payment_idr: float
    principal_idr: float
    monthly_payment_idr: float
    min_monthly_income_idr: float
    total_interest_idr: float
    dsr_used: float
    income_ok: Optional[bool] = None
    dsr_actual: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


def kpr(price_idr: float, *, dp_pct: Optional[float] = None, years: Optional[int] = None,
        rate_pct: Optional[float] = None, dsr_max: Optional[float] = None,
        monthly_income_idr: Optional[float] = None) -> KprResult:
    p = load("financial_params")["kpr"]
    dp_pct = p["down_payment_pct_default"] if dp_pct is None else dp_pct
    years = p["tenor_years_default"] if years is None else years
    rate_pct = p["interest_pct_default"] if rate_pct is None else rate_pct
    dsr = p["dsr_max_default"] if dsr_max is None else dsr_max
    dp = price_idr * dp_pct / 100
    principal = price_idr - dp
    pmt = annuity_payment(principal, rate_pct, years)
    r = KprResult(price_idr, round(dp), round(principal), round(pmt), round(pmt / dsr),
                  round(pmt * years * 12 - principal), dsr)
    if monthly_income_idr:
        r.dsr_actual = round(pmt / monthly_income_idr, 4)
        r.income_ok = r.dsr_actual <= dsr
    return r


def max_affordable_price(monthly_income_idr: float, *, dp_pct: Optional[float] = None, years: Optional[int] = None,
                         rate_pct: Optional[float] = None, dsr_max: Optional[float] = None) -> float:
    """Harga rumah maksimum yang terjangkau: invers rumus anuitas."""
    p = load("financial_params")["kpr"]
    dp_pct = p["down_payment_pct_default"] if dp_pct is None else dp_pct
    years = p["tenor_years_default"] if years is None else years
    rate_pct = p["interest_pct_default"] if rate_pct is None else rate_pct
    dsr = p["dsr_max_default"] if dsr_max is None else dsr_max
    pmt_max = monthly_income_idr * dsr
    n = years * 12
    r = rate_pct / 100 / 12
    principal = pmt_max * n if r == 0 else pmt_max * (1 - (1 + r) ** (-n)) / r
    return principal / (1 - dp_pct / 100)


def sensitivity_grid(price_idr: float, cost_per_m2: float, gfa_m2: float, fixed_cost_idr: float) -> list[dict]:
    """Matriks margin kotor (%) untuk variasi harga & biaya/m2 (grid dari financial_params)."""
    g = load("financial_params")["sensitivity_grid"]
    rows = []
    for dp in g["price_delta_pct"]:
        for dc in g["cost_delta_pct"]:
            pr = price_idr * (1 + dp / 100)
            cost = cost_per_m2 * (1 + dc / 100) * gfa_m2 + fixed_cost_idr
            rows.append({"price_delta_pct": dp, "cost_delta_pct": dc, "price_idr": round(pr),
                         "gross_margin_pct": round((pr - cost) / pr * 100, 2)})
    return rows


"""Program ruang (slide 1.3): luas per ruang, luas bersih → bruto, tangga, standar 9 m2/jiwa.

Rumus:
    A_bersih   = Σ (qty x A_ruang)                       (ruang tertutup, zona != 'luar')
    A_tangga   = n_tangga_lantai x A_1_tangga            (bila lantai > 1)
    GFA_est    = A_bersih / η_kelas + A_tangga           (η = efisiensi: dinding+sirkulasi)
    Footprint  = GFA_est / lantai + A_beratap_luar        (carport/teras beratap masuk KDB; asumsi sebaran lantai merata)
    A_per_jiwa = GFA_est / jumlah_penghuni  ≥ 9,0 m2 (standar) / 7,2 m2 (ambang)   [Kepmen 403/KPTS/M/2002]
Tangga (Blondel): 2r + t = 0,61…0,65 m ; n = ceil(f2f / 0,18) ; run = (n-1) x t
"""

import math
from dataclasses import dataclass, field, asdict
from typing import Optional



@dataclass
class RoomLine:
    room_id: str
    name: str
    priority: str
    qty: int
    unit_area_m2: float
    total_m2: float
    zone: str
    in_gfa: bool
    status: str            # 'disetujui' | 'belum diputuskan' | 'dicoret'
    below_min: bool = False
    min_area_m2: float = 0.0


@dataclass
class ProgramResult:
    finishing_class: str
    lines: list[RoomLine] = field(default_factory=list)
    net_enclosed_m2: float = 0.0
    covered_outdoor_m2: float = 0.0
    stairs_m2: float = 0.0
    efficiency: float = 0.8
    gfa_estimate_m2: float = 0.0
    floors_assumed: int = 1
    footprint_estimate_m2: float = 0.0
    area_per_person_m2: Optional[float] = None
    undecided: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def stair_geometry(floor_to_floor_m: float = 3.2, width_m: float = 0.9, riser_target_m: float = 0.175,
                   blondel_m: float = 0.63, landing_m: float = 1.0) -> dict:
    """Geometri tangga satu lantai (lurus & U dengan bordes). Semua dalam meter."""
    n = max(2, math.ceil(floor_to_floor_m / 0.18 - 1e-9))        # riser max 18 cm
    riser = floor_to_floor_m / n
    tread = max(0.25, blondel_m - 2 * riser)                      # tread min 25 cm
    run = (n - 1) * tread
    straight_area = run * width_m
    half_run = math.ceil((n - 1) / 2) * tread
    u_area = (half_run + max(width_m, landing_m)) * (2 * width_m + 0.1)   # tangga U (2 flight + bordes)
    return {"n_risers": n, "riser_cm": round(riser * 100, 1), "tread_cm": round(tread * 100, 1),
            "blondel_2r_plus_t_cm": round((2 * riser + tread) * 100, 1), "run_m": round(run, 2),
            "area_straight_m2": round(straight_area, 2), "area_U_with_landing_m2": round(u_area, 2),
            "within_blondel": 61 <= (2 * riser + tread) * 100 <= 65}


def suggest_program(persona: BuyerPersona, finishing: str = "menengah") -> dict[str, int]:
    """Usulan jumlah ruang dari persona (titik awal diskusi, bukan keputusan)."""
    size = persona.household_size or 4
    kids = persona.children if persona.children is not None else max(0, size - 2)
    kt_anak = max(1 if size >= 3 else 0, kids)
    bedrooms = 1 + kt_anak
    km = 1 if bedrooms <= 2 else 2
    if finishing == "atas" and bedrooms >= 3:
        km = bedrooms
    wfh = "wfh" in (persona.lifestyle_tags or [])
    out = {"kt_utama": 1, "kt_anak": kt_anak, "km": km, "r_tamu": 1,
           "r_keluarga": 1, "r_makan": 1, "dapur": 1,
           "musholla": 1,   # dedicated vs serbaguna diputuskan pada sesi (slide 1.3)
           "carport": max(1, persona.cars or 1), "taman": 1,
           "r_kerja": 1 if wfh else 0, "r_art": 1 if finishing == "atas" else 0,
           "gudang": 1, "r_cuci": 1, "teras": 1,
           "dapur_kotor": 1 if finishing == "atas" else 0}
    return out


def apply_suggestion(project: PreDesignProject) -> None:
    if not project.program:
        project.init_default_program()
    sug = suggest_program(project.persona, project.product.finishing_class or "menengah")
    for item in project.program:
        if item.room_id in sug:
            item.qty = sug[item.room_id]


def _unit_area(item: RoomProgramItem, spec: dict, finishing: str, persona: BuyerPersona) -> float:
    if item.area_m2 is not None:
        return float(item.area_m2)
    a = float(spec["rec_area_m2"][finishing])
    if spec.get("area_per_unit") and item.room_id == "carport":
        return a  # per mobil
    return a


def compute_program(project: PreDesignProject, floors: Optional[int] = None) -> ProgramResult:
    finishing = project.product.finishing_class or "menengah"
    cat = room_catalog()
    eff = load("room_standards")["efficiency_by_class"][finishing]
    res = ProgramResult(finishing_class=finishing, efficiency=eff)
    persona = project.persona
    motor_area = cat["carport"].get("motorcycle_area_m2", 1.5)

    for item in project.program:
        spec = cat.get(item.room_id)
        if spec is None:           # ruang tambahan buatan pengguna
            spec = {"zone": "semi-privat", "min_area_m2": 0.0, "rec_area_m2": {"standar": item.area_m2 or 0, "menengah": item.area_m2 or 0, "atas": item.area_m2 or 0}}
        status = "disetujui" if item.approved else ("dicoret" if item.approved is False else "belum diputuskan")
        if item.approved is False or item.qty <= 0:
            continue
        unit = _unit_area(item, spec, finishing, persona)
        total = unit * item.qty
        if item.room_id == "carport" and persona.motorcycles:
            total += persona.motorcycles * motor_area * (0.5 if persona.cars else 1.0)   # motor parkir sebagian di carport
        in_gfa = spec["zone"] != "luar"
        below = item.room_id != "taman" and unit + 1e-9 < spec["min_area_m2"]
        line = RoomLine(item.room_id, item.name or spec.get("name", item.room_id), item.priority, item.qty, round(unit, 2),
                        round(total, 2), spec["zone"], in_gfa, status, below, spec["min_area_m2"])
        res.lines.append(line)
        if status == "belum diputuskan" and item.priority in ("Wajib", "Tinggi"):
            res.undecided.append(line.name)
        if below:
            res.issues.append(f"{line.name}: {unit:.1f} m² < minimum {spec['min_area_m2']:.1f} m² (Kepmen 403 / praktik).")
        if item.room_id == "taman":
            continue
        if in_gfa:
            res.net_enclosed_m2 += total
        elif item.room_id in ("carport", "teras"):
            res.covered_outdoor_m2 += total

    floors = floors or (project.regulation.max_floors or 1)
    n_floors = max(1, floors)
    if n_floors > 1:
        fh = load("room_standards")["floor_heights"]["floor_to_floor_m"]
        st = stair_geometry(fh)
        res.stairs_m2 = st["area_U_with_landing_m2"] * (n_floors - 1)
    res.floors_assumed = n_floors
    res.gfa_estimate_m2 = round(res.net_enclosed_m2 / eff + res.stairs_m2, 2)
    res.footprint_estimate_m2 = round(res.gfa_estimate_m2 / n_floors + res.covered_outdoor_m2, 2)
    if persona.household_size:
        res.area_per_person_m2 = round(res.gfa_estimate_m2 / persona.household_size, 2)
        std = load("room_standards")["occupancy_standard"]
        if res.area_per_person_m2 < std["area_per_person_threshold_m2"]:
            res.issues.append(f"Luas {res.area_per_person_m2:.1f} m²/jiwa di bawah AMBANG {std['area_per_person_threshold_m2']} m²/jiwa (Kepmen 403).")
        elif res.area_per_person_m2 < std["area_per_person_standard_m2"]:
            res.issues.append(f"Luas {res.area_per_person_m2:.1f} m²/jiwa di bawah standar {std['area_per_person_standard_m2']} m²/jiwa (masih di atas ambang 7,2).")
    return res


def min_gfa_for_occupants(n: int, standard: bool = True) -> float:
    """Luas lantai minimum rumah untuk n jiwa: 9,0 m2/jiwa (standar) atau 7,2 m2/jiwa (ambang)."""
    s = load("room_standards")["occupancy_standard"]
    return n * (s["area_per_person_standard_m2"] if standard else s["area_per_person_threshold_m2"])


"""Analisis intensitas bangunan: KDB, KLB, KDH, KBG/ketinggian, GSB & jarak bebas (slide 2.1).

Landasan: PP 16/2021 Ps.1 angka 9, 11-15 (definisi), Ps.21-23 (intensitas & jarak bebas);
nilai parameter berasal dari RDTR/RTRW/KRK/PBG setempat (bukan dari modul ini).

Rumus (L = luas kavling):
    Footprint_maks_KDB = KDB x L
    LantaiTotal_maks_KLB = KLB x L
    RuangHijau_min       = KDH x L
    Lantai_maks_tinggi   = floor((Hmax - peil - atap) / floor_to_floor)
    Lantai_efektif       = min(KBG, Lantai_maks_tinggi)
    GFA_maks             = min(KLB x L, Footprint_cap x Lantai_efektif)
    KLB_efektif          = GFA_maks / L
    Envelope             = (B - sisi_kiri - sisi_kanan) x (D - GSB_depan - belakang)
    Footprint_cap        = min(KDB x L, Envelope)
    Hardscape_maks       = L - Footprint - RuangHijau_min      (carport, jalan setapak, teras terbuka)
"""

import math
from dataclasses import dataclass, field, asdict
from typing import Optional



@dataclass
class EnvelopeResult:
    land_area_m2: float
    max_footprint_kdb_m2: Optional[float] = None
    max_gfa_klb_m2: Optional[float] = None
    min_green_m2: Optional[float] = None
    floors_by_height: Optional[int] = None
    floors_effective: Optional[int] = None
    buildable_width_m: Optional[float] = None
    buildable_depth_m: Optional[float] = None
    buildable_envelope_m2: Optional[float] = None
    footprint_cap_m2: Optional[float] = None
    gfa_cap_m2: Optional[float] = None
    klb_effective: Optional[float] = None
    hardscape_allowance_m2: Optional[float] = None
    binding_footprint: str = ""
    binding_gfa: str = ""
    height_estimate_m: dict[int, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def floor_height_model() -> dict:
    return load("room_standards")["floor_heights"]


def building_height_m(floors: int, *, floor_to_floor: Optional[float] = None, raise_m: Optional[float] = None,
                      roof_extra: Optional[float] = None, to_ridge: bool = True) -> float:
    """Tinggi bangunan perkiraan: peil + n x f2f (+ atap jika diukur ke puncak atap)."""
    fh = floor_height_model()
    f2f = fh["floor_to_floor_m"] if floor_to_floor is None else floor_to_floor
    r = fh["ground_floor_raise_m"] if raise_m is None else raise_m
    roof = fh["roof_ridge_extra_m"] if roof_extra is None else roof_extra
    return r + floors * f2f + (roof if to_ridge else 0.0)


def max_floors_by_height(max_height_m: float, *, floor_to_floor: Optional[float] = None,
                         raise_m: Optional[float] = None, roof_extra: Optional[float] = None,
                         to_ridge: bool = True) -> int:
    fh = floor_height_model()
    f2f = fh["floor_to_floor_m"] if floor_to_floor is None else floor_to_floor
    r = fh["ground_floor_raise_m"] if raise_m is None else raise_m
    roof = fh["roof_ridge_extra_m"] if roof_extra is None else roof_extra
    usable = max_height_m - r - (roof if to_ridge else 0.0)
    return max(0, int(math.floor(usable / f2f + 1e-9)))


def buildable_envelope(width_m: float, depth_m: float, *, gsb_front: float, side_left: float,
                       side_right: float, rear: float) -> tuple[float, float, float]:
    w = max(0.0, width_m - side_left - side_right)
    d = max(0.0, depth_m - gsb_front - rear)
    return w, d, w * d


def analyze(product: ProductParameters, reg: RegulationParams, site: Optional[SiteConditions] = None,
            *, height_to_ridge: bool = True) -> EnvelopeResult:
    """Hitung seluruh batas intensitas dari parameter regulasi + geometri kavling."""
    L = product.land_area_m2
    if not L or L <= 0:
        raise ValueError("land_area_m2 wajib diisi (>0) untuk analisis regulasi")
    res = EnvelopeResult(land_area_m2=L)
    defaults = load("regulation_defaults")["setback_defaults_if_unspecified"]

    if reg.kdb_pct is not None:
        res.max_footprint_kdb_m2 = reg.kdb_pct / 100.0 * L
    if reg.klb is not None:
        res.max_gfa_klb_m2 = reg.klb * L
    if reg.kdh_pct is not None:
        res.min_green_m2 = reg.kdh_pct / 100.0 * L

    # lantai
    cands = [x for x in (reg.max_floors,) if x]
    if reg.max_height_m:
        res.floors_by_height = max_floors_by_height(reg.max_height_m, to_ridge=height_to_ridge)
        cands.append(res.floors_by_height)
    res.floors_effective = min(cands) if cands else None
    if reg.max_floors and res.floors_by_height is not None and res.floors_by_height < reg.max_floors:
        res.notes.append(
            f"Batas tinggi {reg.max_height_m:g} m hanya memuat ±{res.floors_by_height} lantai "
            f"(asumsi f2f {floor_height_model()['floor_to_floor_m']} m) — lebih ketat dari KBG {reg.max_floors} lantai.")
    if res.floors_effective:
        res.height_estimate_m = {n: round(building_height_m(n, to_ridge=height_to_ridge), 2)
                                 for n in range(1, res.floors_effective + 1)}

    # envelope (butuh dimensi kavling)
    if product.lot_width_m and product.lot_depth_m:
        if abs(product.lot_width_m * product.lot_depth_m - L) / L > 0.05:
            res.notes.append("Lebar x kedalaman kavling berbeda >5% dari luas tanah — periksa data master plan.")
        sl = reg.gsb_side_left_m if reg.gsb_side_left_m is not None else defaults["side_each_m"]
        sr = reg.gsb_side_right_m if reg.gsb_side_right_m is not None else defaults["side_each_m"]
        rear = reg.gsb_rear_m if reg.gsb_rear_m is not None else defaults["rear_m"]
        if reg.gsb_side_left_m is None or reg.gsb_side_right_m is None or reg.gsb_rear_m is None:
            res.notes.append("Jarak bebas samping/belakang memakai DEFAULT asumsi — isi dari RDTR/Perda.")
        gsb = reg.gsb_front_m or 0.0
        res.buildable_width_m, res.buildable_depth_m, res.buildable_envelope_m2 = buildable_envelope(
            product.lot_width_m, product.lot_depth_m, gsb_front=gsb, side_left=sl, side_right=sr, rear=rear)

    # footprint cap
    caps = {}
    if res.max_footprint_kdb_m2 is not None:
        caps["KDB"] = res.max_footprint_kdb_m2
    if res.buildable_envelope_m2 is not None:
        caps["GSB/jarak bebas (envelope)"] = res.buildable_envelope_m2
    if caps:
        res.binding_footprint = min(caps, key=caps.get)
        res.footprint_cap_m2 = caps[res.binding_footprint]

    # GFA cap
    gcaps = {}
    if res.max_gfa_klb_m2 is not None:
        gcaps["KLB"] = res.max_gfa_klb_m2
    if res.footprint_cap_m2 is not None and res.floors_effective:
        gcaps[f"footprint x {res.floors_effective} lantai"] = res.footprint_cap_m2 * res.floors_effective
    if gcaps:
        res.binding_gfa = min(gcaps, key=gcaps.get)
        res.gfa_cap_m2 = gcaps[res.binding_gfa]
        res.klb_effective = res.gfa_cap_m2 / L
        if reg.klb is not None and res.klb_effective + 1e-9 < reg.klb * 0.5:
            res.notes.append(
                f"KLB {reg.klb:g} tidak mengikat: yang membatasi adalah {res.binding_gfa} "
                f"(KLB efektif ≈ {res.klb_effective:.2f}). Pastikan KLB/KBG pada RDTR konsisten.")

    if res.footprint_cap_m2 is not None and res.min_green_m2 is not None:
        res.hardscape_allowance_m2 = L - res.footprint_cap_m2 - res.min_green_m2
        if res.hardscape_allowance_m2 < 0:
            res.notes.append("KDB maksimum + KDH minimum melebihi luas kavling (jumlah > 100%).")
    return res


def check_target(res: EnvelopeResult, target_gfa_m2: float, floors: Optional[int] = None) -> dict:
    """Uji apakah GFA target muat: butuh footprint = GFA/lantai ≤ footprint_cap, GFA ≤ gfa_cap."""
    floors = floors or res.floors_effective or 1
    foot = target_gfa_m2 / floors
    ok_foot = res.footprint_cap_m2 is None or foot <= res.footprint_cap_m2 + 1e-9
    ok_gfa = res.gfa_cap_m2 is None or target_gfa_m2 <= res.gfa_cap_m2 + 1e-9
    min_floors = None
    if res.footprint_cap_m2:
        min_floors = math.ceil(target_gfa_m2 / res.footprint_cap_m2 - 1e-9)
    return {"floors": floors, "required_footprint_m2": round(foot, 2), "footprint_ok": ok_foot,
            "gfa_ok": ok_gfa, "min_floors_needed": min_floors,
            "footprint_utilization": round(foot / res.footprint_cap_m2, 3) if res.footprint_cap_m2 else None}


def check_gsj(reg: RegulationParams, site: SiteConditions) -> Optional[bool]:
    """True bila batas kavling depan berada pada/lebih jauh dari GSJ (diukur dari as jalan)."""
    if reg.gsj_from_axis_m is None or site.front_boundary_from_axis_m is None:
        return None
    return site.front_boundary_from_axis_m + 1e-9 >= reg.gsj_from_axis_m


"""Pre-sizing struktur (indikatif untuk estimasi biaya & ruang; BUKAN perhitungan struktur DED).

Rumus:
    q_D = Σ beban mati (kg/m2) ; q_L = beban hidup
    q_u = 1,2 q_D + 1,6 q_L                                       (SNI 2847/1727 kombinasi dasar)
    N_u kolom lantai-n = q_u x A_tributari x n
    A_g,perlu = N_u / (φ · 0,80 · (0,85 f'c (1-ρ) + f_y ρ))        (kolom sengkang, φ=0,65, Pn,maks=0,80 Po)
    h_balok,min = L / 16 … L / 21 ; h_pelat,min = L / 20 … L / 28    (tanpa kontrol lendutan)
"""

import math
from typing import Optional


G = 9.80665


def slab_dead_load(slab_t_m: float = 0.12, screed_cm: float = 3, tile_cm: float = 1, ceiling: bool = True, mep: bool = True) -> float:
    s = load("structure_params")
    d = s["dead_load_kg_m2"]
    q = slab_t_m * s["density_kg_m3"]["beton_bertulang"] + screed_cm * d["adukan_per_cm"] + tile_cm * d["penutup_lantai_per_cm"]
    if ceiling:
        q += d["plafon_penggantung"]
    if mep:
        q += d["mep_allowance"]
    return q


def wall_line_load(height_m: float, wall: str = "bata_ringan_10cm") -> float:
    """kg/m' beban dinding (tinggi x berat/m2)."""
    d = load("structure_params")["dead_load_kg_m2"]
    key = {"bata_1_2": "dinding_bata_1_2", "bata_ringan_10cm": "dinding_bata_ringan_10cm", "conblock_10cm": "dinding_conblock_10cm"}[wall]
    return height_m * d[key]


def factored_floor_load(q_dead: float, q_live_kg_m2: float = 200.0) -> float:
    return 1.2 * q_dead + 1.6 * q_live_kg_m2


def column_preliminary(trib_area_m2: float, floors: int, *, q_dead_kg_m2: Optional[float] = None, q_live_kg_m2: float = 200.0,
                       roof_dead_kg_m2: float = 80.0, wall_extra_kg_m2: float = 120.0, fc_mpa: Optional[float] = None,
                       fy_mpa: Optional[float] = None, rho: Optional[float] = None) -> dict:
    cp = load("structure_params")["concrete"]
    fc = cp["fc_mpa_default"] if fc_mpa is None else fc_mpa
    fy = cp["fy_mpa_default"] if fy_mpa is None else fy_mpa
    rho = cp["rho_column_default"] if rho is None else rho
    qd = (slab_dead_load() + wall_extra_kg_m2) if q_dead_kg_m2 is None else q_dead_kg_m2
    floor_loads = max(0, floors - 1) * factored_floor_load(qd, q_live_kg_m2)
    roof_load = 1.2 * roof_dead_kg_m2 + 1.6 * 100.0                       # atap: live 100 kg/m2 (PPIUG)
    nu_kn = (floor_loads + roof_load) * trib_area_m2 * G / 1000.0
    phi, pn = cp["phi_tied_column"], cp["pn_max_factor"]
    ag_mm2 = nu_kn * 1000.0 / (phi * pn * (0.85 * fc * (1 - rho) + fy * rho))
    side = math.sqrt(ag_mm2)
    min_side = 200 if floors >= 2 else 150
    side_round = max(min_side, int(math.ceil(side / 50.0) * 50))
    return {"Nu_kN": round(nu_kn, 1), "Ag_required_mm2": round(ag_mm2), "side_required_mm": round(side),
            "suggested_square_mm": side_round, "rho": rho,
            "note": "Pre-sizing beban gravitasi saja; gempa (SNI 1726) & kelangsingan belum ditinjau."}


def beam_depth_mm(span_m: float, support: str = "both_ends_continuous") -> int:
    r = load("structure_params")["member_min_thickness_ratio"]["beam"][support]
    return int(math.ceil(span_m * 1000 / r / 50.0) * 50)


def slab_thickness_mm(span_m: float, support: str = "both_ends_continuous") -> int:
    r = load("structure_params")["member_min_thickness_ratio"]["slab_one_way"][support]
    return max(load("structure_params")["min_member_sizes_mm"]["pelat_lantai_t_mm"], int(math.ceil(span_m * 1000 / r / 10.0) * 10))


def foundation_advice(soil_condition: str, fill_thickness_m: Optional[float], floors: int) -> list[str]:
    adv = []
    if soil_condition == "timbunan":
        t = fill_thickness_m or 0
        if t <= 1.0:
            adv.append("Timbunan tipis (≤ 1 m) & terkompaksi: footplate + sloof menerus/ pondasi menerus dapat dipertimbangkan setelah sondir.")
        elif t <= 2.5:
            adv.append("Timbunan sedang (1–2,5 m): pertimbangkan footplate di atas lapisan tanah asli (menembus timbunan) atau tiang mini/cerucuk; hindari slab on fill tanpa perbaikan.")
        else:
            adv.append("Timbunan tebal (> 2,5 m): tiang (mini pile/bor pile) menembus timbunan ke tanah keras dianjurkan; hitung negative skin friction.")
        adv.append("Wajib uji tanah (sondir/boring) dan kontrol kepadatan sebelum DED (SNI 8460:2017, SNI 2827:2008, SNI 1742:2008).")
    elif soil_condition == "tanah_asli_lunak":
        adv.append("Tanah lunak: tiang pancang mini/cerucuk bambu-kayu atau perbaikan tanah; hitung konsolidasi.")
    elif soil_condition == "gambut":
        adv.append("Gambut: pondasi dalam wajib; kajian khusus.")
    else:
        adv.append("Tanah baik: pondasi menerus batu kali/footplate (Kepmen 403: σ tanah ≥ 0,5 kg/cm²) setelah verifikasi sondir.")
    if floors >= 2:
        adv.append("Rumah 2 lantai: kolom min 20x20 cm (praktik), sloof saling mengikat, perhitungan gempa SNI 1726:2019 wajib pada DED.")
    return adv


"""Utilitas rumah: air bersih, air limbah/septik, sumur resapan, limpasan, listrik, sampah.

Rumus utama
  Air bersih   Q_hari = n x q ; Q_jam_puncak = C1 x Q_hari/24 ; Q_menit_puncak = C2 x Q_hari/(24x60)
               q = 100 L/org/hari (Kepmen 403)
  Septik       V_air = Q_A x n x t_d ; V_lumpur = Q_L x n x PP ; V = V_air + V_lumpur + P x L x T_bebas   (SNI 2398:2017)
  Limpasan     Q = C x i x A / 3,6e6  [m3/s] (i mm/jam, A m2) ; C_komposit = Σ C_i A_i / Σ A_i
  Sumur resapan (Sunjoto 1988; SNI 03-2453-2002)
               H = Q/(F K) x [1 - exp(-F K T / (π R²))] ; F = 5,5 R ; K ≥ 2 cm/jam
  Listrik      P_terpasang = Σ n x W ; S = P x df / cosφ ; daya = golongan VA terkecil ≥ 1,25 S
"""

import math
from typing import Optional



# ------------------------------------------------------------------ air bersih
def water_demand(n_persons: int, per_capita_l_day: Optional[float] = None, storage_days: Optional[float] = None) -> dict:
    w = load("utilities_params")["water"]
    q = w["per_capita_l_day"] if per_capita_l_day is None else per_capita_l_day
    days = w["storage_days"] if storage_days is None else storage_days
    daily = n_persons * q
    return {"daily_l": daily, "daily_m3": daily / 1000,
            "peak_hour_l_h": round(w["peak_hour_factor_C1"] * daily / 24, 1),
            "peak_minute_l_min": round(w["peak_minute_factor_C2"] * daily / (24 * 60), 2),
            "tank_l": round(daily * days), "per_capita_l_day": q}


# ------------------------------------------------------------------ air limbah & septik
def wastewater_flows(n_persons: int, per_capita_water_l_day: Optional[float] = None) -> dict:
    ww = load("utilities_params")["wastewater"]
    q = per_capita_water_l_day or load("utilities_params")["water"]["per_capita_l_day"]
    total = n_persons * q * ww["return_ratio"]
    black = n_persons * ww["blackwater_l_person_day"]
    return {"total_l_day": round(total, 1), "blackwater_l_day": black, "greywater_l_day": round(max(0.0, total - black), 1)}


def septic_tank(n_persons: int, *, td_days: Optional[float] = None, sludge_l_person_year: Optional[float] = None,
                desludge_years: Optional[float] = None, blackwater_l_person_day: Optional[float] = None,
                depth_m: float = 1.5, min_width_m: float = 0.9) -> dict:
    ww = load("utilities_params")["wastewater"]
    td = ww["detention_days_range"][1] if td_days is None else td_days
    sl = sum(ww["sludge_l_person_year_range"]) / 2 if sludge_l_person_year is None else sludge_l_person_year
    pp = ww["desludge_years_default"] if desludge_years is None else desludge_years
    qa = ww["blackwater_l_person_day"] if blackwater_l_person_day is None else blackwater_l_person_day
    va = qa * n_persons * td / 1000.0                 # m3
    vl = sl * n_persons * pp / 1000.0                 # m3
    v_net = va + vl
    ratio = ww["length_width_ratio"]
    area = v_net / depth_m
    width = math.sqrt(area / ratio)
    length = ratio * width
    adj = False
    if width < min_width_m:
        width, length = min_width_m, ratio * min_width_m
        depth_m = v_net / (width * length)
        adj = True
    fb = ww["freeboard_m"]
    return {"V_air_m3": round(va, 3), "V_lumpur_m3": round(vl, 3), "V_net_m3": round(v_net, 3),
            "length_m": round(length, 2), "width_m": round(width, 2), "liquid_depth_m": round(depth_m, 2),
            "freeboard_m": fb, "total_depth_m": round(depth_m + fb, 2),
            "V_total_m3": round(length * width * (depth_m + fb), 3), "min_width_applied": adj,
            "inputs": {"td_days": td, "sludge_l_person_year": sl, "desludge_years": pp, "blackwater_l_person_day": qa},
            "note": "Jarak septik–sumur air bersih 10 m (praktik; cek SNI 2398). Pada kavling kecil gunakan septik kedap + resapan komunal/IPAL."}


# ------------------------------------------------------------------ limpasan & resapan
def runoff_coefficient(areas_m2: dict[str, float]) -> float:
    c = load("utilities_params")["runoff_coefficient"]
    tot = sum(areas_m2.values())
    if tot <= 0:
        raise ValueError("luas total harus > 0")
    return sum(c[k] * a for k, a in areas_m2.items()) / tot


def runoff_flow_m3_s(c: float, intensity_mm_h: float, area_m2: float) -> float:
    return c * intensity_mm_h * area_m2 / 3.6e6


def lot_runoff(land_area_m2: float, roof_m2: float, paved_m2: float, green_m2: float,
               intensity_mm_h: Optional[float] = None, paving_type: str = "perkerasan_beton_aspal",
               green_type: str = "taman_rumput") -> dict:
    i = load("utilities_params")["infiltration_well"]["default_rain_intensity_mm_h"] if intensity_mm_h is None else intensity_mm_h
    rest = max(0.0, land_area_m2 - roof_m2 - paved_m2 - green_m2)
    areas = {"atap": roof_m2, paving_type: paved_m2, green_type: green_m2}
    if rest > 0:
        areas["tanah_halaman"] = rest
    c = runoff_coefficient({k: v for k, v in areas.items() if v > 0})
    q = runoff_flow_m3_s(c, i, land_area_m2)
    return {"c_composite": round(c, 3), "q_m3_s": q, "q_l_s": round(q * 1000, 2), "intensity_mm_h": i}


def detention_volume_m3(c_post: float, c_pre: float, intensity_mm_h: float, duration_h: float, area_m2: float) -> float:
    """Volume tampung sederhana agar debit puncak pasca-pembangunan = pra-pembangunan: V = (C_post - C_pre) i t A."""
    return max(0.0, (c_post - c_pre) * intensity_mm_h / 1000.0 * duration_h * area_m2)


def infiltration_well(roof_area_m2: float, *, k_cm_per_h: float, radius_m: float = 0.5,
                      intensity_mm_h: Optional[float] = None, duration_h: Optional[float] = None,
                      c_roof: Optional[float] = None, max_practical_depth_m: float = 3.0) -> dict:
    """Kedalaman efektif sumur resapan (Sunjoto)."""
    ip = load("utilities_params")["infiltration_well"]
    i = ip["default_rain_intensity_mm_h"] if intensity_mm_h is None else intensity_mm_h
    t_h = ip["default_rain_duration_h"] if duration_h is None else duration_h
    c = load("utilities_params")["runoff_coefficient"]["atap"] if c_roof is None else c_roof
    if k_cm_per_h < ip["min_permeability_cm_per_hour"]:
        status = "TIDAK memenuhi permeabilitas minimum 2,0 cm/jam (SNI 03-2453-2002) - sumur resapan tidak layak."
    else:
        status = "memenuhi"
    d = 2 * radius_m
    dim_ok = ip["diameter_min_m"] - 1e-9 <= d <= ip["diameter_max_m"] + 1e-9
    k = k_cm_per_h / 100.0 / 3600.0          # m/s
    q = runoff_flow_m3_s(c, i, roof_area_m2)
    f = 5.5 * radius_m
    t = t_h * 3600.0
    h = q / (f * k) * (1 - math.exp(-f * k * t / (math.pi * radius_m ** 2)))
    n = max(1, math.ceil(h / max_practical_depth_m - 1e-9))
    h_each = None
    if n > 1:
        q2 = q / n
        h_each = q2 / (f * k) * (1 - math.exp(-f * k * t / (math.pi * radius_m ** 2)))
    return {"Q_m3_s": q, "F": f, "K_m_s": k, "H_m": round(h, 2), "wells_for_max_depth": n,
            "H_each_m": round(h_each, 2) if h_each else round(h, 2), "diameter_ok": dim_ok, "permeability_status": status,
            "inputs": {"i_mm_h": i, "T_h": t_h, "C": c, "R_m": radius_m, "k_cm_h": k_cm_per_h}}


# ------------------------------------------------------------------ listrik
def electricity_estimate(appliances: dict[str, int], lamp_points: int = 0, margin: float = 1.25) -> dict:
    u = load("utilities_params")["electricity"]
    items = dict(appliances)
    if lamp_points:
        items["lampu_led_titik"] = items.get("lampu_led_titik", 0) + lamp_points
    connected = 0.0
    for k, n in items.items():
        connected += u["appliances_w"][k] * n
    demand_w = connected * u["diversity_factor"]
    s_va = demand_w / u["power_factor"]
    need = s_va * margin
    cls = next((c for c in u["va_classes"] if c >= need), u["va_classes"][-1])
    return {"connected_w": round(connected), "demand_w": round(demand_w), "apparent_va": round(s_va),
            "required_with_margin_va": round(need), "recommended_va_class": cls,
            "meets_min_100va": cls >= u["min_house_va"]}


def solid_waste(n_persons: int) -> dict:
    s = load("utilities_params")["solid_waste"]
    return {"l_day": round(n_persons * s["l_person_day"], 2), "kg_day": round(n_persons * s["kg_person_day"], 2),
            "bin_240l_every_days": round(240 / max(0.1, n_persons * s["l_person_day"]), 1)}



# Namespaces preserve the calculation-module API within this single-file module.
site = SimpleNamespace(**globals())
climate = SimpleNamespace(**globals())
daylight = SimpleNamespace(**globals())
financial = SimpleNamespace(**globals())
program = SimpleNamespace(**globals())
regulation = SimpleNamespace(**globals())
structure = SimpleNamespace(**globals())
utilities = SimpleNamespace(**globals())
csite, cclim, cfin, cprog, creg, cstr, cutil = (
    site, climate, financial, program, regulation, structure, utilities
)
fin, reg = financial, regulation


"""Mesin aturan validasi pre-design. Setiap temuan punya rule_id, severity, rujukan standar, dan saran.

Severity:
    BLOCKER  — desain/keputusan tidak boleh lanjut (melanggar batas absolut / field KRITIS kosong)
    WARNING  — perlu keputusan/mitigasi sebelum DED
    INFO     — catatan & saran
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional



class Severity(str, Enum):
    BLOCKER = "BLOCKER"
    WARNING = "WARNING"
    INFO = "INFO"


_ORDER = {Severity.BLOCKER: 0, Severity.WARNING: 1, Severity.INFO: 2}


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    section: str
    message: str
    reference: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


class _Collector:
    def __init__(self) -> None:
        self.items: list[Finding] = []

    def add(self, rule_id: str, sev: Severity, section: str, msg: str, ref: str = "", sug: str = "") -> None:
        self.items.append(Finding(rule_id, sev, section, msg, ref, sug))


def _fmt(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def _check_persona(p: PreDesignProject, c: _Collector) -> None:
    ps = p.persona
    if ps.age_min is not None and ps.age_max is not None and ps.age_min > ps.age_max:
        c.add("P-001", Severity.BLOCKER, "1.1", f"Usia minimum ({ps.age_min}) > maksimum ({ps.age_max}).")
    if ps.household_size and ps.children is not None and ps.children >= ps.household_size:
        c.add("P-002", Severity.BLOCKER, "1.1", "Jumlah anak ≥ jumlah penghuni; periksa data profil keluarga.")
    if ps.monthly_income_idr is None:
        c.add("P-003", Severity.INFO, "1.1", "Penghasilan rumah tangga belum diisi: uji keterjangkauan KPR (DSR) dilewati.",
              sug="Isi dari data survey agar harga target dapat diuji.")
    elif p.product.target_price_idr:
        k = cfin.kpr(p.product.target_price_idr, monthly_income_idr=ps.monthly_income_idr)
        if k.income_ok is False:
            c.add("P-004", Severity.WARNING, "1.1",
                  f"Angsuran KPR ≈ Rp {_fmt(k.monthly_payment_idr)}/bln = {k.dsr_actual:.0%} penghasilan > DSR {k.dsr_used:.0%}. "
                  f"Penghasilan minimal ≈ Rp {_fmt(k.min_monthly_income_idr)}/bln.",
                  "Praktik perbankan (DSR 30–40%)",
                  "Turunkan harga/luas, tambah DP, atau revisi persona.")
    if ps.cars and p.program:
        cp = p.room("carport")
        if cp is None or cp.approved is False or cp.qty < ps.cars:
            c.add("P-005", Severity.WARNING, "1.1/1.3", f"Persona memiliki {ps.cars} mobil tetapi carport belum menampung.",
                  "Satuan ruang parkir 2,5 x 5,0 m")
    if "wfh" in (ps.lifestyle_tags or []) and p.program:
        rk = p.room("r_kerja")
        if rk is None or rk.approved is False or rk.qty == 0:
            c.add("P-006", Severity.INFO, "1.1/1.3", "Gaya hidup WFH tetapi Ruang Kerja belum masuk program.",
                  sug="Putuskan: ruang kerja dedicated (≥ 4,5 m²) atau dalam kamar tidur.")


def _check_product(p: PreDesignProject, c: _Collector, prog: Optional[cprog.ProgramResult]) -> None:
    pr = p.product
    for k in p.critical_missing():
        label = {"max_construction_cost_per_m2_idr": "Biaya Konstruksi Maks./m²", "num_types": "Jumlah Tipe Rumah",
                 "finishing_class": "Kelas Finishing"}.get(k, k)
        c.add("PR-001", Severity.BLOCKER, "1.2", f"Field KRITIS '{label}' kosong — wajib diputuskan sekarang.",
              "Slide 1.2 (KRITIS)", "Putuskan pada sesi; untuk biaya/m² gunakan solve_max_construction_cost() sebagai usulan awal.")
    if pr.finishing_class and pr.finishing_class not in FINISHING:
        c.add("PR-002", Severity.BLOCKER, "1.2", f"Kelas finishing '{pr.finishing_class}' tidak valid ({', '.join(FINISHING)}).")
    lo, hi = pr.price_range()
    if lo and hi and lo > hi:
        c.add("PR-009", Severity.BLOCKER, "1.2", "Harga minimum > maksimum.")
    if pr.lot_width_m and pr.lot_depth_m and pr.land_area_m2:
        dev = abs(pr.lot_width_m * pr.lot_depth_m - pr.land_area_m2) / pr.land_area_m2
        if dev > 0.05:
            c.add("PR-007", Severity.WARNING, "1.2", f"Lebar x kedalaman = {pr.lot_width_m * pr.lot_depth_m:.1f} m² ≠ luas tanah {pr.land_area_m2:.1f} m².")
    if pr.num_types and pr.num_types > 1:
        c.add("PR-010", Severity.INFO, "1.2", f"{pr.num_types} tipe: setiap tipe butuh program ruang, GFA, dan RAB sendiri; pre-design ini dihitung untuk tipe acuan.")
    # biaya
    if pr.max_construction_cost_per_m2_idr and pr.finishing_class in FINISHING:
        bench = load("finishing_classes")["classes"][pr.finishing_class]["cost_per_m2_idr"]
        if pr.max_construction_cost_per_m2_idr < bench["low"]:
            c.add("PR-004", Severity.WARNING, "1.2",
                  f"Biaya maks Rp {_fmt(pr.max_construction_cost_per_m2_idr)}/m² di bawah rentang kelas {pr.finishing_class} "
                  f"(Rp {_fmt(bench['low'])}–{_fmt(bench['high'])}/m², asumsi).",
                  "Predesign.json:finishing_classes (asumsi)", "Turunkan kelas finishing atau naikkan anggaran; kalibrasi dengan AHSP/HSPK lokal.")
    gfa = pr.target_gfa_m2
    if gfa and pr.target_price_idr and pr.max_construction_cost_per_m2_idr:
        share = gfa * pr.max_construction_cost_per_m2_idr / pr.target_price_idr
        if share > 0.80:
            c.add("PR-005", Severity.BLOCKER, "1.2", f"Biaya konstruksi maksimum = {share:.0%} harga jual — tidak menyisakan ruang untuk tanah, prasarana, dan margin.")
        elif share > 0.55:
            c.add("PR-005", Severity.WARNING, "1.2", f"Biaya konstruksi = {share:.0%} harga jual (tipikal 35–55%).")
    if pr.target_price_idr and pr.land_area_m2 and gfa:
        c.add("PR-008", Severity.INFO, "1.2", f"Harga/m² bangunan ≈ Rp {_fmt(pr.target_price_idr / gfa)}; harga/m² tanah ≈ Rp {_fmt(pr.target_price_idr / pr.land_area_m2)} (indikator awal).")
    # luas per jiwa
    if gfa and p.persona.household_size:
        std = load("room_standards")["occupancy_standard"]
        a = gfa / p.persona.household_size
        if a < std["area_per_person_threshold_m2"]:
            c.add("PR-011", Severity.WARNING, "1.2", f"GFA target {gfa:.0f} m² = {a:.1f} m²/jiwa < ambang {std['area_per_person_threshold_m2']} m²/jiwa.", cite("KEPMEN-403-2002"))
        elif a < std["area_per_person_standard_m2"]:
            c.add("PR-011", Severity.INFO, "1.2", f"GFA target {gfa:.0f} m² = {a:.1f} m²/jiwa (standar {std['area_per_person_standard_m2']} m²/jiwa).", cite("KEPMEN-403-2002"))


def _check_program(p: PreDesignProject, c: _Collector, prog: Optional[cprog.ProgramResult],
                   env: Optional[creg.EnvelopeResult]) -> None:
    if not p.program:
        c.add("PG-000", Severity.WARNING, "1.3", "Program ruang belum dibuat.", sug="Panggil project.init_default_program() lalu apply_suggestion().")
        return
    for it in p.program:
        if it.priority == "Wajib" and it.approved is False:
            c.add("PG-002", Severity.WARNING, "1.3", f"Ruang Wajib '{it.name}' dicoret.", sug="Konfirmasi ulang: ruang wajib jarang dihapus.")
    for need in ("kt_utama", "km", "dapur"):
        it = p.room(need)
        if it is None or it.approved is False or it.qty <= 0:
            c.add("PG-007", Severity.BLOCKER, "1.3", f"Program tidak memuat '{need}' — hunian tidak layak huni (Kepmen 403 sanitasi/ruang minimum).", cite("KEPMEN-403-2002"))
    if prog:
        if prog.undecided:
            c.add("PG-001", Severity.INFO, "1.3", "Belum diputuskan (centang/coret): " + ", ".join(prog.undecided) + ".")
        for msg in prog.issues:
            c.add("PG-004", Severity.WARNING, "1.3", msg, cite("KEPMEN-403-2002"))
        tgt = p.product.target_gfa_m2
        if tgt:
            if prog.gfa_estimate_m2 > tgt * 1.10:
                c.add("PG-003", Severity.WARNING, "1.3",
                      f"Program ({prog.gfa_estimate_m2:.0f} m² bruto) melebihi GFA target {tgt:.0f} m² (>10%).",
                      sug="Kurangi ruang Sedang/ turunkan luas rekomendasi, atau naikkan GFA & harga.")
            elif prog.gfa_estimate_m2 < tgt * 0.85:
                c.add("PG-003", Severity.INFO, "1.3", f"Program ({prog.gfa_estimate_m2:.0f} m²) jauh di bawah GFA target {tgt:.0f} m²: ada ruang untuk menambah/ memperbesar ruang.")
        if env and env.footprint_cap_m2 and prog.footprint_estimate_m2 > env.footprint_cap_m2 + 1e-9:
            c.add("PG-005", Severity.BLOCKER, "1.3/2.1",
                  f"Footprint program ≈ {prog.footprint_estimate_m2:.1f} m² melebihi batas {env.footprint_cap_m2:.1f} m² ({env.binding_footprint}).",
                  cite("PP-16-2021"), "Tambah lantai (bila KBG mengizinkan), kurangi carport/teras beratap, atau perkecil program.")


def _check_regulation(p: PreDesignProject, c: _Collector, env: Optional[creg.EnvelopeResult]) -> None:
    r, pr = p.regulation, p.product
    need = {"kdb_pct": "KDB", "klb": "KLB", "gsb_front_m": "GSB", "kdh_pct": "KDH", "max_floors": "KBG (jumlah lantai)"}
    for k, label in need.items():
        if getattr(r, k) is None:
            c.add("RG-001", Severity.BLOCKER, "2.1", f"Parameter {label} belum diisi.", cite("PP-16-2021"), "Ambil dari RDTR/KRK/PBG setempat.")
    if r.gsj_from_axis_m is None:
        c.add("RG-001", Severity.WARNING, "2.1", "GSJ (jarak dari as jalan) belum diisi.")
    if r.max_height_m is None:
        c.add("RG-001", Severity.WARNING, "2.1", "Ketinggian maksimum belum diisi.")
    sr = load("regulation_defaults")["sanity_ranges"]
    for key, label in (("kdb_pct", "KDB"), ("klb", "KLB"), ("gsb_front_m", "GSB"), ("kdh_pct", "KDH"), ("max_floors", "KBG"), ("max_height_m", "Tinggi")):
        v = getattr(r, key)
        if v is not None:
            lo, hi = sr[key]
            if not lo <= v <= hi:
                c.add("RG-002", Severity.WARNING, "2.1", f"{label} = {v:g} di luar rentang kewajaran [{lo}, {hi}] — cek salah ketik/satuan.")
    if r.kdb_pct is not None and r.kdh_pct is not None and r.kdb_pct + r.kdh_pct > 100:
        c.add("RG-004", Severity.BLOCKER, "2.1", f"KDB {r.kdb_pct:g}% + KDH {r.kdh_pct:g}% > 100%.")
    keys = load("regulation_defaults")["confirmation_keys"]
    unconf = [k.upper() for k in keys if not r.confirmed.get(k)]
    if unconf:
        c.add("RG-003", Severity.WARNING, "2.1", "Belum dikonfirmasi ke RDTR/PBG: " + ", ".join(unconf) + ".",
              cite("PERMEN-ATRBPN-11-2021"), "Tim Teknik wajib verifikasi sebelum keputusan desain.")
    if not r.source:
        c.add("RG-010", Severity.WARNING, "2.1", "Sumber parameter regulasi (RDTR/KRK/PBG) belum dicatat.")
    if r.kdb_pct is not None and r.kdb_pct > load("regulation_defaults")["kepmen_403_rs_sehat"]["kdb_max_pct"]:
        c.add("RG-007", Severity.INFO, "2.1", f"KDB {r.kdb_pct:g}% > 60% (batas Rs Sehat Kepmen 403) — acuan RDTR yang berlaku.", cite("KEPMEN-403-2002"))
    if env:
        for n in env.notes:
            c.add("RG-005", Severity.INFO, "2.1", n)
        if pr.target_gfa_m2 and env.gfa_cap_m2 is not None:
            chk = creg.check_target(env, pr.target_gfa_m2)
            if not chk["gfa_ok"]:
                c.add("RG-008", Severity.BLOCKER, "1.2/2.1",
                      f"GFA target {pr.target_gfa_m2:.1f} m² > batas {env.gfa_cap_m2:.1f} m² ({env.binding_gfa}).",
                      cite("PP-16-2021"), f"Kurangi GFA ≤ {env.gfa_cap_m2:.0f} m² atau tinjau lantai/KDB.")
            if not chk["footprint_ok"]:
                c.add("RG-008", Severity.BLOCKER, "1.2/2.1",
                      f"Footprint yang dibutuhkan {chk['required_footprint_m2']} m² > batas {env.footprint_cap_m2:.1f} m² ({env.binding_footprint}). "
                      f"Butuh ≥ {chk['min_floors_needed']} lantai.", cite("PP-16-2021"))
            elif chk["footprint_utilization"] and chk["footprint_utilization"] > 0.95:
                c.add("RG-008", Severity.WARNING, "2.1", f"Pemakaian footprint {chk['footprint_utilization']:.0%} dari batas — nyaris tanpa toleransi desain.")
        if env.hardscape_allowance_m2 is not None and env.hardscape_allowance_m2 < 0:
            c.add("RG-004", Severity.BLOCKER, "2.1", "Tidak ada sisa lahan untuk hardscape setelah KDB maks + KDH min.")
    gs = creg.check_gsj(r, p.site)
    if gs is False:
        c.add("RG-009", Severity.BLOCKER, "2.1/2.2", "Batas kavling depan berada di dalam GSJ (lebih dekat ke as jalan dari GSJ).", cite("PP-16-2021"))


def _check_site(p: PreDesignProject, c: _Collector, env: Optional[creg.EnvelopeResult]) -> None:
    s = p.site
    labels = {"front_orientation": "orientasi hadap", "topography": "kontur", "soil_condition": "kondisi tanah",
              "vehicle_access_from": "arah akses kendaraan", "pln_entry_from": "posisi PLN masuk"}
    for k, lab in labels.items():
        if not getattr(s, k):
            c.add("ST-001", Severity.WARNING, "2.2", f"Belum diisi: {lab}.")
    for k in ("front_orientation", "best_view_direction", "vehicle_access_from", "pln_entry_from"):
        v = getattr(s, k)
        if v and v not in COMPASS8:
            c.add("ST-000", Severity.BLOCKER, "2.2", f"{k}='{v}' bukan kode kompas valid ({', '.join(COMPASS8)}).")
    if s.front_orientation in COMPASS8:
        city = s.ottv_city if s.ottv_city and s.ottv_city in load("ottv_solar_factor")["cities"] else None
        hot = {"B", "BL", "BD"}
        if s.front_orientation in hot:
            msg = f"Muka depan menghadap {load('ottv_solar_factor')['_meta']['orientation_codes'][s.front_orientation]}: terpapar matahari sore."
            if city:
                ranks = dict(cclim.orientation_ranking(city))
                msg += f" SF {city}: {ranks[s.front_orientation]:.0f} W/m² (rentang {min(ranks.values()):.0f}–{max(ranks.values()):.0f})."
            c.add("ST-002", Severity.WARNING, "2.2", msg, cite("SNI-6389-2020"),
                  "Minimalkan WWR sisi barat, overhang dalam/sirip vertikal, buffer servis, warna fasad cerah.")
        for line in cclim.zoning_advice(s.front_orientation, city, s.best_view_direction)[-2:]:
            c.add("ST-002b", Severity.INFO, "2.2", line)
    if s.best_view_direction in ("B", "BL", "BD"):
        c.add("ST-005", Severity.WARNING, "2.2", f"View terbaik ({s.best_view or s.best_view_direction}) ke arah barat: konflik dengan matahari sore.",
              cite("SNI-6389-2020"), "Bukaan view dengan kaca low-E/ overhang/ vegetasi; teras sebagai buffer.")
    if csite.view_is_water(s.best_view):
        for n in load("site_rules")["view_rules"]["water_body"]["notes"]:
            c.add("ST-006", Severity.INFO, "2.2", n, cite("PERMEN-PUPR-28-2015"))
    # tanah
    sr = csite.soil_rule(s.soil_condition)
    sev = Severity[sr["severity"]]
    if s.soil_condition:
        if s.soil_condition == "timbunan":
            c.add("ST-003", Severity.WARNING, "2.2", "Tapak di atas timbunan: " + " ".join(sr["required_actions"][:2]),
                  cite("SNI-8460-2017", "SNI-2827-2008", "SNI-1742-2008"), sr["required_actions"][3])
            if s.soil_tested is not True:
                c.add("ST-003b", Severity.WARNING, "2.2", "Uji tanah (sondir/boring) belum ada — daya dukung & penurunan belum terverifikasi.", cite("SNI-8460-2017"))
            if s.fill_thickness_m is None:
                c.add("ST-010", Severity.WARNING, "2.2", "Tebal timbunan belum diisi.")
            elif s.fill_age_months is not None and s.fill_age_months < 12:
                c.add("ST-010b", Severity.WARNING, "2.2", f"Timbunan baru ({s.fill_age_months} bln): risiko penurunan; pertimbangkan preloading/pondasi dalam.")
            lo, hi = sr["cost_uplift_pct_construction"]
            c.add("ST-003c", Severity.INFO, "2.2", f"Tambahkan biaya pondasi/perbaikan tanah ±{lo}–{hi}% biaya konstruksi (asumsi) pada anggaran.")
        else:
            c.add("ST-003", sev, "2.2", sr["title"] + ": " + sr["required_actions"][0])
    if s.level_difference_m is not None and s.topography:
        cls = csite.terrain_class(s.level_difference_m)
        if cls != s.topography:
            c.add("ST-004", Severity.INFO, "2.2", f"Beda tinggi {s.level_difference_m:g} m setara kontur '{cls}', tetapi dicatat '{s.topography}'.")
    if s.vehicle_access_from and s.front_orientation in COMPASS8:
        fac = csite.facade_orientations(s.front_orientation)
        if s.vehicle_access_from == fac["belakang"]:
            c.add("ST-007", Severity.WARNING, "2.2", "Akses kendaraan dari sisi belakang kavling, bukan sisi muka: periksa jalan & GSJ.")
    if s.pln_entry_from and s.vehicle_access_from and s.pln_entry_from != s.vehicle_access_from:
        c.add("ST-008", Severity.INFO, "2.2", "Posisi PLN masuk berbeda dari akses kendaraan: rencanakan jalur kabel & panel agar tidak melintasi carport.")
    nn = s.non_negotiables or []
    for d in load("site_rules")["default_non_negotiables"]:
        if d not in nn:
            c.add("ST-009", Severity.INFO, "2.2", f"Non-negotiable standar belum tercantum: '{d}'.")
    if s.latitude is None:
        c.add("ST-011", Severity.INFO, "2.2", "Lintang belum diisi: analisis matahari/ kiblat memakai asumsi.")


def _check_utilities(p: PreDesignProject, c: _Collector) -> None:
    n = p.persona.household_size
    L = p.product.land_area_m2
    if n and L and L < 150:
        c.add("UT-001", Severity.INFO, "2.2", f"Kavling {L:.0f} m²: jarak septik–sumur ≥ 10 m sulit dipenuhi; gunakan PDAM + septik kedap/biofilter atau IPAL komunal.",
              cite("SNI-2398-2017"))
    if p.site.soil_condition == "timbunan":
        c.add("UT-002", Severity.INFO, "2.2", "Sumur resapan di timbunan: uji infiltrasi in-situ; jauhkan ≥ 2–3 m dari pondasi.", cite("SNI-03-2453-2002"))


def validate_project(p: PreDesignProject) -> list[Finding]:
    """Jalankan seluruh aturan; urut dari BLOCKER → INFO."""
    c = _Collector()
    env: Optional[creg.EnvelopeResult] = None
    try:
        env = creg.analyze(p.product, p.regulation, p.site)
    except ValueError as e:
        c.add("PR-003", Severity.BLOCKER, "1.2", str(e))
    prog: Optional[cprog.ProgramResult] = None
    if p.program:
        floors = (env.floors_effective if env and env.floors_effective else None)
        prog = cprog.compute_program(p, floors=floors)
    _check_persona(p, c)
    _check_product(p, c, prog)
    _check_program(p, c, prog, env)
    _check_regulation(p, c, env)
    _check_site(p, c, env)
    _check_utilities(p, c)
    # keputusan
    for sec in ("1.1", "1.2", "1.3", "2.1", "2.2"):
        if not any(d.section_id == sec and d.decided for d in p.decisions):
            c.add("DC-001", Severity.INFO, sec, f"Keputusan seksi {sec} belum dicatat (⚑ KEPUTUSAN).")
    c.items.sort(key=lambda f: (_ORDER[f.severity], f.section, f.rule_id))
    return c.items


def summarize(findings: list[Finding]) -> dict[str, int]:
    out = {s.value: 0 for s in Severity}
    for f in findings:
        out[f.severity.value] += 1
    return out


"""Pembuat laporan Markdown 'Berita Acara Pre-Design' dari PreDesignProject."""

from datetime import datetime
from typing import Optional



def _idr(x: Optional[float]) -> str:
    return "—" if x is None else "Rp " + f"{x:,.0f}".replace(",", ".")


def _n(x, d=1, unit=""):
    return "—" if x is None else f"{x:.{d}f}{unit}"


def build_report(p: PreDesignProject, *, finishing_override: Optional[str] = None) -> str:
    lines: list[str] = []
    w = lines.append
    findings = validate_project(p)
    summ = summarize(findings)
    w(f"# Berita Acara Pre-Design — {p.name}")
    w(f"Lokasi: {p.location or '—'} · Sesi: {p.session_date} · Dibuat: {datetime.now():%Y-%m-%d %H:%M}\n")
    w(f"**Ringkasan validasi:** {summ['BLOCKER']} BLOCKER · {summ['WARNING']} WARNING · {summ['INFO']} INFO\n")

    w("## Kelengkapan Form")
    w("| Seksi | Judul | Terisi | % | Keputusan | Kosong |")
    w("|---|---|---|---|---|---|")
    for sid, v in p.completeness().items():
        w(f"| {sid} | {v['title']} | {v['filled']}/{v['required']} | {v['pct']:.0f}% | {'✔' if v['decided'] else '—'} | {', '.join(v['missing']) or '—'} |")

    pr = p.product
    w("\n## 1.2 Parameter Produk")
    w(f"- Harga jual target: {_idr(pr.target_price_idr)}")
    w(f"- Biaya konstruksi maks./m² (KRITIS): {_idr(pr.max_construction_cost_per_m2_idr)}")
    w(f"- Luas tanah: {_n(pr.land_area_m2, 1, ' m²')} ({_n(pr.lot_width_m,1)} x {_n(pr.lot_depth_m,1)} m) · GFA target: {_n(pr.target_gfa_m2, 1, ' m²')}")
    w(f"- Jumlah tipe (KRITIS): {pr.num_types or '—'} · Kelas finishing (KRITIS): {pr.finishing_class or '—'}")
    if pr.target_price_idr:
        k = cfin.kpr(pr.target_price_idr, monthly_income_idr=p.persona.monthly_income_idr)
        w(f"- Keterjangkauan KPR (DP {k.down_payment_idr/pr.target_price_idr:.0%}, default bunga/tenor): angsuran ≈ {_idr(k.monthly_payment_idr)}/bln · penghasilan minimum ≈ {_idr(k.min_monthly_income_idr)}/bln"
          + (f" · DSR aktual {k.dsr_actual:.0%} ({'OK' if k.income_ok else 'LEBIH'})" if k.dsr_actual else ""))

    env = None
    try:
        env = creg.analyze(p.product, p.regulation, p.site)
    except ValueError:
        pass
    w("\n## 2.1 Intensitas Bangunan (turunan regulasi)")
    if env:
        w("| Parameter | Nilai |")
        w("|---|---|")
        w(f"| Footprint maks. KDB | {_n(env.max_footprint_kdb_m2,1,' m²')} |")
        w(f"| Envelope setelah GSB/jarak bebas | {_n(env.buildable_envelope_m2,1,' m²')} ({_n(env.buildable_width_m)} x {_n(env.buildable_depth_m)} m) |")
        w(f"| **Footprint cap** | **{_n(env.footprint_cap_m2,1,' m²')}** (dibatasi {env.binding_footprint or '—'}) |")
        w(f"| Lantai efektif | {env.floors_effective or '—'} (dari tinggi: {env.floors_by_height if env.floors_by_height is not None else '—'}) |")
        w(f"| GFA maks. KLB | {_n(env.max_gfa_klb_m2,1,' m²')} |")
        w(f"| **GFA cap** | **{_n(env.gfa_cap_m2,1,' m²')}** (dibatasi {env.binding_gfa or '—'}) · KLB efektif {_n(env.klb_effective,2)} |")
        w(f"| RTH/KDH minimum | {_n(env.min_green_m2,1,' m²')} |")
        w(f"| Sisa hardscape maks. | {_n(env.hardscape_allowance_m2,1,' m²')} |")
        for n in env.notes:
            w(f"- ℹ️ {n}")
    else:
        w("_Luas tanah belum diisi._")

    w("\n## 1.3 Program Ruang")
    if p.program:
        pres = cprog.compute_program(p, floors=env.floors_effective if env else None)
        w("| Ruang | Prioritas | Qty | m²/unit | Total m² | Status |")
        w("|---|---|---|---|---|---|")
        for ln in pres.lines:
            w(f"| {ln.name} | {ln.priority} | {ln.qty} | {ln.unit_area_m2:.1f} | {ln.total_m2:.1f} | {ln.status}{' ⚠ <min' if ln.below_min else ''} |")
        w(f"\nLuas bersih tertutup {pres.net_enclosed_m2:.1f} m² ÷ η {pres.efficiency:.2f} + tangga {pres.stairs_m2:.1f} m² → **GFA ≈ {pres.gfa_estimate_m2:.1f} m²** "
          f"({pres.floors_assumed} lantai) · footprint ≈ {pres.footprint_estimate_m2:.1f} m² · "
          f"{_n(pres.area_per_person_m2,1,' m²/jiwa')}")
    else:
        w("_Belum ada program ruang._")

    s = p.site
    w("\n## 2.2 Tapak")
    w(f"- Hadap: {s.front_orientation or '—'} · Kontur: {s.topography or '—'} (Δ {_n(s.level_difference_m,1,' m')}) · Tanah: {s.soil_condition or '—'}"
      + (f" (timbunan {_n(s.fill_thickness_m,1,' m')}, uji tanah: {'ya' if s.soil_tested else 'belum'})" if s.soil_condition == 'timbunan' else ""))
    w(f"- View: {s.best_view or '—'} ({s.best_view_direction or '—'}) · Akses kendaraan: {s.vehicle_access_from or '—'} · PLN: {s.pln_entry_from or '—'}")
    if s.front_orientation in csite.load("ottv_solar_factor")["_meta"]["azimuth_deg"]:
        w("- Orientasi muka: " + ", ".join(f"{k} {v}" for k, v in csite.facade_orientations(s.front_orientation).items()))
        if s.latitude is not None:
            w(f"- Arah kiblat (perkiraan, lon belum tentu diisi): lihat calc.site.qibla_azimuth")
    w("- Non-negotiable: " + "; ".join(s.non_negotiables or ["—"]))

    w("\n## Temuan Validasi")
    w("| Sev | Rule | Seksi | Temuan | Rujukan | Saran |")
    w("|---|---|---|---|---|---|")
    icon = {Severity.BLOCKER: "⛔", Severity.WARNING: "⚠️", Severity.INFO: "ℹ️"}
    for f in findings:
        cell = lambda t: str(t).replace("|", "/").replace("\n", " ")
        w(f"| {icon[f.severity]} {f.severity.value} | {f.rule_id} | {f.section} | {cell(f.message)} | {cell(f.reference)} | {cell(f.suggestion)} |")

    w("\n## Keputusan Tercatat")
    if p.decisions:
        for d in p.decisions:
            w(f"- **{d.section_id}** — {'✔ ' + d.decision_text if d.decided else 'belum'} {('(' + d.decided_by + ', ' + d.decided_at + ')') if d.decided else ''}")
    else:
        w("_Belum ada._")

    w("\n---\n*Catatan:* angka berstatus V0/asumsi pada `Predesign.json` harus diverifikasi ke dokumen SNI/regulasi resmi dan data lokal (RDTR, HSPK) sebelum menjadi dasar keputusan hukum/biaya.")
    return "\n".join(lines)


"""Halaman Streamlit Pre-Design. Impor render dari Predesign.py pada app.py."""

import streamlit as st


K = "pd_"

NUMERIC_HELP = {
    "age_min": "Batas bawah rentang usia pembeli yang disasar; bukan syarat umur legal.",
    "age_max": "Batas atas rentang usia pembeli yang disasar; bukan syarat umur legal.",
    "hh": "Jumlah seluruh penghuni rumah yang diperkirakan. Dipakai untuk menilai kebutuhan ruang dan luas per orang.",
    "kids": "Jumlah anak dalam rumah tangga sasaran; membantu memperkirakan kebutuhan kamar anak.",
    "inc": "Perkiraan pendapatan rumah tangga per bulan. Digunakan sebagai masukan analisis keterjangkauan KPR, bukan verifikasi penghasilan.",
    "cars": "Jumlah mobil yang perlu ditampung pada hunian; memengaruhi usulan jumlah carport.",
    "motor": "Jumlah sepeda motor penghuni; memengaruhi estimasi luasan parkir carport.",
    "price": "Harga jual sasaran per unit rumah. Dipakai untuk menghitung perkiraan batas biaya konstruksi.",
    "lt": "Luas satu bidang tanah/kavling. Dipakai dalam analisis KDB, KLB, KDH dan envelope bangunan.",
    "lw": "Lebar kavling pada sisi muka yang menghadap akses/jalan.",
    "ld": "Panjang kavling dari sisi muka menuju sisi belakang.",
    "lb": "Target luas lantai kotor bangunan per unit (GFA), sebelum pengurangan komponen sesuai definisi regulasi.",
    "ntype": "Jumlah varian/tipe rumah yang akan dikembangkan. Wajib diputuskan untuk menyusun brief produk.",
    "lp": "Perkiraan harga tanah bruto per m² untuk simulasi kelayakan biaya; ganti dengan harga transaksi atau appraisal setempat.",
    "infra": "Anggaran prasarana per unit, misalnya jalan lingkungan dan jaringan utilitas. Masukkan sesuai estimasi proyek.",
    "permit": "Anggaran per unit untuk perizinan dan legal. Masukkan estimasi proyek; bukan tarif resmi.",
    "margin": "Target margin sebagai persentase pendapatan penjualan. Ini asumsi kelayakan proyek, bukan standar teknis atau ketentuan hukum.",
    "kdb": "Koefisien Dasar Bangunan: batas persentase lahan yang boleh tertutup tapak bangunan. Ambil nilai yang berlaku dari RDTR/KRK/KKPR atau dokumen daerah; bukan angka default aplikasi.",
    "klb": "Koefisien Lantai Bangunan: rasio batas total luas lantai terhadap luas lahan. Verifikasi nilai setempat pada RDTR/KRK/KKPR.",
    "kdh": "Koefisien Dasar Hijau minimum: persentase lahan yang harus berupa area hijau sesuai definisi aturan setempat. Verifikasi pada RDTR.",
    "gsb": "Garis Sempadan Bangunan depan: jarak minimum bangunan dari batas/garis yang ditetapkan aturan. Ukur menurut dokumen tata ruang setempat.",
    "gsbl": "Jarak bebas bangunan ke batas samping kiri kavling. Ikuti RDTR/Perda; bila belum diketahui, aplikasi dapat memakai asumsi perhitungan saja.",
    "gsbr": "Jarak bebas bangunan ke batas samping kanan kavling. Ikuti RDTR/Perda; bila belum diketahui, aplikasi dapat memakai asumsi perhitungan saja.",
    "gsbb": "Jarak bebas bangunan ke batas belakang kavling. Ikuti RDTR/Perda; nilai asumsi aplikasi bukan ketentuan yang berlaku.",
    "gsj": "Garis Sempadan Jalan diukur dari as/sumbu jalan sesuai ketentuan setempat. Periksa definisi dan jarak pada RDTR/Perda.",
    "mf": "Jumlah lantai maksimum yang diizinkan (KBG/ketentuan intensitas setempat). Hitung jumlah tingkat sesuai definisi dokumen daerah.",
    "mh": "Batas tinggi bangunan maksimum dalam meter menurut aturan setempat. Pastikan titik ukur (misalnya ke atap/puncak) mengikuti dokumen yang berlaku.",
    "dz": "Perkiraan beda elevasi tertinggi dan terendah pada lahan. Gunakan hasil ukur topografi bila tersedia.",
    "lat": "Lintang lokasi dalam derajat desimal; nilai negatif menunjukkan belahan selatan. Contoh Bandung sekitar -6,9°.",
    "lon": "Bujur lokasi dalam derajat desimal; nilai timur Greenwich positif. Dipakai untuk analisis orientasi matahari.",
    "fill": "Ketebalan material timbunan pada lahan, dalam meter. Isi bila kondisi tanah dipilih sebagai timbunan; konfirmasi dengan survei.",
}

REGULATION_CONFIRMATION_HELP = {
    "kdb": "Centang setelah nilai KDB dicocokkan dengan dokumen tata ruang resmi yang berlaku untuk lokasi proyek.",
    "klb": "Centang setelah nilai KLB dicocokkan dengan dokumen tata ruang resmi yang berlaku untuk lokasi proyek.",
    "gsb": "Centang setelah GSB dan jarak bebas bangunan dicocokkan dengan RDTR/Perda atau dokumen resmi setempat.",
    "gsj": "Centang setelah jarak sempadan jalan dan acuan pengukuran dari as jalan dicocokkan dengan dokumen resmi.",
    "ktg": "Centang setelah ketentuan jumlah lantai/tinggi bangunan dicocokkan dengan dokumen resmi setempat.",
    "kdh": "Centang setelah batas minimum area hijau/KDH dicocokkan dengan dokumen tata ruang resmi setempat.",
}

ROOM_QUESTION_HELP = {
    "kt_utama": "Tentukan jumlah kamar tidur utama. Acuan minimum pada katalog: 9 m² (Kepmen Kimpraswil 403/KPTS/M/2002).",
    "kt_anak": "Tentukan jumlah kamar tidur anak/tamu. Acuan katalog 7,2 m²; konfigurasi ruang tetap perlu memenuhi kebutuhan penghuni.",
    "km": "Tentukan jumlah dan lokasi kamar mandi. Acuan minimum katalog 1,8 m² (Kepmen Kimpraswil 403/KPTS/M/2002).",
    "r_tamu": "Putuskan apakah ruang tamu terpisah atau menyatu dengan ruang lain. Acuan luas katalog 7,2 m²; ukuran bukan pengganti pemeriksaan desain.",
    "r_keluarga": "Putuskan hubungan ruang keluarga dengan ruang tamu. Luas katalog minimum 9 m² adalah acuan praktik.",
    "r_makan": "Putuskan apakah ruang makan menyatu dengan dapur/ruang keluarga. Luas katalog minimum 4,5 m² adalah acuan praktik.",
    "dapur": "Putuskan kebutuhan dapur bersih dan/atau kotor. Luas katalog minimum 4,5 m² adalah acuan praktik; katalog menandai ukuran dapur sebagai praktik.",
    "dapur_kotor": "Tentukan apakah perlu dapur kotor terpisah. Luas katalog minimum 3 m² adalah acuan praktik.",
    "musholla": "Putuskan apakah perlu ruang ibadah khusus atau area serbaguna. Kebutuhan luas bergantung pada kapasitas dan tata letak.",
    "carport": "Tentukan jumlah mobil yang ditampung. Acuan satu ruang parkir mobil pada katalog adalah sekitar 2,5 × 5 m; cek kebutuhan bukaan dan sirkulasi.",
    "taman": "Tentukan kebutuhan area taman/outdoor. Pemenuhan KDH dihitung terpisah menurut definisi aturan setempat.",
    "r_kerja": "Putuskan apakah perlu ruang kerja khusus atau fungsi ruang lain dapat dipakai. Luas katalog merupakan acuan praktik.",
    "r_art": "Putuskan kebutuhan ruang ART/servis. Acuan katalog 7,5 m² bersumber dari dimensi ruang servis Kepmen 403; sesuaikan fungsi.",
    "gudang": "Tentukan kebutuhan penyimpanan dan ukuran minimum. Luas katalog adalah acuan praktik.",
    "r_cuci": "Putuskan area cuci/jemur terbuka atau tertutup. Luas katalog adalah acuan praktik dan menyesuaikan kebutuhan.",
    "teras": "Tentukan kebutuhan teras/entrance. Luas katalog adalah acuan praktik; persyaratan pencahayaan mengacu SNI 03-6575.",
}


def _p() -> PreDesignProject:
    if K + "project" not in st.session_state:
        p = PreDesignProject()
        p.init_default_program()
        st.session_state[K + "project"] = p
    return st.session_state[K + "project"]


def _format_id_number(value, decimals: int = 2) -> str:
    formatted = f"{abs(float(value or 0)):,.{decimals}f}"
    integer, separator, fraction = formatted.partition(".")
    integer = integer.replace(",", ".")
    formatted = f"{integer},{fraction}" if separator else integer
    return f"-{formatted}" if value is not None and value < 0 else formatted


def _parse_id_number(text: str) -> Optional[float]:
    text = text.strip().replace(" ", "")
    if not text:
        return None

    sign = ""
    if text[:1] in ("+", "-"):
        sign, text = text[0], text[1:]
    if not text:
        return None

    if "," in text:
        if text.count(",") != 1:
            return None
        integer, fraction = text.split(",", 1)
        if "." in integer:
            groups = integer.split(".")
            if not (1 <= len(groups[0]) <= 3 and all(len(group) == 3 for group in groups[1:])):
                return None
            integer = "".join(groups)
        if not integer.isdigit() or (fraction and not fraction.isdigit()):
            return None
        normalized = f"{sign}{integer}.{fraction or '0'}"
    elif "." in text:
        groups = text.split(".")
        if (
            1 <= len(groups[0]) <= 3
            and all(len(group) == 3 for group in groups[1:])
        ):
            normalized = sign + "".join(groups)
        elif len(groups) == 2 and groups[0].isdigit() and groups[1].isdigit():
            normalized = f"{sign}{groups[0]}.{groups[1]}"
        else:
            return None
    else:
        if not text.isdigit():
            return None
        normalized = sign + text

    try:
        return float(normalized)
    except ValueError:
        return None


def _format_num_input(key: str, decimals: int) -> None:
    parsed = _parse_id_number(st.session_state[key])
    if parsed is not None:
        st.session_state[key] = _format_id_number(parsed, decimals)


def _number_help(key: str) -> str:
    if key.startswith("q_"):
        room_id = key[2:]
        return (
            ROOM_QUESTION_HELP.get(room_id, "Jumlah unit ruang yang dimasukkan ke dalam program.")
            + " Isi 0 bila tidak diperlukan; jumlah ini menjadi masukan estimasi luas."
        )
    try:
        return NUMERIC_HELP[key]
    except KeyError as exc:
        raise KeyError(f"Tooltip angka Pre-Design belum didefinisikan untuk field {key!r}.") from exc


def _num(label, key, value, *, container=st, decimals=2, **kw):
    number_format = kw.pop("format", None)
    kw.pop("step", None)
    if number_format and "." in number_format:
        precision = number_format.rsplit(".", 1)[1]
        if precision.endswith("f") and precision[:-1].isdigit():
            decimals = int(precision[:-1])
    min_value = kw.pop("min_value", None)
    max_value = kw.pop("max_value", None)
    widget_key = K + key
    if widget_key not in st.session_state:
        st.session_state[widget_key] = _format_id_number(value, decimals)
    text = container.text_input(
        label,
        key=widget_key,
        on_change=_format_num_input,
        args=(widget_key, decimals),
        help=_number_help(key),
        **kw,
    )
    if not text.strip():
        return None
    parsed = _parse_id_number(text)
    if parsed is None:
        container.warning(f"{label}: masukkan angka dengan format Indonesia, misalnya 1.000.000.000,00.")
        return value
    if (min_value is not None and parsed < min_value) or (max_value is not None and parsed > max_value):
        container.warning(f"{label}: nilai harus antara {min_value or 0} dan {max_value or 'tanpa batas'}.")
        return value
    return parsed


def _int(v):
    return int(v) if v else None


def render() -> None:
    p = _p()
    st.subheader("Pre-Design Perumahan Tapak")
    st.caption("Brief produk, parameter regulasi, dan kondisi tapak. Nilai KDB/KLB/GSB/GSJ/KTG/KDH wajib dari RDTR setempat.")
    st.caption("Format angka: titik untuk pemisah ribuan dan koma untuk desimal, misalnya 1.000.000.000,00.")
    t11, t12, t13, t21, t22, thasil = st.tabs(["1.1 Pembeli", "1.2 Produk", "1.3 Program Ruang", "2.1 Regulasi", "2.2 Tapak", "Hasil"])

    with t11:
        pe = p.persona
        c1, c2 = st.columns(2)
        pe.age_min = _int(_num("Usia min", "age_min", pe.age_min, decimals=0, step=1.0))
        pe.age_max = _int(_num("Usia maks", "age_max", pe.age_max, decimals=0, step=1.0))
        pe.household_size = _int(_num("Jumlah penghuni (jiwa)", "hh", pe.household_size, decimals=0, step=1.0))
        pe.children = _int(_num("Jumlah anak", "kids", pe.children, decimals=0, step=1.0))
        pe.monthly_income_idr = _num("Penghasilan rumah tangga / bulan (Rp)", "inc", pe.monthly_income_idr, decimals=0, step=500_000.0)
        pe.cars = _int(_num("Jumlah mobil", "cars", pe.cars, decimals=0, step=1.0))
        pe.motorcycles = _int(_num("Jumlah motor", "motor", pe.motorcycles, decimals=0, step=1.0))
        tags = st.text_input(
            "Gaya hidup (pisah koma, mis. wfh, mobilitas tinggi)",
            ", ".join(pe.lifestyle_tags),
            key=K + "tags",
            help="Masukkan kebutuhan yang memengaruhi ruang, misalnya wfh atau mobilitas tinggi. Pisahkan beberapa tag dengan koma.",
        )
        pe.lifestyle_tags = [t.strip().lower() for t in tags.split(",") if t.strip()]
        pe.aesthetic = st.text_input(
            "Preferensi estetika",
            pe.aesthetic or "",
            key=K + "aes",
            help="Catat gaya/karakter desain yang disukai calon pembeli; gunakan sebagai brief, bukan klasifikasi regulasi.",
        ) or None
        pe.price_sensitivity = st.text_input(
            "Sensitivitas harga",
            pe.price_sensitivity or "",
            key=K + "ps",
            help="Ringkas tingkat prioritas harga dibanding luas, lokasi, dan spesifikasi berdasarkan sasaran pasar.",
        ) or None

    with t12:
        pr = p.product
        pr.target_price_idr = _num("Harga jual target (Rp)", "price", pr.target_price_idr, step=10_000_000.0)
        pr.land_area_m2 = _num("Luas tanah (m²)", "lt", pr.land_area_m2, step=1.0)
        pr.lot_width_m = _num("Lebar kavling (m)", "lw", pr.lot_width_m, step=0.5)
        pr.lot_depth_m = _num("Kedalaman kavling (m)", "ld", pr.lot_depth_m, step=0.5)
        pr.target_gfa_m2 = _num("Luas bangunan target (m²)", "lb", pr.target_gfa_m2, step=1.0)
        pr.num_types = _int(_num("Jumlah tipe (KRITIS)", "ntype", pr.num_types, step=1.0))
        idx = FINISHING.index(pr.finishing_class) if pr.finishing_class in FINISHING else 1
        pr.finishing_class = st.selectbox(
            "Kelas finishing (KRITIS)",
            FINISHING,
            index=idx,
            key=K + "fin",
            help="Kelas standar/menengah/atas memilih asumsi luas rekomendasi ruang dan biaya. Ini klasifikasi internal awal, bukan standar mutu bangunan resmi.",
        )
        st.markdown("**Biaya konstruksi maks./m² (KRITIS)** — hitung mundur dari harga jual")
        a, b, c = st.columns(3)
        land_price = _num("Harga tanah bruto (Rp/m²)", "lp", 3_000_000.0, container=a, decimals=0, step=100_000.0) or 0.0
        infra = _num("Prasarana per unit (Rp)", "infra", 0.0, container=b, decimals=0, step=1_000_000.0) or 0.0
        permit = _num("Perizinan/legal per unit (Rp)", "permit", 0.0, container=c, decimals=0, step=1_000_000.0) or 0.0
        margin = st.slider(
            "Margin target (% dari pendapatan)",
            0.0,
            30.0,
            12.0,
            key=K + "margin",
            help="Asumsi target laba sebagai bagian dari pendapatan penjualan untuk simulasi batas biaya. Bukan standar teknis atau ketentuan hukum.",
        )
        if pr.target_price_idr and pr.land_area_m2 and (pr.target_gfa_m2 or 0) > 0:
            r = fin.solve_max_construction_cost(fin.CostSolveInputs(
                price_idr=pr.target_price_idr, gfa_m2=pr.target_gfa_m2, land_area_m2=pr.land_area_m2,
                land_price_gross_per_m2_idr=land_price, infrastructure_per_unit_idr=infra,
                permits_legal_per_unit_idr=permit, target_margin_pct=margin))
            st.metric(
                "Usulan biaya konstruksi maks.",
                f"Rp {r.max_construction_per_m2_idr:,.0f} / m²".replace(",", "."),
                help="Hasil simulasi dari harga jual, biaya tanah, prasarana/legal, luas bangunan, dan margin target. Periksa asumsi serta harga lokal sebelum dijadikan keputusan.",
            )
            st.caption(f"Kelas setara: {fin.classify_cost_per_m2(r.max_construction_per_m2_idr)} · porsi tanah {r.land_share_of_price:.0%}")
            for wmsg in r.warnings:
                st.warning(wmsg)
            if st.button(
                "Pakai usulan ini sebagai keputusan",
                key=K + "usecost",
                help="Salin hasil simulasi ke parameter biaya konstruksi maksimum proyek. Nilai tetap perlu ditinjau dan disetujui tim.",
            ):
                pr.max_construction_cost_per_m2_idr = float(r.max_construction_per_m2_idr)
        if pr.max_construction_cost_per_m2_idr:
            st.success(f"Keputusan biaya konstruksi maks.: Rp {pr.max_construction_cost_per_m2_idr:,.0f}/m²".replace(",", "."))

    with t13:
        st.caption("Gunakan tanda tanya pada nama ruang, jumlah, dan jawaban untuk melihat panduan. Centang memasukkan ruang ke estimasi; kosong berarti belum disetujui.")
        for r_ in p.program:
            c1, c2, c3 = st.columns([4, 1, 2])
            catalog_room = room_catalog().get(r_.room_id, {})
            room_source = catalog_room.get("source", "")
            room_minimum = catalog_room.get("min_area_m2")
            room_help = ROOM_QUESTION_HELP.get(
                r_.room_id,
                "Tentukan apakah ruang ini termasuk dalam brief dan estimasi kebutuhan hunian.",
            )
            if room_minimum:
                room_help += f" Minimum katalog {room_minimum:g} m²/unit. "
            if room_source:
                room_help += f"Basis katalog: {room_source}. "
            if r_.question:
                room_help += f"Pertanyaan keputusan: {r_.question}"
            ok = c1.checkbox(
                f"{r_.name}  ·  {r_.priority}",
                value=bool(r_.approved),
                key=K + "ap_" + r_.room_id,
                help=room_help,
            )
            r_.approved = ok
            r_.qty = int(_num(
                "qty", "q_" + r_.room_id, r_.qty, container=c2, decimals=0,
                min_value=0, max_value=10,
            ) or 0)
            r_.answer = c3.text_input(
                "Jawaban",
                r_.answer,
                key=K + "an_" + r_.room_id,
                placeholder=r_.question,
                help=f"Catat keputusan untuk ruang ini. Pertanyaan panduan: {r_.question or 'jelaskan kebutuhan khusus atau asumsi ruang.'}",
            )

    with t21:
        rg = p.regulation
        c1, c2, c3 = st.columns(3)
        with c1:
            rg.kdb_pct = _num("KDB maks (%)", "kdb", rg.kdb_pct, step=1.0)
            rg.klb = _num("KLB maks (× LT)", "klb", rg.klb, step=0.1)
            rg.kdh_pct = _num("KDH min (%)", "kdh", rg.kdh_pct, step=1.0)
        with c2:
            rg.gsb_front_m = _num("GSB depan (m)", "gsb", rg.gsb_front_m, step=0.5)
            rg.gsb_side_left_m = _num("Jarak bebas samping kiri (m)", "gsbl", rg.gsb_side_left_m, step=0.5)
            rg.gsb_side_right_m = _num("Jarak bebas samping kanan (m)", "gsbr", rg.gsb_side_right_m, step=0.5)
            rg.gsb_rear_m = _num("Jarak bebas belakang (m)", "gsbb", rg.gsb_rear_m, step=0.5)
        with c3:
            rg.gsj_from_axis_m = _num("GSJ dari as jalan (m)", "gsj", rg.gsj_from_axis_m, step=0.5)
            rg.max_floors = _int(_num("KTG: lantai maks", "mf", rg.max_floors, step=1.0))
            rg.max_height_m = _num("KTG: tinggi maks (m)", "mh", rg.max_height_m, step=0.5)
        rg.source = st.text_input(
            "Sumber (RDTR/KKPR/PBG)",
            rg.source,
            key=K + "src",
            help="Cantumkan nama dokumen, wilayah, nomor/tanggal, dan pasal atau lampiran tempat angka regulasi ditemukan.",
        )
        st.markdown("**Dikonfirmasi ke RDTR?**")
        cols = st.columns(6)
        for col, k in zip(cols, load("regulation_defaults")["confirmation_keys"]):
            rg.confirmed[k] = col.checkbox(
                k.upper(),
                value=rg.confirmed.get(k, False),
                key=K + "cf_" + k,
                help=REGULATION_CONFIRMATION_HELP[k],
            )
        if p.product.land_area_m2 and rg.kdb_pct:
            try:
                e = reg.analyze(p.product, rg, p.site)
                st.info(f"Footprint cap **{e.footprint_cap_m2:.1f} m²** · GFA cap **{e.gfa_cap_m2:.1f} m²** · KLB efektif **{e.klb_effective:.2f}** · RTH min **{e.min_green_m2:.1f} m²**")
                for n in e.notes:
                    st.caption("ℹ️ " + n)
            except ValueError as ex:
                st.warning(str(ex))

    with t22:
        s = p.site
        c1, c2 = st.columns(2)
        with c1:
            s.front_orientation = st.selectbox("Hadap lahan", COMPASS8, index=COMPASS8.index(s.front_orientation) if s.front_orientation in COMPASS8 else 7, key=K + "fo",
                                               format_func=lambda c: {"U": "Utara", "TL": "Timur Laut", "T": "Timur", "TG": "Tenggara", "S": "Selatan", "BD": "Barat Daya", "B": "Barat", "BL": "Barat Laut"}[c],
                                               help="Pilih arah sisi depan kavling. Arah ini membantu analisis orientasi fasad dan paparan matahari.")
            tops = ["datar", "landai", "miring"]
            s.topography = st.selectbox(
                "Kontur",
                tops,
                index=tops.index(s.topography) if s.topography in tops else 0,
                key=K + "top",
                help="Klasifikasikan bentuk permukaan lahan dari survei/topografi. Untuk lahan miring, ukur beda elevasi.",
            )
            s.level_difference_m = _num("Beda tinggi (m)", "dz", s.level_difference_m, step=0.1)
            s.best_view = st.text_input(
                "View terbaik",
                s.best_view,
                key=K + "view",
                help="Sebutkan objek/pemandangan yang ingin diprioritaskan, misalnya taman atau pegunungan.",
            )
            s.latitude = _num("Lintang (negatif = selatan)", "lat", s.latitude, step=0.01, format="%.4f")
            s.longitude = _num("Bujur", "lon", s.longitude, step=0.01, format="%.4f")
        with c2:
            soils = ["tanah_asli_baik", "timbunan", "tanah_asli_lunak", "gambut", "tidak_diketahui"]
            s.soil_condition = st.selectbox(
                "Kondisi tanah",
                soils,
                index=soils.index(s.soil_condition) if s.soil_condition in soils else 4,
                key=K + "soil",
                format_func=lambda value: value.replace("_", " ").capitalize(),
                help="Pilih kondisi berdasarkan informasi awal/survei. Klasifikasi ini bukan pengganti penyelidikan geoteknik.",
            )
            s.fill_thickness_m = _num("Tebal timbunan (m)", "fill", s.fill_thickness_m, step=0.1)
            s.soil_tested = st.checkbox(
                "Uji tanah (sondir/boring) sudah ada",
                value=bool(s.soil_tested),
                key=K + "tested",
                help="Centang jika tersedia laporan uji tanah lapangan, misalnya sondir atau boring; catat hasilnya pada dokumen teknis proyek.",
            )
            opt = [None, *COMPASS8]
            compass_label = lambda value: "Belum diketahui" if value is None else {
                "U": "Utara", "TL": "Timur Laut", "T": "Timur", "TG": "Tenggara",
                "S": "Selatan", "BD": "Barat Daya", "B": "Barat", "BL": "Barat Laut",
            }[value]
            s.vehicle_access_from = st.selectbox(
                "Akses kendaraan dari arah",
                opt,
                index=opt.index(s.vehicle_access_from) if s.vehicle_access_from in opt else 0,
                key=K + "va",
                format_func=compass_label,
                help="Arah sisi kavling yang menjadi akses kendaraan dari jalan. Pilih belum diketahui bila belum disurvei.",
            )
            s.pln_entry_from = st.selectbox(
                "PLN masuk dari arah",
                opt,
                index=opt.index(s.pln_entry_from) if s.pln_entry_from in opt else 0,
                key=K + "pln",
                format_func=compass_label,
                help="Perkiraan sisi masuk sambungan listrik ke kavling; konfirmasi posisi dan kapasitas ke penyedia listrik saat perencanaan.",
            )
            nn = st.text_area(
                "Non-negotiable (satu per baris)",
                "\n".join(s.non_negotiables),
                key=K + "nn",
                help="Daftar kebutuhan yang tidak boleh dihilangkan dari brief, satu hal per baris, misalnya akses kursi roda atau kamar di lantai dasar.",
            )
            s.non_negotiables = [x.strip() for x in nn.splitlines() if x.strip()]

    with thasil:
        fnd = validate_project(p)
        sev = {"BLOCKER": 0, "WARNING": 0, "INFO": 0}
        for f in fnd:
            sev[f.severity.value] += 1
        a, b, c = st.columns(3)
        a.metric("BLOCKER", sev["BLOCKER"]); b.metric("WARNING", sev["WARNING"]); c.metric("INFO", sev["INFO"])
        for f in fnd:
            if f.severity.value == "INFO":
                continue
            (st.error if f.severity.value == "BLOCKER" else st.warning)(f"**{f.rule_id} · {f.section}** — {f.message}" + (f"  \n_Rujukan: {f.reference}_" if f.reference else ""))
        with st.expander("Berita acara lengkap (markdown)"):
            md = build_report(p)
            st.markdown(md)
            st.download_button("Unduh berita acara (.md)", md, file_name="berita_acara_predesign.md", key=K + "dl_md")

        from modules.arsitektur import predesign_export

        completeness = p.completeness()
        env = None
        try:
            env = creg.analyze(p.product, p.regulation, p.site)
        except ValueError:
            pass
        program_result = (
            cprog.compute_program(
                p,
                floors=env.floors_effective if env and env.floors_effective else None,
            )
            if p.program
            else None
        )
        xlsx = predesign_export.build_excel(p, fnd, completeness, env, program_result)
        pdf = predesign_export.build_pdf(p, fnd, completeness, env, program_result)
        st.markdown("### Unduh laporan")
        excel_col, pdf_col, _ = st.columns([1, 1, 2])
        excel_col.download_button(
            "Unduh Excel (.xlsx)",
            xlsx,
            file_name="Laporan_Predesign.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=K + "dl_xlsx",
        )
        pdf_col.download_button(
            "Unduh PDF",
            pdf,
            file_name="Laporan_Predesign.pdf",
            mime="application/pdf",
            key=K + "dl_pdf",
        )
