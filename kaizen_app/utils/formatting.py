"""Format angka gaya Indonesia: 1.234,56"""


def fmt_id(x, nd: int = 0, kosong_jika_nol: bool = False) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return ""
    if kosong_jika_nol and v == 0:
        return ""
    s = f"{v:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
