#!/usr/bin/env python3
"""RUOK laptop brain — run this on the HP with the ESP32 plugged in.

  python software/brain.py
  python software/brain.py --demo
  python software/brain.py --port COM4
  python software/brain.py --vision
  python software/brain.py --demo          # Siri page + fake sensors
"""

from __future__ import annotations

import warnings

warnings.filterwarnings("ignore", message=".*optree.*")

import argparse
import json
import queue
import sys
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import ttk

from agents import AgentOut, greeter, pilot, watch
from resources import maps_url, pick
from serial_link import SerialLink, list_ports
from situation import Situation, parse_packet
from speak import speak, voice_engine
from vision import Eyes
from webapp import serve as serve_siri

TALK_MIN_CM = 40
TALK_MAX_CM = 160
UNSAFE_CM = 30
# ESP32 analog is 0-4095. Wet rain boards usually drop when water hits the pad.
# Flip RAIN_WET_ABOVE if your module goes up when wet.
RAIN_WET_BELOW = 1500
DARK_BELOW = 800

class Brain:
    def __init__(
        self,
        link: SerialLink | None,
        eyes: Eyes | None = None,
        require_person: bool = False,
    ):
        self.link = link
        self.eyes = eyes
        self.require_person = require_person
        self.state = "idle"
        self.need = None
        self.last_sit = Situation()
        self.last_greet = 0.0
        self.last_stop_line = 0.0
        self.events: queue.Queue[str] = queue.Queue()
        self.place_label = ""

    def send(self, cmd: str) -> None:
        if self.link:
            self.link.send(cmd)

    def apply(self, out: AgentOut | None, speak_out: bool = True) -> None:
        if not out:
            return
        if out.cmd:
            self.send(out.cmd)
        if out.line:
            if speak_out:
                speak(out.line)
            who = out.agent or "brain"
            self.events.put(f"{who}: {out.line}")

    def choose_need(self, need: str, speak_out: bool = True) -> None:
        self.need = need
        sit = self.last_sit
        veto = watch(sit)
        if veto:
            self.apply(veto, speak_out=speak_out)
            self.send("beep")
            self.state = "talking"
            return
        out = greeter(sit, need)
        self.apply(out, speak_out=speak_out)
        place = pick("shelter" if need in ("walk", "wet") else need)
        if place:
            self.place_label = f"{place['name']} — {place['address']}"
            self.events.put("place: " + self.place_label)
        self.state = "guiding" if need == "walk" and not sit.wet else "helping"

    def on_packet(self, raw: dict) -> None:
        person = self.eyes.person if self.eyes else None
        sit = parse_packet(
            raw,
            talk_min=TALK_MIN_CM,
            talk_max=TALK_MAX_CM,
            unsafe_cm=UNSAFE_CM,
            rain_wet_below=RAIN_WET_BELOW,
            dark_below=DARK_BELOW,
            person=person,
            require_person=self.require_person,
        )
        self.last_sit = sit
        now = time.time()

        veto = watch(sit)
        if veto:
            if now - self.last_stop_line > 4:
                self.apply(veto)
                self.send("beep")
                self.last_stop_line = now
            else:
                self.send("stop")
            if self.state in ("approaching", "guiding"):
                self.state = "talking" if sit.in_talk_range else "idle"
            return

        if self.state == "idle":
            move = pilot(sit, self.state)
            if move:
                self.apply(move)
                self.state = "approaching"
                self.events.put("pilot: approaching")
        elif self.state == "approaching":
            move = pilot(sit, self.state)
            if sit.in_talk_range:
                self.apply(move or AgentOut(cmd="stop", agent="pilot"))
                self.state = "talking"
                if now - self.last_greet > 8:
                    self.apply(greeter(sit, None))
                    self.last_greet = now
            elif not sit.someone:
                self.apply(move or AgentOut(cmd="stop", agent="pilot"))
                self.state = "idle"
        elif self.state == "talking":
            if sit.tapped and now - self.last_greet > 2:
                self.choose_need("food")
            if not sit.someone and not sit.in_talk_range:
                self.state = "idle"
                self.apply(greeter(sit, "bye"))
        elif self.state == "guiding":
            self.apply(pilot(sit, self.state))
            if sit.tapped:
                self.send("stop")
                self.state = "talking"
                self.apply(greeter(sit, None))
                self.last_greet = now


