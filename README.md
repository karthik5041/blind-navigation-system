# 🦯 Blind Navigation System using Cloud Computing

> **Real-time object detection and audio feedback system for visually impaired individuals** — Raspberry Pi + AWS Rekognition + IoT pipeline

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![AWS](https://img.shields.io/badge/AWS-Rekognition%20%7C%20S3%20%7C%20IoT-orange)](https://aws.amazon.com)
[![Raspberry Pi](https://img.shields.io/badge/Hardware-Raspberry%20Pi%204-red)](https://raspberrypi.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Overview

This project is a **cloud-powered assistive navigation device** for blind and visually impaired users. A Raspberry Pi captures live video via the Pi Camera, frames are streamed to **AWS Rekognition** for real-time object detection, and the identified objects are converted to **audio feedback** delivered through an earpiece — all in under 2 seconds.

Built as a **Bachelor of Technology capstone project** at KL University (2020–2021) and subsequently modernized with production-grade cloud infrastructure, Terraform IaC, and systemd service management.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Edge Device (RPi 4)                  │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐   │
│  │ Pi Cam   │───▶│ Frame Capture│───▶│ MQTT Publisher│   │
│  │  Module  │    │   (OpenCV)   │    │  (AWS IoT)    │   │
│  └──────────┘    └──────────────┘    └───────┬───────┘   │
└──────────────────────────────────────────────┼──────────-┘
                                               │ TLS/MQTT
                          ┌────────────────────▼─────────────────────┐
                          │              AWS Cloud                    │
                          │  ┌──────────┐    ┌──────────────────────┐ │
                          │  │ IoT Core │───▶│  Lambda Processor    │ │
                          │  └──────────┘    └──────────┬───────────┘ │
                          │                             │             │
                          │  ┌──────────────────────────▼───────────┐ │
                          │  │         AWS Rekognition               │ │
                          │  │   (Object Detection / Scene Labels)  │ │
                          │  └──────────────────────────┬───────────┘ │
                          │                             │             │
                          │  ┌──────────────────────────▼───────────┐ │
                          │  │     S3 (Frame Archive) + DynamoDB    │ │
                          │  │         (Detection Logs)             │ │
                          │  └──────────────────────────────────────┘ │
                          └────────────────────┬─────────────────────-┘
                                               │ Result (MQTT)
                          ┌────────────────────▼──────────────────────┐
                          │              Edge Device (RPi 4)           │
                          │  ┌──────────────┐    ┌────────────────┐   │
                          │  │Result Handler│───▶│ TTS / Audio    │   │
                          │  │  (Subscriber)│    │ (pyttsx3/eSpeak│   │
                          │  └──────────────┘    └────────────────┘   │
                          └───────────────────────────────────────────┘
```

---

## ✨ Features

- **Real-time Object Detection** — 15–30 FPS capture with cloud offloading; results in <2s
- **Cloud-Backed Recognition** — AWS Rekognition eliminates local model training; 90%+ accuracy
- **Audio Feedback** — Text-to-speech announces detected objects with confidence scores
- **Distance Awareness** — Ultrasonic sensor (HC-SR04) integration for proximity alerts
- **Offline Fallback** — Local YOLO v5 model activates if cloud connectivity drops
- **Telemetry & Logging** — All detections stored in DynamoDB; Prometheus metrics exposed
- **Production Systemd Services** — Auto-restart, health checks, zero-touch boot
- **Infrastructure as Code** — Full Terraform stack for reproducible AWS environment

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Hardware** | Raspberry Pi 4 (4GB), Pi Camera Module v2, HC-SR04 Ultrasonic |
| **Edge Software** | Python 3.9, OpenCV, pyttsx3, AWS IoT SDK |
| **Cloud** | AWS Rekognition, IoT Core, Lambda, S3, DynamoDB, IAM |
| **IaC** | Terraform 1.5+, Ansible |
| **Observability** | Prometheus, Grafana, CloudWatch |
| **CI/CD** | GitHub Actions |
| **OS** | Raspberry Pi OS Lite (64-bit), systemd |

---

## 📁 Project Structure

```
blind-navigation-system/
├── src/
│   ├── capture/           # Camera capture & frame processing
│   │   ├── camera.py      # Pi camera interface (OpenCV)
│   │   └── preprocessor.py# Frame resizing, compression
│   ├── recognition/       # Object detection logic
│   │   ├── cloud.py       # AWS Rekognition API client
│   │   ├── local.py       # Offline YOLO fallback
│   │   └── result_handler.py
│   ├── audio/             # Text-to-speech feedback
│   │   └── tts.py
│   └── cloud/             # AWS IoT MQTT transport
│       ├── publisher.py
│       └── subscriber.py
├── infra/
│   ├── terraform/         # AWS infrastructure definitions
│   ├── systemd/           # systemd service units
│   └── ansible/           # RPi provisioning playbooks
├── scripts/
│   ├── setup.sh           # One-shot RPi setup script
│   └── deploy.sh          # Deploy updated service
├── tests/                 # Unit + integration tests
├── docs/
│   ├── ARCHITECTURE.md
│   ├── HARDWARE_SETUP.md
│   └── DEMO.md
├── .github/workflows/     # CI/CD pipelines
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Raspberry Pi 4 (2GB+ RAM)
- Pi Camera Module v2
- AWS Account with Rekognition + IoT Core access
- Python 3.9+

### 1. Clone & Setup

```bash
git clone https://github.com/karthik5041/blind-navigation-system
cd blind-navigation-system
chmod +x scripts/setup.sh && sudo ./scripts/setup.sh
```

### 2. Configure AWS Credentials

```bash
cp config/config.example.yaml config/config.yaml
# Fill in your AWS credentials and IoT endpoint
nano config/config.yaml
```

### 3. Provision AWS Infrastructure

```bash
cd infra/terraform
terraform init
terraform plan -var-file="prod.tfvars"
terraform apply
```

### 4. Run as Systemd Service

```bash
sudo cp infra/systemd/blind-nav.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable blind-nav
sudo systemctl start blind-nav
```

### 5. Check Status

```bash
sudo systemctl status blind-nav
journalctl -u blind-nav -f
```

---

## ⚙️ Configuration

```yaml
# config/config.yaml
aws:
  region: us-east-1
  rekognition:
    max_labels: 10
    min_confidence: 75
  iot:
    endpoint: "your-endpoint.iot.us-east-1.amazonaws.com"
    cert_path: /etc/blind-nav/certs/device.pem.crt
    key_path:  /etc/blind-nav/certs/private.pem.key

camera:
  resolution: [640, 480]
  fps: 15
  frame_skip: 3        # Process every Nth frame

audio:
  rate: 150            # Words per minute
  volume: 0.9
  cooldown_seconds: 2  # Avoid repeating same object

hardware:
  ultrasonic_trigger_pin: 23
  ultrasonic_echo_pin:    24
  proximity_threshold_cm: 100
```

---

## 📊 Performance Metrics

| Metric | Value |
|---|---|
| Object detection latency (cloud) | ~1.8s average |
| Detection accuracy (AWS Rekognition) | 90%+ |
| Frame capture rate | 15 FPS |
| CPU usage on RPi 4 | ~35% |
| Memory footprint | ~180MB |
| Uptime (systemd managed) | 99.7% |

---

## 🧪 Running Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v --cov=src
```

---

## 📐 Infrastructure (Terraform)

The `infra/terraform/` directory provisions:

- **IAM Role** with least-privilege Rekognition + IoT permissions
- **IoT Thing** + X.509 certificate for device authentication
- **IoT Rule** to route MQTT messages to Lambda
- **Lambda Function** for Rekognition invocation
- **S3 Bucket** for frame archiving (lifecycle policy: 7 days)
- **DynamoDB Table** for detection event log
- **CloudWatch Log Group** + alarms

```bash
cd infra/terraform
terraform apply -var="environment=prod" -var="device_id=rpi-001"
```

---

## 🔒 Security

- Device authenticates via **X.509 mutual TLS** (AWS IoT)
- Credentials stored in `/etc/blind-nav/certs/` (chmod 400)
- IAM Role follows **least-privilege** principle (Rekognition DetectLabels only)
- No hardcoded secrets — all via config file outside source control
- Logs sanitized before CloudWatch shipping

---

## 🔮 Future Scope

- [ ] GPS integration for outdoor navigation with turn-by-turn directions
- [ ] Multi-language TTS support
- [ ] Edge ML inference (YOLO v8 on RPi 5 / Coral TPU) to reduce cloud costs
- [ ] Mobile companion app for caregiver monitoring
- [ ] Obstacle trajectory prediction using SORT tracking algorithm

---

## 📄 Research Paper

This project was submitted as a B.Tech capstone report:

> *"Blind Navigation System Using Cloud Computing"* — K. Karthik, J. Gangadhar Sai, B. Ganesh, T. Hemanth  
> Department of CSE, KL University, 2020–2021  
> Supervised by Dr. S. Janardhanarao

---

## 👤 Author

**Karthik Katragadda**  
[![Portfolio](https://img.shields.io/badge/Portfolio-karthik5041.github.io-blue)](https://github.com/karthik5041/portfolio)  
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://linkedin.com)

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

<!-- last updated: April 2026 -->
