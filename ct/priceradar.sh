#!/usr/bin/env bash
set -euo pipefail
APP=PriceRadar
REPO_URL="${PRICERADAR_REPO_URL:-https://github.com/HatchetMan111/PriceRadar.git}"
CTID="${CTID:-$(pvesh get /cluster/nextid)}"
HOSTNAME="${HOSTNAME:-priceradar}"
CORES="${CORES:-2}"
RAM="${RAM:-2048}"
DISK="${DISK:-8}"
BRIDGE="${BRIDGE:-vmbr0}"
[[ $EUID -eq 0 ]] || { echo 'Run as root on Proxmox VE.'; exit 1; }
command -v pveversion >/dev/null || { echo 'Proxmox VE not detected.'; exit 1; }
command -v pct >/dev/null || { echo 'pct not found.'; exit 1; }
command -v pveam >/dev/null || { echo 'pveam not found.'; exit 1; }
[[ "$REPO_URL" =~ ^https://[A-Za-z0-9._-]+(/[A-Za-z0-9._~%+-]+)*\.git$ ]] || { echo "PRICERADAR_REPO_URL looks invalid: $REPO_URL"; exit 1; }
info(){ printf '\033[1;36m[INFO]\033[0m %s\n' "$*"; }
ok(){ printf '\033[1;32m[ OK ]\033[0m %s\n' "$*"; }
err(){ printf '\033[1;31m[ERR ]\033[0m %s\n' "$*" >&2; }
if pct status "$CTID" >/dev/null 2>&1 || qm status "$CTID" >/dev/null 2>&1; then CTID="$(pvesh get /cluster/nextid)"; fi
ip link show "$BRIDGE" >/dev/null 2>&1 || { err "Bridge $BRIDGE does not exist."; exit 1; }
TEMPLATE_STORAGE="${TEMPLATE_STORAGE:-$(pvesm status -content vztmpl 2>/dev/null | awk 'NR>1 && $3=="active"{print $1}' | head -n1)}"
CONTAINER_STORAGE="${CONTAINER_STORAGE:-$(pvesm status -content rootdir 2>/dev/null | awk 'NR>1 && $3=="active"{print $1}' | head -n1)}"
[[ -n "$TEMPLATE_STORAGE" ]] || { err 'No storage supports LXC templates.'; exit 1; }
[[ -n "$CONTAINER_STORAGE" ]] || { err 'No storage supports LXC root directories.'; exit 1; }
info 'Refreshing Proxmox template catalog'; pveam update >/dev/null 2>&1 || true
TEMPLATE="$(pveam available -section system 2>/dev/null | awk '$2 ~ /^debian-13-standard_.*_amd64\.tar\.(zst|xz|gz)$/{print $2}' | sort -V | tail -n1)"
[[ -n "$TEMPLATE" ]] || { err 'Could not find Debian 13 amd64 LXC template.'; exit 1; }
if ! pveam list "$TEMPLATE_STORAGE" 2>/dev/null | grep -qF "$TEMPLATE"; then info "Downloading $TEMPLATE"; pveam download "$TEMPLATE_STORAGE" "$TEMPLATE"; fi
info "Creating unprivileged PriceRadar LXC $CTID"
pct create "$CTID" "$TEMPLATE_STORAGE:vztmpl/$TEMPLATE" -hostname "$HOSTNAME" -cores "$CORES" -memory "$RAM" -rootfs "$CONTAINER_STORAGE:$DISK" -net0 "name=eth0,bridge=$BRIDGE,ip=dhcp" -unprivileged 1 -onboot 1 -ostype debian -tags priceradar -start 1
ok "LXC $CTID created"
info 'Installing PriceRadar inside LXC'
# Pass the validated repository URL as an environment value rather than
# interpolating it into shell source executed by pct exec.
pct exec "$CTID" -- env "PRICERADAR_REPO_URL=$REPO_URL" bash -c \
    'apt-get update && apt-get install -y curl && curl -fsSL https://raw.githubusercontent.com/HatchetMan111/PriceRadar/main/install/install-app.sh | bash'
IP="$(pct exec "$CTID" -- hostname -I 2>/dev/null | awk '{print $1}')"
echo '=============================================='
ok 'PriceRadar installation complete'
echo "Container ID : $CTID"
echo "URL          : http://${IP}:8080"
echo "Logs         : pct exec $CTID -- journalctl -u priceradar -f"
echo '=============================================='
