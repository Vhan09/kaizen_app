"""Simpan / muat data input ke folder data/ (format JSON)."""
import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def load(name: str, default=None):
    p = _path(name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save(name: str, payload) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    teks = json.dumps(payload, ensure_ascii=False, indent=2)
    p = _path(name)
    try:
        if p.exists() and p.read_text(encoding="utf-8") == teks:
            return  # tidak ada perubahan, tidak perlu menulis ulang
        tmp = p.with_suffix(".tmp")
        tmp.write_text(teks, encoding="utf-8")
        tmp.replace(p)
    except OSError:
        pass  # folder read-only: aplikasi tetap jalan tanpa simpan


def delete(name: str) -> None:
    try:
        _path(name).unlink(missing_ok=True)
    except OSError:
        pass


def df_to_records(df: pd.DataFrame) -> list:
    return json.loads(df.to_json(orient="records"))
