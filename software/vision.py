"""Optional phone/webcam eyes. Person-only YOLO. Sensors still work if this dies."""

from __future__ import annotations

import threading
import time


class Eyes:
    def __init__(self, camera: int = 0):
        self.camera = camera
        self.person = False
        self.running = False
        self.error = ""
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.running = False

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
            cap = cv2.VideoCapture(self.camera)
            if not cap.isOpened():
                self.error = f"camera {self.camera} would not open"
                print("Vision off:", self.error)
                return
            print("Vision on — person class only")
            while self.running:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.1)
                    continue
                result = model.predict(frame, verbose=False, classes=[0], conf=0.45)[0]
                self.person = len(result.boxes) > 0
                time.sleep(0.08)
            cap.release()
        except Exception as exc:
            self.error = str(exc)
            print("Vision failed:", exc)
            self.person = False
