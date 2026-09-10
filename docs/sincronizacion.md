# Sincronización con servidor central — arquitectura

Objetivo: la app sigue funcionando 100% local (SQLite, sin conexión permanente
requerida), pero puede sincronizar sus datos con un servidor central para
trabajar desde varios PCs/ubicaciones con los mismos datos.

## Hechos de partida (auditados contra el código en 2026-09-04)

- La clave real de relación entre tablas **no es `id`, es `numero`**
  (`MAX(numero)+1` por empresa, `documentos.py:siguiente_numero`), sin
  unicidad compuesta declarada. Es el obstáculo principal para sincronizar:
  dos instalaciones offline pueden generar el mismo `numero` de forma
  independiente.
  - Para **facturas recibidas**, `numero` es solo referencia interna; el
    número con validez legal es `prfactura` (el del proveedor). Colisión =
    problema técnico, no legal.
  - Para **facturas emitidas**, `numero`/`cnumero` sí tiene relevancia legal
    (numeración correlativa sin huecos). Baja actividad actual (1 fila), pero
    hay que diseñarlo bien.
- Cero columnas de auditoría (`created_at`/`updated_at`/`version`) en el
  esquema original.
- Borrado 100% físico (`db.delete()`), sin tombstones.
- Una sola alta de factura toca 6 tablas en un commit (cabecera, apuntes,
  vencimientos, diario, cuentas, lectura proveedor), parte con SQL crudo a
  propósito (evita el FK-sort-error de SQLAlchemy). Descarta sincronizar
  fila a fila.
- Sin autenticación/autorización en la API (ningún endpoint protegido).
- Multi-empresa ya soportado vía `empresa_id` (única FK real declarada).
- `DATABASE_URL` en `database.py` ya soporta Postgres sin tocar código
  (`docker-compose.yml`/`.env.example` ya preparados, sin usar hoy).
- Volumen de datos pequeño: ~5,3 MB, tabla mayor (`diario`) 16k filas. No es
  "big data" — no hace falta CDC fila a fila ni particionado.

## Decisión de arquitectura

**Sincronizar operaciones de negocio, no filas.** Cada instalación mantiene
un log de operaciones (`sync_log`): "creé factura X", "edité factura Y"...
con los mismos datos que recibió el endpoint. El servidor (y las demás
instalaciones) replican reproduciendo esa operación con la misma función de
servicio (`create_factura_rec`, etc.), no copiando filas — así los efectos
derivados (asientos, vencimientos, IVA) se generan con la lógica ya validada.

**`numero`**: reserva online cuando hay conexión (pedir al servidor "el
siguiente número" antes de crear); si se crea offline, `numero` provisional +
remapeo tras sincronizar, reutilizando la función `renumerar_facturas_*` que
ya existe en la app para corregir huecos.

**Conflictos**: nunca fusión automática de datos contables. Cada fila
sincronizable lleva un `version` (ver más abajo); si el servidor tiene una
versión más nueva que la que el cliente editó, se rechaza como conflicto y se
muestra al usuario (quedarme con la mía / con la del servidor / duplicar como
documento nuevo). Last-writer-wins solo para catálogos poco críticos
(clientes, proveedores, artículos).

**Servidor = misma app**, desplegada apuntando a Postgres (`DATABASE_URL`) en
vez de SQLite, con endpoints nuevos de sincronización y registro de
instalaciones añadidos encima. Los PCs locales siguen en SQLite sin cambios
de comportamiento.

### Infraestructura decidida
- Servidor propio (Debian, acceso SSH, sistema "pelado"), accesible desde
  fuera de la red — no VPS nuevo, no PaaS.
- Dominio propio disponible → TLS vía Let's Encrypt (Caddy como proxy
  inverso, gestiona el certificado solo).
- Alcance de autenticación (decidido): **solo se protege el canal de
  sincronización** servidor↔instalaciones. La app local no lleva login
  propio por ahora (queda como está, se asume red de confianza en cada PC).
- Postgres solo en `localhost` del servidor, nunca expuesto directamente;
  firewall (`ufw`) cerrado salvo 22/80/443.

## Fases

1. **Base (COMPLETA, 2026-09-04)** — columnas de sincronización y log de
   operaciones en el backend actual, sin sincronizar nada todavía.
