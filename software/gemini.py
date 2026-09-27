"""Gemini chat for RUOK. Spoken replies come from the model, not canned lines."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from envload import load_env
from resources import FOOD_SNACK, catalog, food_nearby
from situation import Situation

load_env()

MODELS = (
    os.environ.get("GEMINI_MODEL") or "gemini-flash-lite-latest",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemma-4-26b-a4b-it",
)


def _sensors(sit: Situation) -> str:
    bits = [
        f"humidity {sit.humidity:.0f} percent" if sit.humidity >= 0 else "humidity unknown",
        f"{sit.temp_c:.0f} degrees C" if sit.temp_c >= 0 else "temperature unknown",
        "raining or wet" if sit.wet else "dry",
        "dark" if sit.dark else "enough light",
        f"{sit.us_cm} centimeters away" if sit.us_cm >= 0 else "distance unknown",
        "someone is nearby" if sit.someone else "no motion",
    ]
    return "; ".join(bits)


def _places() -> str:
    lines = []
    for kind, rows in catalog().items():
        for row in rows[:2]:
            lines.append(f"{kind}: {row['name']} at {row['address']}")
    return " | ".join(lines)


def enabled() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def generate(prompt: str, max_tokens: int = 80) -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("no GEMINI_API_KEY")
    last = None
    seen = set()
    for model in MODELS:
        if not model or model in seen:
            continue
        seen.add(model)
        try:
            return _call(key, model, prompt, max_tokens)
        except Exception as exc:
            last = exc
            print("Gemini model failed", model, exc)
    raise last or RuntimeError("Gemini failed")


def _call(key: str, model: str, prompt: str, max_tokens: int) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model
        + ":generateContent?key="
        + key
    )
    payload = json.dumps(
        {
            "systemInstruction": {
                "parts": [
                    {
                        "text": (
                            "You are RUOK, a small lunchbox robot in Miami. You are kind, calm, "
                            "and useful. You help with: shelter, weather, food insecurity, "
                            "hazard reports, community events, walking with someone, and "
                            "emotional support. Speak out loud. One or two short sentences. "
                            "No markdown, no lists, no labels. "
                            "If they report a weapon or immediate danger: tell them to get "
                            "somewhere safe and call 911. Never walk toward the danger. "
                            "If they are hurting or scared: stay with them, be gentle, offer 988 "
                            "or 211. Use live sensor numbers for weather. Only name a real "
                            "place if it helps the thing they asked for."
                        )
                    }
                ]
            },
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.6},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST", headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=18) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    cand = (data.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = (parts[0].get("text") if parts else "") or ""
    text = text.strip().strip('"')
    if not text or _looks_like_prompt(text):
        raise RuntimeError("bad Gemini reply")
    return text.split("\n")[0].strip()


def _looks_like_prompt(text: str) -> bool:
    low = text.lower()
    return any(
        s in low
        for s in (
            "need=",
            "nearest help",
            "persona:",
            "constraint",
            "identity:",
            "return only json",
            "system instruction",
        )
    )


def chat(user_text: str, sit: Situation, history: list[dict] | None = None) -> dict:
    history = history or []
    prior = ""
    if history:
        bits = []
        for item in history[-6:]:
            who = "Person" if item.get("role") == "user" else "RUOK"
            bits.append(f"{who}: {item.get('text', '')}")
        prior = "Recent talk:\n" + "\n".join(bits) + "\n\n"
    prompt = (
        f"{prior}"
        f"Live sensors: {_sensors(sit)}.\n"
        f"Real places (only if they ask for help): {_places()}.\n"
        f"Person said: {user_text.strip()}\n"
        "Reply with only the words RUOK should speak."
    )
    need = _guess_need(user_text)
    if need == "food":
        return {
            "reply": FOOD_SNACK,
            "followup": food_nearby(),
            "followup_ms": 5000,
            "need": "food",
            "highlight": [],
        }
    if need == "weapon":
        return {
            "reply": (
                "Thank you for telling me. Get somewhere safe and call 911. "
                "Do not go toward them. I will stay right here with you."
            ),
            "need": "weapon",
            "highlight": [],
        }
    if _crisis(user_text):
        return {
            "reply": (
                "I hear you, and you matter. Please call or text 988 right now. "
                "I can stay with you."
            ),
            "need": "support",
            "highlight": [],
        }
    reply = generate(prompt, max_tokens=110)
    return {
        "reply": reply,
        "need": need,
        "highlight": _highlights(user_text),
    }


def _has(q: str, *words: str) -> bool:
    return any(re.search(r"\b" + re.escape(w) + r"\b", q) for w in words)


def _crisis(text: str) -> bool:
    q = (text or "").lower()
    return any(
        s in q
        for s in (
            "kill myself",
            "suicide",
            "want to die",
            "end my life",
            "don't want to live",
            "dont want to live",
        )
    )


def _guess_need(text: str) -> str | None:
    q = (text or "").lower()
    if any(s in q for s in ("weapon", "gun", "knife", "armed", "shooting")):
        return "weapon"
    if _crisis(q) or "not okay" in q or "not ok" in q:
        return "support"
    if _has(q, "lonely", "scared", "afraid", "sad", "anxious", "panic", "crying"):
        return "support"
    if _has(q, "hazard", "flood", "fire", "unsafe") or "report" in q:
        return "hazard"
    if _has(q, "food", "hungry", "eat", "pantry", "lunch", "meal", "starving"):
        return "food"
    if _has(q, "medicine", "meds", "clinic", "sick", "hospital"):
        return "meds"
    if _has(q, "shelter", "sleep", "homeless", "roof"):
        return "shelter"
    if _has(q, "weather", "rain", "storm", "humid", "hot", "cold", "heat"):
        return "weather"
    if _has(q, "event", "giveaway", "happening"):
        return "event"
    if _has(q, "walk", "guide"):
        return "walk"
    return None


def _highlights(text: str) -> list[str]:
    q = (text or "").lower()
    keys = []
    if any(w in q for w in ("humid", "moisture", "muggy", "weather", "rain")):
        keys.append("humidity")
    if any(w in q for w in ("weather", "temp", "hot", "cold", "degree")):
        keys.append("temp_c")
    if any(w in q for w in ("rain", "wet", "storm")):
        keys.append("rain")
    if any(w in q for w in ("light", "dark", "bright")):
        keys.append("light")
    if any(w in q for w in ("far", "distance", "close", "near")):
        keys.append("us_cm")
    return keys
