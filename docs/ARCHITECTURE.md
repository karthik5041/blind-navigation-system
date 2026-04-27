# System Architecture

## Overview
The Blind Navigation System is a two-tier architecture:
- **Edge tier**: Raspberry Pi 4 handles camera capture, sensor input, and audio output
- **Cloud tier**: AWS handles heavy ML inference via Rekognition

## Data Flow
1. Pi Camera captures frame at 15 FPS
2. Every 3rd frame is JPEG-encoded and published to AWS IoT Core via MQTT/TLS
3. IoT Rule triggers Lambda function
4. Lambda calls AWS Rekognition DetectLabels
5. Results published back to device via MQTT
6. Result handler filters and prioritizes detections
7. TTS engine announces top 3 objects via earpiece

## Component Diagram
See README.md for ASCII architecture diagram.

## Latency Budget
| Step | Time |
|------|------|
| Frame capture + encode | ~50ms |
| MQTT publish | ~80ms |
| Lambda cold start (worst) | ~500ms |
| Rekognition DetectLabels | ~900ms |
| MQTT result delivery | ~80ms |
| TTS synthesis | ~200ms |
| **Total** | **~1.8s avg** |

## Offline Fallback
If AWS IoT connectivity is lost for >5s, the system switches to local YOLOv5 inference.
Accuracy drops from 90%+ to ~75% but the device remains functional.
