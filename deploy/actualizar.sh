#!/usr/bin/env bash
# Actualiza el código en el servidor ya aprovisionado y reinicia el servicio.
# Uso: sudo bash actualizar.sh
set -euo pipefail

APP_USER="kriterio"
APP_DIR="/opt/kriterio-vault"

if [ "$(id -u)" -ne 0 ]; then
    echo "Ejecuta como root (sudo bash actualizar.sh)." >&2
    exit 1
fi

sudo -u "$APP_USER" git -C "$APP_DIR" pull
sudo -u "$APP_USER" "$APP_DIR/backend/venv/bin/pip" install -q -r "$APP_DIR/backend/requirements.txt"
systemctl restart kriterio-vault
echo "Servicio reiniciado. Estado:"
systemctl status kriterio-vault --no-pager -l | head -10
