"""
tests/test_camera.py
Unit tests for camera capture module using mocked OpenCV.
"""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from src.capture.camera import FrameCapture, CameraConfig

@pytest.fixture
def mock_capture():
    with patch("cv2.VideoCapture") as mock_cv:
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap.get.return_value = 15.0
        mock_cv.return_value = mock_cap
        yield mock_cap

def test_camera_opens_successfully(mock_capture):
    cam = FrameCapture(CameraConfig())
    cam.start()
    assert cam._running is True
    cam.stop()

def test_encode_jpeg_returns_bytes(mock_capture):
    cam = FrameCapture(CameraConfig())
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = cam.encode_jpeg(frame)
    assert isinstance(result, bytes)
    assert len(result) > 0

def test_get_frame_returns_none_before_start():
    cam = FrameCapture(CameraConfig())
    assert cam.get_frame() is None

def test_camera_stats_initial():
    cam = FrameCapture(CameraConfig())
    assert cam.stats["total_frames"] == 0
    assert cam.stats["dropped_frames"] == 0