def build_ui(brain: Brain) -> tk.Tk:
    root = tk.Tk()
    root.title("RUOK")
    root.configure(bg="#111111")
    root.geometry("780x580")

    title = tk.Label(
        root,
        text="are you okay?",
        fg="#f4f1ea",
        bg="#111111",
        font=("Helvetica", 28, "bold"),
    )
    title.pack(pady=(18, 8))

    status = tk.Label(root, text="idle", fg="#9ad0b8", bg="#111111", font=("Helvetica", 14))
    status.pack()
    sensors = tk.Label(root, text="", fg="#cfc8bc", bg="#111111", font=("Menlo", 12), justify="left")
    sensors.pack(pady=8)
    place = tk.Label(root, text="", fg="#e2c27a", bg="#111111", font=("Helvetica", 13), wraplength=720)
    place.pack(pady=(0, 6))

    log = tk.Text(root, height=8, bg="#1c1c1c", fg="#e8e2d6", insertbackground="#e8e2d6")
    log.pack(fill="both", expand=True, padx=16, pady=8)

    btns = ttk.Frame(root)
    btns.pack(pady=12)

    def press(need: str) -> None:
        brain.choose_need(need)
        url = maps_url("shelter" if need == "walk" else need)
        if url:
            webbrowser.open(url)
        log.insert("end", f"need → {need}\n")
        log.see("end")

    for label, key in (
        ("Food", "food"),
        ("Medicine", "meds"),
        ("Shelter", "shelter"),
        ("Walk with me", "walk"),
    ):
        tk.Button(
            btns,
            text=label,
            width=16,
            height=2,
            font=("Helvetica", 14, "bold"),
            command=lambda k=key: press(k),
        ).pack(side="left", padx=6)

    def tick() -> None:
        sit = brain.last_sit
        status.config(
            text=f"{brain.state}   need={brain.need or '—'}   voice={voice_engine()}"
        )
        sensors.config(
            text=(
                f"pir={int(sit.pir)}  person={sit.person}  us={sit.us_cm}cm  "
                f"obstacle={int(sit.obstacle)}  touch={int(sit.touch)}\n"
                f"rain={sit.rain}  light={sit.light}  humidity={sit.humidity}  "
                f"temp={sit.temp_c}  vibe={int(sit.vibe)}  wet={sit.wet} dark={sit.dark}"
            )
        )
        place.config(text=brain.place_label)
        try:
            while True:
                log.insert("end", brain.events.get_nowait() + "\n")
                log.see("end")
        except queue.Empty:
            pass
        root.after(150, tick)

    tick()
    return root


def run_console(brain: Brain) -> None:
    print("Console mode (this Mac's Tk crashes). Type food / meds / shelter / walk / quit")
    print("Voice:", voice_engine())
    last_state = ""
    while True:
        try:
            while True:
                print(brain.events.get_nowait())
        except queue.Empty:
            pass
        if brain.state != last_state:
            sit = brain.last_sit
            print(
                f"[{brain.state}] pir={int(sit.pir)} us={sit.us_cm} "
                f"need={brain.need or '—'} {brain.place_label}"
            )
            last_state = brain.state
        # Non-blocking-ish input: only check stdin every loop if the user typed
        if sys.stdin in select_stdin():
            line = sys.stdin.readline().strip().lower()
            if line in ("q", "quit", "exit"):
                return
            if line in ("food", "meds", "shelter", "walk"):
                brain.choose_need(line)
                url = maps_url("shelter" if line == "walk" else line)
                if url:
                    print("maps:", url)
        time.sleep(0.15)


def select_stdin():
    import select

    if sys.platform.startswith("win"):
        return [sys.stdin] if False else []
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    return ready


def packet_loop(brain: Brain, demo: bool) -> None:
    t = 0.0
    while True:
        if demo:
            t += 0.2
            fake = {
                "pir": 1 if t > 1 else 0,
                "us_cm": 200 if t < 3 else 90,
                "obstacle": 0,
                "touch": 0,
                "light": 2000,
                "rain": 2500,
                "humidity": 48,
                "temp_c": 26,
                "vibe": 0,
            }
            brain.on_packet(fake)
            time.sleep(0.2)
            continue
        line = brain.link.read_line() if brain.link else None
        if not line:
            time.sleep(0.02)
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        brain.on_packet(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="RUOK brain")
    parser.add_argument("--port", help="COM4 on the HP, or leave blank to auto-pick")
    parser.add_argument("--demo", action="store_true", help="No ESP32 — fake a person walking up")
    parser.add_argument("--vision", action="store_true", help="Webcam/phone YOLO person detect")
    parser.add_argument(
        "--camera",
        default="0",
        help="0 for a USB webcam, or a phone URL like http://192.168.0.12:4747/video",
    )
    parser.add_argument(
        "--require-person",
        action="store_true",
        help="Only approach when PIR and YOLO both see a person",
    )
    parser.add_argument("--ui", action="store_true", help="Old button window")
    parser.add_argument("--no-ui", action="store_true", help="Terminal only")
    parser.add_argument("--web", action="store_true", help="Siri page (default)")
    parser.add_argument("--http-port", type=int, default=8765)
    args = parser.parse_args()

    eyes = None
    if args.vision:
        cam = int(args.camera) if str(args.camera).isdigit() else args.camera
        eyes = Eyes(cam)
        eyes.start()

    link = None
    if not args.demo:
        port = args.port or SerialLink.autodetect()
        if not port:
            print("No serial port found. Plug the ESP32 into the HP, or use --demo")
            print("Ports:", ", ".join(list_ports()) or "(none)")
            return 1
        print("Opening", port)
        link = SerialLink(port)
        link.open()

    brain = Brain(link, eyes=eyes, require_person=args.require_person)
    threading.Thread(target=packet_loop, args=(brain, args.demo), daemon=True).start()
    print("Voice:", voice_engine())
    if args.no_ui:
        run_console(brain)
    elif args.ui:
        print("Button window. Close Serial Monitor first.")
        build_ui(brain).mainloop()
    else:
        httpd = serve_siri(brain, port=args.http_port)
        url = f"http://127.0.0.1:{httpd.server_port}"
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        print("Siri page:", url)
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            httpd.shutdown()
    if link:
        link.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
