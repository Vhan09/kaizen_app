"""Simpan / muat data input per bidang (format JSON)."""
import json
import logging
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_LOGGER = logging.getLogger(__name__)


def _path(name: str, domain: str = "mep") -> Path:
    return DATA_DIR / domain / f"{name}.json"


def load(name: str, default=None, *, domain: str = "mep"):
    p = _path(name, domain)
    if not p.exists() and domain == "mep":
        p = DATA_DIR / f"{name}.json"
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save(name: str, payload, *, domain: str = "mep") -> bool:
    teks = json.dumps(payload, ensure_ascii=False, indent=2)
    p = _path(name, domain)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and p.read_text(encoding="utf-8") == teks:
            return True
        tmp = p.with_suffix(".tmp")
        tmp.write_text(teks, encoding="utf-8")
        tmp.replace(p)
    except OSError:
        _LOGGER.exception("Gagal menyimpan data %s ke %s", name, p)
        return False
    return True


def delete(name: str, *, domain: str = "mep") -> None:
    try:
        _path(name, domain).unlink(missing_ok=True)
        if domain == "mep":
            (DATA_DIR / f"{name}.json").unlink(missing_ok=True)
    except OSError:
        pass


def df_to_records(df: pd.DataFrame) -> list:
    return json.loads(df.to_json(orient="records"))