2. **Servidor como copia de respaldo centralizada (CÓDIGO Y VERIFICACIÓN
   COMPLETOS, 2026-09-07 — despliegue real pendiente)** — servidor sobre
   Postgres, las instalaciones empujan su log de operaciones (solo subida).
3. **Descarga** — alta de instalación nueva / recuperación trayéndose los
   datos del servidor.
4. **Sincronización bidireccional completa** con la resolución de conflictos
   descrita arriba.
5. **Endurecido** — TLS, autenticación fina, bloqueos suaves en edición
   concurrente.

## Estado de la fase 1 — COMPLETA

Implementado en los **15 agregados raíz** de la aplicación: `FacturaEmitida`,
`FacturaRecibida`, `Cliente`, `Proveedor`, `Vencimiento`, `Banco`, `MovBanco`,
`Familia`, `Articulo`, `AlbaranEmitido`, `AlbaranRecibido`, `Cuenta`, `Extra`,
`UsuarioNNA`, `PagaNNA`. Verificado end-to-end (alta/edición/baja) en 7 de
ellos, incluidos los dos casos más delicados: movimientos bancarios (pagos y
contrapartes de transferencia no generan entradas propias en `sync_log`, solo
la operación pública que las origina) y las altas por SQL crudo de
`usuarios_nna`/`pagas_nna` (el `uuid` se genera a mano en Python antes del
INSERT, ya que el default de `SyncMixin` solo se dispara al instanciar el
modelo por SQLAlchemy).

**Deliberadamente fuera de alcance** (líneas/derivados de un documento padre,
se recrean solo al reproducir la operación del padre): `Apunte`, `ExApunte`,
`Diario`, `DiarioTxt`, `Eriva`, `Pago`. Y tablas sin alta/edición propia hoy
(0 filas, sin servicio CRUD): `Presupuesto`, `PedidoProveedor`,
`PedidoCliente`, `AlbaranInventario`, `AlbaranReparto`, `FamiliaC`,
`ArticuloC`, `Recibo`, `EtiCod`, `EtiDat`.

- `app/models/sync_mixin.py` — `SyncMixin`: columnas `uuid` (identidad
  estable entre instalaciones, no depende de `numero`), `version` (detección
  de conflictos), `created_at`/`updated_at`. `version` se incrementa a mano
  en los servicios de edición, no vía evento ORM genérico — una sola
  operación de alta puede generar más de un `UPDATE` interno (p. ej. fijar el
  `total` tras guardar las líneas) y un incremento automático por cada
  `UPDATE` confundiría eso con una edición real.
- `app/models/sync.py` — tabla `sync_log`: `empresa_id`, `tabla`,
  `entidad_uuid`, `operacion` (C/U/D), `payload` (JSON con los mismos datos
  del endpoint), `origen_instalacion`, `creado_en`, `sincronizado`. Aún no la
  consume nada (no hay servidor todavía) — solo se está registrando.
- `app/services/sync.py` — `obtener_instalacion_id()`: UUID propio de la
  instalación, generado una vez y persistido en `backend/instalacion.json`
  (no depende del hardware, mismo espíritu que `backup_config.json`).
  `registrar_operacion()`: añade la entrada a `sync_log` dentro de la misma
  transacción que el cambio de negocio.
- Migración automática en `main.py:_migraciones()` (mismo patrón que las
  migraciones existentes de la app), generalizada a las 15 tablas vía el
  diccionario `TABLAS_SYNC` (tabla → columna de fecha de negocio a usar para
  aproximar `created_at`/`updated_at` en filas ya existentes, o `None` si no
  hay ninguna y se usa el momento de la migración). Añade las columnas si
  faltan, rellena `uuid` único por fila y crea el índice único. Verificado
  contra la base de datos real: 17.766 filas migradas en total entre las 15
  tablas, 0 sin uuid, 0 duplicados en ninguna.

## Estado de la fase 2 — código y verificación completos, despliegue real pendiente

Implementado (2026-09-07):
- `app/models/sync.py` — `Instalacion`: registro/emparejamiento, `api_key_hash`
  (nunca se guarda la clave en claro), `empresas` (CSV de `empresa_id`
  permitidos, o todas si está vacío).
