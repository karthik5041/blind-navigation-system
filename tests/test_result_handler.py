"""
tests/test_result_handler.py
Unit tests for ResultHandler filtering and prioritization logic.
"""
import pytest
from unittest.mock import MagicMock
from src.recognition.result_handler import ResultHandler, PRIORITY_OBJECTS

def make_detection(label, confidence=90.0):
    d = MagicMock()
    d.label = label
    d.confidence = confidence
    return d

def test_priority_objects_come_first():
    handler = ResultHandler(max_announcements=3)
    detections = [
        make_detection("Tree", 95.0),
        make_detection("Person", 80.0),
        make_detection("Car", 75.0),
    ]
    result = handler.process(detections)
    labels = [d.label for d in result.detections]
    assert labels[0] in PRIORITY_OBJECTS
    assert labels[1] in PRIORITY_OBJECTS

def test_max_announcements_respected():
    handler = ResultHandler(max_announcements=2)
    detections = [make_detection(f"Object{i}", 90.0 - i) for i in range(5)]
    result = handler.process(detections)
    assert len(result.detections) <= 2

def test_empty_detections():
    handler = ResultHandler()
    result = handler.process([])
    assert result.detections == []
    assert result.priority_count == 0

def test_is_new_scene_on_first_call():
    handler = ResultHandler()
    detections = [make_detection("Chair")]
    assert handler.is_new_scene(detections) is True
