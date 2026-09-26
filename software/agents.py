"""Greeter / Pilot / Watch — hook up Google ADK + Gemini after the robot already talks.

Until GEMINI_API_KEY is set, the hard-coded lines in brain.py run the demo.
Agents must return a spoken sentence and a motor command, never a chat window.
"""

from __future__ import annotations

from dataclasses import dataclass

from situation import Situation


@dataclass
class AgentOut:
    line: str | None = None
    cmd: str | None = None  # approach | stop | follow | left | right | beep


def watch(sit: Situation) -> AgentOut | None:
    """Watch always wins."""
    if sit.unsafe or sit.jostled:
        return AgentOut(line="I've got you. I'm stopping.", cmd="stop")
    if sit.wet:
        return AgentOut(cmd="stop")
    return None


def greeter(sit: Situation, need: str | None) -> AgentOut | None:
    if need == "food" and sit.wet:
        return AgentOut(line="It's wet. I will keep the box closed. I can take you somewhere dry.")
    return None


def pilot(sit: Situation, state: str) -> AgentOut | None:
    if state == "approaching" and sit.in_talk_range:
        return AgentOut(cmd="stop")
    if state == "guiding" and not sit.unsafe:
        return AgentOut(cmd="follow")
    return None
