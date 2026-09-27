"""Turn a spoken/typed question into a reply from the live ESP32 JSON."""

from __future__ import annotations

from situation import Situation

from resources import spoken


def answer(text: str, sit: Situation) -> dict:
    q = (text or "").strip().lower()
    if not q:
        return {"reply": "I'm listening.", "highlight": [], "need": None}

    if any(w in q for w in ("humid", "moisture", "muggy", "damp")):
        h = sit.humidity
        reply = (
            f"Humidity is {h:.0f} percent."
            if h >= 0
            else "I don't have a humidity reading yet."
        )
        if sit.wet:
            reply += " It feels wet out, so I'll keep the box closed."
        return {"reply": reply, "highlight": ["humidity"], "need": None}

    if any(w in q for w in ("weather", "rain", "raining", "wet", "storm")):
        bits = []
        if sit.temp_c >= 0:
            bits.append(f"it's {sit.temp_c:.0f} degrees")
        if sit.humidity >= 0:
            bits.append(f"humidity {sit.humidity:.0f} percent")
        if sit.wet:
            bits.append("and my rain pad is wet")
        elif sit.rain > 0:
            bits.append("and it's dry on my rain sensor")
        if sit.dark:
            bits.append("it's pretty dark")
        reply = ("Right now " + ", ".join(bits) + ".") if bits else "I'm still warming up my weather sensors."
        return {"reply": reply, "highlight": ["humidity", "temp_c", "rain", "light"], "need": None}

    if any(w in q for w in ("temp", "hot", "cold", "degree", "heat")):
        t = sit.temp_c
        reply = f"It's {t:.0f} degrees Celsius." if t >= 0 else "Temperature isn't in yet."
        return {"reply": reply, "highlight": ["temp_c"], "need": None}

    if any(w in q for w in ("light", "dark", "bright", "night")):
        reply = "It's dark here." if sit.dark else "There's enough light."
        return {"reply": reply, "highlight": ["light"], "need": None}

    if any(w in q for w in ("how far", "distance", "close", "near")):
        if sit.us_cm < 0:
            reply = "I can't see a distance right now."
        else:
            reply = f"You're about {sit.us_cm} centimeters away."
        return {"reply": reply, "highlight": ["us_cm"], "need": None}

    if "pir" in q or "motion" in q or "anyone" in q or "someone" in q:
        reply = "Yes, I sense someone nearby." if sit.someone else "I don't see motion right now."
        return {"reply": reply, "highlight": ["pir"], "need": None}

    if any(w in q for w in ("food", "hungry", "eat", "pantry", "lunch")):
        return {"reply": "Food. " + spoken("food"), "highlight": [], "need": "food"}
    if any(w in q for w in ("medicine", "meds", "clinic", "sick", "hurt")):
        return {"reply": "Medicine. " + spoken("meds"), "highlight": [], "need": "meds"}
    if any(w in q for w in ("shelter", "sleep", "homeless", "stay", "roof")):
        return {"reply": "Shelter. " + spoken("shelter"), "highlight": [], "need": "shelter"}
    if "walk" in q or "guide" in q or "follow" in q:
        return {"reply": "I can walk with you. " + spoken("shelter"), "highlight": [], "need": "walk"}

    if "okay" in q or "ruok" in q or "who are you" in q or "hello" in q or "hi" in q:
        return {
            "reply": "Hey. Are you okay? You can ask the weather, or say food, medicine, or shelter.",
            "highlight": [],
            "need": None,
        }

    return {
        "reply": "I can tell you the weather or humidity from my sensors, or help with food, medicine, or shelter.",
        "highlight": ["humidity", "temp_c", "rain"],
        "need": None,
    }