- `app/services/sync_replay.py` — `SYNC_REGISTRO`: mapa tabla → (modelo,
  esquemas, funciones crear/editar/borrar) para las 15 tablas sincronizables.
  `replay_operacion()` es idempotente: un 'C' repetido no duplica (comprueba
  por `uuid` antes de crear), un 'U'/'D' sobre algo que no existe se trata
  como ya aplicado, no como error. Tras crear, corrige el `uuid` generado por
  la función de servicio al `entidad_uuid` original de la instalación de
  origen (si no, cada instalación tendría una identidad distinta para la
  misma fila). En 'C'/'U' fuerza `forzar=True` cuando el esquema lo admite
  (facturas recibidas): la validación de duplicados ya se hizo, o se
  confirmó, en la instalación de origen — no tiene sentido repetirla al
  reproducir la operación.
- `app/api/sync.py` — `POST /api/sync/push` (autenticado por cabecera
  `X-Sync-Key`, hash SHA-256 contra `Instalacion.api_key_hash`; rechaza
  empresas no autorizadas para esa instalación) y `POST /api/sync/ejecutar`
  (disparo manual local, sin autenticar — igual que el resto de la API local
  hoy).
- `app/services/sync_push.py` — lado cliente: lee `sync_log` pendiente,
  lo empuja a `SYNC_SERVER_URL`, marca `sincronizado` solo lo confirmado.
  Sin `SYNC_SERVER_URL`/`SYNC_API_KEY` configurados, no hace nada. Enganchado
  al scheduler ya existente de `ajustes.py` (cada 15 min).
- `backend/scripts/crear_instalacion.py` — alta de instalaciones a mano en
  el servidor (por SSH, no por HTTP: no hay admin autenticado que pueda
  hacerlo de otra forma). Muestra la clave de API una sola vez.
- `deploy/` — script de aprovisionamiento Debian (Postgres, Caddy con TLS,
  systemd, ufw), idempotente, más `actualizar.sh` e instrucciones completas
  en `deploy/README.md`. Dominio decidido: `kriteriovault.naslive.es`.

**Verificado extremo a extremo** con dos SQLite independientes simulando
cliente y servidor reales (no contra el servidor real todavía): alta,
edición y baja de un cliente propagadas correctamente; reintento del mismo
alta sin duplicar (idempotencia); clave de API inválida rechazada (401);
empresa no autorizada para la instalación rechazada explícitamente; y una
factura recibida completa (cabecera + líneas + vencimiento) reconstruida en
destino con los mismos datos.

**Pendiente**: ejecutar `deploy/aprovisionar_servidor.sh` en el servidor Debian
real (requiere que el usuario cree antes el registro DNS y añada la deploy
key en GitHub — pasos que no puedo hacer yo). Después de eso, fase 3
(descarga / alta de instalación nueva) y fase 4 (bidireccional con
resolución de conflictos y reserva de `numero` online) siguen pendientes tal
como se describieron al cerrar la fase 1.

## Camino de despliegue alternativo: paquete YunoHost

Además de `deploy/` (Debian a pelo), existe un paquete YunoHost —
`kriterio-vault_ynh`, repositorio aparte (convención `<app>_ynh`, obligada
porque `yunohost app install` espera `manifest.toml` en la raíz del repo) —
para instalar el mismo servidor central en cualquier instancia YunoHost.
Son dos caminos alternativos para instancias distintas, no un reemplazo el
uno del otro; comparten el mismo código de aplicación.

Diferencia principal: la instancia YunoHost queda protegida por su SSO
(usuarios del propio YunoHost, permiso `all_users`) — la única capa de
autenticación delante de la API de sincronización en cualquiera de los dos
caminos, ya que la app no tiene login propio (decisión tomada al diseñar
esto). En `deploy/` (Debian) no hay ninguna capa así: solo la clave de API
entre instalaciones.

Repo del paquete: (pendiente de crear en GitHub, ver su propio README para
los pasos exactos — entre ellos, hacer público el repo principal
`kriterio-vault` para que YunoHost pueda descargar el código). Escrito pero
**sin probar contra una instancia YunoHost real**.
