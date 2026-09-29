# Seguridad y autorización — Kriterio Vault

> Documento vivo. Última revisión: **v1.13.00** (2026-09-28).
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
de registros ajenos (§aislamiento multiempresa).

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
| Administrativos (backups, restaurar, ajustes, empresas escritura, usuarios sistema, sync, shutdown, diagnóstico) | 22 | Permisos explícitos: `backup`, `restore`, `configuration`, `user_management`, `sync`, `admin` |
| Solo autenticación (`GET /me`, `cambiar-password`, `GET /empresas` con filtro) | 4 | `get_current_user` (401 si no autenticado) |
| Públicos (`POST /auth/login`, `POST /sync/push` con API-key, `GET /health`, `GET /`, `GET /api/version`) | 5 | Sin JWT (ver §6) |

Detalle por recurso:

- **`/api/auth`** — `login` (público; usuario inactivo → 401); `me` y
  `cambiar-password` (autenticado); `/usuarios` CRUD + `reset-password` →
  `user_management`.
- **`/api/empresas`** — `GET` lista filtrada por la empresa del usuario
  (sin empresa asignada = todas); `GET /{id}` exige pertenencia; `POST/PUT/DELETE`
  → `configuration`.
- **`/api/ajustes`** — listar/crear backups → `backup`; restaurar → `restore`;
  guardar configuración → `configuration`.
- **`/api/sync`** — `POST /push` autenticado por **API-key de instalación**
  (mecanismo de dispositivo, no de usuario); `POST /ejecutar` → `sync`.
- **`/api/contabilidad/diagnostico`** → `read` (desde v1.13.01: el operador
  también diagnostica; los POST de reparación/generación/cierre exigen `create`).
- **`POST /api/shutdown`** → `admin` + `KRITERIO_NO_SHUTDOWN=1` desactiva la
  parada real (usado por los tests).

---

## 5. Aislamiento multiempresa

- `UsuarioSistema.empresa_id`: `NULL` = todas las empresas (superusuario,
  compatibilidad con usuarios preexistentes); con valor = solo esas empresas.
- **Listados**: todos los queries con `empresa_id` pasan por `empresa_query`
  (el backend mete la empresa del usuario en la query).
- **Detalle/escritura**: `exigir_empresa()` comprueba la pertenencia del recurso
  antes de **leer o escribir** (la comprobación ocurre antes de mutar, no después).
- Recurso ajeno o inexistente → **404** indistinguible.
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

---

## 8. Pruebas

- `tests/test_roles_permisos.py` — **59 tests**: 401 (sin token, token inválido,
  firmado con otra clave, expirado, usuario inactivo, rol cambiado en BD),
  403 de `solo_lectura` en escritura, operador CRUD + 403 en administración,
  admin, y **404 multiempresa** (clientes, facturas, empresas, listas y creación
  cruzadas).
- Suite completa: **160 tests** (`KRITERIO_NO_SHUTDOWN=1 ./venv/bin/python -m pytest -q`).
- Pendiente conocido: **sin tests de frontend** (riesgo de regresión UI al
  ocultar controles; ver RECOMENDACIONES).
