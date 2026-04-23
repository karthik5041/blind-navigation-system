"""
metrics.py - Prometheus metrics for blind-nav systemd service
"""
from prometheus_client import Counter, Histogram, Gauge, start_http_server

DETECTIONS_TOTAL = Counter('blindnav_detections_total', 'Total object detections', ['label'])
REKOGNITION_LATENCY = Histogram('blindnav_rekognition_latency_seconds', 'AWS Rekognition latency')
CAMERA_FPS = Gauge('blindnav_camera_fps', 'Current camera capture FPS')
SYSTEM_UPTIME = Gauge('blindnav_uptime_seconds', 'Service uptime in seconds')

def start_metrics_server(port: int = 9100):
    start_http_server(port)
