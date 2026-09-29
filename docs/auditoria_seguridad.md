# INFORME DE AUDITORÍA DE SEGURIDAD — Kriterio Vault (multiempresa + RBAC)

| Campo | Valor |
|---|---|
| Versión auditada | `1.13.02` (`4109f57`, tag `v1.13.02`) |
| Fecha | 2026-09-29 |
| Alcance | Backend FastAPI + frontend React + documentación (`SECURITY.md`, `RECOMENDACIONES.md`) |
| Método | Estático (introspección de rutas + lectura de código) + dinámico (85 pruebas HTTP con `TestClient`, 6 usuarios/roles, 4 empresas, BD SQLite en memoria) |
| Modificaciones durante la auditoría | **NINGUNA en código/BD/dependencias** — `git status` limpio (0 líneas) durante toda la fase de auditoría; las pruebas y los resultados viven en `/tmp/opencode/audit/` (`test_auditoria.py`, `salida_final.txt`). Este documento es el único entregable añadido al proyecto |
| Suite oficial del proyecto | **170 passed** (`KRITERIO_NO_SHUTDOWN=1 ./venv/bin/python -m pytest -q`) |
| Suite de auditoría | **85 pruebas: 73 PASS / 12 FAIL — los 12 FAIL son los hallazgos F-01…F-11** (un test codifica un hallazgo compuesto) |

> **ACTUALIZACIÓN (v1.13.04, 2026-09-29):** las correcciones de §F **ya están
> aplicadas** en la versión 1.13.04 (SYNC-001..003, EMP-001/002, FN-001,
> RPT-001/002, REL-001, IDOR-001, FE-001; D-01/D-02/D-03 documentados en
> `SECURITY.md`). **Re-auditoría: 85/85 PASS** y suite oficial ampliada a
> **191 tests** (21 regresiones nuevas en
> `backend/tests/test_auditoria_regresion.py`). El cuerpo del informe se
> conserva tal cual como fotografía del estado auditado (1.13.02).

---

## A. Resumen ejecutivo

El backend tiene una **base de autorización sólida y bien diseñada**: cadena JWT→rol→permiso→empresa (`app/services/permissions.py`), matriz de roles única (`ROLE_PERMISSIONS`), 404 deliberado para recursos ajenos, y aislamiento por empresa correcto en **lectura, listados, filtros, creación y borrado** de los 14 recursos muestreados. La escalada de privilegios por JWT está bloqueada (claims de rol ignorados; la BD manda) y la zona admin responde 403 a no-admins.

Sin embargo, la auditoría encuentra **2 vulnerabilidades altas, 3 medias, 1 baja y 2 problemas funcionales altos**:

- **ALTA · SYNC-001/002/003**: `POST /api/sync/push` valida la empresa del *item* contra la instalación, pero `replay_operacion` escribe usando el `payload`/`uuid` **sin revalidar** → una key limitada a empresa 1 puede **crear, modificar y borrar** registros de cualquier empresa (confirmado dinámicamente: cliente de e2 creado/modificado/borrado con `ok=True`).
- **ALTA · EMP-001/EMP-002**: `PUT/DELETE /api/empresas/{id}` exigen solo `configuration` **sin `exigir_empresa`** → un admin de empresa 1 **editó la empresa 2 (200)** y **borró la empresa 4 (200)**.
- **MEDIA · RPT-001/RPT-002**: `/api/auth/usuarios` no filtra por empresa → un admin de empresa 1 **ve** usuarios de empresa 2 y **creó** un usuario asignado a empresa 2 (201).
- **MEDIA · REL-001**: la creación **no valida la pertenencia de las relaciones** → factura de e1 con cliente de e2 y movimiento de e1 con banco de e2 (201).
- **ALTA funcional · FN-001**: los `PUT` ejecutan `exigir_empresa(user, data)` con schemas `Update` que **no llevan `empresa_id`** → cualquier usuario **con empresa asignada recibe 404 también en sus propios recursos** (fail-closed; 14 endpoints confirmados). No es una fuga, pero **rompe la edición para el usuario multiempresa típico**.
- **BAJA · IDOR-001**: el detalle del 404 difiere (`"Recurso no encontrado"` vs `"Cliente no encontrado"`) y permite **enumerar** qué ids existen en otras empresas; contradice `SECURITY.md:21`.
- **MEDIA funcional · FE-001**: los 6 exports y la descarga de backups usan `window.open` **sin cabecera `Authorization`** → el backend responde 401 (confirmado dinámicamente): esos botones fallan en navegador.

Áreas verificadas **sin problemas**: JWT (firma, expiración, `alg=none`, sub inválido, usuario inactivo, claims manipulados), escalada por API de usuarios, permisos de zona admin/backups/shutdown/sync, aislamiento en asientos (PUT/DELETE), renumerar, reparar saldos, reordenar, pagas, NNA, exports con Bearer, mass assignment de `empresa_id`, barrido de 110+ GET sin token → 401.

---

## B. Alcance, metodología y entorno

**Entorno**: Linux, Python 3.13 (`backend/venv`), SQLite en memoria por test, `KRITERIO_NO_SHUTDOWN=1`. Frontend Node 22 (análisis estático; lint/build ya verificados en v1.13.00).

