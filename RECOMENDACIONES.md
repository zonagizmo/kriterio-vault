# Recomendaciones para Kriterio Vault

Análisis completo del proyecto realizado el 2026-09-18.

---

## P0 — CRÍTICO (requiere acción inmediata)

| # | Problema | Detalle |
|---|----------|---------|
| 1 | **Sin autenticación en ninguna API** | Cualquiera en la red puede leer/borrar facturas, restaurar la BD, apagar el servidor (`/api/shutdown`). Solo `/api/sync/push` tiene API key. |
| 2 | **Sin tests** | Ni backend ni frontend tienen un solo test. Para un ERP contable es extremadamente arriesgado. |
| 3 | **Puerto PostgreSQL expuesto** | `docker-compose.yml` expone `5432` a todas las interfaces. Debería ser `127.0.0.1:5432:5432`. |
| 4 | **~~Race conditions en numeración~~** | ~~`siguiente_numero()` hace `MAX(numero)+1` sin bloqueo.~~ **Corregido en v1.10.03** con reintento automático + SQLite WAL/busy_timeout. |

---

## P1 — ALTO (próximas semanas)

| # | Problema | Detalle |
|---|----------|---------|
| 5 | **Raw SQL extenso** | `usuarios.py` y `contabilidad.py` usan SQL crudo masivo en vez de ORM. Riesgo de SQL injection en `sync_replay.py:90-97` donde se interpola `tabla` con f-string. |
| 6 | **Funciones >100 líneas** | `generar_asiento_banco` (~200 líneas), `update_movimiento` (~180 líneas), `get_conciliacion_bancos` (~230 líneas). Difícil de mantener y testear. |
| 7 | **N+1 queries en facturas** | Listados de 50 facturas ejecutan ~300 queries adicionales para cargar pagos y vencimientos. |
| 8 | **Node.js 14 EOL** | `iniciar.sh` usa Node 14 (EOL abril 2023). Vulnerabilidades de seguridad conocidas. Usar Node 18 o 20 LTS. |
| 9 | **`ContabilidadPage.jsx` = 2.026 líneas** | Contiene 13 componentes internos. Deberían ser archivos separados en `pages/contabilidad/`. |
| 10 | **Código duplicado masivo** | `EUR()`, `fmtFecha()`, `hoy()` duplicados en 10+ archivos. Patrón CRUD repetido en Clientes/Proveedores/Artículos. |

---

## P2 — MEDIO (mejoras importantes)

| # | Problema | Detalle |
|---|----------|---------|
| 11 | **Sin relaciones ORM** | Ningún `relationship()` entre modelos. Todo se hace con queries manuales. |
| 12 | **Float para dinero** | `Numeric(15,2, asdecimal=False)` retorna `float`. `0.1 + 0.2 ≠ 0.3`. Usar `Decimal` o integer cents. |
| 13 | **Sin health checks** | Ni en Docker ni en systemd. No hay endpoint `/health`. |
| 14 | **Backups solo locales** | Sin sincronización a S3/GCS. Si el disco muere, se pierde todo. |
| 15 | **Servicios frontend inconsistentes** | 5 de 15 servicios usan `axios` directo sin interceptor de errores. Bancos, Contabilidad, Usuarios, Extras y Ajustes no manejan errores correctamente. |
| 16 | **`confirm()` nativo** | Múltiples páginas usan `window.confirm()` en vez de un modal custom. |
| 17 | **Sin rate limiting** | `/api/sync/push` no limita requests. Vulnerable a DoS. |
| 18 | **`@app.on_event` deprecated** | FastAPI deprecó estos eventos. Usar `lifespan`. |
| 19 | **Caddy básico** | Falta `X-Content-Type-Options`, `X-Frame-Options`, `HSTS`. |

---

## P3 — BAJO (mejoras a largo plazo)

| # | Problema | Detalle |
|---|----------|---------|
| 20 | Sin TypeScript | Los tipos ayudarían con la complejidad de `modal` (null/string/object). |
| 21 | Sin ESLint/Prettier | No hay linting ni formateo consistente. |
| 22 | Loading states deficientes | Solo `<p>Cargando...</p>`. Sin skeletons ni spinners. |
| 23 | Sin dark mode | Tailwind no tiene `darkMode` configurado. |
| 24 | Paginación sin sync con URL | Un refresh pierde la posición. |
| 25 | Sincronización sin conflictos | Solo fase 2 (subida). Sin resolución de conflictos entre instalaciones. |

---

## Plan de acción sugerido

1. **Semana 1-2**: Autenticación básica (JWT simple) + tests críticos (servicios de facturación y contabilidad)
2. **Semana 3-4**: Cerrar race conditions (ya hecho en v1.10.03), sanitizar SQL, actualizar Node.js
3. **Mes 2**: Refactorizar `ContabilidadPage`, extraer utilidades, unificar servicios frontend
4. **Mes 3**: Health checks, backups off-site, hardening de Docker/systemd
5. **Mes 4+**: TypeScript, tests completos, CI/CD

---

## Archivos clave del proyecto

| Ruta | Descripción |
|------|-------------|
| `backend/app/main.py` | Punto de entrada FastAPI, versión, migraciones |
| `backend/app/db/database.py` | Configuración SQLAlchemy (SQLite/PostgreSQL) |
| `backend/app/services/` | Lógica de negocio (14 módulos) |
| `backend/app/api/` | Endpoints REST (16 routers) |
| `backend/app/models/` | Modelos ORM (~35 tablas) |
| `frontend/src/pages/` | 14 páginas React |
| `frontend/src/components/` | 9 componentes reutilizables |
| `frontend/src/services/` | 15 servicios API |
| `deploy/` | Scripts de deploy para Debian |
| `importador/` | Migra datos desde DBF del sistema antiguo |
