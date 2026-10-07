"""Format angka gaya Indonesia: 1.234,56

Pembulatan memakai 'setengah naik' (912,5 -> 913) agar sama dengan Excel.
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def bulatkan(x, nd: int = 0) -> Decimal:
    """Bulatkan setengah naik. Melempar ValueError/InvalidOperation bila bukan angka."""
    return Decimal(str(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)


def fmt_id(x, nd: int = 0, kosong_jika_nol: bool = False) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return ""
    if kosong_jika_nol and v == 0:
        return ""
    try:
        d = bulatkan(v, nd)
    except (InvalidOperation, ValueError):  # NaN / tak hingga
        return ""
    if not d.is_finite():
        return ""
    if d == 0:  # hindari "-0"
        d = abs(d)
    s = f"{d:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")