**Fases**:
1. **Estática**: introspección del árbol de dependencias de las 133 peticiones (auth/permiso/`empresa_query` por endpoint), lectura de `permissions.py`, `auth.py`, los 16 routers, schemas y frontend/docs.
2. **Dinámica**: 85 pruebas en `/tmp/opencode/audit/test_auditoria.py` con 6 usuarios (`admin_global`, `admin_emp1`, `op_emp1`, `op_emp2`, `ro_emp1`, `op_global`), 4 empresas y ~30 recursos sembrados por API. Cada test afirma la **expectativa de seguridad**: fallo = hallazgo.
3. **Suite oficial**: 170 tests del proyecto en verde.
4. **Integridad**: `git status --porcelain` = 0 líneas en todo momento (antes de añadir este informe).

**Figuras de usuario**: `empresa_id = NULL` = todas las empresas (por diseño documentado); con valor = solo esa empresa; roles `admin`/`operador`/`solo_lectura` con la matriz de `ROLE_PERMISSIONS`.

**NO EJECUTADO — entorno/alcance incompleto** (no simulado):
- Rate limiting real (login 10/min, sync 60/min): código presente (`slowapi`), no se ejercitó para no bloquear.
- `POST /api/ajustes/backup`, `restaurar*`, descarga real de backup: crearían/escribirían archivos o la BD del proyecto → prohibido por la regla de no-modificación (la autorización sí está probada: 200/403/401 según rol).
- `POST /api/shutdown` efectivo (solo se probó 403 a no-admins).
- Postgres (la instalación de sincronización del servidor usa Postgres; las pruebas corren sobre SQLite), TLS/HTTPS, carga, dependencias de terceros (`pip-audit` no instalado).

---

## C. Inventario de endpoints (133 peticiones API)

Públicos (sin JWT): `POST /api/auth/login`, `POST /api/sync/push` (API-key `X-SYNC-KEY`, SHA-256 en BD), `GET /api/version`. El resto —130— exigen Bearer (barrido dinámico: todos los GET → 401).

| Módulo (ficheros) | Peticiones | Auth | Permiso | Aislamiento de empresa | Riesgo |
|---|---|---|---|---|---|
| `clientes.py` | 5 | JWT | `require_method_permission` (GET→read, POST→create, PUT→update, DELETE→delete) | GET lista: `empresa_query` · GET/PUT/DELETE id: `exigir_empresa(previo)` · POST: `exigir_empresa(data)` | MEDIO (FN-001 en PUT) |
| `proveedores.py` | 5 | JWT | idem | idem | MEDIO (FN-001) |
| `articulos.py` | 5 | JWT | idem | idem | MEDIO (FN-001) |
| `familias.py` | 5 | JWT | idem | idem | MEDIO (FN-001) |
| `facturas.py` (emi/rec) | 12 | JWT | idem | idem + renumerar con `exigir(body)` | MEDIO (FN-001, REL-001) |
| `albaranes.py` (emi/rec) | 10 | JWT | idem | idem | MEDIO (FN-001, REL-001) |
| `bancos.py` (bancos/movs/vtos) | 14 | JWT | idem | idem + reparar/reordenar con `exigir(previo)` | MEDIO (FN-001) |
| `extras.py` | 7 | JWT | idem | idem + renumerar `exigir(body)` | MEDIO (FN-001) |
| `usuarios.py` (NNA/pagas) | 14 | JWT | idem | `empresa_query` en listas; `exigir` en POST/PUT/DELETE/pagas/mes | BAJO (probado OK) |
| `contabilidad.py` | 30 | JWT | idem + `require_read` en `diagnostico` | `empresa_query` en todas las lecturas; `exigir` en POST/PUT asientos y cuentas; servicio escopado por `(empresa_id, asiento)` | BAJO (probado OK) |
| `dashboard.py` | 1 | JWT | `require_method_permission` | `empresa_query` | BAJO |
| `estadisticas.py` | 8 | JWT | `require_method_permission` | `empresa_query` (incluye exports) | BAJO (FE-001) |
| `empresas.py` | 5 | JWT | GET: solo `get_current_user` · POST/PUT/DELETE: `require_configuration` | GET lista/obtener: `exigir_empresa` · **PUT/DELETE: SIN `exigir_empresa`** | **ALTO (EMP-001/002)** |
| `auth.py` | 7 | JWT (`login` público) | `me`/`cambiar-password`: auth · `/usuarios*`: `user_management` | **sin filtro de empresa** (global por diseño/admin) | **MEDIO (RPT-001/002)** |
| `ajustes.py` | 7 | JWT | `backup` (backups, download, borrar, manual) · `configuration` (PUT config) · `restore` (restaurar*) | sin recorte por empresa (backup = BD completa) | INFORMATIVO (D-01) |
| `sync.py` | 2 | `push`: API-key · `ejecutar`: `sync` | — | validación de empresa **parcial** (solo `item.empresa_id`) | **ALTO (SYNC-001/002/003)** |
| `main.py`/`health` | 1+ | JWT | `admin` (`POST /api/shutdown`) / `version` público | — | BAJO |

Detalle de las 133 líneas (método, ruta, dependencias detectadas por introspección) disponible en la salida de la fase estática (`/tmp/opencode/audit/`); los mecanismos por router coinciden con `SECURITY.md` §6 salvo lo apuntado en hallazgos.

---

## D. Matriz RBAC (roles × operaciones)

Leyenda: ✅ permitido · ❌ 403 · ⚠️ permitido con matiz. Evidencia = test de la suite de auditoría (D=dinámico).

