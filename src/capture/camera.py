"""
camera.py - Pi Camera capture interface
Captures frames from the Raspberry Pi Camera Module v2 using OpenCV/PiCamera2.
Supports configurable resolution, FPS, and frame skipping for cloud offloading.
"""

import time
import logging
import threading
from dataclasses import dataclass
from typing import Generator, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    resolution: tuple = (640, 480)
    fps: int = 15
    frame_skip: int = 3  # Process every Nth frame
    jpeg_quality: int = 85  # Compression quality for cloud upload


class FrameCapture:
    """
    Thread-safe camera capture with frame buffering.
    Uses a background thread to continuously read frames, exposing only
    the latest frame to consumers — avoiding pipeline stalls.
    """

    def __init__(self, config: CameraConfig):
        self.config = config
        self._cap: Optional[cv2.VideoCapture] = None
        self._latest_frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._dropped_frames = 0

    def start(self) -> None:
        """Open camera and start background capture thread."""
        # Try /dev/video0 first (Pi Camera via libcamera), fallback to index 0
        self._cap = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)
        if not self._cap.isOpened():
            logger.warning("Failed to open /dev/video0, trying index 0")
            self._cap = cv2.VideoCapture(0)

        if not self._cap.isOpened():
            raise RuntimeError("Could not open any camera device")

        w, h = self.config.resolution
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        self._cap.set(cv2.CAP_PROP_FPS, self.config.fps)

        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
        logger.info(f"Camera opened: {actual_w}x{actual_h} @ {actual_fps:.1f}fps")

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self) -> None:
        """Background thread: continuously read frames, keep only latest."""
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Frame read failed — camera disconnected?")
                time.sleep(0.1)
                continue

            with self._lock:
                self._latest_frame = frame
                self._frame_count += 1

    def get_frame(self) -> Optional[np.ndarray]:
        """Return the latest captured frame (non-blocking)."""
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def frames_for_processing(self) -> Generator[np.ndarray, None, None]:
        """
        Generator that yields every Nth frame for cloud submission.
        Skips intermediate frames to reduce API call volume.
        """
        frame_idx = 0
        while self._running:
            frame = self.get_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            frame_idx += 1
            if frame_idx % self.config.frame_skip == 0:
                yield frame
            else:
                self._dropped_frames += 1

            time.sleep(1.0 / self.config.fps)

    def encode_jpeg(self, frame: np.ndarray) -> bytes:
        """
        Encode frame to JPEG bytes for S3/Rekognition upload.
        Quality tuned to balance accuracy vs. bandwidth.
        """
        params = [cv2.IMWRITE_JPEG_QUALITY, self.config.jpeg_quality]
        _, buffer = cv2.imencode(".jpg", frame, params)
        return buffer.tobytes()

    @property
    def stats(self) -> dict:
        return {
            "total_frames": self._frame_count,
            "dropped_frames": self._dropped_frames,
            "effective_rate": self._frame_count / max(1, self._dropped_frames + self._frame_count),
        }

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap:
            self._cap.release()
        logger.info(f"Camera stopped. Stats: {self.stats}")
