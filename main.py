"""
main.py - Blind Navigation System entrypoint
Orchestrates camera capture → cloud recognition → audio feedback pipeline.
Designed to run as a systemd service on Raspberry Pi OS.
"""

import logging
import signal
import sys
import time
import yaml
from pathlib import Path

from src.capture.camera import FrameCapture, CameraConfig
from src.recognition.cloud import RekognitionClient
from src.audio.tts import AudioFeedback
from src.cloud.publisher import IoTPublisher, IoTConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/blind-nav/app.log"),
    ],
)
logger = logging.getLogger("blind-nav")


def load_config(path: str = "/etc/blind-nav/config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class BlindNavigationSystem:
    def __init__(self, config: dict):
        self.config = config
        self._shutdown = False

        cam_cfg = config["camera"]
        self.camera = FrameCapture(CameraConfig(
            resolution=tuple(cam_cfg["resolution"]),
            fps=cam_cfg["fps"],
            frame_skip=cam_cfg["frame_skip"],
        ))

        aws_cfg = config["aws"]
        self.rekognition = RekognitionClient(
            region=aws_cfg["region"],
            max_labels=aws_cfg["rekognition"]["max_labels"],
            min_confidence=aws_cfg["rekognition"]["min_confidence"],
        )

        iot_cfg = aws_cfg["iot"]
        self.publisher = IoTPublisher(IoTConfig(
            endpoint=iot_cfg["endpoint"],
            cert_path=iot_cfg["cert_path"],
            key_path=iot_cfg["key_path"],
        ))

        audio_cfg = config["audio"]
        self.audio = AudioFeedback(
            rate=audio_cfg["rate"],
            volume=audio_cfg["volume"],
            cooldown_secs=audio_cfg["cooldown_seconds"],
        )

    def setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame) -> None:
        logger.info(f"Received signal {signum} — initiating graceful shutdown")
        self._shutdown = True

    def run(self) -> None:
        logger.info("Starting Blind Navigation System")

        # Health check before starting
        if not self.rekognition.health_check():
            logger.error("Rekognition health check failed — check AWS credentials and connectivity")
            sys.exit(1)

        self.audio.start()
        self.audio.announce("Navigation system starting", 100.0)

        self.publisher.connect()
        self.camera.start()

        logger.info("All systems ready — entering detection loop")

        try:
            for frame in self.camera.frames_for_processing():
                if self._shutdown:
                    break

                # Encode frame for cloud submission
                jpeg = self.camera.encode_jpeg(frame)

                # Publish to IoT Core (async)
                self.publisher.publish_frame(jpeg)

                # Direct Rekognition call for low-latency feedback
                detections = self.rekognition.detect(jpeg)

                for det in detections[:3]:  # Top 3 most confident objects
                    spoken = self.audio.announce(det.label, det.confidence)
                    if spoken:
                        logger.info(f"Detected: {det}")

                # Periodic health metric push
                if int(time.time()) % 60 == 0:
                    self.publisher.publish_health({
                        "avg_rekognition_latency_ms": self.rekognition.avg_latency_ms,
                        "camera_frames": self.camera.stats["total_frames"],
                        "error_rate": self.rekognition.error_rate,
                    })

        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        logger.info("Shutting down...")
        self.camera.stop()
        self.publisher.disconnect()
        self.audio.stop()
        logger.info("Shutdown complete")


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "/etc/blind-nav/config.yaml"
    if not Path(config_path).exists():
        logger.error(f"Config not found: {config_path}")
        sys.exit(1)

    config = load_config(config_path)
    system = BlindNavigationSystem(config)
    system.setup_signal_handlers()
    system.run()


if __name__ == "__main__":
    main()
