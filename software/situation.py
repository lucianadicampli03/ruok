from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Situation:
    pir: bool = False
    us_cm: int = -1
    obstacle: bool = False
    touch: bool = False
    light: int = 0
    rain: int = 0
    humidity: float = -1
    temp_c: float = -1
    vibe: bool = False
    someone: bool = False
    in_talk_range: bool = False
    unsafe: bool = False
    wet: bool = False
    dark: bool = False
    jostled: bool = False
    tapped: bool = False
    person: bool | None = None
    raw: dict = field(default_factory=dict)


def _num(raw: dict, key: str, default: float = -1) -> float:
    try:
        return float(raw.get(key, default))
    except (TypeError, ValueError):
        return default


def parse_packet(
    raw: dict,
    talk_min: int = 40,
    talk_max: int = 160,
    unsafe_cm: int = 30,
    rain_wet_below: int = 1500,
    dark_below: int = 800,
    person: bool | None = None,
    require_person: bool = False,
) -> Situation:
    pir = int(_num(raw, "pir", 0)) == 1
    us = int(_num(raw, "us_cm", -1))
    obstacle = int(_num(raw, "obstacle", 0)) == 1
    touch = int(_num(raw, "touch", 0)) == 1
    light = int(_num(raw, "light", 0))
    rain = int(_num(raw, "rain", 0))
    humidity = _num(raw, "humidity", -1)
    vibe = int(_num(raw, "vibe", 0)) == 1

    wet = (rain > 0 and rain < rain_wet_below) or (humidity >= 80)
    dark = 0 < light < dark_below
    in_talk = talk_min <= us <= talk_max
    unsafe = obstacle or (0 < us < unsafe_cm)
    # Camera is display-only unless --require-person. Sensors stay in charge.
    if require_person and person is not None:
        someone = pir and person
    else:
        someone = pir

    return Situation(
        pir=pir,
        us_cm=us,
        obstacle=obstacle,
        touch=touch,
        light=light,
        rain=rain,
        humidity=humidity,
        temp_c=_num(raw, "temp_c", -1),
        vibe=vibe,
        someone=someone,
        in_talk_range=in_talk,
        unsafe=unsafe,
        wet=wet,
        dark=dark,
        jostled=vibe,
        tapped=touch,
        person=person,
        raw=raw,
    )
