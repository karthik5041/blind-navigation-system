"""
tts.py - Text-to-speech audio feedback engine
Converts detected object labels into spoken audio using pyttsx3 (offline)
or gTTS (online). Implements cooldown to avoid repeating same objects.
"""

import logging
import queue
import threading
import time
from collections import defaultdict
from typing import Optional

import pyttsx3

logger = logging.getLogger(__name__)


class AudioFeedback:
    """
    Asynchronous TTS engine with deduplication cooldown.
    Runs speech synthesis in a background thread to avoid blocking
    the main detection loop.
    """

    def __init__(
        self,
        rate: int = 150,
        volume: float = 0.9,
        cooldown_secs: float = 2.0,
    ):
        self.rate = rate
        self.volume = volume
        self.cooldown_secs = cooldown_secs

        self._queue: queue.Queue[str] = queue.Queue(maxsize=5)
        self._last_spoken: dict[str, float] = defaultdict(float)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._engine: Optional[pyttsx3.Engine] = None

    def start(self) -> None:
        """Initialize TTS engine and start background speech thread."""
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", self.rate)
        self._engine.setProperty("volume", self.volume)

        voices = self._engine.getProperty("voices")
        if voices:
            # Prefer a female voice if available (clearer for assistive use)
            female = next((v for v in voices if "female" in v.name.lower()), None)
            if female:
                self._engine.setProperty("voice", female.id)

        self._running = True
        self._thread = threading.Thread(target=self._speech_loop, daemon=True)
        self._thread.start()
        logger.info("AudioFeedback engine started")

    def _speech_loop(self) -> None:
        """Drain the speech queue in background thread."""
        while self._running:
            try:
                text = self._queue.get(timeout=0.5)
                logger.debug(f"Speaking: '{text}'")
                self._engine.say(text)
                self._engine.runAndWait()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"TTS error: {e}")

    def announce(self, label: str, confidence: float) -> bool:
        """
        Announce a detected object label.
        Silently drops if the same label was spoken within cooldown_secs.
        Returns True if announcement was queued.
        """
        now = time.monotonic()
        if now - self._last_spoken[label] < self.cooldown_secs:
            return False

        self._last_spoken[label] = now
        text = self._format_announcement(label, confidence)

        try:
            self._queue.put_nowait(text)
            return True
        except queue.Full:
            logger.debug("Speech queue full — dropping announcement")
            return False

    def announce_proximity(self, distance_cm: float) -> None:
        """Speak a proximity warning for ultrasonic sensor trigger."""
        if distance_cm < 50:
            self.announce("obstacle very close", 100.0)
        elif distance_cm < 100:
            self.announce("obstacle ahead", 100.0)

    def _format_announcement(self, label: str, confidence: float) -> str:
        if confidence >= 95:
            return label
        elif confidence >= 85:
            return f"{label} detected"
        else:
            return f"possible {label}"

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._engine:
            self._engine.stop()
        logger.info("AudioFeedback engine stopped")
