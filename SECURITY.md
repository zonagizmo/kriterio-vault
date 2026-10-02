# Seguridad y autorización — Kriterio Vault

> Documento vivo. Última revisión: **v1.13.04** (2026-09-29), tras la auditoría
> multiempresa + RBAC (`docs/auditoria_seguridad.md`).
> Política implementada en `backend/app/services/permissions.py` (única fuente de
> verdad). El frontend (`frontend/src/services/permissions.js`) solo la refleja.

---

## 1. Modelo de autorización

Cadena de decisión en cada petición:

```
Token JWT válido → usuario activo (BD) → Rol → Permisos → Empresa → Recurso
```

| Código | Cuándo | Ejemplo |
|--------|--------|---------|
| **401** | No autenticado: sin token, token inválido/expirado/firmado con otra clave, usuario **inactivo** o rol modificado en BD | `GET /api/clientes` sin `Authorization` |
| **403** | Autenticado pero sin permiso para la acción | `solo_lectura` → `POST /api/clientes` |
| **404** | Recurso inexistente **o perteneciente a otra empresa** (no se revela existencia) | `GET /api/facturas/{id}` de otra empresa |

El 404-cruzado es deliberado: responder 403 daría información sobre la existencia
de registros ajenos (§aislamiento multiempresa). El `detail` es **uniforme**
(`"Recurso no encontrado"`) en todos los routers: inexistente y ajeno son
indistinguibles (IDOR-001, corregido en v1.13.04).

---

## 2. Roles

| Rol | Uso previsto |
|-----|--------------|
| `admin` | Administración total: usuarios, empresas, backups, ajustes, diagnóstico, apagado |
| `operador` | Trabajo diario: crea/edita/borra documentos y movimientos de **sus** empresas |
| `solo_lectura` | Consulta: listados, estadísticas y exportaciones, sin escritura |

---

## 3. Matriz Rol × Permiso

Fuente: `ROLE_PERMISSIONS` en `backend/app/services/permissions.py`
(espejo en `frontend/src/services/permissions.js`).

| Permiso | admin | operador | solo_lectura | Significado |
|---------|:-----:|:--------:|:------------:|-------------|
| `read` | ✅ | ✅ | ✅ | GET (listados, detalle, exportaciones) |
| `create` | ✅ | ✅ | ❌ | POST (alta de registros, renumeraciones, asientos) |
| `update` | ✅ | ✅ | ❌ | PUT/PATCH (edición, conciliación, bajas) |
| `delete` | ✅ | ✅ ¹ | ❌ | DELETE |
| `write` | ✅ | ✅ | ❌ | Alias lógico: `create` o `update` |
| `admin` | ✅ | ❌ | ❌ | Apagar servidor, diagnóstico contable |
| `backup` | ✅ | ❌ | ❌ | Crear/listar backups |
| `restore` | ✅ | ❌ | ❌ | Restaurar backups |
| `user_management` | ✅ | ❌ | ❌ | CRUD usuarios del sistema |
| `configuration` | ✅ | ❌ | ❌ | Ajustes globales, CRUD empresas |
| `sync` | ✅ | ❌ | ❌ | Ejecutar sincronización |

¹ **Decisión documentada §DELETE**: el operador conserva el borrado de registros
operativos (conserva el comportamiento previo a la migración). El borrado de zonas
administrativas (backups, usuarios, empresas) requiere `admin`/`configuration`.

Rol desconocido o `NULL` en BD → **sin permisos** (fail-safe, nunca degrada a
más privilegios).

---

## 4. Endpoints

Clasificación de los 135 endpoints (auditoría completa, sin sin clasificar):

| Grupo | Nº | Protección |
|-------|---:|------------|
| CRUD por método HTTP (12 routers: albaranes, artículos, bancos, clientes, contabilidad, dashboard, estadísticas, extras, facturas, familias, proveedores, usuarios NNA/pagas) | 109 | `require_method_permission`: GET→`read`, POST→`create`, PUT/PATCH→`update`, DELETE→`delete` |
| Administrativos (backups, restaurar, ajustes, empresas escritura, usuarios sistema, sync, shutdown, diagnóstico) | 22 | Permisos explícitos: `backup`, `restore`, `configuration`, `user_management`, `sync`, `admin` (en `shutdown`: `admin` **global**) |
| Solo autenticación (`GET /me`, `cambiar-password`, `GET /empresas` con filtro) | 4 | `get_current_user` (401 si no autenticado) |
| Públicos (`POST /auth/login`, `POST /sync/push` con API-key, `GET /health`, `GET /`, `GET /api/version`) | 5 | Sin JWT (ver §6) |

