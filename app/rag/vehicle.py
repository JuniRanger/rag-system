import re

VEHICLE_BRANDS = (
    "hyundai", "tesla", "toyota", "honda", "ford", "chevrolet", "nissan", "bmw",
    "audi", "mercedes", "volkswagen", "kia", "mazda", "subaru", "jeep", "dodge",
    "ram", "gmc", "lexus", "infiniti", "acura", "volvo", "porsche", "fiat",
    "peugeot", "renault", "seat", "suzuki", "mitsubishi", "isuzu",
)

_PROBLEM_RE = re.compile(
    r"\b(?:falla|fallo|problema|ruido|jaloneo|patina|vibra|no arranca|se apaga|fuga|fuga de"
    r"|código|codigo|dtc|check engine|luz de motor|transmisión|transmision|freno|embrague)\b",
    re.IGNORECASE,
)

_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")


def _normalize_vehicle_key(vehicle: str) -> str:
    return re.sub(r"\s+", " ", vehicle.strip().lower())


def extract_vehicle(message: str) -> str | None:
    """Extrae una descripción breve de vehículo mencionado en el mensaje."""
    text = message.strip()
    lowered = text.lower()

    for brand in VEHICLE_BRANDS:
        if brand not in lowered:
            continue

        start = lowered.find(brand)
        snippet = text[start : start + 80]
        year_match = _YEAR_RE.search(snippet)
        if year_match:
            return _normalize_vehicle_key(snippet[: year_match.end()])

        words = snippet.split()[:4]
        return _normalize_vehicle_key(" ".join(words))

    return None


def vehicles_are_different(current: str | None, previous: str) -> bool:
    if not current or not previous:
        return False
    return _normalize_vehicle_key(current) != _normalize_vehicle_key(previous)


def extract_problem(message: str) -> str | None:
    if not _PROBLEM_RE.search(message):
        return None

    sentence = message.strip()
    if len(sentence) > 180:
        return sentence[:180].strip()
    return sentence