| Operación | admin | operador | solo_lectura | Evidencia |
|---|---|---|---|---|
| GET listado/lectura recursos (con `?empresa_id`) | ✅ 200 | ✅ 200 | ✅ 200 | D (matriz, listados) |
| POST crear recurso | ✅ 201 | ✅ 201 | ❌ 403 | D (matriz) |
| PUT recurso propio | ✅ 200 (global) ⚠️ 404 con empresa | ✅ 200 (global) ⚠️ 404 con empresa | ❌ 403 | D (FN-001) |
| DELETE recurso propio | ✅ 204 | ✅ 204 | ❌ 403 | D (matriz) |
| GET `/api/ajustes/backups` | ✅ 200 (cualquier empresa del admin) | ❌ 403 | ❌ 403 | D |
| POST backup / download / DELETE backup | ✅ 200 (no ejecutado) | ❌ 403 | ❌ 403 | D autorización / NO ejecución |
| PUT `/api/ajustes/config` | ✅ (no ejecutado) | ❌ 403 | ❌ 403 | D autorización |
| POST `restaurar*` | ✅ (no ejecutado) | ❌ 403 | ❌ 403 | D autorización |
| GET/POST/PUT/DELETE `/api/auth/usuarios*` | ✅ 200/201 | ❌ 403 | ❌ 403 | D |
| POST/PUT/DELETE `/api/empresas*` | ✅ 201/200/200 | ❌ 403 | ❌ 403 | D |
| GET `/api/empresas` | ✅ filtrado | ✅ filtrado | ✅ filtrado | D |
| POST `/api/shutdown` | ✅ (no ejecutado) | ❌ 403 | ❌ 403 | D autorización |
| POST `/api/sync/ejecutar` | ✅ (no ejecutado) | ❌ 403 | ❌ 403 | D autorización |
| GET `contabilidad/diagnostico` | ✅ 200 | ✅ 200 | ✅ 200 | D (v1.13.01) |
| POST asientos/cierre/generar-pendientes | ✅ | ✅ create | ❌ 403 | D |
| renumerar / reparar / reordenar | ✅ 200 | ✅ 200 | ❌ 403 | D |
| Exports (con Bearer) | ✅ 200 | ✅ 200 | ✅ 200 | D |
| `login` / `me` / `cambiar-password` | ✅ | ✅ | ✅ | D |

Matriz de permisos de origen (`permissions.py:40-62`): `admin` = todos · `operador` = read/create/update/delete · `solo_lectura` = read. Rol desconocido → sin permisos (fail-safe, código).

---

## E. Matriz multiempresa (escenarios × resultado)

| # | Escenario | Esperado | Real | Resultado |
|---|---|---|---|---|
| 1 | GET recurso individual de otra empresa (12 recursos muestreados) | 404 | 404 | **PASS** |
| 2 | GET listado con `?empresa_id` propio | 200 + solo sus recursos | 200, `empresa_id` correcto | **PASS** |
| 3 | GET listado `?empresa_id` ajeno (12 endpoints: clientes, dashboard, facturas, bancos, usuarios, estadísticas, contabilidad, albaranes, extras, vencimientos, pagas, NNA) | 404 | 404 | **PASS** |
| 4 | GET `?empresa_id` inexistente (999) con usuario de empresa | 404 | 404 | **PASS** |
| 5 | CREATE con `empresa_id` ajeno (clientes, NNA, pagas, pagas/mes) | 404 sin escribir | 404, BD intacta | **PASS** |
| 6 | CREATE con `empresa_id` propio | 201 y asignación correcta | 201 | **PASS** |
| 7 | PUT recurso ajeno (11 recursos) | 404 sin cambios | 404, sin cambios | **PASS** |
| 8 | PUT recurso propio **con empresa asignada** (14 endpoints) | 200 | **404** | **FAIL → FN-001** |
| 9 | PUT recurso propio con usuario global (empresa NULL) | 200 | 200 | **PASS** |
| 10 | DELETE recurso ajeno (clientes, cuentas, extras, NNA, bancos, facturas) | 404 sin borrar | 404, intacto | **PASS** |
| 11 | DELETE recurso propio con empresa asignada | 204 | 204 | **PASS** |
| 12 | Mass assignment `PUT {"empresa_id": ajeno}` | ignorado, empresa intacta | campo no existe en `Update`; empresa intacta | **PASS** |
| 13 | Relación cross-company en CREATE (factura e1→cliente e2; movimiento e1→banco e2) | 400/404 | **201** | **FAIL → REL-001** |
| 14 | `PUT/DELETE /api/empresas/{otra}` con `admin_emp1` | 404 | **200 / 200** (edita y borra) | **FAIL → EMP-001/002** |
| 15 | `GET /api/empresas/{otra}` con `admin_emp1` | 404 | 404 | **PASS** |
| 16 | `GET /api/auth/usuarios` con `admin_emp1` | sin usuarios de otras empresas | **incluye `op_emp2` (e2)** | **FAIL → RPT-001** |
| 17 | `POST /api/auth/usuarios` con `empresa_id` ajeno | rechazar | **201** | **FAIL → RPT-002** |
| 18 | Sync push `C/U/D` con key limitada a e1 hacia e2 | `ok:false`, sin escribir | **`ok:true`, escribe/borra en e2** | **FAIL → SYNC-001/002/003** |
| 19 | Sync push con `empresa_id` de item no autorizado | `ok:false` | `ok:false` (solo se valida el item) | PASS (parcial) |
| 20 | Asientos PUT/DELETE cross (número ajeno con body/query propio o ajeno) | 404 | 404 (servicio escopado `(empresa_id, asiento)`) | **PASS** |
| 21 | renumerar / reparar_saldos / reordenar cross vs propio | 404 / 200 | 404 / 200 | **PASS** |
| 22 | Exports con empresa ajena (estadísticas, gastos, pagas, contabilidad) | 404 | 404 | **PASS** |
| 23 | NNA: PUT/DELETE ajeno, crear ajeno | 404 | 404 | **PASS** |
| 24 | Usuario `empresa_id NULL` accede a ambas empresas | sí (por diseño) | sí | PASS (decisión documentada) |
| 25 | Detalle 404 id-ajeno vs id-inexistente | idéntico | **diferente** | **FAIL → IDOR-001** |

