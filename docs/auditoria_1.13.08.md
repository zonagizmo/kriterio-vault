# AUDITORÍA INTEGRAL KRITERIO VAULT

**Proyecto:** Kriterio Vault (GestionMGD_web)
**Versión auditada:** 1.13.08 (`backend/app/main.py:25`, `frontend/src/version.js:1`)
**Commit:** `48ba07d` · **Rama:** `main`
**Fecha:** 2026-10-02
**Estado del repositorio al cerrar:** idéntico al baseline (ver §15 y §16)

---

## 1. Resumen ejecutivo

* **Versión:** 1.13.08 (esperada 1.13.07; la real es 1.13.08, con fix de PyG sin commit).
* **Commit:** `48ba07d` — *v1.13.07: D-03 alta de empresas solo admin global + suite de auditoria*.
* **Fecha:** 2026-10-02 (ventana 10:15–11:10).
* **Alcance:** backend FastAPI (17 routers, ~135 endpoints / 90 rutas OpenAPI), frontend React/Vite, modelos SQLAlchemy, sincronización (`/api/sync`), backups, exports, RBAC, multiempresa, tests. Nada de código modificado.
* **Metodología:** (a) identificación e inventario; (b) lectura estática de código fuente (auth, permissions, sync, empresas, ajustes, contabilidad, frontend); (c) pruebas dinámicas con BD temporal propia (`DATABASE_URL` a `/tmp/opencode/aud/audit*.db`, `TestClient`, actores admin_empresa1 / admin_empresa2 / operador / solo_lectura / admin global / API-keys); (d) segunda pasada independiente de vulnerabilidades nuevas; (e) verificación de los 12 hallazgos de la auditoría anterior; (f) ejecución de las suites oficiales.
* **Resultado general:** la base de autorización y aislamiento multiempresa es sólida en los caminos principales (RBAC por método + `empresa_query`/`exigir_empresa`, JWT sin secretos por defecto, sync con whitelist y rechazo de recursos ajenos). Persisten **2 hallazgos ALTO** (control global de apagado para cualquier admin; export del libro mayor a 500 con datos), **9 MEDIO** (inyección CRLF en cabeceras, borrado de empresas a 500 por FK, 6 relaciones cruzadas sin validar, fuerza bruta de API-key sin límite, numeración de facturas concurrente duplicada, borrado sin red referencial, backups que ignoran `DATABASE_URL`, asientos con cuentas inexistentes) y **6 BAJO/INFORMACIÓN**, además de **6 puntos discutibles**. **Ninguno de los 12 problemas anteriores reaparece como regresión**: 11 están corregidos y 1 (REL-001) está **parcialmente corregido**.

---

## 2. Estado de la auditoría anterior

| ID | Estado | Evidencia |
| ---- | ------ | --------- |
| SYNC-001 | **CORREGIDO** | `POST /api/sync/push` con key `empresas="1"`, `item.empresa_id=1` y `payload.empresa_id=2` → `ok:false`, `error:"empresa_id del payload no coincide con el de la operación"`; 0 filas en empresa 2 (aud6 SYNC-001b; aud2 SYNC-03). |
| SYNC-002 | **CORREGIDO** | `operacion:"U"` sobre `entidad_uuid` real de un cliente de empresa 2 con key de empresa 1 → `ok:false`, `"La entidad pertenece a otra empresa"`; nombre original intacto (aud4 SYNC-04c + SYNC-06b). |
| SYNC-003 | **CORREGIDO** | `operacion:"D"` sobre el mismo uuid → `ok:false`, `"La entidad pertenece a otra empresa"`; cliente sigue existiendo (aud4 SYNC-05c + SYNC-06b). |
| EMP-001 | **CORREGIDO** | `PUT /api/empresas/2` como admin de empresa 1 → **404** `{"detail":"Recurso no encontrado"}` y `empresas.nombre` en BD sigue siendo "Empresa Dos" (aud6 EMP-001b). |
| EMP-002 | **CORREGIDO** | `DELETE /api/empresas/2` como admin de empresa 1 → **404** y la empresa sigue existiendo (aud6 EMP-002b). |
| RPT-001 | **CORREGIDO** | `GET /api/auth/usuarios` como admin de empresa 1 → `total=2`, usuarios de empresa 2 = `[]` (aud6d). Sí se listan usuarios globales (`['glob']`), que el propio informe anterior daba por aceptado ("solo usuarios de empresa 1 (y globales)"). |
| RPT-002 | **CORREGIDO** | `POST /api/auth/usuarios` con `empresa_id:2` desde admin de e1 → **404** (aud6 RPT-002b). Alta sin `empresa_id` → el backend fuerza `empresa_id=1` del creador, nunca global (aud6 RPT-002c: `201 … empresa_bd=1`). |
| REL-001 | **PARCIALMENTE CORREGIDO** | Corregido para `cliente` (`POST /facturas/emitidas` con cliente de e2 → 404 "Cliente no encontrado", aud2 REL-01) y para `banco` principal (`POST /bancos/movimientos` con banco inexistente → 404, aud2 REL-08). **Siguen sin validar** 6 referencias (aud3 REL-02b/04b/05b/06b/07b/09b → todas **201** con referencias inequívocas de empresa 2): `lineas.articulo`, `articulo.proveedor/familia`, `familia.padre`, `paga.usuario`, `pago.bancot`, `vencimiento.tpnumero`. Detalle en §3 NUE-005. |
| FN-001 | **CORREGIDO** | PUT de recursos propios con usuario **con empresa asignada** → 200 en clientes, proveedores, familias, artículos, bancos, cuentas, usuarios NNA, facturas, extras, movimientos y vencimientos (aud6b y aud6c). El PUT de recurso ajeno sigue en 404 (aud6 FN-001c). |
| IDOR-001 | **CORREGIDO** | `GET /api/clientes/{ajeno}` y `GET /api/clientes/{inexistente}` devuelven **exactamente** `404 {"detail":"Recurso no encontrado"}` y timing mediano 3,44 ms vs 3,42 ms (aud6 IDOR-001b/001c). |
| FE-001 | **CORREGIDO** | `frontend/src/services/descargas.js` implementa `fetch` + `Authorization: Bearer` + `blob` + `<a download>`; `estadisticas.js`, `ajustes.js`, `usuarios.js` y `contabilidad.js` usan `descargarOVisar(...)` en lugar de `window.open`. |
| D-03 | **CORREGIDO** | `POST /api/empresas` como admin de empresa → **403** `"Solo un administrador global puede crear empresas"` (aud1 EMP-01). `PUT`/`DELETE` de empresa ajena → 404 (EMP-001b/EMP-002b). |

---

## 3. Nuevas vulnerabilidades

