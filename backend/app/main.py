import asyncio
import datetime
import os
import signal
import uuid as uuid_lib
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import crear_tablas, engine
from app.api import empresas, clientes, proveedores, familias, articulos, albaranes, facturas, bancos, contabilidad, usuarios, extras, sync
from app.api.dashboard import router as dashboard_router
from app.api.estadisticas import router as estadisticas_router
from app.api.ajustes import router as ajustes_router, iniciar_scheduler, detener_scheduler
import app.models.usuarios  # registra tablas usuarios_nna y pagas_nna
import app.models.sync  # registra tabla sync_log

VERSION = "1.10.00"


def _migraciones():
    """Migraciones SQL para columnas añadidas tras la creación inicial."""
    raw = engine.raw_connection()
    cur = raw.cursor()
    cols_mov = {r[1] for r in cur.execute("PRAGMA table_info(mov_bancos)")}
    if "conciliado" not in cols_mov:
        cur.execute("ALTER TABLE mov_bancos ADD COLUMN conciliado INTEGER DEFAULT 0")
    # La columna almacena la paga MENSUAL desde el principio; el nombre era un resto histórico
    cols_nna = {r[1] for r in cur.execute("PRAGMA table_info(usuarios_nna)")}
    if "paga_semanal" in cols_nna and "paga_mensual" not in cols_nna:
        cur.execute("ALTER TABLE usuarios_nna RENAME COLUMN paga_semanal TO paga_mensual")
    cols_empresas = {r[1] for r in cur.execute("PRAGMA table_info(empresas)")}
    for col in ("nif", "domicilio", "localidad", "provincia", "cod_postal", "telefono", "email"):
        if col not in cols_empresas:
            cur.execute(f"ALTER TABLE empresas ADD COLUMN {col} TEXT")

    # Columnas de sincronización (fase 1: uuid/version/timestamps) en los 15
    # agregados raíz sincronizables. El valor indica la columna de fecha de
    # negocio a usar para aproximar created_at/updated_at en filas ya
    # existentes (None = no hay, se usa el momento de esta migración).
    TABLAS_SYNC = {
        "facturas_emitidas": "fecha", "facturas_recibidas": "fecha",
        "clientes": None, "proveedores": None,
        "vencimientos": "fecha", "bancos": None, "mov_bancos": "fecha",
        "familias": None, "articulos": None,
        "albaranes_emitidos": "fecha", "albaranes_recibidos": "fecha",
        "cuentas": None, "extras": "fecha",
        "usuarios_nna": None, "pagas_nna": "fecha",
    }
    ahora_txt = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for tabla, fecha_col in TABLAS_SYNC.items():
        cols = {r[1] for r in cur.execute(f"PRAGMA table_info({tabla})")}
        if "uuid" not in cols:
            cur.execute(f"ALTER TABLE {tabla} ADD COLUMN uuid TEXT")
        if "version" not in cols:
            cur.execute(f"ALTER TABLE {tabla} ADD COLUMN version INTEGER DEFAULT 1")
        if "created_at" not in cols:
            cur.execute(f"ALTER TABLE {tabla} ADD COLUMN created_at TEXT")
        if "updated_at" not in cols:
            cur.execute(f"ALTER TABLE {tabla} ADD COLUMN updated_at TEXT")
        # Rellenar filas ya existentes: uuid propio por fila, timestamp aproximado
        # a partir de la fecha de negocio si existe (si no, el momento de la migración).
        campo_sel = fecha_col or "NULL"
        for (row_id, fecha) in cur.execute(f"SELECT id, {campo_sel} FROM {tabla} WHERE uuid IS NULL").fetchall():
            ts = f"{fecha} 00:00:00" if fecha else ahora_txt
            cur.execute(
                f"UPDATE {tabla} SET uuid = ?, version = 1, created_at = ?, updated_at = ? WHERE id = ?",
                (str(uuid_lib.uuid4()), ts, ts, row_id),
            )
        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{tabla}_uuid ON {tabla}(uuid)")

    raw.commit()
    raw.close()

app = FastAPI(
    title="Kriterio Vault",
    description="ERP de gestión empresarial",
    version=VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    crear_tablas()
    _migraciones()
    iniciar_scheduler()


@app.on_event("shutdown")
def shutdown():
    detener_scheduler()


app.include_router(empresas.router)
app.include_router(clientes.router)
app.include_router(proveedores.router)
app.include_router(familias.router)
app.include_router(articulos.router)
app.include_router(albaranes.router)
app.include_router(facturas.router)
app.include_router(bancos.router)
app.include_router(contabilidad.router)
app.include_router(extras.router)
app.include_router(usuarios.router)
app.include_router(sync.router)
app.include_router(ajustes_router)
app.include_router(dashboard_router)
app.include_router(estadisticas_router)


@app.get("/")
def raiz():
    return {"estado": "ok", "app": "Kriterio Vault", "version": VERSION}


@app.get("/api/version")
def version():
    return {"version": VERSION}


async def _apagar():
    await asyncio.sleep(0.3)
    os.kill(os.getpid(), signal.SIGTERM)


@app.post("/api/shutdown")
async def shutdown(background_tasks: BackgroundTasks):
    background_tasks.add_task(_apagar)
    return {"ok": True}
