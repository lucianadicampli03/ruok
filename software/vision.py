"""Phone/webcam feed for the Siri page. Does not drive wheels.

Person-only YOLO is a badge on screen. ESP32 JSON still owns the robot.
"""

from __future__ import annotations

import sys
import threading
import time


class Eyes:
    def __init__(self, camera: int | str = 0):
        self.camera = camera
        self.person = False
        self.running = False
        self.error = ""
        self.jpeg = b""
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.running = False

    def snapshot(self) -> bytes:
        with self._lock:
            return self.jpeg

    def _loop(self) -> None:
        try:
            import cv2
            from ultralytics import YOLO
        except ImportError:
            self.error = "pip install ultralytics opencv-python"
            print("Vision off:", self.error)
            return
        try:
            model = YOLO("yolov8n.pt")
            source = self.camera
            if isinstance(source, int) and sys.platform == "darwin":
                cap = cv2.VideoCapture(source, cv2.CAP_AVFOUNDATION)
            else:
                cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                self.error = f"camera {self.camera} would not open"
                print("Vision off:", self.error)
                if sys.platform == "darwin":
                    print(
                        "Mac camera permission: System Settings → Privacy & Security → Camera\n"
                        "  turn ON Terminal (and Cursor if you run from here).\n"
                        "Iriun: open the Mac Iriun app AND the phone app, then use --camera 0 or 1\n"
                        "  (not an http URL — Iriun is a webcam, not a website)."
                    )
                return
            print("Vision on — person class only")
            while self.running:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.1)
                    continue
                result = model.predict(frame, verbose=False, classes=[0], conf=0.45)[0]
                self.person = len(result.boxes) > 0
                ok_jpg, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if ok_jpg:
                    with self._lock:
                        self.jpeg = buf.tobytes()
                time.sleep(0.08)
            cap.release()
        except Exception as exc:
            self.error = str(exc)
            print("Vision failed:", exc)
            self.person = False
