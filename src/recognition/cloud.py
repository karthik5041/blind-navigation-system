"""
cloud.py - AWS Rekognition object detection client
Submits JPEG frames to AWS Rekognition DetectLabels API and returns
structured detection results for audio feedback.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional
import boto3
from botocore.exceptions import ClientError, EndpointResolutionError

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    label: str
    confidence: float
    parents: list[str]  # e.g., ["Vehicle", "Transportation"]
    timestamp: float = 0.0

    def __str__(self) -> str:
        return f"{self.label} ({self.confidence:.0f}%)"


class RekognitionClient:
    """
    Thin wrapper around AWS Rekognition DetectLabels.
    Handles retries, error classification, and metric emission.
    """

    def __init__(
        self,
        region: str = "us-east-1",
        max_labels: int = 10,
        min_confidence: float = 75.0,
        max_retries: int = 2,
    ):
        self.region = region
        self.max_labels = max_labels
        self.min_confidence = min_confidence
        self.max_retries = max_retries

        self._client = boto3.client("rekognition", region_name=region)
        self._call_count = 0
        self._error_count = 0
        self._total_latency = 0.0

        logger.info(f"RekognitionClient initialized (region={region}, min_confidence={min_confidence})")

    def detect(self, image_bytes: bytes) -> list[Detection]:
        """
        Submit raw JPEG bytes to Rekognition DetectLabels.
        Returns sorted list of Detection objects (highest confidence first).
        Retries up to max_retries on transient errors.
        """
        for attempt in range(self.max_retries + 1):
            try:
                start = time.monotonic()
                response = self._client.detect_labels(
                    Image={"Bytes": image_bytes},
                    MaxLabels=self.max_labels,
                    MinConfidence=self.min_confidence,
                )
                latency = time.monotonic() - start

                self._call_count += 1
                self._total_latency += latency
                logger.debug(f"Rekognition call #{self._call_count} completed in {latency:.2f}s")

                return self._parse_response(response)

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code in ("ThrottlingException", "ServiceUnavailableException"):
                    wait = 2 ** attempt
                    logger.warning(f"Rekognition throttled (attempt {attempt+1}), retrying in {wait}s")
                    time.sleep(wait)
                else:
                    # Non-retryable error (e.g., InvalidImageFormatException)
                    self._error_count += 1
                    logger.error(f"Rekognition ClientError [{error_code}]: {e}")
                    return []

            except (EndpointResolutionError, ConnectionError) as e:
                logger.warning(f"Network error on attempt {attempt+1}: {e}")
                if attempt < self.max_retries:
                    time.sleep(1.0)
                else:
                    self._error_count += 1
                    raise

        return []

    def _parse_response(self, response: dict) -> list[Detection]:
        """Extract Detection objects from raw Rekognition API response."""
        detections = []
        for label in response.get("Labels", []):
            parents = [p["Name"] for p in label.get("Parents", [])]
            detections.append(
                Detection(
                    label=label["Name"],
                    confidence=label["Confidence"],
                    parents=parents,
                    timestamp=time.time(),
                )
            )
        # Sort by confidence descending
        return sorted(detections, key=lambda d: d.confidence, reverse=True)

    @property
    def avg_latency_ms(self) -> float:
        if self._call_count == 0:
            return 0.0
        return (self._total_latency / self._call_count) * 1000

    @property
    def error_rate(self) -> float:
        total = self._call_count + self._error_count
        return self._error_count / max(1, total)

    def health_check(self) -> bool:
        """Lightweight connectivity check — detect on a 1x1 white pixel JPEG."""
        try:
            # Minimal valid JPEG (1x1 white pixel)
            _PIXEL = (
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
                b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
                b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
                b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e\x1b"
                b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
                b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
                b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xf5\x0f\xff\xd9"
            )
            self._client.detect_labels(
                Image={"Bytes": _PIXEL}, MaxLabels=1, MinConfidence=99.0
            )
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