---

## F. Hallazgos

> Formato: `ID / SEVERIDAD / TIPO / MÓDULO / ARCHIVO:LÍNEA / ENDPOINT / MÉTODO / ROL / EMPRESA / ESCENARIO / RESULTADO ESPERADO / RESULTADO REAL / IMPACTO / EVIDENCIA / RECOMENDACIÓN`. **No se ha aplicado ninguna corrección.**

---

### F-01 · SYNC-001
**ID:** SYNC-001 · **SEVERIDAD:** ALTA · **TIPO:** vulnerabilidad (autorización cross-company)
**MÓDULO:** sincronización · **ARCHIVO:LÍNEA:** `backend/app/api/sync.py:36-47` + `backend/app/services/sync_replay.py:106-124`
**ENDPOINT:** `/api/sync/push` · **MÉTODO:** POST · **ROL:** (sin usuario; API-key de instalación) · **EMPRESA:** cualquierCompanyId
**ESCENARIO:** Instalación registrada con `empresas="1"` (límite explícito). Se envía `item={tabla:"clientes", empresa_id:1 (autorizado), payload:{nombre:"SYNC-HACK", empresa_id:2}}`.
**RESULTADO ESPERADO:** `ok:false`; no se escribe en empresa 2 (la instalación no está autorizada para e2).
**RESULTADO REAL:** `ok:true`; **cliente creado en empresa 2** (`fila.empresa_id=2`).
**IMPACTO:** escritura transversal en cualquier empresa: quien posea una API-key —incluso una instalación limitada a una sola empresa— puede insertar registros en todas. Alteración de datos contables/financieros de otras compañías.
**EVIDENCIA:** `test_sync_create_payload_empresa_ajena_bloqueado` → `push creó cliente en empresa 2 con key limitada a empresa 1 (ok=True, fila=2)`.
**RECOMENDACIÓN (no aplicada):** en `replay_operacion`, fijar `datos["empresa_id"] = item.empresa_id` (y rechazar `payload.empresa_id` distinto), o validar antes de cada replay que `payload.empresa_id == item.empresa_id` y que el uuid no pertenezca a otra empresa.

---

### F-02 · SYNC-002
**ID:** SYNC-002 · **SEVERIDAD:** ALTA · **TIPO:** vulnerabilidad (IDOR de actualización)
**MÓDULO:** sincronización · **ARCHIVO:LÍNEA:** `backend/app/services/sync_replay.py:125-133` (búsqueda por `uuid` sin empresa)
**ENDPOINT:** `/api/sync/push` · **MÉTODO:** POST · **ROL:** API-key limitada a e1 · **EMPRESA:** 2
**ESCENARIO:** `item={tabla:"clientes", empresa_id:1, operacion:"U", entidad_uuid:<uuid de cliente B (e2)>, payload:{nombre:"SYNC-HACK-U"}}`.
**RESULTADO ESPERADO:** `ok:false`; cliente B intacto.
**RESULTADO REAL:** `ok:true`; **cliente B renombrado a `SYNC-HACK-U`**.
**IMPACTO:** modificación arbitraria de registros de otras empresas vía sync (el `existente` se busca solo por `uuid`).
**EVIDENCIA:** `test_sync_update_recurso_ajeno_bloqueado` → `(ok=True, nombre='SYNC-HACK-U')`.
**RECOMENDACIÓN (no aplicada):** filtrar la búsqueda por `empresa_id=item.empresa_id` además del `uuid` y rechazar si no coincide.

---

### F-03 · SYNC-003
**ID:** SYNC-003 · **SEVERIDAD:** ALTA · **TIPO:** vulnerabilidad (IDOR de borrado)
**MÓDULO:** sincronización · **ARCHIVO:LÍNEA:** `backend/app/services/sync_replay.py:135-141` (rama `D`)
**ENDPOINT:** `/api/sync/push` · **MÉTODO:** POST · **ROL:** API-key limitada a e1 · **EMPRESA:** 2
**ESCENARIO:** `operacion:"D"` con el `uuid` de un cliente de e2 y `item.empresa_id=1`.
**RESULTADO ESPERADO:** `ok:false`; cliente B sigue existiendo.
**RESULTADO REAL:** `ok:true`; **cliente B borrado**.
**IMPACTO:** destrucción de datos de otras empresas (pérdida de clientes, facturas, asientos si se aplica a esas tablas).
**EVIDENCIA:** `test_sync_delete_recurso_ajeno_bloqueado` → `push borró un cliente de empresa 2 con key de empresa 1 (ok=True)`.
**RECOMENDACIÓN (no aplicada):** igual que SYNC-002 (empresa en la consulta) + `item.empresa_id` como única fuente.

---