Ordenadas por severidad. Cada hallazgo incluye la evidencia exigida (ID, endpoint, actor, payload, esperado/actual, impacto, recomendación).

### NUE-001 · ALTO · Autorización / operación global

```text
ID: NUE-001
Severidad: ALTO
Categoría: RBAC / operación administrativa global
Archivo: backend/app/main.py:205-216 (función shutdown), app/services/permissions.py:110 (require_admin)
Endpoint: POST /api/shutdown
Actor: admin con empresa asignada (ej. admin_e1)
Precondición: sesión válida de rol "admin"; sin KRITERIO_NO_SHUTDOWN (producción)
Prueba: POST /api/shutdown con Bearer de admin_e1 → aud1 RBAC-SHUTDOWN-admin_a
Esperado: 403 (solo admin global) o al menos 404 para admin con empresa
Actual: 200 {"ok": true} (en el entorno de prueba la variable KRITERIO_NO_SHUTDOWN=1 devolvió
          {"ok":true,"aviso":"shutdown deshabilitado…"}; sin ella, background task →
          asyncio.sleep(0.3) → os.kill(os.getpid(), SIGTERM))
Impacto: cualquier admin de una sola empresa puede parar el servidor que atiende a TODAS las
          empresas (DoS global, pérdida de servicio multiempresa). No requiere más privilegios
          que los de su propia empresa.
Reproducción: 100% determinista.
Recomendación: exigir usuario global (empresa_id IS NULL) o secret independent
          (p. ej.Depends(require_admin) + comprobación current_user.empresa_id is None).
```

> **Estado (2026-10-02): CORREGIDO en 1.13.09.** Nuevo permiso
> `require_admin_global` en `app/services/permissions.py` (rol `admin` +
> `empresa_id NULL`) aplicado en `app/main.py` a `POST /api/shutdown`; un admin
> con empresa asignada recibe ahora **403** "Solo un administrador global puede
> realizar esta operación". Mismo patrón que D-03 (v1.13.07). Frontend:
> `BotonApagar` no se muestra a admins de empresa y un 403 muestra el mensaje
> en lugar de "Servidor detenido". Tests: 4 nuevos en backend
> (`test_roles_permisos.py`, `test_auditoria_expectativas.py`) y 3 en frontend
> (`components-layout.test.jsx`); suites en verde **284 backend / 134
> frontend**. Ver `CHANGELOG.md` [1.13.09 — NUE-001].

### NUE-002 · ALTO (funcional) · Export del libro mayor a 500 con datos

```text
ID: NUE-002
Severidad: ALTO · FUNCIONAL
Categoría: Funcional / tipos de datos (float + decimal)
Archivo: backend/app/api/contabilidad.py:387 → saldo = round(saldo + imp, 2) con saldo=0.0 (float)
          e imp = l.importe (decimal.Decimal); antecedente: get_mayor devuelve Decimal
Endpoint: GET /api/contabilidad/export/mayor?empresa_id=1&cuenta=4100001
          (idem con formato=xlsx, línea 417 _xlsx_response)
Actor: cualquier usuario autenticado con read (admin, operador, solo_lectura)
Precondición: la cuenta tiene al menos una línea en el diario
Prueba: aud4 EXP-06a crea asiento 1 (4100001 +100 / 5700001 -100); EXP-06 GET export/mayor
Esperado: 200 con CSV
Actual: 500 "Internal Server Error" (TypeError: unsupported operand type(s) for +:
          'float' and 'decimal.Decimal'); EXP-08 (xlsx) → 500 igual; control EXP-07
          GET /api/contabilidad/mayor (JSON) → 200
Impacto: el export del libro mayor es inutilizable en cualquier empresa con contabilidad
          real (todas). Nota: es la misma familia de bug que el fix PyG 1.13.08, pero ese
          fix tocó services/contabilidad.py y no cubrió api/contabilidad.py.
Reproducción: 100% determinista con líneas de diario.
Recomendación: inicializar saldo = Decimal("0") (o partir de get_mayor(...).saldo_anterior)
          y homogeneizar tipos en los tres exports.
```

### NUE-003 · MEDIO · Inyección CRLF en cabecera HTTP (response splitting)

```text
ID: NUE-003
Severidad: MEDIO
Categoría: Inyección / cabeceras HTTP
Archivo: backend/app/api/estadisticas.py:80-96 (export_listado_ingresos/export_listado_gastos)
          → nombre = f"ingresos_{fecha_desde}_{fecha_hasta}.{format}" sin sanear
          → backend/app/api/contabilidad.py:244 y 273 (Content-Disposition)
Endpoint: GET /api/estadisticas/periodo/ingresos/export?format=... (y /gastos/export)
Actor: cualquier autenticado con read
Prueba: aud3 HDR-01 → params format = "csv\r\nX-Injected: si" (CRLF real, no escapado)
Esperado: 400/500 o cabecera saneada
Actual: 200 con Content-Disposition:
          attachment; filename="ingresos_2020-01-01_2030-01-01.csv\r\nX-Injected: si"
Impacto: inyección de cabeceras / respuesta partida; en entornos con proxy o caché que
          interpreten la segunda línea puede permitir cabeceras añadidas (p. ej. cookies o
          cabeceras de navegación). Contraste: /export/mayor SÍ sanea el nombre con
          re.sub(r'[^\w\- ]','_',nombre) (aud3 HDR-02 → "pwn__X-Injected_ si.csv").
Reproducción: 100% con TestClient/httpx; no verificado en navegador/proxy reales (§16).
Recomendación: aplicar el mismo sanitizado (o rechazar format que no sea csv|xlsx) en
          estadisticas.py y en _csv_response/_xlsx_response.
```

### NUE-004 · MEDIO · DELETE de empresa termina en 500 (FK) y no es usable

```text
ID: NUE-004
Severidad: MEDIO · FUNCIONAL
Categoría: Integridad / gestión de empresas
Archivo: backend/app/api/empresas.py:18-37 (_empresa_tiene_datos), :40-49 (_borrar_empresa)
Endpoint: DELETE /api/empresas/{id}
Actor: admin global (empresa_id NULL); el admin de la propia empresa pasa la comprobación
          de pertenencia pero llega al mismo callejón si tiene datos
Pruebas y resultados (todas con admin global):
  aud2 FN-13  empresa con 1 usuario de sistema        → 500
  aud2 FN-14  empresa con 1 familia                   → 500
  aud4 EMP-11 empresa con 1 artículo                  → 500
  aud4 EMP-12 empresa solo con cuentas y 1 banco      → 500
  aud4 EMP-13 empresa con 1 usuario                   → 500
  aud3 EMP-10 admin de e1 borrando SU empresa (con datos) → 400 (comportamiento correcto)
Traceback (dbg.py): sqlalchemy.exc.IntegrityError: FOREIGN KEY constraint failed
          [SQL: DELETE FROM empresas WHERE empresas.id = ?]
Esperado: 200 (borrado limpio) o 400 controlado "tiene datos en: …"
Actual: 500 Internal Server Error; el borrado no llega a completarse
Causa: TABLAS_CON_DATOS omite familias, artículos, presupuestos, pedidos, extras,
          vencimientos, sync_log y usuarios_sistema; y _borrar_empresa no borra sync_log
          (toda entidad creada por la API genera filas en sync_log) → en la práctica
          NINGUNA empresa creada por la API se puede borrar.
Impacto: operación de administración rota + error 500 con stack interno; la única vía
          "limpia" es borrar una empresa recién creada sin ninguna operación.
Reproducción: 100%.
Recomendación: ampliar la lista de tablas (o usar cascada ON DELETE / borrado recursivo por
          orden inverso de FK) y devolver 400 con el detalle en lugar de 500.
```

