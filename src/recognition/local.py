"""
local.py - Offline YOLOv5 fallback when AWS connectivity is unavailable.
Automatically activates when cloud detection fails for >5 seconds.
"""
import logging
import time
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LocalDetection:
    label: str
    confidence: float
    bbox: tuple  # (x, y, w, h)
    timestamp: float = 0.0

class LocalDetector:
    """
    YOLOv5 offline detector — activates when cloud is unreachable.
    Requires: pip install ultralytics
    Model: yolov5s.pt (~14MB, auto-downloaded on first run)
    """
    def __init__(self, model_path="yolov5s.pt", confidence=0.5):
        self.model_path = model_path
        self.confidence = confidence
        self._model     = None
        self._loaded    = False
        self._last_fail: float = 0.0

    def load(self):
        try:
            import torch
            self._model  = torch.hub.load("ultralytics/yolov5", "yolov5s", pretrained=True)
            self._model.conf = self.confidence
            self._loaded = True
            logger.info("YOLOv5 local model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLOv5: {e}")
            self._loaded = False

    def detect(self, frame: np.ndarray) -> list[LocalDetection]:
        if not self._loaded:
            logger.warning("Local model not loaded — no detections")
            return []
        try:
            results = self._model(frame)
            detections = []
            for *box, conf, cls in results.xyxy[0].tolist():
                label = results.names[int(cls)]
                x1, y1, x2, y2 = map(int, box)
                detections.append(LocalDetection(
                    label=label,
                    confidence=round(conf * 100, 1),
                    bbox=(x1, y1, x2 - x1, y2 - y1),
                    timestamp=time.time(),
                ))
            return sorted(detections, key=lambda d: d.confidence, reverse=True)
        except Exception as e:
            logger.error(f"Local detection error: {e}")
            return []

    @property
    def is_ready(self) -> bool:
        return self._loaded
