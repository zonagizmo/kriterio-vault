# CHANGELOG — Kriterio Vault (antes GestionMGD Web)

Formato de versión: **X.XX.XX** (se muestra como X.X.X eliminando ceros iniciales por componente)
- **X** — cambio mayor (rediseño, incompatibilidad)
- **XX** — nueva funcionalidad o módulo
- **XX** — corrección de bugs y ajustes menores

## [1.10.01] — 2026-09-10 — Fix: migraciones de arranque rompían en PostgreSQL

### Corregido
- **`_migraciones()` (`app/main.py`) fallaba al arrancar contra una base de datos PostgreSQL nueva** — usa sintaxis `PRAGMA table_info(...)` propia de SQLite, que no existe en Postgres (`psycopg2.errors.SyntaxError`), y la app no arrancaba. Descubierto en la primera instalación real del [servidor central por YunoHost](https://github.com/zonagizmo/kriterio-vault_ynh). Como `crear_tablas()` (`Base.metadata.create_all()`) ya crea el esquema completo actual en cualquier base de datos nueva, `_migraciones()` ahora se salta por completo cuando el dialecto no es SQLite — su único propósito es poner al día un esquema SQLite local antiguo, no aplica a una Postgres recién creada.

---

## [1.10.00] — 2026-09-07 — Fase 2 de sincronización: servidor central (solo subida)

### Nuevo
- **Servidor central de sincronización**: la misma app FastAPI, con endpoints nuevos para recibir y aplicar las operaciones que empuja cada instalación. `POST /api/sync/push` (autenticado por clave de API por instalación, `app/api/sync.py`) recibe un lote de `sync_log` y las reproduce con la misma lógica de servicio que las generó (`app/services/sync_replay.py`, registro de las 15 tablas sincronizables), no copiando filas sueltas — así se regeneran también los efectos derivados (asientos, vencimientos...). Idempotente ante reintentos.
- **Cliente de sincronización**: `app/services/sync_push.py` empuja el log pendiente al servidor configurado (`SYNC_SERVER_URL`/`SYNC_API_KEY`), cada 15 minutos vía el scheduler ya existente para backups, y bajo demanda en `POST /api/sync/ejecutar`. Sin conexión, se reintenta en el siguiente ciclo sin bloquear la app.
- **Registro de instalaciones**: modelo `Instalacion` + script `backend/scripts/crear_instalacion.py` (se ejecuta a mano en el servidor, no por HTTP — no hay admin autenticado que pueda dar de alta otras instalaciones). Cada instalación puede acotarse a empresas concretas.
- **Aprovisionamiento del servidor**: `deploy/` — script idempotente para Debian (PostgreSQL, Caddy con TLS automático, systemd, firewall), instrucciones completas en `deploy/README.md`. Servidor: `kriteriovault.naslive.es`.
- Verificado extremo a extremo con dos bases de datos independientes simulando cliente y servidor reales: alta, edición, baja, reintento idempotente, autenticación y restricción por empresa, y una factura completa (cabecera + líneas + vencimiento) reconstruida correctamente en destino.

---

## [1.09.00] — 2026-09-04 — Fase 1 de sincronización completada en toda la app

### Nuevo
- **`SyncMixin` (uuid/version/created_at/updated_at) y registro en `sync_log` en los 15 agregados raíz** de la aplicación: FacturaEmitida/Recibida, Cliente, Proveedor, Vencimiento, Banco, MovBanco, Familia, Articulo, AlbaranEmitido/Recibido, Cuenta, Extra, UsuarioNNA, PagaNNA. Quedan fuera deliberadamente las líneas/derivados de un documento padre (Apunte, ExApunte, Diario, DiarioTxt, Eriva, Pago) y las tablas sin alta/edición propia (Presupuesto, Pedidos, Albaranes de inventario/reparto...). Migración de 17.766 filas existentes verificada (0 sin uuid, 0 duplicados). Detalle completo en `docs/sincronizacion.md`.
- Caso especial resuelto: las altas de `usuarios_nna`/`pagas_nna` usan SQL crudo (no ORM), así que el `uuid` se genera a mano en Python antes del INSERT.

---

## [1.08.00] — 2026-09-04 — Base para sincronización con servidor central (fase 1)

### Nuevo
- **Infraestructura de sincronización, sin sincronizar nada aún**: primer paso de un proyecto más amplio para poder trabajar desde varios PCs con los mismos datos vía un servidor central (ver `docs/sincronizacion.md` para la arquitectura completa). Implementado como referencia solo en el módulo de Facturas (emitidas y recibidas):
  - Columnas nuevas `uuid`, `version`, `created_at`, `updated_at` (`app/models/sync_mixin.py`) — `uuid` es la identidad estable entre instalaciones (el `numero` de negocio no sirve, puede colisionar entre instalaciones offline).
  - Tabla `sync_log` (`app/models/sync.py`): registro de operaciones de alta/edición/baja, con los mismos datos que recibió el endpoint, para poder reproducirlas en el servidor más adelante.
  - Identidad de instalación (`app/services/sync.py`): UUID propio por instalación, persistido en `backend/instalacion.json`.
  - Migración automática de las 1.343 facturas existentes (uuid único por fila, sin duplicados, verificado).

---

## [1.07.00] — 2026-09-04 — Control de facturas recibidas duplicadas

### Nuevo
- **Aviso de factura recibida duplicada**: al crear o editar una factura recibida, si ya existe otra del mismo proveedor con el mismo nº de factura del proveedor (`prfactura`), se muestra un aviso antes de guardar — coincida o no el total (si difiere, el mensaje muestra ambos importes para detectar errores de tecleo). El usuario puede confirmar y guardar igualmente (no es un bloqueo, por si es un caso legítimo). Backend: `FacturaDuplicadaError` en `services/facturas.py`, respuesta 409 en `POST/PUT /api/facturas/recibidas`; nuevo campo `forzar` en el payload para omitir el aviso.

---

## [1.06.00] — 2026-07-23 — Nueva página Ingresos y Gastos

### Nuevo
- **Página "Ingresos y Gastos"** (menú, justo después de Contabilidad): rango de fechas libre (desde/hasta) con totales de ingresos, gastos y resultado del período, más desglose por categoría de cada uno. Usa el mismo criterio de negocio que Inicio y Estadísticas (Facturas + Extras + Pagas NNA + cuenta 7691000 cheques fundación) — distinto del "P&G" ya existente en Contabilidad, que trabaja directamente sobre cuentas contables 6xx/7xx del Libro Diario sin filtrar por tipo de documento. Backend: nuevo endpoint `GET /api/estadisticas/periodo` + función `ingresos_por_categoria` en `services/estadisticas.py`.

---

## [1.05.00] — 2026-07-23 — Ficha de empresa editable en Ajustes

### Nuevo
- **Ajustes con pestañas**: "Empresa" y "Copias de seguridad" (antes todo en una sola página).
- **Ficha de la empresa activa**: nueva pestaña con formulario editable — NIF/CIF, domicilio, localidad, provincia, código postal, teléfono, email (además de nombre, que ya existía). Modelo `Empresa` ampliado con estos campos (antes solo código/nombre/activa); migración automática al arrancar el backend añade las columnas sin perder datos existentes. Nuevos endpoints `GET/PUT /api/empresas/{id}`.

---

## [1.04.01] — 2026-07-22 — Filtros en Extras

### Nuevo
- **Página Extras — filtros**: se añaden búsqueda por concepto, fecha desde/hasta y estado (Pendiente/Cobrado-Pagado), con el mismo patrón visual que Facturas (incluido botón "Borrar filtros"). Antes solo se podía filtrar por tipo (Gasto/Ingreso).

---

## [1.04.00] — 2026-07-21 — Nueva página Estadísticas

### Nuevo
- **Página Estadísticas** (debajo de Contabilidad en el menú): selector de año y tres gráficos para la empresa activa — evolución mensual de ingresos/gastos (barras), gastos por categoría del año (Facturas recibidas / Gastos generales / Pagas NNA / Salidas terapéuticas) y evolución del saldo bancario total a fin de cada mes. Backend nuevo: `app/services/estadisticas.py` + `app/api/estadisticas.py` (`GET /api/estadisticas`, `GET /api/estadisticas/anios`).
- **Pagas NNA incluidas en ingresos/gastos**: tanto Estadísticas como el resumen de Inicio usan ahora la misma lógica compartida (`services/estadisticas.py`), que además de Facturas y Extras suma las pagas NNA del módulo dedicado (tabla `pagas_nna`, activo desde el 30/06/2026, sustituto de los extras tipo `M` que se dejaron de usar). Antes esas pagas no se contaban en absoluto a partir de esa fecha.
- **Estadísticas no muestra meses futuros**: si se consulta el año en curso, los gráficos de evolución mensual y saldo bancario se cortan en el mes actual en vez de rellenar el resto del año con ceros/saldo repetido (que daba la falsa impresión de datos reales para meses que aún no han pasado).

---

## [1.03.00] — 2026-07-21 — Inicio: Extras incluidos en ingresos/gastos del mes

### Nuevo
- **Página Inicio — resumen del mes en curso**: "Ingresos" y "Gastos" ahora incluyen también los Extras (tipos `G` gasto y `M` pagas mensuales NNA), no solo facturas emitidas/recibidas. Se filtran por la fecha del extra igual que las facturas (día 1 del mes hasta hoy). Se excluyen los tipos `A` (apertura), `R` (regularización) y `Z` (cierre) por no ser gasto/ingreso operativo, y el código suelto `X` (datos de prueba sin uso real). El tipo `I` (ingreso) está soportado pero de momento no hay extras dados de alta con ese tipo.
- **Ingresos también desde cuenta 7691000**: los cheques de fundación ingresados directamente en banco (cuenta `7691000 INGRESOS CHEQUES FUNDACION`, asiento tipo `B`) no pasaban por Facturas ni Extras y no se contaban. Ahora se suman a "Ingresos" con el mismo criterio de fecha.

---

## [1.02.01] — 2026-07-21 — Corrección de vencimientos de extras mal enlazados por la migración

### Correcciones de datos
- **Vencimientos de extras (tipo X) mal enlazados**: en la migración desde el sistema antiguo, el campo `tpnumero` de los vencimientos de extras se rellenó con el número de línea de apunte (`ex_apuntes.numero`, un contador global) en vez del número real del extra/documento. Corregidos 1.118 vencimientos en empresas 1 y 2 recalculando el extra real a partir de la línea de apunte que coincide en cuenta e importe (incluye 7 casos donde el vencimiento legítimo tenía la cuenta en blanco, que inicialmente quedaron sin detectar). Sin esta corrección, algunos extras no podían borrarse por creerse enlazados a pagos bancarios que en realidad pertenecían a otro extra. Backups previos guardados en `backend/backups/gestionmgd_pre-fix-tpnumero-extras_*.db`. Script: `backend/scripts/fix_tpnumero_extras.py`

---

## [1.02.00] — 2026-07-20 — Conciliación bancaria, cuentas automáticas y UX de altas rápidas

### Correcciones de datos y conciliación
- **Duplicados en el diario (empresas 1 y 2)**: eliminados varios asientos duplicados/mal etiquetados que inflaban el mayor de CAJA, CAJA EQUIPO TÉCNICO y SOFIA; corregido `saldoini` de CAJA (empresa 1) que arrastraba un traspaso contado dos veces
- **Movimientos fantasma en SOFIA (empresa 1)**: eliminados 2 movimientos bancarios sin texto ni pagos que distorsionaban el saldo y la conciliación
- **Conciliación de bancos**: excluye ahora las líneas de cierre de ejercicio (`tpasiento='Z'`) del cálculo del saldo del mayor — un banco/caja cerrado ya no muestra una diferencia permanente aunque los datos sean correctos

### Nuevo
- **Cuenta contable automática**: al dar de alta un proveedor o cliente sin indicar cuenta, se asigna automáticamente (`400xxxx` proveedores, `430xxxx` clientes), evitando colisión con cuentas migradas
- **Extras — fecha de vencimiento editable**: al generar el vencimiento de pago de un extra nuevo, se propone por defecto la fecha del propio extra, pero puede modificarse
- **Diario — ordenar por fecha o nº de asiento**: nuevo selector en la pestaña Diario, con "Fecha" por defecto
- **Altas rápidas seguidas**: en Facturas, Extras y Movimientos de banco, al guardar un registro nuevo el formulario se vacía y permanece abierto (en vez de cerrarse) para seguir dando de alta sin reabrir el modal cada vez
- **Ir al movimiento creado**: al crear un movimiento bancario nuevo, la vista salta a la página donde queda y resalta la fila, igual que ya ocurría en Facturas

### Mejoras de interfaz
- **Menú lateral**: "Bancos" reordenado justo después de "Inicio"
- **Cabeceras con scroll**: en Bancos, Facturas, Proveedores, Albaranes, Artículos, Clientes, Extras, Usuarios, Contabilidad y Movimientos de banco, la cabecera ya no queda fija — se desplaza junto con el contenido

---

## [1.01.62] — 2026-07-03 — Rendimiento y mejoras menores (revisión, 5ª y última tanda)

### Mejoras
- **Listado de movimientos ~O(1) consultas**: los pagos de la página se cargan en una sola consulta y el enriquecimiento (cuentas, vencimientos, facturas, extras, pagas NNA, proveedores/clientes, bancos contraparte) se hace en lote — antes eran ~5 consultas por pago
- **`_recalcular_saldos`**: eliminado el parámetro `desde_numero` que se ignoraba (siempre recalculaba el banco completo; ahora la firma es honesta)
- **Retención de backups**: los safety backups `*_antes_restauracion.db` también se limpian a los 30 días (el parseo de fecha fallaba con el sufijo y quedaban para siempre)
- **Editar usuario NNA**: enviar el nombre vacío o nulo ya no rompe (se ignora el cambio y se conserva el nombre actual); el resto de campos se actualizan igualmente

---

## [1.01.61] — 2026-07-03 — Abonos, PyG unificado y filtros en servidor (revisión, 4ª tanda)

### Correcciones y mejoras
- **Reordenar movimientos**: al intercambiar el orden de dos movimientos se renumera el asiento completo (todas sus líneas, no solo la del banco) anclando por el banco propio — antes el asiento quedaba con líneas apuntando a números distintos y podía tocar asientos de otro banco con el mismo número
- **Abonos (vencimientos negativos)**: los vencimientos con importe negativo ahora funcionan — el pago los compensa hacia 0 en magnitud, la reversión respeta el signo, el estado del documento se sincroniza por magnitud y aparecen en las listas de pendientes (antes `max(0,…)` los dejaba inservibles con `pendiente=0`)
- **PyG unificado**: pantalla y export CSV usan el mismo cálculo (`get_pyg`): importes netos por cuenta (una cuenta de gasto con abonos puede restar), exclusión de apertura y saldo inicial de bancos incluidos en ambos — antes el export excluía tipos distintos y sus filas no sumaban el total
- **Editar total de factura**: el ajuste del vencimiento recorta el pendiente al rango válido y sincroniza el estado del documento (antes podía quedar pendiente negativo o una factura "Pendiente" ya cobrada)
- **Filtro "Solo no conciliados"**: se aplica en el servidor — la paginación y el contador total ahora son correctos (antes se filtraba en cliente la página ya cargada)

---

## [1.01.60] — 2026-07-02 — Validaciones de servidor y protecciones de borrado (revisión, 3ª tanda)

### Correcciones y mejoras
- **Cuadre en la API**: crear o editar un asiento descuadrado devuelve error 400 (antes la validación solo existía en el frontend y cualquier otro cliente podía descuadrar el diario)
- **Renumerar banco**: al cambiar el número de una cuenta bancaria se actualizan también los asientos del diario (`tpasiento='B{n}'`), que antes quedaban apuntando al número antiguo y rompían la conciliación
- **Protecciones de borrado**: no se puede eliminar un banco con movimientos, una cuenta contable con apuntes en el diario, ni un usuario NNA con pagas o apuntes en su cuenta 4001xxx; el mensaje del servidor se muestra en pantalla
- **Registro mensual de pagas**: guarda anti-duplicados — se omiten los usuarios que ya tienen una paga registrada en el mismo mes (un doble clic ya no duplica las pagas); las pagas extra pueden seguir registrándose individualmente
- **Asientos bancarios sin churn**: editar solo el texto/notas/estado/conciliación de un movimiento ya no elimina y regenera su asiento (solo se regenera si cambia el importe, los pagos, la fecha o la clave); si el movimiento no tenía asiento se genera automáticamente al guardar
- **Renombrado `paga_semanal` → `paga_mensual`**: la columna siempre almacenó la paga mensual; migración automática al arrancar (SQLite RENAME COLUMN) y limpieza del SQL crudo — de paso se corrige que la respuesta de crear usuario devolviera siempre `paga_mensual=0`

---

## [1.01.59] — 2026-07-02 — Correcciones de integridad contable (revisión de código, 2ª tanda)

### Correcciones
- **Numeración de vencimientos**: el número nuevo evita también los números referenciados por pagos de vencimientos ya borrados (helper `siguiente_numero_vencimiento`, aplicado en facturas, extras, pagas NNA y creación manual); eliminado el parche de `pagos_previos` que hacía que un vencimiento nuevo pudiera "heredar" pagos de un documento distinto y nacer pagado
- **Edición de asientos**: al editar un asiento desde Contabilidad se preservan `tipo`, `numero`, `tpasiento` y `clave` si el cliente no los envía — antes se perdía el vínculo con el documento origen (factura/extra/banco) y una regeneración posterior creaba un asiento duplicado
- **Sumas y saldos / PyG / cierre**: el filtro `excluir_tipos` ya no descarta las líneas con `tpasiento` NULL (semántica de `NOT IN` con NULL en SQL)
- **Caché de cuentas**: las pagas NNA actualizan ahora el debe/haber cacheado de `cuentas` (6780007 y 4001xxx) al crearse y borrarse; reparación puntual de las 418 cuentas con caché desfasada (el diagnóstico contable usaba estos valores)
- Aviso de vencimientos inexistentes en Bancos: el texto ya no promete re-vinculación automática (eliminada con el parche de `pagos_previos`)

---

## [1.01.58] — 2026-07-02 — Correcciones de integridad contable (revisión de código)

### Correcciones
- **Conciliación**: editar un movimiento bancario ya no desmarca su casilla de conciliado (el default `False` del esquema `MovimientoUpdate` reseteaba el campo en cada edición)
- **Vencimientos**: al editar o eliminar un movimiento que pagaba un vencimiento, el pendiente restaurado se recorta al importe del vencimiento (antes podía quedar `pendiente > importe` y el documento volvía a "Pendiente" estando pagado)
- **Borrado protegido**: ya no se puede eliminar una factura, extra o paga NNA cuyo vencimiento tenga pagos bancarios asociados; el servidor devuelve un error explicando qué movimiento hay que eliminar primero (evita pagos huérfanos y descuadres en la cuenta del tercero)
- **Transferencias**: el lado receptor de una transferencia sin pago propio ya no genera su propio asiento si otro banco tiene un pago apuntando a él (causa raíz de los asientos duplicados detectados en la conciliación de SOFIA/JUSTIFICADO/CAJA 3)
- **Borrado de movimientos**: al eliminar un movimiento se filtra el asiento por banco propio (no puede borrar el asiento de otro banco con el mismo número) y, al borrar el lado receptor de una transferencia, se elimina también el asiento numerado por el banco origen (antes quedaba huérfano)
- **Export Balance**: la fila "Resultado del ejercicio" ahora se incluye en el CSV (un `if` fuera del bucle hacía que nunca se escribiera y el balance exportado no cuadraba)
- **Cierre de ejercicio**: la regularización cierra por saldo neto, incluyendo cuentas de gasto (6xxx) con saldo acreedor y de ingreso (7xxx) con saldo deudor que antes quedaban abiertas; mismo ajuste en el resultado del Balance de situación
- **Edición de movimientos con asiento**: `_eliminar_asiento_banco` hacía `expire_all()` sin flush previo, descartando los cambios pendientes del movimiento (conciliado, texto, fecha…) — por eso el checkbox de conciliación solo funcionaba en movimientos sin asiento contable
- **Transferencias sin dirsubcta**: no generaban asiento en NINGÚN lado (el chequeo de "receptor" bloqueaba a ambos porque los pagos son simétricos); ahora genera el asiento el lado pagador (total negativo) y el receptor difiere
- Los mensajes de error de borrado del servidor se muestran ahora en pantalla (Extras, Pagas NNA) en lugar del genérico "Error al eliminar"

---

## [1.01.57] — 2026-07-02 — Pagas NNA: vencimiento automático para pago por banco

### Nuevas funcionalidades
- **Vencimiento de paga NNA**: al registrar una paga (individual o mensual masiva) se crea automáticamente un vencimiento tipo `N` con `pendiente=importe` para que pueda liquidarse desde el módulo Bancos vinculando el movimiento al vencimiento
- Al eliminar una paga también se elimina su vencimiento asociado
- En Bancos, al vincular un pago a un vencimiento tipo `N`, se muestra el nombre del NNA y la fecha de la paga en la información del documento

### Correcciones
- Conciliación bancaria: corregido bug por el que el checkbox no funcionaba al tener el servidor cargada la versión anterior (1.01.55); reiniciado el backend para cargar el código nuevo

---

## [1.01.56] — 2026-07-02 — Dashboard, conciliación bancaria, filtro de estado y alertas de vencimiento

### Nuevas funcionalidades
- **Dashboard (Inicio)**: nueva pantalla de inicio con saldos bancarios, importes pendientes de cobro/pago, ingresos y gastos del mes con comparativa respecto al mes anterior, y lista de vencimientos próximos (7 días) y recuento de vencidos — nuevo endpoint `GET /api/dashboard`
- **Conciliación bancaria (Bancos → Movimientos)**: cada movimiento tiene un checkbox para marcarlo como conciliado con el extracto bancario oficial; nuevo filtro "Solo no conciliados" en la cabecera; campo `conciliado` añadido al modelo `mov_bancos` (migración automática al arrancar)
- **Filtro por estado en Facturas**: selector Todos / Pendientes / Cobradas|Pagadas / Vencidas en el listado de facturas emitidas y recibidas; "Vencidas" muestra facturas pendientes con fecha de vencimiento ya pasada
- **Alertas de vencimiento en Facturas**: las facturas pendientes muestran el badge "Vencida" (rojo) si el vencimiento ya pasó, o "Vence en Nd" (naranja) si vence en 7 días o menos

---

## [1.01.55] — 2026-07-01 — Corrección masiva de estados Pendiente incorrectos en Empresa 2

### Correcciones
- **Facturas recibidas cnumero 399, 403, 404** (internas 406, 410, 411): aparecían como Pendiente pese a tener pago registrado — vencimientos 764, 781, 785 corregidos a `pendiente=0` y facturas a `estado='C'`
- **Anomalía detectada** en vencimiento 781 (cnumero 403): `pendiente=21.9` con `importe=10.95` (el doble), indicando que el pendiente fue restaurado sin volver a descontarse; corregido a 0
- Todos los casos siguen el mismo patrón: movimiento bancario creado antes que la factura/extra → el `_crear_vencimiento` original no comprobaba pagos previos → vencimiento nacía con `pendiente=importe` ignorando el pago existente

---

## [1.01.54] — 2026-06-30 — Bancos: corrección estado Pendiente/Cobrado y aviso de vencimiento roto

### Correcciones
- **Bug estado Pendiente incorrecto (3ª ocurrencia)**: extra 372 empresa 2 aparecía como Pendiente aunque tenía pago en banco Caja Coordinación. Causa raíz: el movimiento bancario se creó antes que el extra; al crearse el vencimiento, su `pendiente` se inicializaba con el importe completo sin verificar pagos previos que ya lo referenciaban
- **Fix estructural en `create_extra` y `_crear_vencimiento`**: al crear un vencimiento nuevo se comprueban los pagos existentes que apunten a ese número; si los hay, `pendiente` se inicializa descontando lo ya pagado y `_sync_estado_factura` actualiza el estado del documento padre
- **Saldo de cabecera en Movimientos Banco no se actualizaba**: al guardar, eliminar o reordenar un movimiento, el saldo de la tarjeta del banco en la cabecera ahora se refresca automáticamente

### Mejoras
- **Aviso visual de vencimiento roto en editor de movimientos**: si un pago referencia un vencimiento inexistente (el extra/factura fue eliminado y recreado), aparece icono ⚠ amarillo con tooltip explicativo
- **Confirmación antes de guardar** si hay líneas con vencimiento roto, indicando los números afectados

---

## [1.01.53] — 2026-06-30 — Cabecera de página y columnas fijas en todos los listados

### Mejoras
- **Cabecera de página fija**: el área de título, filtros, buscadores y botones de acción queda siempre visible al hacer scroll en todos los listados (Clientes, Proveedores, Artículos, Facturas, Albaranes, Extras, Bancos, Movimientos, Usuarios NNA y Contabilidad)
- **Columna de encabezado de tabla también fija**: combinado con la cabecera de página, la fila de nombres de columna (`thead`) permanece visible dentro de su propio contenedor de scroll
- Arquitectura: cada página usa `flex flex-col h-full` — la cabecera es `flex-shrink-0` (siempre visible) y el contenido es `flex-1 overflow-y-auto` (scroll propio), eliminando cualquier conflicto entre dos elementos `sticky` al mismo `top-0`
- En páginas con tabs (Facturas, Albaranes, Bancos, Usuarios, Contabilidad) los tabs también forman parte de la cabecera fija

---

## [1.01.52] — 2026-06-30 — Cabecera fija en todos los listados

### Mejoras
- **Sticky header en todos los listados**: la fila de encabezado de columnas queda fija al hacer scroll en las 10 páginas con tablas principales (Extras, Facturas, Bancos, Movimientos, Clientes, Proveedores, Artículos, Albaranes, Usuarios y todas las pestañas de Contabilidad)
- Eliminado `overflow-hidden` de las cards que envuelven tablas (era necesario para que `position: sticky` funcione con el scroll de la página)
- Los wrappers `overflow-x-auto` internos convertidos a `<div>` plano para no crear un contexto de scroll que bloqueara el sticky
- Las tablas dentro de modales no se ven afectadas

---

## [1.01.51] — 2026-06-30 — Bancos: reparar saldo automático al crear movimiento

### Mejoras
- **Reparar saldo automático**: al guardar un nuevo movimiento bancario, `_recalcular_saldos` se ejecuta automáticamente en orden `(fecha, numero)` — ya no es necesario pulsar "Reparar saldo" manualmente
- Si el movimiento incluye transferencia a otro banco, también se recalcula el banco destino

---

## [1.01.50] — 2026-06-30 — Extras: correcciones de pago y mejoras de visualización

### Correcciones
- **Bug pago_info incorrecto en Extras**: cuando un extra tenía más de un vencimiento (migración + pago real), `_cargar_pago_info` cogía siempre el más antiguo, mostrando banco y fecha erróneos. Ahora itera de más reciente a más antiguo y devuelve el primero con pago real asociado
- **Cuenta contrapartida del vencimiento**: al activar "Generar vencimiento de pago" en Nuevo Extra, el campo "Cuenta contrapartida" se rellena automáticamente con la cuenta del primer apunte en el Haber

### Mejoras
- **Columna Estado en lista de Extras**: muestra el badge de estado (Pagado/Cobrado/Pendiente) igual que Facturas — badge de color + nombre del banco en gris debajo, con tooltip completo (banco + fecha) al pasar el ratón

---

## [1.01.49] — 2026-06-30 — Ajustes: programación configurable del backup y restauración desde lista

### Nuevas funcionalidades
- **Programación del backup automático**: nueva tarjeta en Ajustes para seleccionar días de la semana y hora del backup automático
- Los días se muestran como botones toggle (Lun–Dom) y la hora con selector de tiempo
- La configuración se persiste en `backup_config.json` y se aplica en caliente sin reiniciar el servidor
- El scheduler de APScheduler se gestiona desde `ajustes.py` (refactorización interna: movido desde `main.py`)
- Nuevo endpoint `PUT /api/ajustes/config` para actualizar hora y días; `GET /api/ajustes/backups` devuelve la config completa
- **Restaurar desde la lista de backups**: botón "Restaurar" en cada fila de la tabla de copias de seguridad
- Restaura directamente desde el archivo ya almacenado en el servidor, sin necesidad de descargarlo y volver a subirlo
- Crea un backup de seguridad de la BD actual antes de restaurar, igual que el flujo de subida manual
- Nuevo endpoint `POST /api/ajustes/restaurar-backup/{nombre}`; lógica de restauración extraída a función helper `_restaurar_desde_path` compartida por ambos endpoints

---

## [1.01.48] — 2026-06-26 — Ajustes: restaurar BD desde archivo de copia de seguridad

### Nuevas funcionalidades
- **Restaurar backup**: nueva tarjeta en Ajustes para cargar un archivo `.db` y reemplazar la BD actual
- Validación del archivo: comprueba magic bytes SQLite y que se puede abrir como BD válida antes de restaurar
- Backup de seguridad automático antes de restaurar (`gestionmgd_YYYY-MM-DD_HH-MM_antes_restauracion.db`)
- `engine.dispose()` libera el pool de conexiones SQLAlchemy antes de reemplazar el archivo
- El regex de validación de nombres permite tanto backups normales como los de seguridad pre-restauración

---

## [1.01.47] — 2026-06-26 — Ajustes: backup automático diario + backup manual con descarga

### Nuevas funcionalidades
- **Apartado Ajustes** en el menú principal (debajo de Contabilidad)
- **Backup automático**: APScheduler lanza `hacer_backup()` cada día a las 02:00 (zona horaria Europe/Madrid); los backups se guardan en `backend/backups/gestionmgd_YYYY-MM-DD_HH-MM.db`; retención automática de 30 días
- **Endpoint `POST /api/ajustes/backup`**: crea un backup bajo demanda de forma segura con `sqlite3.Connection.backup()` (atómico, seguro con BD en uso)
- **Endpoint `GET /api/ajustes/backups`**: lista todos los backups con fecha y tamaño
- **Endpoint `GET /api/ajustes/backup/download/{nombre}`**: descarga un backup; valida el nombre con regex para evitar path traversal
- **Endpoint `DELETE /api/ajustes/backup/{nombre}`**: elimina un backup concreto
- **Página Ajustes**: tarjeta de backup con botón "Hacer backup ahora", tabla de backups con Descargar/Eliminar por fila, feedback visual de éxito/error
- `apscheduler==3.11.2` añadido a requirements.txt

---

## [1.01.46] — 2026-06-26 — Facturas: corrección campo proveedor/cliente se borraba al tabular

### Correcciones
- **AutocompleteEntidad**: al tabular tras seleccionar un proveedor/cliente, la selección ya no desaparece. La causa era `onFocus={abrir}` en la `div` del elemento seleccionado — al recibir el foco por Tab disparaba el modo búsqueda mostrando el input vacío. Ahora la `div` solo abre la búsqueda con clic, Enter o Espacio

---

## [1.01.45] — 2026-06-26 — Bancos: navegación con teclado en el menú Añadir

### Mejoras UX
- Botón **+ Añadir ▾** en el formulario de movimientos acepta navegación por teclado: `↓`/`↑` mueven el resaltado entre opciones (con wrap), `Enter` ejecuta la opción seleccionada, `Escape` cierra el menú
- `↓` abre el menú directamente si estaba cerrado (resaltando la primera opción); `↑` resalta la última
- El hover del ratón sincroniza el resaltado con el índice del teclado

---

## [1.01.44] — 2026-06-26 — Exportar pagas NNA: botón Exportar con Excel y CSV

### Cambios
- Botón **Exportar ▾** con dropdown: Excel (.xlsx) y CSV (.csv)
- CSV usa separador `;` y BOM UTF-8 para compatibilidad con Excel español
- Endpoint `GET /api/usuarios/pagas/export?format=xlsx|csv`

---

## [1.01.43] — 2026-06-26 — Exportar pagas NNA a Excel

### Funcionalidades nuevas
- Botón **Excel** en la pestaña Pagas: descarga `pagas_nna_{empresa}_{desde}_{hasta}.xlsx`
- Respeta los filtros activos (usuario, fecha desde/hasta)
- Columnas: Fecha · Usuario (nombre completo) · Importe (formato moneda)
- Fila de TOTAL al final del listado
- Endpoint `GET /api/usuarios/pagas/export`

---

## [1.01.42] — 2026-06-26 — Registrar mes: todos los NNA activos con importe individual

### Cambios
- `ModalMes` reescrito: carga todos los NNA activos (222 en empresa 2) en lugar de solo los que tienen paga_mensual>0
- Nuevo campo de búsqueda en el modal para filtrar por nombre
- Lista con botón "×" por fila para quitar usuarios de ese registro mensual (con "Restaurar todos")
- Importe individual por NNA (defecto = paga_mensual); filas con importe=0 no generan paga
- Corrección de datos: 4 usuarios faltantes en empresa 2 añadidos (4001079, 4001099, 4001116, 4001174); 25 con activo=0 en empresa 2 corregidos a activo=1

---

## [1.01.41] — 2026-06-26 — Pagas NNA: periodicidad mensual (renombrado de semanal)

### Cambios
- `paga_semanal` → `paga_mensual` en modelo, esquemas, servicios, API y frontend (columna BD conserva nombre `paga_semanal` por compatibilidad con SQLite 3.11)
- Endpoint `/pagas/semana` → `/pagas/mes`; función interna `registrar_semana` → `registrar_mes`
- Todos los textos UI actualizados: "Registrar semana" → "Registrar mes", "Paga semanal" → "Paga mensual", "Total semanal" → "Total mensual"

---

## [1.01.40] — 2026-06-26 — Usuarios NNA: migración desde cuentas 4001xxx y contabilización de pagas

### Funcionalidades nuevas
- **Migración de usuarios NNA**: 217 usuarios importados desde cuentas `4001001–4001218` (empresa 1) y 222 (empresa 2) — el sufijo de la cuenta es el número del usuario
- **Cuentas 4001xxx en la tabla usuarios**: al crear un nuevo usuario NNA se auto-crea la cuenta contable `4001XXX` si no existe
- **Pagas vinculadas al diario**: al registrar una paga (individual o semanal) se crean dos líneas en `diario` (`tipo='P'`, `tpasiento='PAG'`): DR 6780007 (GASTOS PAGAS MENORES) / CR 4001xxx; al eliminar la paga se eliminan las entradas correspondientes
- **Saldo por usuario**: nuevo endpoint `GET /api/usuarios/saldos?empresa_id=X` devuelve el saldo contable desde `diario` para cada cuenta 4001xxx
- **Tabla usuarios mejorada**: muestra columna Cuenta (4001xxx), Saldo desde diario y botón "Mayor" para navegar directamente al Libro Mayor filtrado por esa cuenta

---

## [1.01.39] — 2026-06-26 — Plan de cuentas: debe/haber calculados desde diario (fuente de verdad)

### Correcciones
- **Plan de cuentas calculaba mal debe/haber/saldo**: la tabla `cuentas` era una caché incremental que quedó desfasada desde la migración (las entradas `tipo=None` se insertaron en `diario` sin actualizar `cuentas`); muchas cuentas mostraban debe=0, haber=0 con saldo=0 siendo incorrectos
- **`get_cuentas` reescrito con JOIN desde diario**: ahora calcula `debe` y `haber` con `SUM(importe)` directamente desde `diario` en cada consulta — nunca puede quedar desfasado
- **Recalculados manualmente** los saldos de la tabla `cuentas` para ambas empresas como corrección puntual

---

## [1.01.38] — 2026-06-25 — Plan de cuentas: filtro saldo≠0 y botón → Mayor

### Mejoras
- **Filtro "Solo con saldo"**: checkbox en Plan de cuentas que muestra únicamente las cuentas con debe≠haber; soporte añadido en servicio y endpoint (`solo_con_saldo=true`)
- **Botón → Mayor**: cada fila del plan de cuentas tiene un botón que navega directamente al Libro mayor precargado con esa cuenta

---

## [1.01.37] — 2026-06-25 — P&G excluye apertura para que resultado+saldo_inicial = total bancos

### Correcciones
- **P&G excluye tpasiento='A'**: las entradas de apertura (tp='A') de cuentas 6/7 son arrastres de ejercicio anterior y no deben contarse como ingresos/gastos del año actual; al incluirlas se producía un descuadre de 17,94 € (7780000 apertura) entre "Resultado + saldo inicial" y el total real en bancos
- **Resultado ahora cuadra**: con la exclusión de 'A', la fórmula `resultado + saldo_inicial_bancos = total 57xxxx en Diario` es exacta (ambos = 3.783,55 €)

---

## [1.01.36] — 2026-06-25 — P&G incluye saldo inicial de bancos en el resultado

### Nuevas funcionalidades
- **P&G muestra saldo inicial de bancos**: el endpoint `/pyg` calcula el saldo de las cuentas 57xxxx del asiento de apertura (`tpasiento='A'`) y lo devuelve como `saldo_inicial_bancos`
- **Resultado + saldo inicial**: nuevo campo `resultado_con_saldo_inicial` = resultado del ejercicio + saldo inicial; permite ver la posición económica real considerando el capital en bancos al empezar
- **Frontend P&G**: cuando hay saldo inicial, se muestran dos filas adicionales: el saldo de apertura (azul) y el resultado combinado
- **Fechas por defecto corregidas**: el tab P&G ahora usa el año actual (`anioActual`) en lugar del año anterior, evitando que empresa 2 (2026) aparezca vacía con las fechas por defecto

---

## [1.01.35] — 2026-06-25 — Fix FK error en _crear_lineas_raw + extra 1 emp1 duplicado

### Correcciones
- **`_crear_lineas_raw` usa raw SQL para Diario y Cuenta**: `db.add(Diario(...))` fallaba en `db.flush()` con `NoReferencedTableError` (`diario.empresa_id → empresas`) al tener asientos pendientes en empresa 1; ahora usa INSERT raw igual que `_eliminar_asiento_banco`
- **`generar_asiento_extra` usa raw SQL para DiarioTxt**: el upsert de DiarioTxt (`db.add(DiarioTxt(...))` y mutación ORM) causaba el mismo error FK; sustituido por INSERT/UPDATE raw SQL
- **Extra 1 empresa 1 duplicado**: asiento 12 (migración apertura) tenía entradas de extra 1 con `tipo=None`; convertidas a `tipo='X', numero=1`; asientos duplicados 2991 y el previo 14 eliminados
- **Cuenta 1290000 empresa 1 saldada**: saldo=0.0 tras eliminar los duplicados (el año 2025 ya estaba cerrado con asiento Z)

---

## [1.01.34] — 2026-06-25 — Cuentas descuadradas por duplicados de extras de migración

### Correcciones
- **Cuentas 4101082 y 4101108 descuadradas**: asientos 2033 y 2034 eran duplicados generados porque los asientos de migración (2 y 3) tenían `tipo=NULL` en sus entradas de extras — invisibles para `_ya_tiene_asiento` que filtra `tipo='X'`
- **Asiento 2 convertido**: entradas de extra 6 (cuentas 6780008/4101082) actualizadas a `tipo='X', tpasiento='EXT', numero=6`; asiento 2033 eliminado
- **Asiento 3 saneado**: entradas de extra 299 (6780008/4101108) eliminadas de asiento 3 — ya cubiertas por asiento 2034 con fecha correcta (2026-05-23)
- **Tabla Cuenta recalculada**: debe/haber de 4101082, 4101108 y 6780008 recalculados desde Diario; saldos resultan 0.0, 0.0 y 1638.44 respectivamente

---

## [1.01.33] — 2026-06-25 — Revisión completa del código de generación de asientos bancarios

### Correcciones
- **`_eliminar_asiento_banco` protege asientos mixtos**: si el asiento a eliminar contiene entradas no-B (asientos de migración que mezclan entradas bancarias con otras contables), solo se eliminan las entradas B del banco actual; las entradas no bancarias quedan intactas
- **`_eliminar_asiento_banco` usa raw SQL**: igual que otras funciones, evita el error `NoReferencedTableError` de SQLAlchemy al hacer flush con operaciones mezcladas de DELETE + UPDATE en tablas con FK
- **Guardia cross-bank con fallback fecha+importe**: el comprobador "¿ya generó el banco contraparte su asiento?" también busca ahora asientos de migración con `numero=NULL` comparando por fecha e importe del movimiento receptor, consistente con el fallback añadido en `_ya_tiene_asiento_banco`

---

## [1.01.32] — 2026-06-25 — Corrección bug duplicados en generar_pendientes

### Correcciones
- **`_ya_tiene_asiento_banco` con fallback fecha+importe**: cuando no hay entrada con `tipo='B' AND numero=X`, busca además por `(tipo='B', numero=NULL, fecha, importe)` para detectar asientos de migración que quedaron sin número de movimiento (ej. asiento 3 con `numero=NULL`)
- **Asiento 3 número corregido**: las entradas bancarias (5700000, 5703002) tenían `numero=NULL`; se actualizó a `numero=1` (movimiento CAJA correspondiente) para que `_ya_tiene_asiento_banco` las encuentre directamente
- **Asiento 2035 eliminado**: duplicado generado porque el fallback aún no existía al correr `generar_pendientes` tras el fix de la v1.01.31

---

## [1.01.31] — 2026-06-25 — Conciliación bancaria: 5 discrepancias corregidas

### Correcciones
- **5 bancos con discrepancia 0** tras identificar y corregir asientos migrados con `tpasiento` incorrecto:
  - Asiento 3 (tipo=`None`/`M`): transferencia CAJA→CAJA ET de 97.5€ — actualizado a `tipo='B' tpasiento='B1'` para que conciliación lo reconozca
  - Asiento 1294 (`tpasiento='B17'` → `'B1'`): transferencia CAJA mov 1055 → CAJA ET (0.82€)
  - Asiento 1350 (`tpasiento='B8'` → `'B14'`): transferencia PENDIENTE mov 1081 → CAJA (10€)
  - Asiento 1362 (`tpasiento='B7'` → `'B6'`): transferencia SOFIA mov 1089 → CAJA (49.9€)
  - Asiento 1314 (`tpasiento='B16'` → `'B6'`): transferencia SOFIA mov 1085 → CAJA3 (1.85€)
- **Asientos duplicados eliminados** (2027, 2028, 2030, 2031, 2032): `generar_pendientes` los había creado al no reconocer los asientos originales por sus tpasientos incorrectos

---

## [1.01.30] — 2026-06-25 — Tab Diagnóstico en Contabilidad

### Nuevas funcionalidades
- **Tab "Diagnóstico" en Contabilidad**: panel que analiza la base de datos en busca de extras con apuntes completos sin asiento EXT, movimientos bancarios con contrapartida resoluble sin asiento, y cuentas de proveedor (4xxxx) con saldo deudor
- **Botón "Reparar todo"**: llama a `generar-pendientes` y muestra cuántos asientos se generaron por tipo
- **Botón "Generar" por movimiento**: permite regenerar el asiento de un movimiento bancario individual directamente desde el diagnóstico
- **Endpoint `GET /api/contabilidad/diagnostico`**: detecta las tres categorías de inconsistencias con filtros inteligentes (excluye transferencias ya cubiertas por el banco contraparte, excluye movimientos históricos sin contrapartida resoluble, limita a 50 más recientes)

### Correcciones
- **Prevención en `update_extra`**: aunque no haya cambio de apuntes ni fecha, si el extra tiene apuntes D+H completos y no tiene asiento EXT, lo genera automáticamente

---

## [1.01.29] — 2026-06-23 — Corrección cuenta 4000631 y bugs de asientos

### Correcciones
- **Cuenta 4000631 a 0**: generados asientos EXT para extras 352 y 353 que existían con apuntes D/H completos pero sin asiento contable
- **`_ya_tiene_asiento_banco` mejorado**: en lugar de filtrar SOLO por tpasiento=`'B{n}'` (que rechazaba asientos migrados 'M'), ahora acepta entradas migradas/manuales (tpasiento sin 'B' + dígito) y solo descarta entradas atribuidas a un banco diferente (`'B{otro}'`)
- **`_eliminar_asiento_banco` con tpasiento**: evita destruir asientos de otros bancos al eliminar/regenerar; versión anterior podía borrar el asiento del banco contraparte si tenía el mismo numero de movimiento
- **Asiento 1356 `tpasiento` corregido**: era `'B8'` (CAJA COORDINACION) pero pertenece a banco 5 (COORDINACION SERGIO, cuenta='5709000'); corregido a `'B5'`

---

## [1.01.28] — 2026-06-23 — Corrección conciliación bancos: transferencias entre bancos

### Correcciones
- **Falso positivo `ya_cubierto`**: `_ya_tiene_asiento_banco` y `_eliminar_asiento_banco` ahora filtran por `tpasiento='B{banco.numero}'`, evitando confundir asientos generados por el banco contraparte que comparten el mismo número de movimiento
- **Receptor sin `dirsubcta` no genera asiento**: si un pago tiene `bancot+numerot` pero `dirsubcta=None`, el movimiento es el lado receptor de la transferencia; el emisor es quien genera el asiento, así que el receptor ahora devuelve `None` y no crea duplicados
- **Conciliación paso 3**: reconoce tanto el lado receptor como el lado emisor de transferencias cuando el asiento fue generado por el banco contraparte (y por tanto usa el número de movimiento del otro banco); ambos casos se emparejan correctamente sin mostrar discrepancias
- **Conciliación paso 1**: solo agrupa líneas del Libro Mayor generadas por el banco actual (`tpasiento='B{N}'`), evitando que entradas del banco contraparte consuman matches de movimientos no relacionados
- **Frontend**: al pulsar "Generar" y obtener `regenerado=false`, se muestra el motivo junto al movimiento en lugar de ignorarlo silenciosamente; movimientos del lado receptor de una transferencia muestran la etiqueta "transferencia" en lugar del botón "Generar"

---

## [1.01.27] — 2026-06-23 — Encabezados editables y nombre de fichero por plantilla

### Nuevas funcionalidades
- **Encabezados editables**: clic en el nombre de cualquier columna en el modal lo convierte en un input editable; Enter confirma, Escape cancela; los nombres modificados aparecen en azul con indicación del nombre original
- **Nombre de fichero desde plantilla**: al cargar o guardar una plantilla, el fichero exportado (CSV o Excel) toma el nombre de la plantilla (ej. `Gastos NNA junio.xlsx`)
- Las plantillas ahora guardan también los encabezados personalizados y los restauran al cargar
- El botón de guardar plantilla cambia a "↑ Actualizar" cuando hay una plantilla activa

---

## [1.01.26] — 2026-06-23 — Plantillas de columnas en exportación del Libro Mayor

### Nuevas funcionalidades
- **Plantillas guardadas**: en el modal de exportación hay una sección "Plantillas" que permite guardar la selección y orden de columnas con un nombre libre y recuperarla en cualquier momento
- Guardar: pulsar "+ Guardar actual", escribir el nombre (Enter confirma, Escape cancela)
- Si se guarda con un nombre ya existente, lo reemplaza
- Cargar: pulsar el chip de la plantilla (carga selección + orden)
- Borrar: pulsar × en el chip
- Persistencia en `localStorage` (clave `gestion_mgd_mayor_plantillas`), sin necesidad de backend

---

## [1.01.25] — 2026-06-23 — Exportar Libro Mayor a Excel, reordenar columnas y fecha dd/mm/aaaa

### Nuevas funcionalidades
- **Exportar a Excel (.xlsx)**: nuevo botón "Descargar Excel" en el modal; genera fichero con cabecera coloreada, anchos de columna automáticos y números nativos (sin reemplazar el punto decimal)
- **Reordenar columnas**: las filas del modal son arrastrables (drag-and-drop HTML5 nativo) con indicador `⠿`; el orden elegido se respeta en el fichero exportado
- **Fecha en formato dd/mm/aaaa** en lugar de yyyy-mm-dd (tanto CSV como Excel)
- Dependencia añadida: `openpyxl==3.1.5`

---

## [1.01.24] — 2026-06-23 — Cuenta y descripción de contrapartida en Libro Mayor

### Nuevas funcionalidades
- **2 columnas nuevas en la exportación del Libro Mayor**: Cuenta contrapartida (código de la cuenta del lado contrario del asiento) y Descripción contrapartida (nombre de esa cuenta desde el plan de cuentas)
- En asientos con varias contrapartidas, los valores se muestran separados por ` / `

---

## [1.01.23] — 2026-06-23 — DiarioTxt en extras y columna Notas

### Nuevas funcionalidades
- **DiarioTxt automático al crear/editar extras**: `generar_asiento_extra` hace upsert en `diario_txt` con el `texto` (nombre del beneficiario) y las `notas` del extra; al eliminar un extra también se borra su DiarioTxt
- **Columna Notas** añadida al formulario de exportación del Libro Mayor (disponible junto a Concepto tercero)

### Corrección de bug
- **Extras nuevos no generaban asiento**: con `autoflush=False`, los `ExApuntes` añadidos en `_crear_apuntes` no eran visibles en la query de `generar_asiento_extra`; corregido añadiendo `db.flush()` antes de llamar al generador en `create_extra` y `update_extra`

---

## [1.01.22] — 2026-06-23 — Columnas adicionales en exportación del Libro Mayor

### Nuevas funcionalidades
- **4 columnas nuevas en la exportación del Libro Mayor**: Tipo documento (`X`=extra, `F`=factura, `B`=banco), N.º documento (número de factura / movimiento bancario / extra), Descripción cuenta (nombre del plan de cuentas), Concepto tercero (nombre del cliente/proveedor/trabajador desde DiarioTxt)
- El modal de exportación muestra la descripción de cada columna al pasar el cursor
- Botón "Por defecto" para restaurar la selección estándar de 7 columnas

---

## [1.01.21] — 2026-06-23 — Formulario de columnas en Libro Mayor

### Nuevas funcionalidades
- **Formulario de columnas para exportación del Libro Mayor**: el botón "Exportar CSV..." abre un modal donde se seleccionan qué columnas incluir en el fichero (Fecha, N.º Asiento, Tipo, Referencia, Debe, Haber, Saldo acumulado), con botón "Todas/Ninguna" para selección rápida
- El endpoint `/export/mayor` acepta el parámetro `columnas` (lista separada por comas); si no se proporciona, exporta todas las columnas como antes

---

## [1.01.20] — 2026-06-23 — Balance de situación, Cierre de ejercicio y Exportar CSV

### Nuevas funcionalidades
- **Balance de situación** (nueva pestaña): calcula activo, pasivo y patrimonio neto siguiendo el PGC español; muestra resultado del ejercicio integrado en PN; detecta si el balance no cuadra
- **Cierre de ejercicio automático** (botón en la pestaña Balance): genera los asientos de regularización (6xxx/7xxx → cuenta 129), cierre (todos los saldos a cero) y apertura del ejercicio siguiente (01/01/año+1), con verificación de que no se cierre dos veces el mismo año
- **Exportar CSV** en las pestañas Diario, Libro Mayor, Sumas y saldos, P&G y Balance; los archivos se descargan directamente desde el navegador con separador `;` compatible con Excel

---

## [1.01.19] — 2026-06-22 — Tipos descriptivos en el Diario

### Mejoras
- **Diario — Tipo de asiento**: los asientos generados automáticamente ahora llevan etiqueta descriptiva: `ENV` (facturas enviadas), `REC` (facturas recibidas), `EXT` (extras), `B{n}` (movimiento del banco nº n)
- **Editor de asientos manual**: el selector Tipo incluye las nuevas etiquetas ENV, REC, EXT y M (migración)
- Migración de datos: los registros existentes con `FV`→`ENV`, `FP`→`REC`, `GX`→`EXT`, `BN`→`B{n}`

---

## [1.01.18] — 2026-06-22 — Integridad del Diario en todas las operaciones

### Correcciones
- **Extras — Eliminar**: al borrar un extra ahora se eliminan correctamente sus asientos del Diario/Libro Mayor (antes quedaban entradas huérfanas)
- **Extras — Editar**: al modificar los apuntes o la fecha de un extra se regenera su asiento contable; el Diario queda siempre actualizado
- **Facturas — Editar**: el asiento contable se regenera siempre que cambien las líneas de detalle (sin importar si el total varía o no), la cuenta principal del cliente/proveedor o la fecha; antes solo se regeneraba cuando el total cambiaba

---

## [1.01.17] — 2026-06-22 — Reordenación de bancos por número

### Mejoras
- **Bancos — cambio de Nº**: en el modal de edición de una cuenta bancaria aparece el campo "Nº (orden)", permitiendo asignar un número diferente para reordenar los bancos; el cambio se propaga en cascada a todos los movimientos y pagos asociados; si el número ya está en uso se muestra un error antes de tocar nada

---

## [1.01.16] — 2026-06-22 — Navegación rápida desde Clientes/Proveedores y búsqueda extendida en Facturas

### Mejoras
- **Acceso directo desde Clientes/Proveedores**: cada fila del listado incluye botones "Facturas" (abre el módulo con el cliente/proveedor ya filtrado) y "Mayor" (abre Libro Mayor con la cuenta precargada y búsqueda automática); "Mayor" aparece en gris si el registro no tiene cuenta asignada
- **Búsqueda extendida en Facturas**: además del campo de referencia, filtros por rango de fechas (Desde/Hasta) y por cliente/proveedor con autocomplete desplegable y botón ✕ para limpiar; botón "Borrar filtros" cuando hay alguno activo

---

## [1.01.15] — 2026-06-22 — Paginación configurable y autocomplete de cuentas

### Mejoras
- **Paginación en toda la app**: selector 50 / 100 / 150 / Todo en todos los módulos (Clientes, Proveedores, Artículos, Albaranes, Facturas, Extras, Bancos, Movimientos, Diario, Libro Mayor, Plan de Cuentas, Usuarios/Pagas)
- **Corrección UsuariosPage**: paginación estaba rota (`pagina`/`onChange` → `skip`/`onCambiar`)
- **Autocomplete de cuentas contables**: nuevo componente `AutocompleteCuenta` que busca por prefijo de código o nombre de cuenta; integrado en filtro del Diario, líneas de asiento (debe/haber) y campo del Libro Mayor
- Campo de autocomplete a doble de tamaño (input `w-72`/`w-80`, desplegable 560px)

---

## [1.01.14] — 2026-06-22 — Módulo Facturas: información de cuenta de pago

### Mejoras
- **Facturas recibidas y emitidas**: cuando el vencimiento ha sido pagado/cobrado, el modal muestra la cuenta bancaria, fecha e importe del pago (igual que en el módulo Extras)
- **Lista de facturas**: la columna Estado muestra el nombre del banco bajo el badge "Cobrada/Pagada"
- Backend: nueva función `_cargar_pago_info` en `services/facturas.py` que sigue la cadena vencimiento → pago → banco → movimiento; inyectada en todas las funciones de lectura (lista y detalle, emitidas y recibidas)
- Schema: `FacturaPagoInfo` añadido a `schemas/facturacion.py`; campo `pago_info: Optional[FacturaPagoInfo]` en `FacturaEmiRead` y `FacturaRecRead`

---

## [1.01.13] — 2026-06-22 — Conciliación bancaria empresa 2: corrección de asientos cruzados

### Correcciones
- **19 bancos empresa 2 en 0 discrepancias**: se detectó y corrigió un patrón sistemático donde los asientos de transferencias entre cajas tenían los números de movimiento cruzados (el número del banco origen se usaba en ambas líneas en vez del número propio de cada banco)
- **14 asientos eliminados** (1339, 1347, 1348, 1349, 1350, 1361, 1363, 1364, 1379, 1383, 1384, 1386, 1395, 1399) y reemplazados por **10 asientos correctos** (1445–1454) con el número de movimiento real de cada banco en su línea correspondiente
- **5 líneas de diario corregidas** en asientos 1393, 1441, 1442, 1443, 1444 (número de movimiento incorrecto en la línea de la cuenta destino)
- **3 pares de transferencia sin asiento** creados: CAJA↔COORD.SERGIO (+150€), CAJA↔CAJA.ADMIN (−150€), COORD.SOFIA↔TICKET.CONSUM (9,98€)

---

## [1.01.12] — 2026-06-19 — Conciliación bancaria: correcciones de lógica

### Correcciones
- **Saldo banco corregido**: ahora usa `saldoini + saldoact` (saldo real visible en el módulo de bancos) en lugar de solo `saldoact`
- **Saldo libro mayor corregido**: ahora suma todos los asientos del diario para la cuenta (incluyendo apertura, migrados y bancarios), igual que lo que muestra el libro mayor
- **Algoritmo de emparejamiento mejorado**: doble paso — primero por número exacto, luego por `(fecha, importe)` para absorber desfases de numeración de datos migrados; evita mostrar cientos de falsos positivos en empresas con datos históricos
- **Rastreo por id de entrada**: el seguimiento de asientos emparejados se hace por `Diario.id` en lugar de por `numero`, corrigiendo un bug que ocultaba líneas de asientos con múltiples entradas bajo el mismo número
- El detalle pasa de mostrar 178 items (92 falsos + 86 falsos) a los 8 problemas reales con la suma de diferencias cuadrando exactamente con la discrepancia global

---

## [1.01.11] — 2026-06-19 — Libro mayor: saldo continuo entre páginas

### Correcciones
- **Libro mayor paginado**: el saldo acumulado ya continúa correctamente al pasar de página; el backend calcula `saldo_anterior` (suma de importes de todas las filas previas al `skip`) y el frontend lo usa como base; en páginas 2+ se muestra una fila informativa "Saldo anterior (N movimientos)" al inicio de la tabla

---

## [1.01.10] — 2026-06-19 — Conciliación bancaria: comparación de saldos

### Cambios
- **Conciliación bancaria rediseñada**: en vez de comparar totales de movimientos, ahora compara **saldo banco** (`saldoact`) vs **saldo libro mayor** (suma de asientos tipo 'B' en Diario para la cuenta del banco); muestra la diferencia global y, cuando no cuadra, lista los movimientos con asiento faltante, importe diferente o asientos huérfanos con su número, fecha y detalle para facilitar la corrección

---

## [1.01.09] — 2026-06-19 — Libro mayor: corrección de desfases en cuentas de proveedor

### Correcciones
- **Cuenta 4000022 (DECATHLON)**: facturas 393 y 394 no generaban asiento porque `prcuenta=''`; corregidas con `prcuenta='4000022'` y cuenta de gasto `6780000`, asientos regenerados vía `generar_asientos_pendientes`
- **Cuenta 4000732 (EURLI)**: asiento migrado 759 tenía línea con `cuenta=NULL` e importe 34,60 que ocultaba el pago; corregido asignando `cuenta='4000732'` y actualizando acumulados en tabla `cuentas`
- **Backend `create_factura_rec`**: ahora auto-rellena `prcuenta` desde `proveedor.cuenta` si el campo llega vacío, evitando facturas sin asiento contable
- **Frontend `FacturasPage`**: al seleccionar proveedor en el formulario, se auto-rellena `prcuenta` con la cuenta contable del proveedor
- **Auditoría completa de cuentas**: verificado que no existen más desfases — todas las cuentas 4xxxxx y 41xxxxx tienen saldo cero, sin vencimientos pendientes ni movimientos bancarios sin asiento

---

## [1.01.08] — 2026-06-19 — Sumas y Saldos: asientos faltantes de extras y facturas recibidas

### Correcciones
- **14 cuentas 4XXXXXX con saldo deudor** en empresa 2: generados los asientos contables faltantes de 9 extras (tipo G con apuntes D/H) y 15 facturas recibidas que existían en BD pero nunca tuvieron asiento en Diario
- Las facturas sin `prcuenta` reciben la cuenta del proveedor asociado; los apuntes sin `cuenta` reciben `6780000` (cuenta de gastos usada en todas las facturas existentes de la empresa)
- **`generar_asiento_extra`**: nueva función en `services/contabilidad.py` que genera el asiento D/H de un extra a partir de sus ExApuntes; llamada automáticamente desde `create_extra`
- **`generar_asientos_pendientes`** ampliado para incluir extras (además de bancos, facturas recibidas y emitidas)

---

## [1.01.07] — 2026-06-18 — Extras: estado automático + banco de pago

### Nuevo
- **Extras — banco de pago**: al editar un extra con estado Cobrado/Pagado, el formulario muestra una barra verde con el banco, fecha e importe del pago bancario registrado
- **Extras — sync automático de estado**: al registrar o eliminar un pago bancario sobre un vencimiento tipo X, el extra.estado se actualiza a C o P automáticamente (igual que facturas)
- **Extras — reparación masiva de estados históricos**: 564 extras corregidos a C y 572 a P en ambas empresas, sincronizando con vencimiento.pendiente

---

## [1.01.06] — 2026-06-18 — Corrección asientos bancarios: números de contrapartida

### Correcciones
- **Asiento 1392** (CAJA COORDINACION ↔ PAGAS): la línea de contrapartida de CAJA COORD usaba `num=1074` (número del movimiento receptor de PAGAS), lo que colisionaba con el asiento propio de CAJA COORD para su mov 1074; corregido a `num=1077` (número del movimiento emisor de CAJA COORD)
- **Asiento 1352** (COORDINACION SOFIA → CAJA 3): la línea de CAJA 3 usaba `num=1090` (su propio movimiento receptor), impidiendo que CAJA 3 mov 1090 se detectase como contrapartida; corregido a `num=1085` (número del movimiento emisor de SOFIA)
- Ambas empresas quedan sin errores `sin_asiento` ni `importe_diff` en Conciliación
- Estas correcciones son de datos en BD; la lógica de heurística `asiento_principal` del servicio `get_conciliacion_bancos` se mantiene como salvaguarda para futuros casos similares

---

## [1.01.05] — 2026-06-18 — Extras: estado Pendiente / Pagado / Cobrado

### Nuevo
- **Extras — Estado**: campo `estado` con valores `P` (Pendiente) y `C` (Cobrado/Pagado)
- Badge de estado en el listado: "Cobrado" (verde) para ingresos cobrados, "Pagado" (verde) para gastos pagados, "Pendiente" (amarillo) en caso contrario
- Selector de estado en el formulario del Extra (editable manualmente)
- Nuevos extras se crean con `estado = 'P'` por defecto
- El estado se sincroniza automáticamente al registrar o eliminar un pago bancario vinculado al Extra (vencimiento tipo `'X'`): igual que Facturas

---

## [1.01.04] — 2026-06-18 — Extras: botón Renumerar

### Nuevo
- **Extras — Renumerar**: botón global que reasigna `cnumero` por año en orden de fecha (igual que Facturas); botón `↺` por fila para renumerar desde ese extra en adelante dentro del mismo año
- Endpoint `POST /api/extras/renumerar` con campo opcional `desde_id`
- El Nº mostrado usa `cnumero` (si existe) o `numero` como fallback

---

## [1.01.03] — 2026-06-18 — Extras: número en formato Nº X/AAAA

### Correcciones
- El campo Nº en el listado de Extras ahora muestra `numero/año` (p.ej. `42/2024`) igual que Facturas

---

## [1.01.02] — 2026-06-18 — Eliminado campo "Cuenta contable" en líneas Vto. de movimiento bancario

### Correcciones
- El campo editable "Cuenta contable" ya no aparece en las líneas de tipo Vto. pendiente del formulario de movimiento bancario; el campo `dirsubcta` sigue enviándose al backend desde el vencimiento seleccionado, pero no es editable en este formulario

---

## [1.01.01] — 2026-06-18 — Corrección color/signo extras importados (tipo M)

### Correcciones
- Extras con `tipo='M'` (importados del sistema anterior) aparecían en verde positivo aunque son gastos; ahora muestran rojo negativo igual que `tipo='G'`
- La lógica de color y signo en ExtrasPage es ahora `tipo === 'I' ? verde/positivo : rojo/negativo` para cubrir todos los tipos no-ingreso (G, M, A, R, Z)
- `TIPOS` ampliado con M='Gasto', A='Apertura', R='Regulariz.', Z='Cierre' para mostrar etiqueta correcta en lugar de la letra

---

## [1.01.00] — 2026-06-18 — Mejoras de UX y correcciones de saldos

### Nuevo
- **Bancos — cabecera fija**: al hacer scroll en un banco, el encabezado (nombre, saldo, filtro y botón «Nuevo movimiento») permanece visible
- **Bancos — Reparar saldos**: botón por banco que recalcula `saldonue` de todos sus movimientos en orden `(fecha, numero)` y sincroniza `saldoact`; endpoint `POST /api/bancos/{id}/reparar_saldos`
- **Facturas — scroll al nuevo registro**: al crear una factura el listado va a la página 1 y hace scroll con resaltado hasta la fila creada
- **Extras — scroll al nuevo registro**: comportamiento idéntico al de Facturas
- **Extras — orden más reciente primero**: el listado ahora ordena por `(fecha DESC, numero DESC)`, igual que Facturas
- **Versionado**: sistema `X.XX.XX` en `frontend/src/version.js` y `backend/app/main.py`; se muestra como `X.X.X` en el sidebar; endpoint `GET /api/version`
- **CHANGELOG.md**: registro de cambios en la raíz del proyecto

### Correcciones
- `extra_tipo` añadido a `VencimientoRead`; extras de tipo Gasto ahora aparecen con importe negativo (pago) en «Vtos. pendientes» de Bancos
- `_recalcular_saldos` reescrito para ordenar por `(fecha, numero)` en lugar de `numero`; `saldoact` se sincroniza al final desde la suma real de movimientos
- `delete_movimiento` llamaba a `_recalcular_saldos` manualmente con actualización incremental de `saldoact`; ahora llama correctamente a `_recalcular_saldos` después del borrado
- `create_banco` inicializaba `saldoact = saldoini` (duplicaba el saldo inicial); corregido a `saldoact = 0`
- `saltarUltima` eliminado de ExtrasPage (ya no necesario con orden DESC)

---

## [1.00.00] — 2026-06-18 — Release inicial versionada

### Módulos implementados

#### Empresas
- Selección de empresa al iniciar la aplicación (pantalla completa en `/`)
- Soporte multi-empresa; todos los datos están aislados por `empresa_id`
- La empresa activa se persiste en `localStorage`

#### Clientes y Proveedores
- CRUD completo con paginación y búsqueda
- Campos: nombre, NIF/CIF, dirección, cuenta contable, cuenta de contrapartida
- Formulario de contacto reutilizable (`FormContacto`)

#### Artículos y Familias
- CRUD de artículos con precio de venta, tipo de IVA y descuento
- Agrupación por familias

#### Albaranes
- CRUD de albaranes emitidos con líneas de artículos
- Componente `LineasDocumento` compartido con Facturas

#### Facturas
- Facturas emitidas y recibidas en el mismo módulo (tabs)
- Creación/edición con líneas de artículos (`LineasDocumento`)
- Autocomplete de cliente/proveedor por nombre o CIF (`AutocompleteEntidad`)
- Navegación por teclado en el autocomplete (↑↓ para moverse, Enter para seleccionar, Escape para cerrar)
- Orden de tabulación en el formulario: Fecha → Cliente/Proveedor → Nº factura proveedor → Fecha factura prov. → Notas → Añadir línea → Estado
- Campo precio con soporte de coma y punto numérico como separador decimal
- Texto por defecto "Total" en descripción de nueva línea; foco automático al añadir línea
- Estado Pendiente / Cobrada/Pagada; sincronización automática al registrar el pago
- Renumeración de facturas (global o desde una factura concreta)
- Generación automática de asiento contable al guardar

#### Bancos
- CRUD de cuentas bancarias con saldo inicial
- Listado de movimientos por banco con saldo acumulado por fila
- Encabezado fijo (sticky) al hacer scroll dentro de un banco
- Formulario de nuevo movimiento con foco automático en el campo Fecha
- Líneas de movimiento por tipo:
  - **V** — vencimiento (factura recibida/emitida/extra): importe prefijado desde el pendiente
  - **D** — apunte directo a subcuenta contable
  - **B** — transferencia a otro banco (crea movimiento espejo automáticamente)
- Selector de vencimientos pendientes (`VtosSelector`): signo automático según tipo (facturas recibidas y extras-gasto → negativo; emitidas y extras-ingreso → positivo)
- Al añadir línea "Otro banco", el importe se prefija con el saldo restante del movimiento
- Botón "Reparar saldos" por banco: recalcula `saldonue` de cada movimiento y sincroniza `saldoact`
- Badges de tipo de vencimiento en las líneas (Recibida / Enviada / Extra)
- Reordenación de movimientos dentro del mismo día (↑ ↓)

#### Extras
- CRUD de apuntes extra (gastos/ingresos no vinculados a factura)
- Apuntes contables con campos Cuenta y Descripción sincronizados bidireccionalmente mediante autocompletado
- Alternancia automática D/H al añadir nueva línea (si la última fue Debe, la siguiente es Haber)
- Foco automático en el campo Fecha al abrir el formulario
- Foco en el campo Cuenta de la nueva línea al añadir

#### Contabilidad
- **Plan de cuentas** — CRUD completo
- **Diario** — listado y edición de asientos con líneas Debe/Haber
- **Libro mayor** — filtro por cuenta y rango de fechas
- **Sumas y saldos** — con filtro por fechas y nivel de agrupación
- **Pérdidas y Ganancias** — cuentas 6xx/7xx; excluye asientos de regularización/cierre
- **Conciliación bancos vs. contabilidad** — detecta:
  - Movimientos sin asiento contable
  - Asientos con importe incorrecto
  - Asientos huérfanos (sin movimiento bancario)
  - Contrapartes de transferencias internas (por `dirsubcta` o por `bancot+numerot`)
  - Botones "Generar" y "Corregir" para regenerar asientos desde la UI
- Generación automática de asientos desde movimientos bancarios y facturas
- Endpoint `POST /api/contabilidad/generar-pendientes`

#### Usuarios NNA
- Registro de usuarios con datos personales y pagas

### Infraestructura

#### Script de arranque (`iniciar.sh`)
- Portátil: funciona aunque la carpeta se mueva de ubicación (`${BASH_SOURCE[0]}`)
- Detecta automáticamente Node.js v14 instalado via nvm (compatible con GLIBC 2.23)
- Libera los puertos 8000 y 5173 antes de arrancar (evita conflictos al relanzar)
- Arranca el backend (`uvicorn`) desde `backend/` para que `load_dotenv()` encuentre `.env`
- Arranca el frontend (Vite) y espera hasta que responda en `http://localhost:5173`
- Abre el navegador automáticamente (`xdg-open`)
- Limpia los procesos hijos al salir (`trap`)

#### Botón "Apagar"
- Variante `sidebar`: visible en el menú lateral
- Variante `selector`: visible en la pantalla de selección de empresa
- Flujo: idle → confirmación → apagando → mensaje de cierre
- Llama a `POST /api/shutdown` (el servidor se detiene con `SIGTERM` tras 300 ms)

#### Selección de empresa
- Pantalla de inicio (`/`) con tarjetas de empresa — reemplaza la navegación directa al dashboard
- Al seleccionar empresa, navega a `/inicio`
- El sidebar muestra el nombre de la empresa activa (sin desplegable); botón "← Cambiar empresa"
- Si no hay empresa activa, cualquier ruta redirige a `/`

#### Versionado
- Sistema de versiones `X.XX.XX` en `frontend/src/version.js` y `backend/app/main.py`
- Versión visible en la parte inferior del sidebar
- Endpoint `GET /api/version` expone la versión del backend

### Corrección de bugs

| # | Descripción | Ficheros afectados |
|---|-------------|-------------------|
| 1 | `_enrich_mov`: tipo `'E'` → `'F'` para facturas emitidas (lookup incorrecto) | `api/bancos.py` |
| 2 | Badges de vencimiento en movimientos: `vto_tipo === 'E'` → `'F'` | `MovimientosBancoPage.jsx` |
| 3 | `delete_extra` no eliminaba el `Vencimiento` asociado (tipo `'X'`) | `services/extras.py` |
| 4 | `update_factura_emi/rec`: al cambiar el total no se actualizaba el vencimiento ni se regeneraba el asiento | `services/facturas.py` |
| 5 | Extras de tipo Gasto aparecían como cobro en "Vtos. pendientes" de bancos: `VencimientoRead` no incluía `extra_tipo`; lógica de signo no distinguía gastos de ingresos | `schemas/bancos.py`, `api/bancos.py`, `MovimientosBancoPage.jsx` |
| 6 | `create_banco` inicializaba `saldoact = saldoini` en lugar de `0`, duplicando el saldo inicial en la cabecera | `services/bancos.py` |
| 7 | `delete_movimiento` actualizaba `saldoact` manualmente pero no llamaba `_recalcular_saldos`; los `saldonue` de movimientos posteriores quedaban desactualizados | `services/bancos.py` |
| 8 | `_recalcular_saldos` ordenaba por `numero` (inserción) en lugar de `(fecha, numero)` (orden de pantalla); los saldos por fila eran incorrectos cuando había movimientos backdateados | `services/bancos.py` |
| 9 | Conciliación bancos: condición `(total > 0)` y `(not p.dirsubcta)` excluían transferencias salientes y pagos con subcuenta | `services/contabilidad.py` |
| 10 | Asientos bancarios con `numero = movimiento - 1` (off-by-one) en CAJA, CAJA 3, B22, B25, B29 empresa 1 y 2; corregidos con `UPDATE` seguro excluyendo colisiones | BD (corrección SQL) |
| 11 | Generación de asientos: fallback añadido para pagos sin `dirsubcta` ni `bancot` → resuelve cuenta desde `vto → Vencimiento.cuentadef → FacturaRecibida.prcuenta → Proveedor.cuenta` | `services/contabilidad.py` |
| 12 | `iniciar.sh`: uvicorn arrancaba desde la raíz del proyecto; `load_dotenv()` no encontraba `backend/.env` y SQLite creaba la BD en ubicación incorrecta | `iniciar.sh`, `backend/.env` |
