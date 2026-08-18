#!/usr/bin/env bash
set -euo pipefail
APP_DIR=/opt/priceradar
DATA_DIR=/var/lib/priceradar
ENV_FILE=/etc/priceradar.env
BROWSER_DIR=/opt/priceradar/browsers
REPO_URL="${PRICERADAR_REPO_URL:-https://github.com/HatchetMan111/PriceRadar.git}"
INSTALL_BROWSER="${PRICERADAR_INSTALL_BROWSER:-true}"
[[ "$REPO_URL" =~ ^https://[A-Za-z0-9._-]+(/[A-Za-z0-9._~%+-]+)*\.git$ ]] || { echo "PRICERADAR_REPO_URL looks invalid: $REPO_URL" >&2; exit 1; }

apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git python3 python3-venv python3-pip
id -u priceradar >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --create-home --shell /usr/sbin/nologin priceradar
rm -rf "$APP_DIR"
git clone --depth 1 "$REPO_URL" "$APP_DIR"
mkdir -p "$DATA_DIR"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# Chromium is optional. HTTP extraction still works without it, while browser
# mode handles JavaScript-rendered pages. Install it by default for the full MVP.
if [[ "$INSTALL_BROWSER" == "true" ]]; then
    echo "Installing Chromium for JavaScript-rendered pages..."
    mkdir -p "$BROWSER_DIR"
    chown -R priceradar:priceradar "$BROWSER_DIR"
    export PLAYWRIGHT_BROWSERS_PATH="$BROWSER_DIR"
    "$APP_DIR/venv/bin/python" -m playwright install --with-deps chromium
fi

chown -R priceradar:priceradar "$APP_DIR" "$DATA_DIR" "$BROWSER_DIR"

# Generate credentials on first install so the web UI is not exposed
# unauthenticated by default. Existing credentials survive re-installs.
if [[ ! -f "$ENV_FILE" ]]; then
    GENERATED_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
    umask 077
    cat > "$ENV_FILE" <<EOF
PRICERADAR_AUTH_USER=admin
PRICERADAR_AUTH_PASSWORD=${GENERATED_PASSWORD}
PRICERADAR_BROWSER_ENABLED=${INSTALL_BROWSER}
PRICERADAR_PLAYWRIGHT_BROWSERS_PATH=${BROWSER_DIR}
EOF
    chown root:priceradar "$ENV_FILE"
    chmod 640 "$ENV_FILE"
fi

install -m 0644 "$APP_DIR/systemd/priceradar.service" /etc/systemd/system/priceradar.service
systemctl daemon-reload
systemctl enable --now priceradar
sleep 2
IP=$(hostname -I | awk '{print $1}')
echo "PriceRadar installed successfully. Open http://${IP}:8080"
if [[ -n "${GENERATED_PASSWORD:-}" ]]; then
    echo "Login       : admin / ${GENERATED_PASSWORD}"
    echo "              (stored in $ENV_FILE - change it any time)"
fi
echo "Browser     : ${INSTALL_BROWSER}"
echo "Smart poll  : enabled by default; stable prices back off, changes poll faster"
echo "Service: systemctl status priceradar"
echo "Logs: journalctl -u priceradar -f"
