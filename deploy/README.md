# Despliegue del servidor central — fase 2

Servidor: Debian propio, acceso SSH, dominio `kriteriovault.naslive.es`.
Ver `docs/sincronizacion.md` para la arquitectura completa.

## 1. Antes de ejecutar nada

Crea el registro DNS de tipo A: `kriteriovault.naslive.es` → IP pública de
este servidor, en el panel de tu proveedor de dominio. Sin esto Caddy no
podrá emitir el certificado TLS (Let's Encrypt valida por dominio, no por IP).

## 2. Copiar y ejecutar el script

Copia esta carpeta `deploy/` al servidor (o clona el repo temporalmente para
sacarla — el script luego clona su propia copia en `/opt/kriterio-vault`),
y ejecútalo como root:

```bash
sudo bash aprovisionar_servidor.sh
```

Es idempotente: puedes volver a ejecutarlo si algo falla a mitad, no
duplica usuarios, bases de datos ni claves ya creadas.

**A mitad de ejecución te pedirá algo manual**: generará una clave SSH y
te pedirá añadirla como *Deploy key* de **solo lectura** en
`https://github.com/zonagizmo/kriterio-vault/settings/keys` → *Add deploy
key* (pega la clave, NO marques "Allow write access"). Pulsa Enter en la
terminal cuando la hayas añadido para que continúe.

Qué hace el script (ver comentarios dentro para el detalle):
- Instala PostgreSQL (solo en `localhost`, nunca expuesto), Python, Caddy, ufw, fail2ban.
- Crea un usuario de sistema `kriterio` (la app no corre como root).
- Crea la base de datos y credenciales en Postgres (contraseña aleatoria, guardada en `/root/.kriterio-vault-secrets`).
- Clona el repo en `/opt/kriterio-vault` y prepara el entorno Python.
- Genera `backend/.env` con `DATABASE_URL` apuntando a ese Postgres.
- Instala el servicio `systemd` (`kriterio-vault`, arranque automático, un solo proceso — ver nota abajo).
- Configura Caddy como proxy inverso con TLS automático para el dominio.
- Cierra el firewall (`ufw`) a todo excepto 22/80/443.

## 3. Comprobar que funciona

```bash
curl -s https://kriteriovault.naslive.es/api/version
```

Debería devolver `{"version": "..."}`. La primera vez puede tardar unos
segundos mientras Caddy obtiene el certificado.

## 4. Dar de alta la primera instalación cliente

En el propio servidor:

```bash
sudo -u kriterio /opt/kriterio-vault/backend/venv/bin/python \
    /opt/kriterio-vault/backend/scripts/crear_instalacion.py \
    --nombre "PC Oficina" --empresas 1,2
```

(`--empresas` es opcional; si se omite, esa instalación puede sincronizar
cualquier empresa). El script imprime una clave de API **una sola vez** —
cópiala.

## 5. Configurar la instalación cliente (el PC local)

En `backend/.env` del PC que va a sincronizar (créalo si no existe, a partir
de `.env.example`):

```
SYNC_SERVER_URL=https://kriteriovault.naslive.es
SYNC_API_KEY=<la clave que imprimió el paso anterior>
```

Reinicia el backend local. A partir de ahí, cada 15 minutos (y también al
llamar manualmente a `POST /api/sync/ejecutar`) empujará las operaciones
pendientes de `sync_log` al servidor. Si no hay conexión, simplemente lo
reintenta en el siguiente ciclo — no bloquea el uso normal de la app.

## 6. Actualizar el servidor más adelante

```bash
sudo bash actualizar.sh
```

Hace `git pull` + reinstala dependencias + reinicia el servicio.

## Notas importantes

- **Un solo proceso** (`uvicorn` sin `--workers`): el backup automático y el
  push de sincronización usan un scheduler en memoria (APScheduler); con
  varios workers cada uno lanzaría el suyo y se duplicarían backups y envíos.
- **Alcance de esta fase**: solo sincronización de subida (cada instalación
  empuja su log; el servidor lo aplica). Las instalaciones aún no descargan
  cambios de otras instalaciones ni hay resolución de conflictos — eso es la
  fase 3/4 (ver `docs/sincronizacion.md`).
- **Autenticación**: solo se protege el canal de sincronización (la API key
  por instalación). La API local de cada PC sigue sin login, tal como se
  decidió explícitamente al diseñar esto — no es un descuido.
- El servidor no sirve el frontend (solo la API): esta fase es
  deliberadamente mínima, un backend + Postgres como copia central. Si más
  adelante quieres navegar los datos centrales desde un navegador, habría
  que desplegar también el frontend ahí.