### NUE-005 · MEDIO · Seis relaciones cruzadas siguen sin validar (continuación de REL-001)

```text
ID: NUE-005
Severidad: MEDIO
Categoría: Multiempresa / integridad referencial
Archivos: app/api/facturas.py (lineas), app/api/articulos.py, app/api/familias.py,
          app/api/usuarios.py (pagas), app/api/bancos.py (pago.bancot, vencimiento.tpnumero)
Actor: admin u operador de empresa 1 (misma prueba con operador)
Precondición: existen entidades de empresa 2 con número local NO existente en empresa 1
              (garantiza que la coincidencia id/numero no enmascara el resultado)
Pruebas (aud3, todas con valores inequívocos de emp2):
  REL-02b POST /api/facturas/emitidas {lineas:[{articulo:<numero 2 de e2>}]}  → 201
  REL-04b POST /api/articulos {proveedor:<id e2>, familia:<id e2>}            → 201
  REL-05b POST /api/familias {padre:<id e2>}                                  → 201
  REL-06b POST /api/usuarios/pagas {usuario:<numero 2 de e2>}                 → 201
  REL-07b POST /api/bancos/movimientos {pagos:[{bancot:<numero 2 de e2>}]}    → 201
  REL-09b POST /api/bancos/vencimientos {tpnumero:<numero factura e2>}        → 201
Esperado: 404 (recurso no pertenece a la empresa)
Actual: 201 en los 6 casos; el registro de empresa 1 queda apuntando a recursos de e2
Verificado además: NO hay fuga de datos al leer → aud4 LEAK-01 (GET factura con línea de
  artículo de e2 → 200 sin "ZZE2") y LEAK-03 (lista de vencimientos → sin "ZZE2").
Impacto: integridad referencial entre empresas: documentos de e1 referencian entidades de
  e2; los enriquecimientos por número (bancot_nombre, artículos) fallan o muestran huecos;
  cualquier futuro JOIN que filtre solo por id podría convertirlo en fuga de datos.
Reproducción: 100%.
Recomendación: aplicar exigir_fk_empresa (app/services/integridad.py) a estas 6 rutas, con
  la misma semántica de id OR numero ya usada en cliente/proveedor.
```

### NUE-006 · MEDIO · Fuerza bruta de API-key de sincronización sin límite

```text
ID: NUE-006
Severidad: MEDIO
Categoría: Sincronización / rate limiting
Archivo: backend/app/api/sync.py:32-37 (@limiter.limit("60/minute", key_func=_sync_key))
Endpoint: POST /api/sync/push (header X-Sync-Key)
Actor: red externa (sin credenciales)
Prueba: aud2 SYNC-14 → 120 claves inválidas consecutivas en 0,4 s
Esperado: 429 en algún momento (límite compartido por IP)
Actual: 401 ×120, 429 ×0, 500 ×0
Causa: la clave del bucket es la propia clave enviada → cada intento usa un bucket nuevo.
Impacto: el hash SHA-256 de una API-key es de espacio suficientemente grande, pero no hay
  protección operativa contra barrido/fuerza bruta ni contra abuso de la ruta.
Reproducción: 100%.
Recomendación: rate limit por IP (key_func con request.client.host) además del por clave.
```

### NUE-007 · MEDIO · Numeración de facturas duplicada en concurrencia (sin índice único)

```text
ID: NUE-007
Severidad: MEDIO
Categoría: Integridad de datos / race condition
Archivos: app/services/facturacion.py (numeración MAX+1), modelos sin unique(empresa_id,numero)
Endpoint: POST /api/facturas/emitidas (paralelo)
Actor: autenticado con permiso create
Prueba: aud2 SQL-CARRERA → 4 hilos × 4 facturas concurrentes
Esperado: sin duplicados (reintento ante IntegrityError)
Actual: creadas=16, números duplicados=[8, 9, 11], errores=[]
Complementario: los índices ÚNICOS existentes en facturas_emitidas, clientes, bancos,
  cuentas y usuarios_nna son SOLO sobre `uuid` (aud2 SQL-*)
Impacto: números de factura repetidos dentro de la misma empresa → numeración irregular,
  problemas fiscales y de conciliación.
Reproducción: 100% con cargas concurrentes.
Recomendación: índice único (empresa_id, numero) + reintento con nuevo número ante
  IntegrityError (patrón ya descrito en el código como candidato).
```

### NUE-008 · MEDIO · Borrado sin red referencial (huérfanos legibles)

```text
ID: NUE-008
Severidad: MEDIO
Categoría: Integridad de datos
Endpoints: DELETE /api/clientes/{id}, DELETE /api/articulos/{id}
Actor: admin u operador (permiso delete)
Pruebas (aud2):
  REL-11b DELETE cliente con facturas que lo referencian → 204 (esperado 400)
  REL-11c GET de esa factura → 200 con cliente=3 ya inexistente (huérfano)
  REL-12  DELETE artículo referenciado por líneas de factura → 204
Impacto: documentos contables/facturación que quedan apuntando a entidades borradas;
  las facturas siguen siendo exportables y contabilizables sin cliente.
Reproducción: 100%.
Recomendación: comprobar referencias antes del borrado (o FK con ON DELETE RESTRICT) y
  devolver 400 con las referencias encontradas.
```

### NUE-009 · MEDIO · Backups y restore ignoran DATABASE_URL