### F-04 · EMP-001
**ID:** EMP-001 · **SEVERIDAD:** ALTA · **TIPO:** vulnerabilidad (escritura cross-company en zona administrativa)
**MÓDULO:** empresas · **ARCHIVO:LÍNEA:** `backend/app/api/empresas.py:83-92`
**ENDPOINT:** `/api/empresas/2` · **MÉTODO:** PUT · **ROL:** admin · **EMPRESA:** asignada a 1 (objetivo: 2)
**ESCENARIO:** `admin_emp1` (rol admin, `empresa_id=1`) envía `{"nombre":"EMPRESA COMPROMETIDA"}` a la empresa 2. `actualizar_empresa` exige solo `require_configuration` y **no llama `exigir_empresa`** (a diferencia de `obtener_empresa`, sí la llama con `campo="id"`).
**RESULTADO ESPERADO:** 404; nombre de e2 intacto.
**RESULTADO REAL:** **200**; `empresa 2.nombre = "EMPRESA COMPROMETIDA"` en BD.
**IMPACTO:** un admin recortado a una empresa puede alterar nombre/código/estado de empresas ajenas (fraude de identificación, desactivación de empresas rivales).
**EVIDENCIA:** `test_admin_emp1_put_empresa_ajena_bloqueado` → `PUT devolvió 200`.
**RECOMENDACIÓN (no aplicada):** añadir `exigir_empresa(current_user, empresa, campo="id")` al inicio de `actualizar_empresa` (igual que `obtener_empresa`).

---

### F-05 · EMP-002
**ID:** EMP-002 · **SEVERIDAD:** ALTA · **TIPO:** vulnerabilidad (borrado cross-company en zona administrativa)
**MÓDULO:** empresas · **ARCHIVO:LÍNEA:** `backend/app/api/empresas.py:95-104`
**ENDPOINT:** `/api/empresas/4` · **MÉTODO:** DELETE · **ROL:** admin · **EMPRESA:** asignada a 1 (objetivo: 4)
**ESCENARIO:** `admin_emp1` borra la empresa 4 (vacía; la única guardia es `_empresa_tiene_datos`).
**RESULTADO ESPERADO:** 404.
**RESULTADO REAL:** **200** — empresa 4 eliminada de la BD.
**IMPACTO:** pérdida de empresas ajenas (y con `_borrar_empresa`, de sus datos si estuvieran vacías solo por recién creadas). Eliminación irreversible de la unidad de negocio.
**EVIDENCIA:** `test_admin_emp1_delete_empresa_ajena_bloqueado` → `DELETE 200`.
**RECOMENDACIÓN (no aplicada):** `exigir_empresa(current_user, empresa, campo="id")` también en `eliminar_empresa`.

---

### F-06 · RPT-001
**ID:** RPT-001 · **SEVERIDAD:** MEDIA · **TIPO:** debilidad (fuga de información entre empresas)
**MÓDULO:** usuarios del sistema · **ARCHIVO:LÍNEA:** `backend/app/api/auth.py:76-93`
**ENDPOINT:** `/api/auth/usuarios` · **MÉTODO:** GET · **ROL:** admin · **EMPRESA:** 1
**ESCENARIO:** `admin_emp1` lista los usuarios del sistema.
**RESULTADO ESPERADO:** solo usuarios de empresa 1 (y globales).
**RESULTADO REAL:** 200 incluyendo `op_emp2` con `empresa_id:2` (nombre, email, rol, actividad de otra empresa).
**IMPACTO:** fuga de datos de identidad y de la estructura de usuarios de otras empresas; base para dirigir ataques (qué admin/operador existe en la empresa rival).
**EVIDENCIA:** `test_admin_emp1_usuarios_sin_recororte_empresa` → lista con `{'id': 4, 'username': 'op_emp2', 'empresa_id': 2}`.
**RECOMENDACIÓN (no aplicada):** filtrar por `current_user.empresa_id` (como hace `GET /api/empresas`) salvo `empresa_id IS NULL`. Documentar si la visibilidad global es intencionada.

---

### F-07 · RPT-002
**ID:** RPT-002 · **SEVERIDAD:** MEDIA · **TIPO:** vulnerabilidad (escritura cross-company)
**MÓDULO:** usuarios del sistema · **ARCHIVO:LÍNEA:** `backend/app/api/auth.py:96-115`
**ENDPOINT:** `/api/auth/usuarios` · **MÉTODO:** POST · **ROL:** admin · **EMPRESA:** 1 → crea en 2
**ESCENARIO:** `admin_emp1` crea `{"username":"invitado_e2","rol":"operador","empresa_id":2}`.
**RESULTADO ESPERADO:** rechazo (400/403/404) o creación solo en e1.
**RESULTADO REAL:** **201** — usuario operador creado adscrito a empresa 2 por el admin de empresa 1.
**IMPACTO:** inserción de cuentas (incluso con rol `admin`) en empresas ajenas → control remoto de la empresa víctima.
**EVIDENCIA:** `test_admin_emp1_crear_usuario_en_otra_empresa_bloqueado` → `HTTP 201`.
**RECOMENDACIÓN (no aplicada):** exigir que `data.empresa_id` sea nulo o igual a `current_user.empresa_id` (además de filtrar en el PUT, que hoy tampoco valida la empresa de destino).

---

### F-08 · REL-001
**ID:** REL-001 · **SEVERIDAD:** MEDIA · **TIPO:** debilidad (referencias cruzadas entre empresas)
**MÓDULO:** facturación / bancos · **ARCHIVO:LÍNEA:** `backend/app/api/facturas.py:65-66`, `backend/app/api/bancos.py:237-238` (solo se valida `empresa_id` del payload, no el de los recursos referenciados)
**ENDPOINT:** `/api/facturas/emitidas`, `/api/bancos/movimientos` · **MÉTODO:** POST · **ROL:** operador · **EMPRESA:** 1 (recursos de 2)
**ESCENARIO:** operador de e1 crea factura con `cliente=<id de e2>` y movimiento con `banco=<id de e2>`.
**RESULTADO ESPERADO:** 400/404 (el cliente/banco no pertenece a la empresa de la factura).
**RESULTADO REAL:** **201 en ambos casos**; el registro queda en e1 apuntando a recursos de e2.
**IMPACTO:** integridad referencial entre empresas: informes de una empresa incluyen datos heredados de otra; posibles fugas al listar las relaciones; contabilización sobre cuentas/bancos ajenos.
**EVIDENCIA:** `test_create_relacion_cross_company_bloqueada` → `factura empresa 1 creada con cliente de empresa 2 (201); movimiento empresa 1 creado con banco de empresa 2 (201)`.
**RECOMENDACIÓN (no aplicada):** cargar el recurso referenciado (`Cliente`, `Banco`, `Proveedor`) y aplicar `exigir_empresa(user, ...)` antes de crear (patrón ya usado en los GET individuales).

