#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  iniciar.sh — arranca backend + frontend y abre el navegador
#  Funciona desde cualquier ubicación de la carpeta GestionMGD_web
# ─────────────────────────────────────────────────────────────

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
UVICORN="$BACKEND/venv/bin/uvicorn"
VITE="$FRONTEND/node_modules/.bin/vite"
URL="http://localhost:5173"

# ── Colores ───────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ── Buscar Node.js compatible (v22 LTS) ──────────────────────
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh" --no-use 2>/dev/null

# Preferir v22 explícito; si no, usar el primero disponible en nvm; si no, el del PATH
if   [ -x "$NVM_DIR/versions/node/v22.22.0/bin/node" ]; then
  NODE="$NVM_DIR/versions/node/v22.22.0/bin/node"
elif ls "$NVM_DIR/versions/node/" 2>/dev/null | grep -q "^v22"; then
  V22=$(ls "$NVM_DIR/versions/node/" | grep "^v22" | sort -V | tail -1)
  NODE="$NVM_DIR/versions/node/$V22/bin/node"
elif command -v node &>/dev/null; then
  NODE="$(command -v node)"
else
  echo -e "${RED}Error: no se encontró Node.js.${NC}"
  echo "  Instala Node.js v22 con: nvm install 22"
  echo "  (Linux con glibc < 2.28: usa el build glibc-217 de unofficial-builds.nodejs.org)"
  exit 1
fi
# Asegurar que los subprocess de npm/vite resuelvan el mismo node
export PATH="$(dirname "$NODE"):$PATH"

# ── Validaciones ──────────────────────────────────────────────
missing=0
[ ! -f "$UVICORN" ] && echo -e "${RED}✗ No se encontró uvicorn en backend/venv${NC}" && missing=1
[ ! -f "$VITE"    ] && echo -e "${RED}✗ No se encontró vite en frontend/node_modules${NC}" && missing=1
[ $missing -eq 1  ] && echo -e "${YELLOW}Pista: ejecuta 'pip install -r requirements.txt' en backend/ y 'npm install' en frontend/${NC}" && exit 1

# ── Watches inotify disponibles ────────────────────────────────
# Algunos programas (pcloud, Firefox...) consumen casi todos los
# watches y Vite muere con ENOSPC. Si quedan pocos, usamos polling.
watches_libres() {
  local max used=0 p fd link n nfd
  max=$(cat /proc/sys/fs/inotify/max_user_watches 2>/dev/null) || max=0
  [ "$max" -gt 0 ] || { echo 999999; return; }
  for p in /proc/[0-9]*; do
    for fd in "$p"/fd/*; do
      link=$(readlink "$fd" 2>/dev/null || true)
      [ "$link" = "anon_inode:inotify" ] || continue
      nfd="${fd##*/}"
      n=$(grep -c '^inotify wd:' "$p/fdinfo/$nfd" 2>/dev/null) || n=0
      used=$((used + ${n:-0}))
    done
  done
  [ "$used" -lt "$max" ] && echo $((max - used)) || echo 0
}

LIBRES=$(watches_libres)
if [ "$LIBRES" -lt 2048 ]; then
  echo -e "${YELLOW}⚠ Solo $LIBRES watches inotify libres — Vite usará polling (sube fs.inotify.max_user_watches con sudo para evitarlo).${NC}"
  export CHOKIDAR_USEPOLLING=true
fi

# ── Liberar puertos ocupados ───────────────────────────────────
liberar_puerto() {
  local puerto=$1
  local pids
  pids=$(lsof -ti:"$puerto" 2>/dev/null) || true
  if [ -n "$pids" ]; then
    echo -e "${YELLOW}  Puerto $puerto ocupado — cerrando procesos anteriores...${NC}"
    echo "$pids" | xargs kill 2>/dev/null || true
    sleep 1
    # Si siguen vivos, forzar
    pids=$(lsof -ti:"$puerto" 2>/dev/null) || true
    if [ -n "$pids" ]; then
      echo "$pids" | xargs kill -9 2>/dev/null || true
      sleep 1
    fi
  fi
}

liberar_puerto 8000
liberar_puerto 5173

# ── Limpieza al salir ─────────────────────────────────────────
cleanup() {
  echo -e "\n${YELLOW}Deteniendo servidores...${NC}"
  kill "$PID_BACK" "$PID_FRONT" 2>/dev/null || true
  wait "$PID_BACK" "$PID_FRONT" 2>/dev/null || true
  echo -e "${GREEN}Hasta luego.${NC}"
}
trap cleanup EXIT INT TERM

# ── Arrancar backend ──────────────────────────────────────────
echo -e "${BOLD}${CYAN}▶ Backend${NC}  (puerto 8000)"
(cd "$BACKEND" && "$UVICORN" app.main:app \
  --host 127.0.0.1 --port 8000 \
  --log-level warning 2>&1) &
PID_BACK=$!

# ── Arrancar frontend ─────────────────────────────────────────
echo -e "${BOLD}${CYAN}▶ Frontend${NC} (puerto 5173)"
(cd "$FRONTEND" && "$NODE" "$VITE" --logLevel warn 2>&1) &
PID_FRONT=$!

# ── Esperar a que el frontend esté listo ──────────────────────
echo -n "  Esperando..."
for i in $(seq 1 20); do
  sleep 0.5
  if curl -s "$URL" -o /dev/null 2>/dev/null; then
    break
  fi
done
echo ""

# ── Abrir navegador ───────────────────────────────────────────
xdg-open "$URL" 2>/dev/null || open "$URL" 2>/dev/null || true

echo -e "${GREEN}${BOLD}✓ GestionMGD disponible en ${URL}${NC}"
echo -e "  Pulsa ${BOLD}Ctrl+C${NC} para detener todo."
echo ""

wait
