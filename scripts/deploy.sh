#!/usr/bin/env bash
# deploy.sh - Push updated app code to Raspberry Pi over SSH
# Usage: ./scripts/deploy.sh pi@192.168.1.100
set -euo pipefail

TARGET="${1:-pi@raspberrypi.local}"
APP_DIR="/opt/blind-nav"

echo "==> Syncing code to $TARGET:$APP_DIR"
rsync -avz --exclude='*.pyc' --exclude='__pycache__' \
  --exclude='.git' --exclude='*.docx' --exclude='*.zip' \
  ./ "$TARGET:$APP_DIR/"

echo "==> Restarting service"
ssh "$TARGET" "sudo systemctl restart blind-nav && sudo systemctl status blind-nav --no-pager"

echo "==> Deploy complete! Tailing logs..."
ssh "$TARGET" "journalctl -u blind-nav -f --no-pager -n 20"
