"""
publisher.py - AWS IoT Core MQTT publisher
Sends compressed frames to IoT Core topic over mutual TLS.
Designed for low-latency edge-to-cloud transport on Raspberry Pi.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import base64

from awscrt import mqtt
from awsiot import mqtt_connection_builder

logger = logging.getLogger(__name__)

TOPIC_FRAMES = "blindnav/frames"
TOPIC_RESULTS = "blindnav/results"
TOPIC_HEALTH  = "blindnav/health"


@dataclass
class IoTConfig:
    endpoint: str
    cert_path: str
    key_path: str
    ca_path: str = "/etc/ssl/certs/AmazonRootCA1.pem"
    client_id: str = ""
    keep_alive_secs: int = 30

    def __post_init__(self):
        if not self.client_id:
            self.client_id = f"blindnav-{uuid.uuid4().hex[:8]}"


class IoTPublisher:
    """
    Publishes encoded frames to AWS IoT Core via MQTT over TLS.
    Handles reconnection transparently using the AWS CRT library.
    """

    def __init__(self, config: IoTConfig):
        self.config = config
        self._connection: Optional[mqtt.Connection] = None
        self._connected = False
        self._published = 0
        self._failed = 0

    def connect(self) -> None:
        """Establish MQTT connection with X.509 client auth."""
        for path in [self.config.cert_path, self.config.key_path]:
            if not Path(path).exists():
                raise FileNotFoundError(f"Certificate not found: {path}")

        self._connection = mqtt_connection_builder.mtls_from_path(
            endpoint=self.config.endpoint,
            cert_filepath=self.config.cert_path,
            pri_key_filepath=self.config.key_path,
            ca_filepath=self.config.ca_path,
            client_id=self.config.client_id,
            clean_session=False,
            keep_alive_secs=self.config.keep_alive_secs,
            on_connection_interrupted=self._on_interrupted,
            on_connection_resumed=self._on_resumed,
        )

        connect_future = self._connection.connect()
        connect_future.result(timeout=10.0)
        self._connected = True
        logger.info(f"Connected to IoT Core as {self.config.client_id}")

    def publish_frame(self, frame_bytes: bytes, device_id: str = "rpi-001") -> bool:
        """
        Publish a JPEG frame as base64-encoded MQTT payload.
        Returns True on successful enqueue.
        """
        if not self._connected:
            logger.warning("Not connected — skipping frame publish")
            self._failed += 1
            return False

        payload = {
            "device_id": device_id,
            "timestamp": time.time(),
            "frame": base64.b64encode(frame_bytes).decode("utf-8"),
            "frame_size": len(frame_bytes),
        }

        try:
            future, _ = self._connection.publish(
                topic=TOPIC_FRAMES,
                payload=json.dumps(payload),
                qos=mqtt.QoS.AT_LEAST_ONCE,
            )
            future.result(timeout=5.0)
            self._published += 1
            return True

        except Exception as e:
            logger.error(f"Publish failed: {e}")
            self._failed += 1
            return False

    def publish_health(self, metrics: dict) -> None:
        """Send periodic heartbeat with device metrics."""
        if not self._connected:
            return
        payload = {"timestamp": time.time(), **metrics}
        self._connection.publish(
            topic=TOPIC_HEALTH,
            payload=json.dumps(payload),
            qos=mqtt.QoS.AT_MOST_ONCE,
        )

    def _on_interrupted(self, connection, error, **kwargs) -> None:
        logger.warning(f"MQTT connection interrupted: {error}")
        self._connected = False

    def _on_resumed(self, connection, return_code, session_present, **kwargs) -> None:
        logger.info(f"MQTT connection resumed (return_code={return_code})")
        self._connected = True

    def disconnect(self) -> None:
        if self._connection and self._connected:
            disconnect_future = self._connection.disconnect()
            disconnect_future.result(timeout=5.0)
            self._connected = False
        logger.info(f"IoT Publisher disconnected. published={self._published}, failed={self._failed}")