---

### F-09 · FN-001
**ID:** FN-001 · **SEVERIDAD:** ALTA (funcional; fail-closed, **no** es fuga) · **TIPO:** bug funcional / regresión multiempresa
**MÓDULO:** todos los CRUD · **ARCHIVO:LÍNEA:** patrón `exigir_empresa(user, data)` en PUT — `clientes.py:47`, `proveedores.py:47`, `articulos.py:46`, `familias.py:37`, `bancos.py:176/251/323`, `extras.py:55`, `facturas.py:76/143`, `albaranes.py:48/98`, `contabilidad.py:47`, `usuarios.py:50`; causa raíz en `permissions.py:162-171` (`getattr(obj, "empresa_id", None)` → `None` cuando el schema no lo lleva) y `puede_ver_empresa:150-153` (`None` → `False` si el usuario tiene empresa)
**ENDPOINT:** 14 PUT (ver lista) · **MÉTODO:** PUT · **ROL:** admin/operador/solo_lectura con `empresa_id` asignado · **EMPRESA:** cualquierCompanyId
**ESCENARIO:** usuario con `empresa_id=1` edita un recurso **de su propia empresa**. Los schemas `*Update` **no tienen campo `empresa_id`** (confirmado: `ClienteUpdate`), por lo que la segunda llamada `exigir_empresa(user, data)` recibe `None` → 404 siempre.
**RESULTADO ESPERADO:** 200.
**RESULTADO REAL:** **404 en los 14 PUT muestreados**: clientes, proveedores, artículos, familias, bancos, movimientos, vencimientos, extras, facturas emitidas/recibidas, albaranes emitidos/recibidos, cuentas y usuarios NNA. (Excepción: **asientos sí funcionan** porque el PUT usa `AsientoCreate`, que sí lleva `empresa_id`.)
**IMPACTO:** los usuarios multiempresa (empresa asignada) **no pueden editar nada**; la app quedaría utilizable solo en modo global (`empresa_id NULL`). El aislamiento PUT "se cumple" trivialmente (también da 404 al recurso ajeno), por lo que los tests de 404 cruzado existentes no lo detectaron. Usuarios sin empresa asignada no lo notan (es el caso de los fixtures de la suite oficial: 170 tests en verde).
**EVIDENCIA:** `test_put_recurso_propio_deberia_200` → `PUT propio con empresa asignada devolvió 404`; `test_put_recursos_propios_varios_deberian_200` (7 rutas); `test_put_recursos_propios_avanzados_deberian_200` (6 rutas); contraste `test_put_asiento_propio_funciona_y_ajeno_404` → 200.
**RECOMENDACIÓN (no aplicada):** en los PUT eliminar la validación redundante `exigir_empresa(user, data)` (basta `exigir_empresa(user, previo)`) o usar un centinela en `exigir_empresa` que **omit**a la comprobación cuando el objeto no tiene el atributo; añadir tests de PUT con usuario **con** empresa (regresión). Mantener el chequeo en POST (los `*Create` sí llevan `empresa_id`).

---

### F-10 · IDOR-001
**ID:** IDOR-001 · **SEVERIDAD:** BAJA · **TIPO:** debilidad (enumeración de existencia)
**MÓDULO:** API general · **ARCHIVO:LÍNEA:** endpoints con `HTTPException(404, "<Recurso> no encontrado")` p. ej. `clientes.py:30`, frente al 404 genérico de `exigir_empresa`/`empresa_query` (`permissions.py:159,170` → `"Recurso no encontrado"`)
**ENDPOINT:** p. ej. `/api/clientes/{id}` · **MÉTODO:** GET · **ROL:** operador · **EMPRESA:** 1
**ESCENARIO:** se sondea `GET /api/clientes/{n}` con n de otra empresa vs n inexistente.
**RESULTADO ESPERADO:** misma respuesta en ambos casos (`SECURITY.md:21-23` lo promete: "no se revela existencia").
**RESULTADO REAL:** ajeno → `{"detail":"Recurso no encontrado"}`; inexistente → `{"detail":"Cliente no encontrado"}` → **el atacante puede enumerar ids válidos de otras empresas** (y de su propia empresa).
**IMPACTO:** reconocimiento para ataques posteriores; contradice la documentación de seguridad.
**EVIDENCIA:** `test_404_id_inexistente_mismo_detalle_que_ajeno`.
**RECOMENDACIÓN (no aplicada):** unificar el `detail` de los 404 de "no encontrado" y "no pertenece a la empresa" (mensaje único, p. ej. `"Recurso no encontrado"`) en todos los routers.

---

