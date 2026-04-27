"""
preprocessor.py - Frame preprocessing before cloud submission.
Handles resizing, noise reduction, and brightness normalization.
"""
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class FramePreprocessor:
    def __init__(self, target_size=(640, 480), denoise=False):
        self.target_size = target_size
        self.denoise     = denoise

    def process(self, frame: np.ndarray) -> np.ndarray:
        # Resize
        if frame.shape[:2][::-1] != self.target_size:
            frame = cv2.resize(frame, self.target_size, interpolation=cv2.INTER_AREA)
        # Brightness normalization
        frame = self._normalize_brightness(frame)
        # Optional denoise (slower, better accuracy in low light)
        if self.denoise:
            frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)
        return frame

    def _normalize_brightness(self, frame: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv[:, :, 2] = cv2.equalizeHist(hsv[:, :, 2])
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    def crop_center(self, frame: np.ndarray, ratio=0.8) -> np.ndarray:
        h, w = frame.shape[:2]
        ch, cw = int(h * ratio), int(w * ratio)
        y, x = (h - ch) // 2, (w - cw) // 2
        return frame[y:y+ch, x:x+cw]