Detalle por recurso:

- **`/api/auth`** — `login` (público; usuario inactivo → 401); `me` y
  `cambiar-password` (autenticado); `/usuarios` CRUD + `reset-password` →
  `user_management` **y aislamiento por empresa**: el listado filtra por la
  empresa del admin (más usuarios globales `NULL`), el alta de un admin con
  empresa se fuerza a su propia empresa, y PUT/DELETE/reset sobre usuarios de
  otra empresa → 404 (RPT-001/002).
- **`/api/empresas`** — `GET` lista filtrada por la empresa del usuario
  (sin empresa asignada = todas); `GET/PUT/DELETE /{id}` exigen pertenencia
  (`exigir_empresa`, EMP-001/002); `POST/PUT/DELETE` → `configuration`.
  **Decisión D-03 (v1.13.07)**: `POST /api/empresas` ahora exige además
  **admin global** (`empresa_id NULL`); un admin con empresa asignada recibe
  403. Antes cualquier admin con `configuration` podía crear empresas: generaba
  empresas huérfanas que su propio `GET /empresas` (filtrado por pertenencia)
  no le dejaba ver ni gestionar (PUT/DELETE → 404). El frontend oculta el
  botón "+ Nueva empresa" en el mismo caso.
- **`/api/ajustes`** — listar/crear backups → `backup`; restaurar → `restore`;
  guardar configuración → `configuration`.
  **Decisión D-01 (documentada)**: los backups son la **BD completa con todas
  las empresas** y **no se filtran por empresa**: cualquier admin, incluso con
  empresa asignada, puede listar/descargar/restaurarlos. Es coherente con
  "admin = administración total", pero implica que un admin de una empresa
  accede a datos globales vía backups.
- **`/api/sync`** — `POST /push` autenticado por **API-key de instalación**
  (mecanismo de dispositivo, no de usuario); `POST /ejecutar` → `sync`.
  El replay valida **tres capas**: la key solo puede escribir en sus
  `empresas`, `item.empresa_id` es la única fuente de verdad (un
  `payload.empresa_id` distinto se rechaza) y la entidad `uuid` solo se
  edita/borra si pertenece a esa empresa (SYNC-001/002/003).
- **`/api/contabilidad/diagnostico`** → `read` (desde v1.13.01: el operador
  también diagnostica; los POST de reparación/generación/cierre exigen `create`).
- **`POST /api/shutdown`** → **admin global** (`require_admin_global`: permiso
  `admin` **y** `empresa_id NULL`). **NUE-001 (v1.13.09)**: antes valía
  `require_admin` y cualquier admin de una empresa podía parar el servidor de
  **todas** las empresas (DoS global); ahora un admin con empresa asignada
  recibe 403 (mismo patrón que D-03). El frontend oculta el botón "Apagar" en
  el mismo caso. `KRITERIO_NO_SHUTDOWN=1` desactiva la parada real (tests).

---

## 5. Aislamiento multiempresa

- `UsuarioSistema.empresa_id`: `NULL` = todas las empresas (superusuario,
  compatibilidad con usuarios preexistentes); con valor = solo esas empresas.
  **Decisión D-02**: desde v1.13.04 un admin con empresa asignada **no puede
  crear usuarios globales ni de otra empresa** (el alta se fuerza a su empresa);
  crear usuarios con `empresa_id NULL` queda reservado a los admins globales.
- **Listados**: todos los queries con `empresa_id` pasan por `empresa_query`
  (el backend mete la empresa del usuario en la query).
- **Detalle/escritura**: `exigir_empresa()` comprueba la pertenencia del recurso
  antes de **leer o escribir** (la comprobación ocurre antes de mutar, no después).
  Si el objeto no tiene el atributo de empresa (esquemas `*Update`, que nunca lo
  incluyen) la comprobación se omite: la válida es la del recurso ya cargado
  (corrige el bug FN-001, que rechazaba también el recurso propio).
- **Referencias entre recursos**: cliente/proveedor/banco referenciados por un
  documento deben pertenecer a la misma empresa que el documento
  (`app/services/integridad.py`, REL-001), también en el replay de sync.
