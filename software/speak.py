"""Speak a line. ElevenLabs if ELEVENLABS_API_KEY is set, else Windows/Mac voice."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

from envload import load_env

load_env()

DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs Rachel — swap in .env


def voice_engine() -> str:
    if os.environ.get("ELEVENLABS_API_KEY"):
        return "elevenlabs"
    if sys.platform.startswith("win"):
        return "windows"
    if shutil.which("say"):
        return "mac"
    return "print"


def speak(text: str) -> None:
    threading.Thread(target=_speak_sync, args=(text,), daemon=True).start()


def _speak_sync(text: str) -> None:
    print("RUOK:", text)
    if os.environ.get("ELEVENLABS_API_KEY"):
        try:
            _elevenlabs(text)
            return
        except Exception as exc:
            print("ElevenLabs failed, falling back:", exc)
    _local_voice(text)


def _local_voice(text: str) -> None:
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


def _elevenlabs(text: str) -> None:
    key = os.environ["ELEVENLABS_API_KEY"]
    voice = os.environ.get("ELEVENLABS_VOICE_ID") or DEFAULT_VOICE
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    body = (
        '{"text":%s,"model_id":"eleven_turbo_v2_5","voice_settings":{"stability":0.5,"similarity_boost":0.7}}'
        % _json_str(text)
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        audio = resp.read()
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    with open(path, "wb") as fh:
        fh.write(audio)
    _play_mp3(path)


def _json_str(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _play_mp3(path: str) -> None:
    if shutil.which("afplay"):
        subprocess.run(["afplay", path], check=False)
        return
    if sys.platform.startswith("win"):
        uri = Path_uri(path)
        cmd = (
            "Add-Type -AssemblyName presentationCore; "
            "$p = New-Object System.Windows.Media.MediaPlayer; "
            f"$p.Open([Uri]'{uri}'); $p.Play(); "
            "while (-not $p.NaturalDuration.HasTimeSpan) { Start-Sleep -Milliseconds 80 }; "
            "$ms = [int]$p.NaturalDuration.TimeSpan.TotalMilliseconds + 200; "
            "Start-Sleep -Milliseconds $ms; $p.Close()"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=False)
        return
    if shutil.which("ffplay"):
        subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path], check=False)
        return
    time.sleep(0.2)


def Path_uri(path: str) -> str:
    return "file:///" + path.replace("\\", "/").replace("'", "''")