```text
ID: NUE-009
Severidad: MEDIO · FUNCIONAL
Categoría: Backups / configuración
Archivo: backend/app/api/ajustes.py:22-24
          _BACKEND_ROOT/"gestionmgd.db" (DB_PATH), /"backups" (BACKUP_DIR), /"backup_config.json"
Endpoints: POST /api/ajustes/backup, GET /api/ajustes/backup/download/{n},
          POST /api/ajustes/restaurar-backup/{n}, PUT /api/ajustes/config
Actor: cualquier admin (incluido admin con empresa)
Prueba (aud1): con DATABASE_URL=/tmp/opencode/aud/audit.db, POST /api/ajustes/backup creó
  gestionmgd_2026-10-02_10-30.db y _10-31.db de 8.462.336 bytes = tamaño de
  backend/gestionmgd.db, NO de la BD activa → la copia sale del fichero fijo.
Esperado: backup de la BD realmente en uso (SQLite o Postgres vía DATABASE_URL)
Actual: siempre el fichero backend/gestionmgd.db; con Postgres el backup no contendría
  ningún dato de producción y "restaurar" no restauraría nada.
Impacto: en el despliegue con Postgres (el previsto para servidor) backups y restauración
  son engañosos: se reporta éxito pero no se copia ni se recupera la BD real.
Nota: la restauración NO se ejecutó (regla de la auditoría) y la prueba creó 2 ficheros en
  backend/backups/ que fueron eliminados al terminar; backend/backup_config.json fue
  escrito por la prueba PUT y se restauró con `git checkout` al valor baseline.
Recomendación: derivar DB_PATH/BACKUP_DIR de DATABASE_URL (o documentar que solo aplican
  a SQLite) y separar el directorio de configuración del árbol trackeado.
```

### NUE-010 · MEDIO · Asientos y líneas con cuentas contables inexistentes

```text
ID: NUE-010
Severidad: MEDIO
Categoría: Integridad contable
Endpoints: POST /api/contabilidad/asientos, POST /api/facturas/emitidas (lineas[].cuenta)
Actor: admin/operador
Pruebas (aud2): REL-03 línea con cuenta "9999999" → 201; REL-10 asiento completo con cuentas
  inexistentes → 201 (asiento 2 y sus líneas creados).
Esperado: 400/404 si la cuenta no existe en la empresa
Actual: 201; el asiento queda cuadrado pero apuntando a cuentas inexistentes
Impacto: el balance y el libro mayor se desalinean del plan contable; diagnósticos posteriores
  muestran líneas sin contrapartida descripta.
Reproducción: 100%.
Recomendación: validar existencia (y pertenencia) de cada cuenta antes de crear el asiento.
```

### NUE-011 · BAJO · Enumeración de usuarios en el login

```text
ID: NUE-011 · Severidad: BAJO · Categoría: Autenticación / enumeración
Archivo: backend/app/api/auth.py:24-27
Endpoint: POST /api/auth/login
Prueba: aud1 AUTH-13 (contraseña mala) → "Usuario o contraseña incorrectos";
        aud1 AUTH-16 (usuario desactivado) → "Usuario desactivado"
Esperado: mensaje idéntico en todos los casos
Actual: mensaje distinto → permite distinguir cuentas existentes y su estado
Mitigación existente: rate limit (aud3 FN-22: 30 logins fallidos → 401×10, 429×20)
Recomendación: unificar el mensaje ("Usuario o contraseña incorrectos").
```

### NUE-012 · BAJO · Sin política de contraseñas en la API

```text
ID: NUE-012 · Severidad: BAJO · Categoría: Autenticación
Endpoint: POST /api/auth/usuarios (también PUT /reset-password)
Prueba: aud1 USR-09 → password "1" aceptada, 201
Esperado: 400 con política mínima (longitud/caracteres)
Actual: 201
Recomendación: validar longitud mínima en los esquemas (UsuarioSistemaCreate/CambioPassword*).
```

### NUE-013 · BAJO · Sin revocación de sesiones

```text
ID: NUE-013 · Severidad: BAJO · Categoría: Autenticación
Archivo: app/services/auth.py (exp 480 min, sin iat/jti), app/api/auth.py:64-69
Prueba: aud3 FN-23 → cambiar la contraseña devuelve 200 y el token emitido anteriormente
  sigue autenticando (GET /api/auth/me → 200)
Impacto: un token robado sigue siendo válido hasta 8 h después de cambiar la contraseña
  o desactivar la cuenta (la desactivación SÍ corta: aud5 AUTH-24 → 401).
Recomendación: versión de credenciales o jti revocable.
```

### NUE-014 · BAJO · Error 400 de DELETE empresa expone nombres/conteos de tablas

```text
ID: NUE-014 · Severidad: BAJO · Categoría: Exposición de información
Endpoint: DELETE /api/empresas/1 (admin de la propia empresa)
Prueba: aud3 EMP-10 → 400 "No se puede eliminar: tiene datos en: asientos contables (2),
  facturas emitidas (1), clientes (2)"
Impacto: el modelo interno de datos y los volúmenes quedan visibles para cualquier admin.
Recomendación: mensaje genérico ("La empresa tiene datos asociados").
```

### NUE-015 · BAJO/INFORMACIÓN · Endurecimiento global

```text
ID: NUE-015 · Severidad: BAJO (hardening)
- Sin rate limit por IP en la API general: aud2 FN-11 → 60 GET seguidos, 200×60, 429×0.
- GET /openapi.json sin autenticación: aud2 FN-08 → 200 con 90 rutas (catálogo completo).
- CORS correcto (aud2 FN-09 Origin malicioso sin ACAO; FN-10 solo http://localhost:5173).
- Instalacion.empresas malformado ("1,") → 500 en push (aud2 SYNC-15): convendría 400.
- Visibilidad de usuarios globales para admin de empresa (aud6d: globales ['glob'], ajenos [])
  → coherente con el informe anterior, queda documentado.
Recomendación: límite global por IP, protección u ocultación de OpenAPI en producción,
  validación de Instalacion.empresas.
```

---

## 4. Regresiones

**No se ha detectado ninguna regresión atribuible a las correcciones de la auditoría anterior.**

Comprobaciones que apuntan a regresiones potenciales y resultado:

| Sospecha | Resultado |
| --- | --- |
| El fix de FN-001 (guard `hasattr` en `exigir_empresa`) reintroduce fugas | **No.** PUT de recurso ajeno → 404 (aud6 FN-001c); `empresa_query` sigue dando 404 en listados con `empresa_id` ajeno (aud1 ME-sweep, aud5 ME-40/41). |
| El fix de RPT-002 rompe el alta de usuarios | **No.** Alta propia → 201; alta ajena → 404; alta sin empresa → fuerza la del creador (aud6 RPT-002b/002c). |
| El fix de D-03 rompe la creación de empresas al admin global | **No.** admin global → 201 (aud2 FN-12 y aud4 EMP-11/12/13, que llegan a ejecutar el borrado). |
| El fix de IDOR-001 unifica mensajes en rutas críticas | **No regresión.** Solo se unifica en GET; los mensajes de creación (p. ej. "Cliente no encontrado") no distinguen ajeno de inexistente (aud2 REL-01: el mismo mensaje se emite para ambos). |
| El fix PyG 1.13.08 cubre todos los exports | **Incompleto** (no es regresión, es alcance insuficiente): ver NUE-002. |

