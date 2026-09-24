# Recomendaciones para Kriterio Vault

Análisis completo del proyecto realizado el 2026-09-18.

---

## P0 — CRÍTICO (requiere acción inmediata)

| # | Problema | Detalle |
|---|----------|---------|
| 1 | **~~Sin autenticación en ninguna API~~** | ~~Cualquiera en la red puede leer/borrar facturas, restaurar la BD, apagar el servidor.~~ **Corregido en v1.11.00**: auth JWT completo con roles (admin/operador/solo_lectura) + CRUD usuarios + guard de rutas. Usa `bcrypt` nativo (passlib+bcrypt 4.x tenía bug de verificación). |
| 2 | **~~Sin tests~~** | ~~Ni backend ni frontend tienen un solo test.~~ **Corregido en v1.11.01**: 96 tests backend con pytest (auth, bancos, contabilidad, documentos, facturas). Coverage 45% global, 81% en auth. Infraestructura: conftest con BD en memoria, fixtures por rol, coverage configurado. |
| 3 | **Puerto PostgreSQL expuesto** | `docker-compose.yml` expone `5432` a todas las interfaces. Debería ser `127.0.0.1:5432:5432`. **Pendiente** — no urgente mientras se use SQLite local. |
| 4 | **~~Race conditions en numeración~~** | ~~`siguiente_numero()` hace `MAX(numero)+1` sin bloqueo.~~ **Corregido en v1.10.03** con reintento automático + SQLite WAL/busy_timeout. |

---

## P1 — ALTO (próximas semanas)

| # | Problema | Detalle |
|---|----------|---------|
| 5 | **~~Raw SQL extenso~~** | ~~`usuarios.py` y `contabilidad.py` usan SQL crudo masivo en vez de ORM. Riesgo de SQL injection en `sync_replay.py:90-97` donde se interpola `tabla` con f-string.~~ **Corregido en v1.11.21**: whitelist de tablas en `_corregir_uuid()`. SQL injection en `_eliminar_asiento_banco()` fixeado (f-string → ORM `.in_()`). 12 queries raw SQL convertidas a ORM en `usuarios.py` (9) y `contabilidad.py` (3). Se mantienen raw SQL en `get_cuentas` (agregación compleja parametrizada) y `_crear_lineas_raw` (FK sort error documentado). |
| 6 | **~~Funciones >100 líneas~~** | ~~`generar_asiento_banco` (~200 líneas), `update_movimiento` (~180 líneas), `get_conciliacion_bancos` (~230 líneas).~~ **Corregido en v1.11.02**: refactorizadas en sub-funciones (< 65 líneas cada una). |
| 7 | **~~N+1 queries en facturas~~** | ~~Listados de 50 facturas ejecutan ~300 queries adicionales para cargar pagos y vencimientos.~~ **Corregido en v1.11.02**: `_batch_cargar_info` carga datos en 4 queries en vez de ~5N. |
| 8 | **Node.js 14 EOL** | `iniciar.sh` usa Node 14 (EOL abril 2023). Vulnerabilidades de seguridad conocidas. Usar Node 18 o 20 LTS. **Pendiente** — requiere verificar compatibilidad de Vite v4.5.14 con Node 18+. |
| 9 | **~~`ContabilidadPage.jsx` = 2.026 líneas~~** | ~~Contiene 13 componentes internos.~~ **Corregido en v1.11.03**: dividido en 10 archivos en `pages/contabilidad/` (utils, TabCuentas, TabDiario, TabMayor, TabSumasSaldos, TabPyG, TabBalance, TabConciliacion, TabDiagnostico, ContabilidadPage). |
| 10 | **~~Código duplicado masivo~~** | ~~`EUR()`, `fmtFecha()`, `hoy()` duplicados en 10+ archivos. Patrón CRUD repetido en Clientes/Proveedores/Artículos.~~ **Corregido en v1.11.04-v1.11.06**: `utils/format.js` centraliza EUR/fmtFecha/hoy (13 archivos). `useCrud.js` encapsula CRUD. `CrudPage.jsx` componente genérico con columnas configurables (Clientes/Proveedores son wrappers de ~50 líneas). |

---

## P2 — MEDIO (mejoras importantes)

