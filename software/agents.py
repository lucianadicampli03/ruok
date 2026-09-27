"""Greeter / Pilot / Watch.

Watch always wins. Greeter writes the spoken line (Gemini if GEMINI_API_KEY is set).
Pilot only emits wheel commands. No chat window.
"""

from __future__ import annotations

from dataclasses import dataclass

from envload import load_env
import gemini
from resources import FOOD_SNACK
from situation import Situation

load_env()

HELLO = "Hello, I am RUOK. Can I help you?"

LINES = {
    "ruok": HELLO,
    "food": FOOD_SNACK,
    "meds": "I can offer what's in the box, or help you find a clinic.",
    "shelter": "I can walk with you toward somewhere dry and safe.",
    "weather": "I can tell you what I feel outside, and help you get out of the heat or rain.",
    "hazard": "Thank you. If anyone is in danger call 911. For a street problem, call 311.",
    "weapon": "Get somewhere safe and call 911. Do not go toward them. I will stay with you.",
    "event": "I can point you to a meal, a giveaway, or today's help nearby.",
    "support": "I hear you. You are not alone. I can stay with you, or you can call 988.",
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
    if need in (None, "ruok"):
        return AgentOut(line=HELLO, cmd="stop", agent="greeter")
    if need == "food":
        return AgentOut(line=FOOD_SNACK, cmd="stop", agent="greeter")
    cmd = "follow" if need == "walk" else "stop"
    return AgentOut(line=_line(sit, need), cmd=cmd, agent="greeter")


def _line(sit: Situation, need: str) -> str:
    asked = {
        "food": "I don't have enough food.",
        "meds": "I need medicine.",
        "shelter": "I need a safe place to stay.",
        "weather": "How's the weather, and where can I get out of it?",
        "hazard": "I need to report a hazard.",
        "weapon": "I saw someone with a weapon.",
        "event": "What's going on nearby that could help me?",
        "support": "I'm not okay. Can you stay with me?",
        "walk": "Walk with me.",
        "wet": "It's wet. I need somewhere dry.",
        "dark": "It's dark. Can you help?",
        "bye": "Thanks, I am okay now.",
        "stop": "Stop.",
    }.get(need or "", "Can you help me?")
    try:
        return gemini.chat(asked, sit)["reply"]
    except Exception as exc:
        print("Gemini failed, canned line:", exc)
        return LINES.get(need or "", HELLO)


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


