#!/usr/bin/env bash
# setup.sh — One-shot provisioning for Raspberry Pi OS (64-bit)
# Run as root: sudo ./scripts/setup.sh
set -euo pipefail

APP_DIR="/opt/blind-nav"
CONFIG_DIR="/etc/blind-nav"
LOG_DIR="/var/log/blind-nav"
USER="blindnav"

echo "==> [1/7] Creating system user and directories"
id "$USER" &>/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin "$USER"
mkdir -p "$APP_DIR" "$CONFIG_DIR/certs" "$LOG_DIR"
chown -R "$USER:$USER" "$LOG_DIR"
chmod 700 "$CONFIG_DIR/certs"

echo "==> [2/7] Installing system dependencies"
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev \
    libopencv-dev python3-opencv \
    espeak espeak-ng \
    libgpiod2 \
    libatlas-base-dev \
    libjpeg-dev libpng-dev

echo "==> [3/7] Installing libcamera for Pi Camera Module v2"
apt-get install -y --no-install-recommends \
    libcamera-apps libcamera-dev \
    python3-libcamera 2>/dev/null || echo "libcamera not available, using OpenCV v4l2 fallback"

echo "==> [4/7] Setting up Python virtual environment"
python3.11 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip wheel
"$APP_DIR/venv/bin/pip" install -r requirements.txt

echo "==> [5/7] Copying application files"
rsync -a --exclude='*.pyc' --exclude='__pycache__' --exclude='.git' \
    ./ "$APP_DIR/"
chown -R root:"$USER" "$APP_DIR"
chmod -R o-rwx "$APP_DIR"

echo "==> [6/7] Installing systemd service"
cp infra/systemd/blind-nav.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable blind-nav

echo "==> [7/7] Enabling camera interface"
raspi-config nonint do_camera 0 2>/dev/null || echo "raspi-config not found; enable camera manually"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy your AWS IoT certificates to $CONFIG_DIR/certs/"
echo "  2. Edit $CONFIG_DIR/config.yaml with your IoT endpoint and AWS region"
echo "  3. sudo systemctl start blind-nav"
echo "  4. sudo journalctl -u blind-nav -f"