### F-11 · FE-001
**ID:** FE-001 · **SEVERIDAD:** MEDIA (funcional) · **TIPO:** bug funcional · **MÓDULO:** frontend exports
**ARCHIVO:LÍNEA:** `frontend/src/services/estadisticas.js:32,37`, `usuarios.js:34,45`, `ajustes.js:12`, `contabilidad.js:69`
**ENDPOINT:** `/api/estadisticas/periodo/*/export`, `/api/usuarios/pagas/export`, `/api/usuarios/pagas/resumen-anual/export`, `/api/contabilidad/export/*`, `/api/ajustes/backup/download/{n}` · **MÉTODO:** GET · **ROL:** cualquiera autenticado · **EMPRESA:** propia
**ESCENARIO:** el frontend abre la URL con `window.open(...)`, que **no puede añadir la cabecera `Authorization`**; no se pasa token por query.
**RESULTADO ESPERADO:** descarga del fichero.
**RESULTADO REAL:** **401** en el navegador (confirmado: `GET ... sin Bearer → 401`; con Bearer → 200). Todos los exports y la descarga de backups estarían rotos en la UI.
**IMPACTO:** imposibilidad funcional de exportar/descargar; posible presión para "arreglarlo" desactivando la autenticación (riesgo futuro).
**EVIDENCIA:** `test_export_requiere_autenticacion`, `test_backup_download_sin_auth_401`.
**RECOMENDACIÓN (no aplicada):** usar `fetch` con Bearer → `blob` + `<a download>`, o soporte de token corto en query solo para exports con expiración corta, o cookie httpOnly.

---

### F-12 · D-01 (decisión de diseño, informativo)
**ID:** D-01 · **SEVERIDAD:** INFO · **TIPO:** decisión de diseño (documentar/validar)
**MÓDULO:** ajustes/backup · **ARCHIVO:LÍNEA:** `ajustes.py:129-175` (permiso por rol, sin filtro de empresa)
**ESCENARIO:** `admin_emp1` accede a `/api/ajustes/backups` → **200** (probado): los backups son la **BD completa con todas las empresas**.
**IMPACTO:** cualquier admin —incluso con empresa asignada— puede descargar/restaurar datos de todas las empresas. Coherente con "admin = administración total", pero conviene explicitarlo en `SECURITY.md` y decidir si un admin con empresa debe ver backups globales.
**EVIDENCIA:** `test_admin_emp1_zona_admin_sin_recororte_empresa`.

**D-02 (INFO):** `empresa_id NULL` en el usuario = superusuario de todas las empresas (`permissions.py:150-153`, documentado en `SECURITY.md:98-99`). Comprobado dinámicamente (`test_usuario_global_ve_las_dos_empresas`). Recomendación: evitar crear usuarios nuevos con `empresa_id NULL` (el formulario de alta lo permite).

**D-03 (INFO):** `PUT/DELETE` de empresas con `require_configuration` permite a **cualquier admin (con o sin empresa)** crear/editar/borrar empresas — tras EMP-001/002 corregidos conviene decidir si la pertenencia debe condicionar también `POST /api/empresas`.

---

## G. Análisis del frontend (estático + comprobación de endpoints)

| Punto | Estado | Detalle |
|---|---|---|
| Protección de rutas | Correcta | `ProtectedRoute` envuelve `/*` (`App.jsx:52-56`); `RequierePermiso` en `/ajustes` (configuration) y `/usuarios-sistema` (user_management) |
| Nav/controles por permiso | Correcto (v1.13.00) | `Layout` filtra secciones y link usuarios (`user_management`); `BotonApagar` solo admin; `CrudPage` y botones de cada página con `has(...)` |
| Backend = fuente de verdad | Confirmado | La UI solo oculta controles; todas las denegaciones probadas ocurren en backend (403/404) |
| Token en `localStorage` (`auth.js:8-18`) | Riesgo aceptado/Baja | Robable por XSS; mitigado: React escapa por defecto, **sin `dangerouslySetInnerHTML`/`eval`** en `frontend/src` (grep vacío). Recomendación futura: cookie httpOnly + CSRF |
| Interceptor 401 → logout (`api.js:17-27`) | Correcto | cerrar sesión automático ante token caducado |
| `isAuthenticated = !!getToken()` | Informativo | no valida expiración; el interceptor 401 corrige en la primera llamada |
| Exports/descarga con `window.open` | **Roto (FE-001)** | 401 sin Bearer — ver F-11 |
| Frontend sin tests | Pendiente | `RECOMENDACIONES.md` #26 (preexistente) |

## H. Documentación vs código (`SECURITY.md`)

| Afirmación | Veredicto |
|---|---|
| §21-23 "404 no revela existencia" | **Contradicha** por IDOR-001 (detalles distintos) |
| §6 matriz de permisos/`require_*` | ✅ coincide con la introspección de las 133 rutas |
| §82 `/api/empresas` GET filtrado | ✅ correcto; **omite** que PUT/DELETE no están recortados (EMP-001/002) |
| §87-88 sync push con API-key | ✅ correcto; **omite** que la validación no alcanza al `payload` (SYNC-001..003) |
| §98-99 `empresa_id NULL` = todas | ✅ coincide (D-02) |
| §DELETE operador conserva borrado operativo | ✅ coincide con tests (DELETE propio 204 / solo_lectura 403) |
| `RECOMENDACIONES.md` #26 (tests frontend) | sigue pendiente |

## I. Pruebas y cobertura

**Ejecutadas**
- Suite oficial: **170 passed** (incluye RBAC, aislamiento, sync, backup, JWT ya existentes).
- Suite de auditoría: **85 pruebas / 73 PASS / 12 FAIL** en `/tmp/opencode/audit/test_auditoria.py` (salidas: `salida*.txt`, `salida_final.txt`).