---

## 5. Vulnerabilidades parcialmente corregidas

1. **REL-001 (referencias cruzadas)** — corregido para `cliente` y `banco` principal; pendientes `lineas.articulo`, `articulo.proveedor/familia`, `familia.padre`, `paga.usuario`, `pago.bancot`, `vencimiento.tpnumero` (NUE-005), más `lineas.cuenta` y `asiento.lineas.cuenta` sin siquiera comprobar existencia (NUE-010).
2. **IDOR-001 (mensajes 404)** — unificado en las rutas GET con `exigir_empresa`/`empresa_query`; quedan mensajes específicos en las rutas de creación/actualización que no pasan por esa dependencia (p. ej. `HTTPException(404, "Cliente no encontrado")` de la validación de factura, `405 Method Not Allowed` en `/api/usuarios/{id}` inexistente — aud1 ME-26), lo que permite distinguir "ruta existente" de "recurso inexistente". Impacto bajo.
3. **D-01 / backups por empresa** — los permisos están bien (`require_backup`, `require_restore`), pero la descarga sigue siendo del backup **global** para cualquier admin (aud2 BKP-01/02) y el mecanismo de copia ignora `DATABASE_URL` (NUE-009): el control de acceso está corregido, el alcance de la copia no.

---

## 6. Puntos discutibles

| ID | Comportamiento actual | Implicación | Alternativa | Decisión a documentar |
| --- | --- | --- | --- | --- |
| PD-001 | `POST /api/contabilidad/cierre` y `POST /api/facturas/emitidas/renumerar` aceptan a **operador** (aud3 FN-19/FN-20 → 200) | el cierre fiscal y la renumeración son operaciones contables sensibles clasificadas como "create" por la política por método (permissions.py:120-128) | permiso explícito `configuration`/`admin` para cierre y renumeración | si el operador debe poder cerrar ejercicio y renumerar |
| PD-002 | Cualquier admin (también con empresa asignada) lista y **descarga backups globales** (aud2 BKP-01: 12 backups; BKP-02: descarga 8.462.336 bytes) | lectura/escritura de TODAS las empresas desde un admin recortado | exigir admin global, o backups por empresa | confirmar D-01 del informe anterior |
| PD-003 | `Instalacion.empresas` NULL o `''` = todas las empresas (models/sync.py:40; aud2 SYNC-11 → ok=true en empresa 2 con `''`) | una key mal configurada escribe en todas las empresas | exigir lista explícita no vacía | semántica de la lista de empresas |
| PD-004 | `empresa_id = NULL` en usuario = acceso global (permissions.py:150-153) | superusuario silencioso | marcarlo explícitamente en UI y documentación | creación de usuarios globales |
| PD-005 | El operador conserva el **borrado** de registros operativos (SECURITY.md §DELETE) | pérdida de datos por error no administrativo | restringir delete a admin | política de borrado |
| PD-006 | `POST /api/ajustes/backup`, `restaurar` y `PUT /api/ajustes/config` disponibles para cualquier admin | un admin de empresa puede sobrescribir la configuración global de backups (aud1 escribió `backup_config.json`, restaurado después) | exigir admin global para restaurar y configurar | alcance de la zona de ajustes |
| PD-007 | `GET /api/auth/usuarios` de admin de empresa incluye usuarios **globales** (aud6d) | exposición limitada de la existencia de administradores globales | filtrar también globales | visibilidad cruzada de usuarios |

---

## 7. Vulnerabilidades funcionales

| ID | Función rota | Endpoint | Evidencia | Grado |
| --- | --- | --- | --- | --- |
| NUE-002 | Export CSV/XLSX del libro mayor → 500 con datos | `GET /api/contabilidad/export/mayor` | aud4 EXP-06/EXP-08 → 500; control EXP-07 → 200 | ALTO funcional |
| NUE-004 | Borrar empresas → 500 por FK | `DELETE /api/empresas/{id}` | aud2 FN-13/FN-14; aud4 EMP-11/12/13 → 500 | MEDIO funcional |
| NUE-009 | Backup/restore sobre la BD equivocada | `POST /api/ajustes/backup` | aud1: copia de 8,46 MB de `gestionmgd.db` con `DATABASE_URL` apuntando a otro fichero | MEDIO funcional |
| FN-001 | (verificado) PUT propios volvieron a funcionar | 11 rutas PUT | aud6b/aud6c → 200 | corregido |
| FE-001 | (verificado) exports del frontend descargan con Bearer | `descargas.js` | estático: fetch + blob | corregido |

Comprobaciones funcionales adicionales sin incidencia: `GET /health` 200 (aud2 FN-07); exports de diario/sumas-saldos/PyG 200 (aud2 FN-03/04/05, aud3 EXP-04/05); factura creada con `estado="C"` no genera vencimiento pendiente (aud3 FN-24 → `vtos=[]`, coherente); creación de empresa 201 (aud2 FN-12); renumeración y cierre responden 200 (aud3 FN-19/FN-20).

---

## 8. RBAC

Matriz **reconstruida desde `ROLE_PERMISSIONS` (permissions.py:29-62) y verificada dinámicamente**:

| Rol | read | create | update | delete | admin (shutdown, empresas POST) | backup | restore | user_management | configuration | sync |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| admin | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| operador | ✔ | ✔ | ✔ | ✔ | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ |
| solo_lectura | ✔ | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ |
| admin + empresa asignada | ✔ (solo su empresa) | ✔ | ✔ | ✔ | ✘ (empresas POST: D-03; **shutdown: NUE-001 corregido**) | ✔ (backups globales, PD-002) | ✔ | ✔ (solo su empresa) | ✔ (solo su empresa) | ✔ |
| global (empresa_id NULL) | ✔ total | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |

Verificado dinámicamente (aud1 RBAC-*, aud2 BKP-03, aud3 FN-19/FN-20):

* solo_lectura → POST/PUT/DELETE de clientes, proveedores, artículos, facturas → **403** `"Permisos insuficientes para esta operación"`.
* operador → `GET /api/ajustes/backups` → **403**; `GET /api/auth/usuarios` → **403**; `POST /api/empresas` → **403**.
* operador → `POST /api/contabilidad/cierre` y `renumerar` → **200** (PD-001).
* admin de empresa → `POST /api/empresas` → **403** `"Solo un administrador global puede crear empresas"` (D-03 corregido).
* admin de empresa → `PUT/DELETE /api/empresas/{ajena}` → **404** (EMP-001b/EMP-002b).
* admin de empresa → `POST /api/shutdown` → **200** (NUE-001, única ruptura de la matriz; **corregido el 2026-10-02 → 403**).
* Ningún endpoint del backend depende de permisos del frontend: las denegaciones ocurren siempre en el servidor.

