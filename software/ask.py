"""Turn a spoken/typed question into a Gemini reply using live sensors."""

from __future__ import annotations

from situation import Situation

import gemini


def answer(text: str, sit: Situation, history: list[dict] | None = None) -> dict:
    q = (text or "").strip()
    if not q:
        return {"reply": "I'm listening.", "highlight": [], "need": None}

    try:
        out = gemini.chat(q, sit, history)
        print("Gemini:", out["reply"])
        return out
    except Exception as exc:
        print("Gemini failed, fallback:", exc)
        return {
            "reply": "I heard you. I can help with food, shelter, weather, a hazard, or just sit with you.",
            "highlight": [],
            "need": gemini._guess_need(q),
        }
