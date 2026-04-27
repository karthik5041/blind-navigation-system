# Demo & Usage Guide

## Hardware Setup Photo
```
[Pi Camera] --> [Raspberry Pi 4] --> [Earpiece]
                      |
              [HC-SR04 Sensor]
```

## Sample Output
When the system detects objects, it speaks via TTS:
```
$ sudo systemctl start blind-nav
$ journalctl -u blind-nav -f

[INFO] Camera opened: 640x480 @ 15.0fps
[INFO] Connected to IoT Core as blindnav-a1b2c3d4
[INFO] All systems ready — entering detection loop
[INFO] Detected: Person (98%)
[INFO] Detected: Car (91%)
[INFO] Detected: Traffic Light (85%)
```

## Audio Feedback Examples
| Scene | Spoken Output |
|-------|--------------|
| Person walking toward you | *"Person detected"* |
| Car nearby | *"Car"* |
| Possible chair | *"possible Chair"* |
| Obstacle <50cm | *"obstacle very close"* |

## Running Tests
```bash
pip install -r requirements.txt
pytest tests/ -v --cov=src
```

Expected output:
```
tests/test_camera.py ....      [ 50%]
tests/test_recognition.py .....[ 100%]
9 passed in 1.23s
```

## Performance on Raspberry Pi 4
- Boot to ready: ~8 seconds
- Detection latency: ~1.8s average
- CPU usage: ~35% (one core)
- Memory: ~180MB RSS
- Runs continuously 24/7 via systemd watchdog