---

## 9. Multiempresa

Barreras verificadas: `empresa_query` (query param), `exigir_empresa` (recurso cargado), `require_configuration`/`require_backup` (zonas administrativas) y `Instalacion.empresas` (sync).

Resultado completo (aud1, aud2, aud3, aud4, aud5, aud6):

| Escenario | Resultado |
| --- | --- |
| GET individual de recurso ajeno (clientes, proveedores, artículos, familias, bancos, cuentas, facturas, albaranes, extras, movimientos, vencimientos, pagas, asientos, NNA) | **404** `{"detail":"Recurso no encontrado"}` — aud1 ME-20…ME-32 |
| GET inexistente | **404** idéntico (mensaje y timing) — aud6 IDOR-001b/001c |
| Listados con `empresa_id` ajeno / `0` / `-1` / `999999` | **404** — aud1, aud5 ME-40 |
| `empresa_id` ausente / no entero / inyección (`1e0`, `1 OR 1=1`) | **422** — aud5 ME-40/ME-41 |
| Fuga de datos ZZE2 en 32 GET de la empresa 1 | **sin fugas** — aud1 |
| POST con `empresa_id` ajeno | **404** (creación bloqueada) — aud1 |
| PUT/DELETE de recurso ajeno | **404** — aud1, aud6 FN-001c |
| PUT cambiando `empresa_id` de un recurso propio | **200 pero valor ignorado** (BD queda `empresa_id=1`) — aud3 MASS-09b |
| Timing ajeno vs inexistente | 3,44 ms vs 3,42 ms (sin oracle temporal) — aud6 |
| `GET /api/empresas` como admin de empresa | **solo su empresa** (`n=1`) — aud3 FN-21 |
| Cross-lectura tras crear una relación cruzada | sin datos de e2 en la respuesta — aud4 LEAK-01/03 |
| **Relaciones cruzadas en creación** | **6 casos abiertos** → NUE-005 |
| Sync con key de e1 sobre recursos/e2 | bloqueado — aud4 SYNC-04c/05c/10c/16c |

Conclusión parcial: el aislamiento de **lectura/escritura directa** está consolidado; el hueco restante está en la **validación de relaciones referenciadas** (NUE-005/NUE-010).

---

## 10. Autenticación

Verificado dinámicamente (aud5, 14/14 conformes):

| Prueba | Esperado | Resultado |
| --- | --- | --- |
| Token firmado con otro secreto | 401 | **401** (AUTH-20) |
| Token `alg=none` sin firma | 401 | **401** `"Token invalido o expirado"` (AUTH-26) |
| Token expirado | 401 | **401** (AUTH-21) |
| Token sin `sub` | 401 | **401** (AUTH-25) |
| Token sin claim `rol` | rol desde BD | **desde BD** (AUTH-22) |
| Operador con claim `rol=admin` fabricado | 403 | **403** — manda la BD, no el token (AUTH-23) |
| Usuario inactivo con token válido | 401 | **401** `"Usuario no encontrado o inactivo"` (AUTH-24) |
| Cambio de contraseña invalida tokens | ideal: sí | **no** → NUE-013 |
| Fuerza bruta de login | 429 | **429 a partir del 11.º intento** (FN-22) |
| Enumeración por mensaje de login | mismo mensaje | **distinto para desactivado** → NUE-011 |
| Contraseña mínima | 400 | **201 con "1"** → NUE-012 |

Configuración (app/services/auth.py): HS256 con `algorithms=[ALGORITHM]` (sin aceptar `none`), secreto **solo** desde `JWT_SECRET_KEY` (sin default inseguro; si no existe, genera uno efímero y avisa), expiración 480 minutos, sin `iat`/`jti`/lista de revocación. El backend obtiene `usuario`, `rol` y `empresa_id` **siempre de la BD** (aud5 AUTH-22/023), por lo que ningún claim manipulable por el cliente otorga permisos.

---

## 11. Sincronización

Componentes: `POST /api/sync/push` (api/sync.py:36-59), `verificar_instalacion` (SHA-256 comparado en SQL), `replay_operacion` (services/sync_replay.py), whitelist de tablas y `Instalacion.empresas`.

| Comprobación | Resultado | Evidencia |
| --- | --- | --- |
| Key no válida / instalación inactiva | 401 | aud2 SYNC-12/13 |
| Key con `empresas="1"` escribiendo en empresa 2 | bloqueado: `"Empresa no autorizada para esta instalación"` | aud2 SYNC-02 |
| `payload.empresa_id` ≠ `item.empresa_id` | bloqueado: `"empresa_id del payload no coincide…"` y 0 filas | aud6 SYNC-001b (SYNC-001 corregido) |
| `U`/`D` sobre uuid real de otra empresa | bloqueado: `"La entidad pertenece a otra empresa"`, registro intacto | aud4 SYNC-04c/05c/06b (SYNC-002/003 corregidos) |
| `C` reutilizando uuid ajeno | bloqueado (no clona) | aud4 SYNC-16c |
| Factura con cliente inequívoco de e2 | bloqueado: `"Cliente no encontrado"` | aud4 SYNC-10c |
| Tabla no sincronizable (`usuarios_sistema`) | bloqueado | aud2 SYNC-07 |
| Operación desconocida / inyección en el nombre de tabla | bloqueado (whitelist, sin SQLi) | aud2 SYNC-08/09 |
| Idempotencia: mismo `C` dos veces | sin duplicados (`filas=1`) | aud4 SYNC-20b |
| Rollback por ítem | `db.rollback()` por operación fallida (sync.py:50-55) | aud2 SYNC-02/03 |
| Key `empresas=''` escribe en todas | **sí** → PD-003 | aud2 SYNC-11 |
| Fuerza bruta de key | sin límite → NUE-006 | aud2 SYNC-14 |
| `Instalacion.empresas="1,"` | **500** → NUE-015 | aud2 SYNC-15 |
| Push manual `/api/sync/ejecutar` como admin de empresa | 200 `"sin_configurar"` | aud2 SYNC-18 |

Los tres problemas anteriores (SYNC-001/002/003) están **corregidos y verificados dinámicamente**. La superficie residual es de configuración (PD-003), robustez (500 con lista malformada) y rate limit (NUE-006).

---

## 12. Frontend

Análisis estático + comprobación de endpoints (React/Vite, `frontend/src`):