| # | Problema | Detalle |
|---|----------|---------|
| 11 | **Sin relaciones ORM** | Ningún `relationship()` entre modelos. Todo se hace con queries manuales. **Pendiente** — requiere refactor cuidadoso de ~50 queries en services. |
| 12 | **~~Float para dinero~~** | ~~`Numeric(15,2, asdecimal=False)` retorna `float`. `0.1 + 0.2 ≠ 0.3`. Usar `Decimal` o integer cents.~~ **Corregido en v1.11.07**: 36 campos `Numeric` cambiados a `Mapped[Decimal]`. Eliminados ~80 casts `float()` en services y API. Adapter SQLite para serialización Decimal. |
| 13 | **~~Sin health checks~~** | ~~Ni en Docker ni en systemd. No hay endpoint `/health`.~~ **Corregido en v1.11.08**: endpoint `GET /health` sin auth, verifica DB con `SELECT 1`. Retorna 200 si OK, 503 si error. Tests incluidos. |
| 14 | **Backups solo locales** | Sin sincronización a S3/GCS. Si el disco muere, se pierde todo. Parcialmente corregido en v1.11.02: rutas de backup corregidas a absolutas (antes dependían del CWD). **Pendiente** — sincronización off-site (S3/GCS/rsync al NAS). Encriptación de backups. Verificación de integridad. |
| 15 | **~~Servicios frontend inconsistentes~~** | ~~5 de 15 servicios usan `axios` directo sin interceptor de errores.~~ **Corregido en v1.11.00**: todos usan `api` instance. **Corregido en v1.11.02**: eliminado doble prefijo `/api/` en 5 services. |
| 16 | **~~`confirm()` nativo~~** | ~~Múltiples páginas usan `window.confirm()` en vez de un modal custom.~~ **Corregido en v1.11.09**: 25 llamadas a `confirm()` reemplazadas por `ConfirmModal` (componente reutilizable con 3 variantes: danger/warning/info). 13 archivos modificados. |
| 17 | **~~Sin rate limiting~~** | ~~`/api/sync/push` no limita requests. Vulnerable a DoS.~~ **Corregido en v1.11.10**: `slowapi` integrado. Login: 10/min por IP. Sync push: 60/min por API key. Global: 200/min por IP. Tests incluidos. |
| 18 | **~~`@app.on_event` deprecated~~** | ~~FastAPI deprecó estos eventos. Usar `lifespan`.~~ **Corregido en v1.11.11**: migrado a `@asynccontextmanager` con `lifespan`. Eliminados 4 DeprecationWarning. |
| 19 | **~~Caddy básico~~** | ~~Falta `X-Content-Type-Options`, `X-Frame-Options`, `HSTS`.~~ **Corregido en v1.11.20**: Headers de seguridad añadidos al Caddyfile: HSTS (1 año + preload), X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Cache-Control no-store, eliminación de Server header. |

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

1. **Semana 1-2**: ~~Autenticación básica (JWT simple)~~ **Hecho en v1.11.00** + ~~tests críticos~~ **Hecho en v1.11.01** (96 tests, 45% coverage)
2. **Semana 3-4**: ~~Cerrar race conditions~~ **Hecho en v1.10.03**, ~~sanitizar SQL~~ **Pendiente**, ~~actualizar Node.js~~ **Pendiente**
3. **Mes 2**: ~~Refactorizar `ContabilidadPage`~~ **Hecho en v1.11.03**, ~~extraer utilidades~~ **Hecho en v1.11.04**, ~~unificar servicios frontend~~ **Hecho en v1.11.00/v1.11.02**, ~~deduplicar código~~ **Hecho en v1.11.04-v1.11.06**, ~~Decimal para dinero~~ **Hecho en v1.11.07**
4. **Mes 3**: ~~Health checks~~ **Hecho en v1.11.08**, ~~backups off-site~~ **Parcial (paths corregidos)**, hardening de Docker/systemd
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
| `frontend/src/pages/` | 15 páginas React (incluye UsuariosSistemaPage) |
| `frontend/src/hooks/useAuth.jsx` | Gestión de autenticación (login, logout, roles) |
| `frontend/src/components/` | 9 componentes reutilizables |
| `frontend/src/services/` | 15 servicios API |
| `deploy/` | Scripts de deploy para Debian |
| `importador/` | Migra datos desde DBF del sistema antiguo |
