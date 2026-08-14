#!/usr/bin/env bash
set -euo pipefail
APP_DIR=/opt/priceradar
DATA_DIR=/var/lib/priceradar
REPO_URL="${PRICERADAR_REPO_URL:-https://github.com/HatchetMan111/PriceRadar.git}"
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git python3 python3-venv python3-pip
id -u priceradar >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --create-home --shell /usr/sbin/nologin priceradar
rm -rf "$APP_DIR"
git clone --depth 1 "$REPO_URL" "$APP_DIR"
mkdir -p "$DATA_DIR"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
chown -R priceradar:priceradar "$APP_DIR" "$DATA_DIR"
install -m 0644 "$APP_DIR/systemd/priceradar.service" /etc/systemd/system/priceradar.service
systemctl daemon-reload
systemctl enable --now priceradar
sleep 2
IP=$(hostname -I | awk '{print $1}')
echo "PriceRadar installed successfully. Open http://${IP}:8080"
echo "Service: systemctl status priceradar"
echo "Logs: journalctl -u priceradar -f"