- Recurso ajeno o inexistente → **404** indistinguible (mensaje uniforme).
- Migración (§23): usuarios existentes con rol `NULL`/inválido pasan a
  `operador`; nunca a `admin`.

---

## 6. Tokens y sesiones (JWT)

- **Algoritmo** HS256; claims `sub` (id de usuario) + `exp`.
- **Caducidad**: 8 h (`JWT_EXPIRE_MINUTES`, por defecto 480).
- **Clave**: única variable `JWT_SECRET_KEY`. **No existe secreto por defecto**:
  si falta, se genera clave efímera por proceso y se avisa con `RuntimeWarning`
  (los tokens no sobreviven a un reinicio). En producción la genera
  `deploy/aprovisionar_servidor.sh` con `openssl rand`.
- **Invalidación efectiva**: el rol/activo se releen de la BD en cada petición
  → desactivar o degradar un usuario surte efecto inmediato (el token ya emitido
  no lo respalda).
- Contraseñas: `bcrypt` (hash con salt por usuario).

---

## 7. Frontend: reflejo, no seguridad

- `usePermissions()` / `has(perm)` ocultan controles inútiles (botones de
  alta/edición/borrado para `solo_lectura`, navegación administrativa, apagado).
- `RequierePermiso` en `App.jsx` protege rutas `/ajustes` (`configuration`) y
  `/usuarios-sistema` (`user_management`) redirigiendo a `/inicio`.
- **Esto nunca es seguridad**: cualquier llamada directa a la API con un token
  válido vuelve a pasar por `permissions.py`. La política vive y se valida en el
  backend.
- **Exports y descargas**: `window.open` no envía el header `Authorization` →
  401 (FE-001). Desde v1.13.04 los exports (estadísticas, pagas, contabilidad)
  y la descarga de backups usan `fetch` con Bearer + blob
  (`frontend/src/services/descargas.js`).

---

## 8. Pruebas

- `tests/test_roles_permisos.py` — 401 (sin token, token inválido, firmado con
  otra clave, expirado, usuario inactivo, rol cambiado en BD), 403 de
  `solo_lectura` en escritura, operador CRUD + 403 en administración, admin, y
  **404 multiempresa** (clientes, facturas, empresas, listas y creación cruzadas).
- `tests/test_auditoria_regresion.py` — **21 tests de regresión de la
  auditoría** (v1.13.04): PUT propio con empresa (FN-001), sync cross-company
  (SYNC-001..003), empresas PUT/DELETE cross (EMP-001/002), usuarios del
  sistema por empresa (RPT-001/002), FK entre empresas (REL-001) y 404
  uniforme (IDOR-001). Si uno falla, la vulnerabilidad ha regresado.
- Suite completa: **276 tests**
  (`KRITERIO_NO_SHUTDOWN=1 ./venv/bin/python -m pytest -q`).
- `tests/test_auditoria_expectativas.py` — **85 pruebas de la re-auditoría**
  (`docs/auditoria_seguridad.md`), **85/85 en verde** tras las correcciones de
  §F. Viven en el repo desde v1.13.06 (antes en `/tmp/opencode/audit/`);
  autocontenida (fixture `env` propia, no usa `conftest.py`).
- **Frontend** (`npm test` / `npx vitest run`, v1.13.05): **128 tests en 16
  ficheros** con Vitest + testing-library (jsdom).
  - Unidad: `usePermissions` (matriz rol×permiso), `useAuth` e interceptores
    axios (401 → logout+redirect, `detail` → `Error.message`), descargas
    (FE-001: `fetch` con Bearer, no `window.open`), formateadores.
  - Componentes: `CrudPage` (matriz de permisos CRUD y ciclo de vida),
    `Layout`/navegación por rol, Modal/ConfirmModal/Paginación.
  - Rutas: `ProtectedRoute` y `RequierePermiso` (`/ajustes`, `/usuarios-
    sistema`, comodines).
  - Smoke por página y rol (admin vs `solo_lectura`): login, selector de
    empresas, inicio, CRUD básicas, documentos/facturas, bancos, contabilidad
    (8 pestañas), ingresos/gastos + export con token, extras, ajustes.
  - El API se mockea sustituyendo `api.defaults.adapter` (interceptores
    reales se ejercitan); configuración en `frontend/vitest.config.js` y
    `frontend/src/__tests__/helpers.jsx`.
