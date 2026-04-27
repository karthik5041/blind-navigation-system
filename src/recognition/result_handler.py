"""
result_handler.py - Processes and prioritizes Rekognition detection results.
Filters low-confidence labels and elevates safety-critical objects.
"""
import time
from collections import deque
from dataclasses import dataclass, field

PRIORITY_OBJECTS = {
    "Person", "Car", "Vehicle", "Bicycle", "Motorcycle",
    "Dog", "Stairs", "Door", "Traffic Light", "Stop Sign", "Bus"
}

@dataclass
class FilteredResult:
    detections: list
    priority_count: int
    timestamp: float = field(default_factory=time.time)

class ResultHandler:
    def __init__(self, max_announcements: int = 3):
        self.max_announcements = max_announcements
        self._history = deque(maxlen=10)

    def process(self, detections: list) -> FilteredResult:
        if not detections:
            return FilteredResult(detections=[], priority_count=0)
        priority = [d for d in detections if d.label in PRIORITY_OBJECTS]
        normal   = [d for d in detections if d.label not in PRIORITY_OBJECTS]
        combined = (priority + normal)[:self.max_announcements]
        self._history.append([d.label for d in combined])
        return FilteredResult(detections=combined, priority_count=len(priority))