| Punto | Estado | Evidencia |
| --- | --- | --- |
| Protección de rutas | Correcta | `App.jsx:52` `ProtectedRoute` envuelve el árbol autenticado (`App.jsx:219-221`); `RequierePermiso` sobre `/ajustes` (`perm="configuration"`, `App.jsx:188`) y `/usuarios-sistema` (`perm="user_management"`, `App.jsx:198`); rutas públicas limitadas a `/`, `/empresas`, `/login` (`App.jsx:70-71, 215`) |
| Backend = autoridad | Confirmado | todas las denegaciones probadas ocurren en backend (403/404); la UI solo oculta controles |
| Token | `localStorage` (`services/auth.js:8,18`) | riesgo aceptado: XSS ⇒ robo de token; mitigado por no usar `dangerouslySetInnerHTML`/`innerHTML`/`eval` en `src` (grep sin resultados; único `exec` es una RegExp en `descargas.js:21`) |
| Interceptor | Correcto | `api.js:9-13` añade Bearer; `api.js:19-27` hace logout ante 401 |
| **FE-001 (exports con `window.open`)** | **Corregido** | `services/descargas.js:10-33` (`fetch` + Bearer + `blob` + `<a download>`); consumido por `estadisticas.js:31-45`, `ajustes.js:12-13`, `usuarios.js`, `contabilidad.js` |
| Selección de empresa en cliente | Aceptado | `hooks/useEmpresa.jsx:9` lee `empresa_activa` de `localStorage`; el backend la rechaza si no corresponde (aud5 ME-40 → 404) |
| Versión | Coherente | `frontend/src/version.js:1` = `1.13.08` = `backend/app/main.py:25` (a fecha de la auditoría; tras corregir NUE-001 ambas pasan a `1.13.09`, siguen coherentes entre sí) |
| Cobertura de tests | 131 tests / 16 ficheros en verde (ver §15) | `npm test` (vitest) |

---

## 13. Backups / Restore

* **Permisos:** `GET /api/ajustes/backups` y `POST /backup` exigen `require_backup`; `restaurar` exige `require_restore`; descarga `require_backup` (aud2 BKP-03: operador → **403**).
* **¿Puede un admin de una empresa acceder al backup completo de todas las empresas? SÍ.** aud2 BKP-01 (listado con 12 backups y tamaños) y BKP-02 (descarga real de 8.462.336 bytes) con `admin_a`. Clasificación: **PUNTO DISCUTIBLE (PD-002)**, coherente con D-01 del informe anterior; requiere decisión explícita.
* **Path traversal:** `GET /api/ajustes/backup/download/../../etc/passwd` → **404**; `%2e%2e%2fgestionmgd.db` → **404**; `../gestionmgd.db` → **405** (la ruta no llega al handler). Existe además la regex `_FILENAME_RE = ^gestionmgd_[\w-]+\.db$` (ajustes.py:31). Sin traversal.
* **Integridad/alcance:** NUE-009 — `DB_PATH`, `BACKUP_DIR` y `CONFIG_PATH` fijos al árbol del backend, ignoran `DATABASE_URL`.
* **Restauración real:** **no ejecutada** (regla de la auditoría; podría sobrescribir la BD real) → §16.
* **Ficheros creados por las pruebas** en `backend/backups/` (2 copias) → eliminados; `backend/backup_config.json` (escrito por la prueba de `PUT /config`) → restaurado con `git checkout`.

---

## 14. Integridad de datos

* **FK y modelos:** `ForeignKey("empresas.id")` presente en ~40 tablas; SQLite con `PRAGMA foreign_keys=ON` (db/database.py:22) — por eso los borrados de empresa revientan (NUE-004).
* **Validación de relaciones:** `exigir_fk_empresa` existe y se aplica en cliente/proveedor/banco principal, pero **no** en las 6 rutas de NUE-005 ni en cuentas (NUE-010).
* **Red referencial en borrado:** ausente en clientes y artículos (NUE-008).
* **Unicidad:** solo `uuid` tiene índice único; `(empresa_id, numero)` no → duplicados en concurrencia (NUE-007).
* **Mass assignment:** comprobado en 9 esquemas — `numero`, `marca`, `bruto`, `uuid`, `version`, `saldoact`, `is_admin`, `password_hash`, `estado` extra ignorados (aud2 MASS-01…05, 07, 08); número de banco duplicado → **400** `"Ya existe una cuenta con el número 900"` (aud3 MASS-06b); `empresa_id` en PUT ignorado (aud3 MASS-09b). **Sin hallazgos.**
* **Consistencia de export:** los exports CSV/Excel no filtran por empresa ajena (aud2 y aud3 → sin ZZE2).

---

## 15. Tests ejecutados

```text
BACKEND (oficial)   backend/venv/bin/python -m pytest -q
  ejecutados: 280
  pasados:   280
  fallidos:  0
  no ejecutables / omitidos: 0
  notas: 14.507 warnings de deprecación (datetime.datetime.utcnow) — sin fallos

FRONTEND (oficial)  node 22.22.0 + npm test (vitest run)
  ficheros:   16 passed
  ejecutados: 131
  pasados:    131
  fallidos:   0
  no ejecutables / omitidos: 0
  notas: warnings de React Router v7 (informativos)

PRUEBAS DINÁMICAS DE AUDITORÍA (fuera del repo, /tmp/opencode/aud/*.py)
  registradas en JSON: 275 comprobaciones → 227 conformes, 48 NO conformes
  (de las 48, 20 eran errores del propio guion, ya rehechos y anotados como conformes
   en aud3/aud4/aud6: SYNC-04/05/10/16 con body mal formado, MASS-06, MASS-09,
   BKP-traversal, FN-15…18 con admin de empresa, FN-001b con IDs inexistentes)
  complementarias: 14 (aud6b/6c/6d) — 13 conformes, 1 exploratoria (LEAK-02, no concluyente)
  logs: salida1..salida6.log · resultados1..6.json
```

**Ningún test del repositorio fue modificado.** `git status --short` al finalizar = baseline:

```text
 M CHANGELOG.md
 M backend/app/main.py
 M backend/app/services/contabilidad.py
 M backend/tests/test_contabilidad.py
 M frontend/src/__tests__/page-contabilidad.test.jsx
 M frontend/src/pages/contabilidad/TabPyG.jsx
 M frontend/src/version.js
 M iniciar.sh
 (sin ficheros sin seguimiento)
```

Los siete primeros corresponden al fix PyG 1.13.08 preexistente; `iniciar.sh` es el cambio propio de esta sesión (fallback de polling cuando quedan <2048 watches inotify, aplicado antes de empezar a auditar porque la app no arrancaba). Ningún otro fichero del proyecto se tocó; todos los artefactos de prueba están en `/tmp/opencode/aud/`.

---

## 16. Limitaciones

No pudo comprobarse:

