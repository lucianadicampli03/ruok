#!/usr/bin/env python3
"""RUOK laptop brain — run this on the HP with the ESP32 plugged in.

  python software/brain.py
  python software/brain.py --demo          # no board, fake sensors
  python software/brain.py --port COM4
"""

from __future__ import annotations

import argparse
import json
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from situation import Situation, parse_packet
from speak import speak
from serial_link import SerialLink, list_ports

TALK_MIN_CM = 40
TALK_MAX_CM = 160
UNSAFE_CM = 30
# ESP32 analog is 0-4095. Wet rain boards usually drop when water hits the pad.
# Flip RAIN_WET_ABOVE if your module goes up when wet.
RAIN_WET_BELOW = 1500
DARK_BELOW = 800

LINES = {
    "ruok": "Hey. Are you okay? Food, medicine, or a place to stay?",
    "food": "I can share what's in the box, or walk you toward a pantry.",
    "meds": "I can offer what's in the box, or help you find a clinic.",
    "shelter": "I can walk with you toward somewhere dry and safe.",
    "walk": "Okay. Stay near me and I will go slowly.",
    "wet": "It's wet. I will keep the box closed. I can take you somewhere dry.",
    "dark": "It's dark. I can walk you somewhere with more light.",
    "stop": "I've got you. I'm stopping.",
    "bye": "Okay. I'm here if you need me.",
}


class Brain:
    def __init__(self, link: SerialLink | None):
        self.link = link
        self.state = "idle"
        self.need = None
        self.last_sit = Situation()
        self.last_greet = 0.0
        self.last_stop_line = 0.0
        self.said_wet = False
        self.events: queue.Queue[str] = queue.Queue()

    def send(self, cmd: str) -> None:
        if self.link:
            self.link.send(cmd)

    def speak_line(self, key: str) -> None:
        speak(LINES[key])
        self.events.put(f"said: {LINES[key]}")

    def choose_need(self, need: str) -> None:
        self.need = need
        self.state = "helping"
        sit = self.last_sit
        if sit.wet:
            self.speak_line("wet")
            self.send("stop")
            return
        if need == "walk":
            self.speak_line("walk")
            if sit.dark:
                self.speak_line("dark")
            self.state = "guiding"
            self.send("follow")
            return
        if sit.dark:
            self.speak_line("dark")
        self.speak_line(need)

    def on_packet(self, raw: dict) -> None:
        sit = parse_packet(
            raw,
            talk_min=TALK_MIN_CM,
            talk_max=TALK_MAX_CM,
            unsafe_cm=UNSAFE_CM,
            rain_wet_below=RAIN_WET_BELOW,
            dark_below=DARK_BELOW,
        )
        self.last_sit = sit
        now = time.time()

        if sit.unsafe or sit.jostled:
            self.send("stop")
            if now - self.last_stop_line > 4:
                self.speak_line("stop")
                self.send("beep")
                self.last_stop_line = now
            if self.state in ("approaching", "guiding"):
                self.state = "talking" if sit.in_talk_range else "idle"
            return

        if self.state == "idle":
            if sit.someone:
                self.state = "approaching"
                self.send("approach")
                self.events.put("PIR — approaching")
        elif self.state == "approaching":
            if sit.in_talk_range:
                self.send("stop")
                self.state = "talking"
                if now - self.last_greet > 8:
                    self.speak_line("ruok")
                    self.last_greet = now
            elif not sit.someone:
                self.send("stop")
                self.state = "idle"
        elif self.state == "talking":
            if sit.tapped and now - self.last_greet > 2:
                self.choose_need("food")
            if not sit.someone and not sit.in_talk_range:
                self.state = "idle"
                self.speak_line("bye")
        elif self.state == "guiding":
            if sit.in_talk_range:
                self.send("follow")
            elif sit.us_cm > 0 and sit.us_cm < TALK_MIN_CM:
                self.send("stop")
            if sit.tapped:
                self.send("stop")
                self.state = "talking"
                self.speak_line("ruok")


def build_ui(brain: Brain) -> tk.Tk:
    root = tk.Tk()
    root.title("RUOK")
    root.configure(bg="#111111")
    root.geometry("720x520")

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

    log = tk.Text(root, height=8, bg="#1c1c1c", fg="#e8e2d6", insertbackground="#e8e2d6")
    log.pack(fill="both", expand=True, padx=16, pady=8)

    btns = ttk.Frame(root)
    btns.pack(pady=12)

    def press(need: str) -> None:
        brain.choose_need(need)
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
        status.config(text=f"{brain.state}   need={brain.need or '—'}")
        sensors.config(
            text=(
                f"pir={int(sit.pir)}  us={sit.us_cm}cm  obstacle={int(sit.obstacle)}  "
                f"touch={int(sit.touch)}  rain={sit.rain}  light={sit.light}\n"
                f"humidity={sit.humidity}  temp={sit.temp_c}  vibe={int(sit.vibe)}  "
                f"wet={sit.wet} dark={sit.dark}"
            )
        )
        try:
            while True:
                log.insert("end", brain.events.get_nowait() + "\n")
                log.see("end")
        except queue.Empty:
            pass
        root.after(150, tick)

    tick()
    return root


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
    args = parser.parse_args()

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

    brain = Brain(link)
    threading.Thread(target=packet_loop, args=(brain, args.demo), daemon=True).start()
    print("RUOK panel open. Close Serial Monitor in Arduino IDE first.")
    build_ui(brain).mainloop()
    if link:
        link.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