**Cubierto:** GET/POST/PUT/DELETE cross-company en 14 recursos; listados y filtros en 12+ endpoints; exports; asientos (alta/edición/borrado cross); renumerar/reparar/reordenar; pagas y pagas/mes; NNA; JWT (firma falsa, `alg=none`, expirado, sub inválido/inexistente, inactivo, claims de rol manipulados, token sin claim rol); escalada (operador→usuarios, solo_lectura→escrituras, zona admin por rol); empresas (GET/PUT/DELETE por rol y empresa); sync (key ausente/inválida, empresa del item, payload/uuid cross); mass assignment; 404 coherentes; 405; barrido de todos los GET sin token; `version` público.

**NO EJECUTADO — entorno incompleto (no simulado):** rate limiting efectivo; generación/descarga/restauración real de backups (escribiría el proyecto); shutdown efectivo; Postgres; TLS; carga; `pip-audit`.

**Sugerencias de tests para incorporar a la suite oficial tras corregir:** PUT con usuario **con** empresa (regresión FN-001), sync cross (SYNC-001..003), empresas PUT/DELETE cross (EMP-001/002), auth usuarios filtrado por empresa (RPT-001/002), relaciones cross (REL-001), uniformidad de 404 (IDOR-001).

## J. Recomendaciones (priorizadas; ninguna aplicada)

1. **Inmediato (ALTO):** corregir SYNC-001/002/003 (empresa del `item` como única fuente + filtro por empresa en `U`/`D`); corregir EMP-001/002 (`exigir_empresa(..., campo="id")` en PUT/DELETE de empresas).
2. **Inmediato (ALTO funcional):** corregir FN-001 (quitar el `exigir_empresa(user, data)` redundante en PUT o centinela por ausencia de atributo) + test de PUT con usuario con empresa.
3. **Corto plazo (MEDIO):** RPT-001/002 (filtrar y validar `empresa_id` en usuarios del sistema), REL-001 (validar pertenencia de referencias en CREATE).
4. **Corto plazo (MEDIO funcional):** FE-001 (exports con Bearer vía blob o token de descarga).
5. **Medio plazo (BAJO):** IDOR-001 (unificar mensaje de 404), D-01/D-02 (documentar alcance global de backups y usuarios `empresa_id NULL`; restringir altas).
6. **Proceso:** añadir los tests de §I a la suite oficial; revisar `SECURITY.md` (§21-23, §82, §87-88) tras las correcciones; considerar cookie httpOnly para JWT.

---

## §35 · CONCLUSIÓN DE LA AUDITORÍA

**SEGURIDAD CONFIRMADA EN:** autenticación JWT (HS256, expiración 480 min, rechazo de firma falsa/`alg=none`/token expirado/sub inválido/usuario inactivo; claims de rol ignorados — manda la BD); escalada de privilegios vía API (operador y solo_lectura reciben 403 en zona admin, usuarios del sistema, empresas y shutdown); matriz RBAC rol×método en los CRUD; aislamiento por empresa en **lectura individual (12 recursos), listados y filtros (?empresa_id ajeno → 404 en 12+ endpoints), creación con empresa ajena (404 sin escritura), borrado cross-company (404), exports, asientos, renumerar/reparar/reordenar, pagas y NNA**; mass assignment de `empresa_id` bloqueado; 130/133 peticiones exigen Bearer; barrido completo de GET sin token → 401; rate limiters presentes en código; documentación de permisos (`SECURITY.md` §6) coherente con el código.

**PROBLEMAS ENCONTRADOS:**
- **Vulnerabilidades ALTA:** SYNC-001, SYNC-002, SYNC-003 (key limitada a una empresa escribe/modifica/borra en cualquier empresa), EMP-001, EMP-002 (admin de e1 edita y borra empresas ajenas).
- **Vulnerabilidades MEDIA:** RPT-001, RPT-002 (usuarios del sistema sin recorte de empresa: lectura y alta de cuentas en empresa ajena), REL-001 (relaciones cross-company aceptadas al crear).
- **Bug funcional ALTA (fail-closed):** FN-001 (14 PUT devuelven 404 a usuarios con empresa asignada, también con sus propios recursos).
- **Debilidad BAJA:** IDOR-001 (el detalle del 404 permite enumerar existencia, contra lo prometido en `SECURITY.md`).
- **Bug funcional MEDIA:** FE-001 (exports y descarga de backups sin `Authorization` → 401 en navegador).
- **Decisiones de diseño a documentar/validar:** D-01 (backups globales para admin con empresa), D-02 (`empresa_id NULL` = superusuario), D-03 (alcance de `configuration` en empresas).

**ASPECTOS NO VERIFICADOS (NO EJECUTADO — entorno incompleto):** ejecución real de backup/restauración/shutdown, rate limiting efectivo, comportamiento en Postgres (instalación de sincronización del servidor), TLS/red, carga, vulnerabilidades de dependencias de terceros, y tests de frontend automatizados.

**VEREDICTO FINAL:** **PROBLEMAS ENCONTRADOS.** La arquitectura de autorización es correcta y el 86 % de las pruebas de seguridad pasan, pero existen **5 vulnerabilidades altas** (sync y empresas) que permiten lectura/escritura/borrado transversal entre empresas, **2 medias** adicionales en usuarios del sistema y **1 alta funcional** que rompe la edición para el usuario multiempresa. **No se declara SEGURIDAD CONFIRMADA.** Correcciones propuestas sin aplicar (§F); tras aplicarlas será obligatoria una nueva auditoría con los tests de §I incorporados a la suite oficial (§36 del procedimiento).
