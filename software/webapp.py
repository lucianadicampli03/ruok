from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ask import answer
from speak import speak, speak_then, voice_engine

SIRI_DIR = Path(__file__).resolve().parent / "siri"


def make_handler(brain):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(body)
            except BrokenPipeError:
                return

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/api/state":
                sit = brain.last_sit
                us = sit.us_cm
                if sit.touch or sit.tapped:
                    hw = "help"
                elif 0 <= us <= 25:
                    hw = "stopped"
                elif us <= 120:
                    hw = "approaching"
                else:
                    hw = "waiting"
                payload = {
                    "state": hw,
                    "need": brain.need,
                    "place": brain.place_label,
                    "voice": voice_engine(),
                    "pir": sit.pir,
                    "someone": sit.someone,
                    "touch": sit.touch,
                    "us_cm": sit.us_cm,
                    "humidity": sit.humidity,
                    "temp_c": sit.temp_c,
                    "rain": sit.rain,
                    "light": sit.light,
                    "wet": sit.wet,
                    "dark": sit.dark,
                    "jostled": sit.jostled,
                    "obstacle": sit.obstacle,
                    "person": sit.person,
                    "has_camera": bool(brain.eyes),
                }
                self._send(200, json.dumps(payload).encode(), "application/json")
                return
            if path == "/api/frame.jpg":
                frame = brain.eyes.snapshot() if brain.eyes else b""
                if not frame:
                    self._send(204, b"", "image/jpeg")
                    return
                self._send(200, frame, "image/jpeg")
                return
            if path not in ("/", "/index.html"):
                self._send(404, b"not found", "text/plain")
                return
            file = SIRI_DIR / "index.html"
            self._send(200, file.read_bytes(), "text/html; charset=utf-8")

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/ask":
                self._send(404, b"no", "text/plain")
                return
            n = int(self.headers.get("Content-Length", "0"))
            raw = json.loads(self.rfile.read(n) or b"{}")
            text = str(raw.get("text") or "")
            out = answer(text, brain.last_sit, getattr(brain, "chat_log", []))
            if text:
                brain.chat_log.append({"role": "user", "text": text})
                brain.chat_log.append({"role": "model", "text": out["reply"]})
            if out.get("need") in ("food", "meds", "shelter", "walk"):
                brain.choose_need(out["need"], speak_out=False, talk=False)
            elif out.get("need") in ("weapon", "hazard"):
                brain.send("stop")
            if not raw.get("client_tts"):
                if out.get("followup"):
                    speak_then(out["reply"], 5, out["followup"])
                elif not out.get("need"):
                    speak(out["reply"])
            brain.events.put("siri: " + out["reply"])
            self._send(200, json.dumps(out).encode(), "application/json")

    return Handler


class _Server(ThreadingHTTPServer):
    allow_reuse_address = True


def serve(brain, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    handler = make_handler(brain)
    last_error = None
    for try_port in range(port, port + 12):
        try:
            return _Server((host, try_port), handler)
        except OSError as exc:
            last_error = exc
            continue
    raise last_error or OSError("could not bind a port")
