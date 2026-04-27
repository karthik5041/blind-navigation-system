"""
subscriber.py - AWS IoT Core MQTT subscriber
Listens for Rekognition results on blindnav/results topic
and passes detections to the audio feedback engine.
"""
import json
import logging
import threading
from typing import Callable, Optional
from awscrt import mqtt
from awsiot import mqtt_connection_builder

logger = logging.getLogger(__name__)
TOPIC_RESULTS = "blindnav/results"

class IoTSubscriber:
    def __init__(self, config, on_result: Callable):
        self.config    = config
        self.on_result = on_result
        self._connection = None
        self._connected  = False

    def connect(self):
        self._connection = mqtt_connection_builder.mtls_from_path(
            endpoint=self.config.endpoint,
            cert_filepath=self.config.cert_path,
            pri_key_filepath=self.config.key_path,
            ca_filepath=self.config.ca_path,
            client_id=f"{self.config.client_id}-sub",
            clean_session=False,
            keep_alive_secs=30,
        )
        self._connection.connect().result(timeout=10.0)
        self._connected = True
        subscribe_future, _ = self._connection.subscribe(
            topic=TOPIC_RESULTS,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self._on_message,
        )
        subscribe_future.result(timeout=5.0)
        logger.info(f"Subscribed to {TOPIC_RESULTS}")

    def _on_message(self, topic, payload, **kwargs):
        try:
            data = json.loads(payload.decode("utf-8"))
            labels = data.get("labels", [])
            logger.debug(f"Received {len(labels)} labels from cloud")
            self.on_result(labels)
        except Exception as e:
            logger.error(f"Failed to parse result message: {e}")

    def disconnect(self):
        if self._connection and self._connected:
            self._connection.disconnect().result(timeout=5.0)
            self._connected = False
        logger.info("IoT Subscriber disconnected")
