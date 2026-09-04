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

# ── Buscar Node.js compatible (v14 via nvm) ───────────────────
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh" --no-use 2>/dev/null

# Preferir v14 explícito; si no, usar el primero disponible en nvm; si no, el del PATH
if   [ -x "$NVM_DIR/versions/node/v14.21.3/bin/node" ]; then
  NODE="$NVM_DIR/versions/node/v14.21.3/bin/node"
elif ls "$NVM_DIR/versions/node/" 2>/dev/null | grep -q "^v14"; then
  V14=$(ls "$NVM_DIR/versions/node/" | grep "^v14" | sort -V | tail -1)
  NODE="$NVM_DIR/versions/node/$V14/bin/node"
elif command -v node &>/dev/null; then
  NODE="$(command -v node)"
else
  echo -e "${RED}Error: no se encontró Node.js.${NC}"
  echo "  Instala Node.js v14 con: nvm install 14"
  exit 1
fi

# ── Validaciones ──────────────────────────────────────────────
missing=0
[ ! -f "$UVICORN" ] && echo -e "${RED}✗ No se encontró uvicorn en backend/venv${NC}" && missing=1
[ ! -f "$VITE"    ] && echo -e "${RED}✗ No se encontró vite en frontend/node_modules${NC}" && missing=1
[ $missing -eq 1  ] && echo -e "${YELLOW}Pista: ejecuta 'pip install -r requirements.txt' en backend/ y 'npm install' en frontend/${NC}" && exit 1

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
