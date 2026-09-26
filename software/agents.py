"""Greeter / Pilot / Watch.

Watch always wins. Greeter writes the spoken line (Gemini if GEMINI_API_KEY is set).
Pilot only emits wheel commands. No chat window.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from envload import load_env
from resources import as_prompt, spoken
from situation import Situation

load_env()

LINES = {
    "ruok": "Hey. Are you okay? Food, medicine, or a place to stay?",
    "food": "I can share what's in the box, or walk you toward food.",
    "meds": "I can offer what's in the box, or help you find a clinic.",
    "shelter": "I can walk with you toward somewhere dry and safe.",
    "walk": "Okay. Stay near me and I will go slowly.",
    "wet": "It's wet. I will keep the box closed. I can take you somewhere dry.",
    "dark": "It's dark. I can walk you somewhere with more light.",
    "stop": "I've got you. I'm stopping.",
    "bye": "Okay. I'm here if you need me.",
}


@dataclass
class AgentOut:
    line: str | None = None
    cmd: str | None = None
    agent: str = ""


def watch(sit: Situation) -> AgentOut | None:
    if sit.unsafe or sit.jostled:
        return AgentOut(line=LINES["stop"], cmd="stop", agent="watch")
    return None


def greeter(sit: Situation, need: str | None) -> AgentOut:
    if sit.wet and need in ("food", "meds", None):
        line = _line(sit, "wet") + " " + spoken("shelter")
        return AgentOut(line=line.strip(), cmd="stop", agent="greeter")
    if need == "walk":
        place_need = "shelter" if sit.wet or sit.dark else "food"
        line = _line(sit, "walk") + " " + spoken(place_need)
        if sit.dark:
            line = line + " " + LINES["dark"]
        return AgentOut(line=line.strip(), cmd="follow", agent="greeter")
    if need in ("food", "meds", "shelter"):
        line = _line(sit, need) + " " + spoken(need)
        if sit.dark:
            line = line + " " + LINES["dark"]
        return AgentOut(line=line.strip(), cmd="stop", agent="greeter")
    if need in LINES:
        return AgentOut(line=_line(sit, need), cmd="stop", agent="greeter")
    return AgentOut(line=_line(sit, "ruok"), cmd="stop", agent="greeter")


def _line(sit: Situation, need: str) -> str:
    return _maybe_gemini(sit, need)


def pilot(sit: Situation, state: str) -> AgentOut | None:
    if state == "idle" and sit.someone:
        return AgentOut(cmd="approach", agent="pilot")
    if state == "approaching" and sit.in_talk_range:
        return AgentOut(cmd="stop", agent="pilot")
    if state == "approaching" and not sit.someone:
        return AgentOut(cmd="stop", agent="pilot")
    if state == "guiding" and sit.unsafe:
        return AgentOut(cmd="stop", agent="pilot")
    if state == "guiding":
        if sit.us_cm > 0 and sit.us_cm < 40:
            return AgentOut(cmd="stop", agent="pilot")
        return AgentOut(cmd="follow", agent="pilot")
    return None


def _maybe_gemini(sit: Situation, need: str) -> str:
    fallback = LINES.get(need, LINES["ruok"])
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return fallback
    prompt = (
        "You are RUOK, a small help robot. Say ONE short spoken sentence (max 20 words). "
        "No lists, no emoji, no name-asking. Need=%s. Wet=%s Dark=%s Person=%s. %s"
        % (need, sit.wet, sit.dark, sit.person, as_prompt(need if need in ("food", "meds", "shelter", "wet", "walk") else "food"))
    )
    try:
        return _gemini(key, prompt) or fallback
    except Exception as exc:
        print("Gemini failed, canned line:", exc)
        return fallback


def _gemini(key: str, prompt: str) -> str:
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model
        + ":generateContent?key="
        + key
    )
    payload = json.dumps(
        {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 60}}
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST", headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    return text.split("\n")[0].strip().strip('"')