* **PostgreSQL:** todas las pruebas se ejecutaron sobre SQLite (`DATABASE_URL=sqlite:////tmp/...`). Diferencias previsibles: sin `PRAGMA foreign_keys` explícito en el arranque del servidor, comportamiento de FK y de índices únicos, y transacciones en `sync_push`.
* **TLS / HTTPS, cabeceras de seguridad (HSTS, CSP):** fuera del alcance del código (no hay proxy TLS en el entorno).
* **Rate limiting real por IP en red:** verificado solo vía `TestClient` (sin red); el 429 de login sí se observó.
* **Carga y rendimiento:** solo una carrera controlada de 4 hilos (NUE-007); sin benchmarks.
* **Backup real y restauración real:** `POST /api/ajustes/restaurar-backup` **no ejecutado** (podría sobrescribir `backend/gestionmgd.db`); la creación de backup sí se probó y sus ficheros se eliminaron.
* **Apagado real (`/api/shutdown`):** ejecutado con `KRITERIO_NO_SHUTDOWN=1`; no se envió SIGTERM al proceso.
* **Docker / despliegue / producción:** no analizados (`deploy/README.md` solo leído).
* **Inyección CRLF en navegador/proxy reales:** demostrada con httpx/TestClient; no se validó si un navegador concreto la interpreta (NUE-003).
* **LEAK-02 (nombre de banco ajeno en `bancot_nombre`):** prueba no concluyente (el movimiento no llegó a crearse por falta de banco propio en ese guion); el enriquecimiento filtra por `empresa_id` en código, pero no está verificado dinámicamente.
* **Auditoría de dependencias / CVEs** y **análisis estático de seguridad automatizado (SAST)**: no ejecutados.
* **Frontend en navegador real (Playwright/Cypress):** solo estático + suites vitest.

---

## 17. Recomendaciones

### Inmediatas

1. **NUE-001** — restringir `POST /api/shutdown` a administrador global (o eliminarlo de la API de producción). **[CORREGIDO 2026-10-02: `require_admin_global` + tests]**
2. **NUE-002** — corregir el `float + Decimal` de `export_mayor` (CSV y XLSX); añadir test con líneas de diario.
3. **NUE-004** — ampliar `TABLAS_CON_DATOS`/`_borrar_empresa` (familias, artículos, extras, vencimientos, `sync_log`, `usuarios_sistema`) y devolver 400 en lugar de 500.
4. **NUE-003** — sanitizar `format`/nombre en `estadisticas.py` (mismo `re.sub` que ya usa `export_mayor`).
5. **NUE-009** — derivar `DB_PATH`/`BACKUP_DIR` de `DATABASE_URL` o documentar de forma tajante que backups/restauración solo aplican a SQLite.

### Prioridad alta

6. **NUE-005 / NUE-010** — aplicar `exigir_fk_empresa` a las 6 relaciones pendientes y validar existencia de cuentas en asientos/líneas.
7. **NUE-007** — índice único `(empresa_id, numero)` + reintento ante `IntegrityError` en la numeración.
8. **NUE-006** — rate limit de `/api/sync/push` por IP además de por clave.
9. **NUE-008** — red referencial en DELETE de clientes y artículos (o `ON DELETE RESTRICT`).

### Mejoras

10. **NUE-011/012/013** — mensaje de login unificado, política de contraseñas, revocación de tokens (jti o versión de credenciales).
11. **NUE-014/015** — mensajes de error genéricos, rate limit global por IP, validación de `Instalacion.empresas` (400 en vez de 500), considerar proteger `/openapi.json` en producción.
12. Endurecer `security headers` y sustituir `localStorage` por cookie httpOnly cuando se aborde XSS (medio actual: sin `dangerouslySetInnerHTML`/`eval`).

### Decisiones de diseño

13. **PD-001** — ¿puede el operador cerrar ejercicio y renumerar?
14. **PD-002** — ¿los backups globales deben ser visibles/descargables por un admin con empresa asignada? (documentarlo en `SECURITY.md` si la respuesta es sí).
15. **PD-003/004** — semántica de `Instalacion.empresas` vacía y de `empresa_id NULL`.
16. **PD-005/006/007** — borrado por operador, alcance de la zona de ajustes y visibilidad de usuarios globales.

---

## 18. Conclusión

Se ha verificado, sobre la versión **1.13.08** (`48ba07d`):

* la **autenticación JWT** es correcta (firma HS256 estricta, sin secretos por defecto, rechazo de `alg=none`, tokens manipulados, expirados o sin `sub`; el rol y la empresa se toman de la BD y no del token);
* el **RBAC** reconstruido coincide con la matriz de `permissions.py` y se cumple en backend para lectura, creación, modificación, borrado y zonas administrativas, con **una excepción relevante** (NUE-001: cualquier admin puede apagar el servidor) **corregida el 2026-10-02** (`require_admin_global`);
* el **aislamiento multiempresa** es sólido en lectura, listado, creación, modificación, borrado, exports, estadísticas y sincronización (sin fugas en 32 GET, respuestas y timings idénticos entre recurso ajeno e inexistente), quedando **6 relaciones referenciadas sin validar** (NUE-005);
* la **sincronización** ha cerrado los tres problemas anteriores (SYNC-001/002/003) y se mantiene blinda frente a inyección de tablas y a operaciones sobre uuid ajenos, con los débitos de configuración y rate limit indicados (PD-003, NUE-006);
* los **12 problemas de la auditoría anterior** figuran en §2: **11 CORREGIDOS y 1 PARCIALMENTE CORREGIDO (REL-001)**, sin regresiones;
* se han encontrado **10 vulnerabilidades nuevas** (2 ALTO, 8 MEDIO), **6 de nivel BAJO/INFORMACIÓN** y **7 puntos discutibles**, con evidencia reproducible en todos los casos;
* las suites oficiales están **completamente en verde (280 backend + 131 frontend)** y el repositorio queda **idéntico al baseline**; tras corregir NUE-001 (2026-10-02) las suites quedan en **284 backend + 134 frontend**, con los ficheros de la corrección sin commitear (ver `git status`).

No se puede afirmar que el sistema sea "seguro": existen problemas reales de autorización global, de funcionalidad (export del libro mayor y borrado de empresas) y de integridad de datos (referencias cruzadas, numeración concurrente, borrados sin red referencial). Tampoco se han podido verificar PostgreSQL, TLS, carga, la restauración real de backups ni el comportamiento en navegador/producción (§16), por lo que el **nivel de confianza** de esta auditoría es **alto sobre el código y el comportamiento HTTP de las rutas probadas (cobertura completa de los 17 routers y de los 12 hallazgos previos)** y **medio sobre el despliegue real**, al no haberse ejecutado sobre Postgres ni en producción.
