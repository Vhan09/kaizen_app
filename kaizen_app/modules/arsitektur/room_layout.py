"""Generate conceptual, non-scale room-zoning diagrams for pre-design reports."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


@dataclass
class FloorPlanImage:
    floor: int
    png: bytes


_COLORS = {
    "publik": (222, 235, 247),
    "semi-privat": (226, 239, 218),
    "privat": (252, 228, 214),
    "servis": (255, 242, 204),
    "luar": (217, 234, 211),
}
_ORDER = (
    "carport", "teras", "r_tamu", "r_keluarga", "musholla", "r_makan",
    "r_kerja", "kt_utama", "kt_anak", "km", "dapur", "dapur_kotor",
    "r_art", "gudang", "r_cuci", "taman",
)
_FRONT_ORDER = {"U": "Utara", "TL": "Timur Laut", "T": "Timur", "TG": "Tenggara",
                "S": "Selatan", "BD": "Barat Daya", "B": "Barat", "BL": "Barat Laut"}


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    font_path = Path("C:/Windows/Fonts") / font_name
    try:
        return ImageFont.truetype(str(font_path), size)
    except OSError:
        return ImageFont.load_default()


def _floor_rooms(
    program_result: Any,
    floors: int,
    floor_programs: dict[int, Any] | None = None,
) -> dict[int, list[dict[str, Any]]]:
    result = {floor: [] for floor in range(1, floors + 1)}
    if floor_programs is not None:
        for floor, floor_result in floor_programs.items():
            if floor not in result:
                continue
            for line in floor_result.lines:
                result[floor].append({
                    "room_id": line.room_id,
                    "name": line.name,
                    "qty": line.qty,
                    "area": line.unit_area_m2,
                    "total_area": line.total_m2,
                    "zone": line.zone,
                })
        upper_floors = range(2, floors + 1)
        for floor in upper_floors:
            stair_area = program_result.stairs_m2 / max(1, floors - 1)
            result[floor].append({
                "room_id": "tangga",
                "name": "Tangga / sirkulasi vertikal",
                "qty": 1,
                "area": stair_area,
                "total_area": stair_area,
                "zone": "servis",
            })
        return result

    upper_floors = list(range(2, floors + 1))
    private_ids = {"kt_utama", "kt_anak"}
    private_index = 0
    for line in program_result.lines:
        room = {
            "room_id": line.room_id,
            "name": line.name,
            "qty": line.qty,
            "area": line.unit_area_m2,
            "total_area": line.total_m2,
            "zone": line.zone,
        }
        if upper_floors and line.room_id in private_ids:
            destination = upper_floors[private_index % len(upper_floors)]
            result[destination].append(room)
            private_index += 1
        elif upper_floors and line.room_id == "km":
            result[upper_floors[0]].append(room)
        else:
            result[1].append(room)
    if upper_floors:
        for floor in upper_floors:
            result[floor].append({
                "room_id": "tangga",
                "name": "Tangga / sirkulasi vertikal",
                "qty": 1,
                "area": program_result.stairs_m2 / max(1, floors - 1),
                "total_area": program_result.stairs_m2 / max(1, floors - 1),
                "zone": "servis",
            })
    for floor_rooms in result.values():
        floor_rooms.sort(key=lambda room: (
            _ORDER.index(room["room_id"]) if room["room_id"] in _ORDER else len(_ORDER),
            room["name"].casefold(),
        ))
    return result


def _draw_floor(floor: int, rooms: list[dict[str, Any]], floors: int, orientation: str) -> bytes:
    columns = 3
    rows = max(1, math.ceil(len(rooms) / columns))
    width, margin = 1500, 72
    card_width, card_height, gap = 430, 164, 22
    grid_height = rows * card_height + max(0, rows - 1) * gap
    height = 290 + grid_height + 135
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    title_font, header_font = _font(38, True), _font(26, True)
    label_font, detail_font, note_font = _font(23, True), _font(20), _font(17)

    draw.text((margin, 35), f"SIMULASI ZONING — LANTAI {floor}", fill=(31, 56, 100), font=title_font)
    front = _FRONT_ORDER.get(orientation, "belum ditentukan")
    draw.text(
        (margin, 91),
        f"Fasad depan / akses utama: {front}  |  Skema konsep, tidak berskala dan bukan gambar kerja",
        fill=(72, 81, 93),
        font=detail_font,
    )
    draw.rounded_rectangle((margin, 145, width - margin, 202), radius=12, fill=(238, 242, 248))
    draw.text((margin + 18, 160), "JALAN / AKSES UTAMA", fill=(31, 56, 100), font=header_font)
    draw.text((width - margin - 62, 158), f"{orientation or '?'}", fill=(31, 56, 100), font=header_font)

    start_y = 226
    if not rooms:
        draw.text((margin, start_y), "Belum ada ruang yang disetujui untuk lantai ini.", fill=(80, 80, 80), font=detail_font)
    for index, room in enumerate(rooms):
        row, col = divmod(index, columns)
        x = margin + col * (card_width + gap)
        y = start_y + row * (card_height + gap)
        color = _COLORS.get(room["zone"], (238, 242, 248))
        draw.rounded_rectangle(
            (x, y, x + card_width, y + card_height),
            radius=14,
            fill=color,
            outline=(100, 112, 128),
            width=2,
        )
        label = room["name"]
        if len(label) > 34:
            label = label[:31] + "..."
        draw.text((x + 16, y + 18), label, fill=(31, 41, 55), font=label_font)
        draw.text(
            (x + 16, y + 65),
            f"{room['area']:.1f} m2/unit  x {room['qty']}  ({room['total_area']:.1f} m2)",
            fill=(55, 65, 81),
            font=detail_font,
        )
        draw.text(
            (x + 16, y + 112),
            room["zone"].replace("-", " ").upper(),
            fill=(72, 81, 93),
            font=note_font,
        )

    legend_y = start_y + grid_height + 32
    draw.text(
        (margin, legend_y),
        "Zona: publik · semi-privat · privat · servis · luar. Atas = muka/akses. Verifikasi matahari dan sirkulasi dengan arsitek.",
        fill=(72, 81, 93),
        font=note_font,
    )
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def build_floor_plans(
    program_result: Any,
    floors: int,
    orientation: str,
    *,
    floor_programs: dict[int, Any] | None = None,
) -> list[FloorPlanImage]:
    """Build one conceptual PNG zoning diagram for each planned floor."""
    floors = max(1, min(int(floors), 5))
    rooms_by_floor = _floor_rooms(program_result, floors, floor_programs)
    return [
        FloorPlanImage(floor=floor, png=_draw_floor(floor, rooms, floors, orientation))
        for floor, rooms in rooms_by_floor.items()
    ]
