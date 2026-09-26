"""Speak a line on the HP (Windows SAPI) or this Mac (`say`). Never blocks the UI."""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading


def speak(text: str) -> None:
    threading.Thread(target=_speak_sync, args=(text,), daemon=True).start()


def _speak_sync(text: str) -> None:
    print("RUOK:", text)
    if sys.platform.startswith("win"):
        safe = text.replace("'", "''")
        cmd = (
            "Add-Type -AssemblyName System.Speech; "
            f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe}')"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    if shutil.which("say"):
        subprocess.run(["say", text], check=False)
        return
    # Last resort: printed only. Swap in ElevenLabs later.
