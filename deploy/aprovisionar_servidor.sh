#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Aprovisiona un Debian "pelado" como servidor central de
# sincronización de Kriterio Vault: PostgreSQL, la app (backend
# FastAPI), Caddy con TLS automático y firewall.
#
# Idempotente: se puede volver a ejecutar sin duplicar nada (útil
# para actualizar tras cambios de infraestructura; para actualizar
# solo el código de la app usa deploy/actualizar.sh).
#
# Uso (como root, en el propio servidor):
#   sudo bash aprovisionar_servidor.sh
#
# Antes de ejecutarlo:
#   1. Crea el registro DNS: kriteriovault.naslive.es -> IP pública
#      de este servidor (en el panel de tu proveedor de dominio).
#   2. El script te pedirá añadir una clave de despliegue de solo
#      lectura en GitHub a mitad de ejecución — ten abierta la
#      sesión en github.com para poder pegarla.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

DOMINIO="kriteriovault.naslive.es"
REPO="zonagizmo/kriterio-vault"
APP_USER="kriterio"
APP_DIR="/opt/kriterio-vault"
PG_DB="kriterio_vault"
PG_USER="kriterio_vault"
ENV_FILE="$APP_DIR/backend/.env"
SECRETS_FILE="/root/.kriterio-vault-secrets"

if [ "$(id -u)" -ne 0 ]; then
    echo "Ejecuta este script como root (sudo bash aprovisionar_servidor.sh)." >&2
    exit 1
fi

echo "== 1/9: paquetes base =="
apt-get update
apt-get install -y postgresql postgresql-contrib libpq-dev python3-venv python3-pip \
    build-essential git curl ufw fail2ban debian-keyring debian-archive-keyring apt-transport-https gnupg

echo "== 2/9: repositorio de Caddy =="
if [ ! -f /usr/share/keyrings/caddy-stable-archive-keyring.gpg ]; then
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
        | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
        > /etc/apt/sources.list.d/caddy-stable.list
    apt-get update
fi
apt-get install -y caddy

echo "== 3/9: usuario de sistema para la app =="
id -u "$APP_USER" &>/dev/null || useradd --system --create-home --shell /bin/bash "$APP_USER"

echo "== 4/9: base de datos PostgreSQL =="
if [ -f "$SECRETS_FILE" ]; then
    # shellcheck disable=SC1090
    source "$SECRETS_FILE"
else
    PG_PASSWORD="$(openssl rand -base64 24)"
    echo "PG_PASSWORD=$PG_PASSWORD" > "$SECRETS_FILE"
    chmod 600 "$SECRETS_FILE"
fi
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$PG_USER'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE ROLE $PG_USER WITH LOGIN PASSWORD '$PG_PASSWORD';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$PG_DB'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE $PG_DB OWNER $PG_USER;"

echo "== 5/9: clave SSH de despliegue (solo lectura del repo privado) =="
SSH_DIR="/home/$APP_USER/.ssh"
DEPLOY_KEY="$SSH_DIR/id_ed25519_deploy"
if [ ! -f "$DEPLOY_KEY" ]; then
    sudo -u "$APP_USER" mkdir -p "$SSH_DIR"
    sudo -u "$APP_USER" ssh-keygen -t ed25519 -f "$DEPLOY_KEY" -N "" -C "kriterio-vault-servidor"
    sudo -u "$APP_USER" bash -c "ssh-keyscan -H github.com >> '$SSH_DIR/known_hosts' 2>/dev/null"
    sudo -u "$APP_USER" bash -c "cat >> '$SSH_DIR/config'" <<EOF
Host github.com-kriterio
    HostName github.com
    User git
    IdentityFile $DEPLOY_KEY
    IdentitiesOnly yes
EOF
    echo
    echo ">>> Añade esta clave pública como 'Deploy key' de SOLO LECTURA en:"
    echo ">>> https://github.com/$REPO/settings/keys  ->  Add deploy key"
    echo
    cat "$DEPLOY_KEY.pub"
    echo
    read -rp "Pulsa Enter cuando la hayas añadido en GitHub... "
fi

echo "== 6/9: clonar / actualizar el repositorio =="
if [ ! -d "$APP_DIR/.git" ]; then
    mkdir -p "$APP_DIR"
    chown "$APP_USER:$APP_USER" "$APP_DIR"
    sudo -u "$APP_USER" git clone "git@github.com-kriterio:$REPO.git" "$APP_DIR"
else
    sudo -u "$APP_USER" git -C "$APP_DIR" pull
fi

echo "== 7/9: entorno Python =="
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/backend/venv"
sudo -u "$APP_USER" "$APP_DIR/backend/venv/bin/pip" install --upgrade pip -q
sudo -u "$APP_USER" "$APP_DIR/backend/venv/bin/pip" install -q -r "$APP_DIR/backend/requirements.txt"

if [ ! -f "$ENV_FILE" ]; then
    SECRET_KEY="$(openssl rand -hex 32)"
    cat > "$ENV_FILE" <<EOF
DATABASE_URL=postgresql://$PG_USER:$PG_PASSWORD@localhost:5432/$PG_DB
SECRET_KEY=$SECRET_KEY
EOF
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi

echo "== 8/9: servicio systemd =="
cp "$APP_DIR/deploy/kriterio-vault.service" /etc/systemd/system/kriterio-vault.service
systemctl daemon-reload
systemctl enable --now kriterio-vault
systemctl restart kriterio-vault

echo "== 9/9: Caddy (TLS) y firewall =="
sed "s/DOMINIO_PLACEHOLDER/$DOMINIO/" "$APP_DIR/deploy/Caddyfile" > /etc/caddy/Caddyfile
systemctl reload caddy 2>/dev/null || systemctl restart caddy

ufw allow 22/tcp   >/dev/null
ufw allow 80/tcp   >/dev/null
ufw allow 443/tcp  >/dev/null
ufw --force enable >/dev/null

echo
echo "─────────────────────────────────────────────"
echo "Listo. Comprueba en unos segundos (la primera vez Caddy tarda"
echo "en emitir el certificado TLS):"
echo "  curl -s https://$DOMINIO/api/version"
echo
echo "Para dar de alta la primera instalación cliente:"
echo "  sudo -u $APP_USER $APP_DIR/backend/venv/bin/python \\"
echo "    $APP_DIR/backend/scripts/crear_instalacion.py --nombre \"PC Oficina\""
echo "─────────────────────────────────────────────"
