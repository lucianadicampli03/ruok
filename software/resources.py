from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
def _load() -> dict[str, list[dict[str, str]]]:
    path = Path(__file__).with_name("resources.json")
    return json.loads(path.read_text(encoding="utf-8"))


def pick(need: str) -> dict[str, str] | None:
    data = _load()
    key = "shelter" if need in ("shelter", "walk", "wet") else need
    if key not in data:
        return None
    return data[key][0]


def spoken(need: str) -> str:
    place = pick(need)
    if not place:
        return ""
    return f"{place['name']} — {place['address']}."


def maps_url(need: str) -> str:
    place = pick(need)
    if not place:
        return ""
    dest = urllib.parse.quote(place["address"])
    return f"https://www.google.com/maps/dir/?api=1&destination={dest}"


def as_prompt(need: str) -> str:
    place = pick(need)
    if not place:
        return ""
    return f"Nearest help: {place['name']} at {place['address']}."
