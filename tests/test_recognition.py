"""
tests/test_recognition.py
Unit tests for AWS Rekognition client using moto mocking.
"""

import time
import pytest
from unittest.mock import MagicMock, patch
from src.recognition.cloud import RekognitionClient, Detection


# Minimal JPEG for testing (1x1 white pixel)
SAMPLE_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\xff\xd9"
)

MOCK_RESPONSE = {
    "Labels": [
        {"Name": "Person", "Confidence": 98.5, "Parents": []},
        {"Name": "Car",    "Confidence": 91.2, "Parents": [{"Name": "Vehicle"}]},
        {"Name": "Tree",   "Confidence": 78.0, "Parents": [{"Name": "Plant"}]},
    ]
}


@pytest.fixture
def mock_rekognition_client():
    with patch("boto3.client") as mock_boto:
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.detect_labels.return_value = MOCK_RESPONSE
        yield mock_client


def test_detect_returns_sorted_detections(mock_rekognition_client):
    client = RekognitionClient(min_confidence=75.0)
    results = client.detect(SAMPLE_JPEG)

    assert len(results) == 3
    assert results[0].label == "Person"
    assert results[0].confidence == pytest.approx(98.5)
    # Sorted by confidence descending
    assert results[0].confidence >= results[1].confidence >= results[2].confidence


def test_detect_empty_on_client_error(mock_rekognition_client):
    from botocore.exceptions import ClientError
    mock_rekognition_client.detect_labels.side_effect = ClientError(
        {"Error": {"Code": "InvalidImageFormatException", "Message": "bad image"}},
        "DetectLabels",
    )
    client = RekognitionClient()
    results = client.detect(SAMPLE_JPEG)
    assert results == []


def test_detection_str_format():
    d = Detection(label="Chair", confidence=92.3, parents=["Furniture"])
    assert "Chair" in str(d)
    assert "92" in str(d)


def test_avg_latency_zero_before_calls():
    with patch("boto3.client"):
        client = RekognitionClient()
    assert client.avg_latency_ms == 0.0


def test_parents_parsed_correctly(mock_rekognition_client):
    client = RekognitionClient()
    results = client.detect(SAMPLE_JPEG)
    car = next(r for r in results if r.label == "Car")
    assert "Vehicle" in car.parents
