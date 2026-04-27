"""
ultrasonic.py - HC-SR04 proximity sensor interface for Raspberry Pi.
Runs in background thread and fires callback when obstacle within threshold.
"""
import threading
import time
import logging

logger = logging.getLogger(__name__)
SPEED_OF_SOUND_CM_S = 34300

class UltrasonicSensor:
    def __init__(self, trigger_pin=23, echo_pin=24, threshold_cm=100.0, on_proximity=None):
        self.trigger_pin  = trigger_pin
        self.echo_pin     = echo_pin
        self.threshold_cm = threshold_cm
        self.on_proximity = on_proximity
        self._running     = False
        self._last_distance = None
        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(trigger_pin, GPIO.OUT)
            GPIO.setup(echo_pin, GPIO.IN)
            GPIO.output(trigger_pin, False)
            time.sleep(0.1)
        except ImportError:
            logger.warning("RPi.GPIO not available — running in simulation mode")
            self._gpio = None

    def _measure(self):
        if not self._gpio:
            return 150.0  # Simulate safe distance
        GPIO = self._gpio
        GPIO.output(self.trigger_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trigger_pin, False)
        start = time.time()
        while GPIO.input(self.echo_pin) == 0:
            if time.time() - start > 0.1: return None
            start = time.time()
        end = time.time()
        while GPIO.input(self.echo_pin) == 1:
            if time.time() - end > 0.1: return None
            end = time.time()
        return round(((end - start) * SPEED_OF_SOUND_CM_S) / 2, 1)

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._running:
            d = self._measure()
            if d and d <= self.threshold_cm and self.on_proximity:
                self.on_proximity(d)
            time.sleep(0.2)

    def stop(self):
        self._running = False
        if self._gpio:
            self._gpio.cleanup()
