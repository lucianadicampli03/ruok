from __future__ import annotations

import sys
import time

import serial
from serial.tools import list_ports as _list_ports


def list_ports() -> list[str]:
    return [p.device for p in _list_ports.comports()]


class SerialLink:
    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.ser: serial.Serial | None = None
        self._buf = ""

    @staticmethod
    def autodetect() -> str | None:
        ports = list(_list_ports.comports())
        prefer = []
        for p in ports:
            blob = f"{p.device} {p.description} {p.hwid}".lower()
            if any(k in blob for k in ("usb", "uart", "serial", "cp210", "ch340", "wch", "silicon")):
                prefer.append(p.device)
        if prefer:
            return prefer[0]
        if ports:
            # On Windows skip Bluetooth COM ports if we can
            for p in ports:
                if "bluetooth" not in p.description.lower():
                    return p.device
            return ports[0].device
        return None

    def open(self) -> None:
        self.ser = serial.Serial(self.port, self.baud, timeout=0.05)
        time.sleep(1.5)  # ESP32 resets when the port opens
        if self.ser:
            self.ser.reset_input_buffer()

    def close(self) -> None:
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send(self, cmd: str) -> None:
        if not self.ser:
            print("cmd (no serial):", cmd)
            return
        line = cmd.strip() + "\n"
        self.ser.write(line.encode("utf-8"))
        print("→", cmd)

    def read_line(self) -> str | None:
        if not self.ser:
            return None
        chunk = self.ser.read(256).decode("utf-8", errors="ignore")
        if not chunk:
            return None
        self._buf += chunk
        if "\n" not in self._buf:
            return None
        line, self._buf = self._buf.split("\n", 1)
        return line.strip()


if __name__ == "__main__":
    print("platform", sys.platform)
    print("ports", list_ports())
    print("pick", SerialLink.autodetect())
