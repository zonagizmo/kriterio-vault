import json
import re
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/ajustes", tags=["ajustes"])

DB_PATH    = Path("./gestionmgd.db")
BACKUP_DIR = Path("./backups")
CONFIG_PATH = Path("./backup_config.json")
RETENTION_DAYS = 30

_FILENAME_RE = re.compile(r'^gestionmgd_[\w-]+\.db$')
_HORA_RE     = re.compile(r'^\d{2}:\d{2}$')

_scheduler = BackgroundScheduler(timezone="Europe/Madrid")


def leer_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            hora = data.get("hora", "02:00")
            dias = data.get("dias", list(range(7)))
            if _HORA_RE.match(hora) and dias and all(0 <= d <= 6 for d in dias):
                return {"hora": hora, "dias": sorted(dias)}
        except Exception:
            pass
    return {"hora": "02:00", "dias": list(range(7))}


def _guardar_config(hora: str, dias: list):
    CONFIG_PATH.write_text(json.dumps({"hora": hora, "dias": sorted(dias)}, ensure_ascii=False))


def _reprogramar_job(hora: str, dias: list):
    h, m = map(int, hora.split(":"))
    dias_str = ",".join(str(d) for d in sorted(dias))
    _scheduler.reschedule_job("backup_auto", trigger="cron", hour=h, minute=m, day_of_week=dias_str)


def iniciar_scheduler():
    cfg = leer_config()
    h, m = map(int, cfg["hora"].split(":"))
    dias_str = ",".join(str(d) for d in cfg["dias"])
    _scheduler.add_job(hacer_backup, "cron", hour=h, minute=m, day_of_week=dias_str, id="backup_auto")
    _scheduler.start()


def detener_scheduler():
    _scheduler.shutdown(wait=False)


def hacer_backup() -> Path:
    BACKUP_DIR.mkdir(exist_ok=True)
    ts   = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dest = BACKUP_DIR / f"gestionmgd_{ts}.db"

    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dest)
    src.backup(dst)
    dst.close()
    src.close()

    _limpiar_antiguos()
    return dest


def _limpiar_antiguos():
    limite = datetime.now() - timedelta(days=RETENTION_DAYS)
    for f in BACKUP_DIR.glob("gestionmgd_*.db"):
        try:
            # Primeros 16 chars: YYYY-MM-DD_HH-MM — cubre también los safety
            # backups 'gestionmgd_<ts>_antes_restauracion.db', que el parseo
            # completo rechazaba y quedaban sin limpiar para siempre
            resto = f.stem.replace("gestionmgd_", "")
            ts = datetime.strptime(resto[:16], "%Y-%m-%d_%H-%M")
            if ts < limite:
                f.unlink()
        except (ValueError, IndexError, OSError):
            pass


def _info_backup(f: Path) -> dict:
    fecha_str = None
    resto = f.stem.replace("gestionmgd_", "")
    # Extraer los primeros 16 chars: YYYY-MM-DD_HH-MM
    try:
        fecha_str = datetime.strptime(resto[:16], "%Y-%m-%d_%H-%M").strftime("%Y-%m-%dT%H:%M")
    except (ValueError, IndexError):
        pass
    return {
        "nombre":  f.name,
        "fecha":   fecha_str,
        "tamanio": f.stat().st_size,
    }


class ConfigBackup(BaseModel):
    hora: str
    dias: list[int]


@router.get("/backups")
def listar_backups():
    cfg = leer_config()
    if not BACKUP_DIR.exists():
        return {"backups": [], **cfg, "retencion_dias": RETENTION_DAYS}
    archivos = sorted(BACKUP_DIR.glob("gestionmgd_*.db"), reverse=True)
    return {
        "backups": [_info_backup(f) for f in archivos],
        **cfg,
        "retencion_dias": RETENTION_DAYS,
    }


@router.put("/config")
def actualizar_config(body: ConfigBackup):
    if not _HORA_RE.match(body.hora):
        raise HTTPException(status_code=400, detail="Formato de hora inválido (esperado HH:MM)")
    if not body.dias or not all(0 <= d <= 6 for d in body.dias):
        raise HTTPException(status_code=400, detail="Días inválidos (0=Lun … 6=Dom)")
    _guardar_config(body.hora, body.dias)
    _reprogramar_job(body.hora, body.dias)
    return {"ok": True, "hora": body.hora, "dias": sorted(body.dias)}


@router.post("/backup")
def backup_manual():
    if not DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Base de datos no encontrada")
    dest = hacer_backup()
    return {"ok": True, "backup": _info_backup(dest)}


@router.get("/backup/download/{nombre}")
def descargar_backup(nombre: str):
    if not _FILENAME_RE.match(nombre):
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")
    path = BACKUP_DIR / nombre
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backup no encontrado")
    return FileResponse(path, media_type="application/octet-stream", filename=nombre)


@router.delete("/backup/{nombre}")
def eliminar_backup(nombre: str):
    if not _FILENAME_RE.match(nombre):
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")
    path = BACKUP_DIR / nombre
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backup no encontrado")
    path.unlink()
    return {"ok": True}


_SQLITE_MAGIC = b"SQLite format 3\x00"


def _restaurar_desde_path(origen: Path) -> str:
    """Valida y restaura la BD desde una ruta de archivo. Devuelve el nombre del safety backup."""
    contenido = origen.read_bytes()
    if not contenido.startswith(_SQLITE_MAGIC):
        raise HTTPException(status_code=400, detail="El archivo no es una base de datos SQLite válida")

    try:
        conn = sqlite3.connect(origen)
        conn.execute("SELECT name FROM sqlite_master LIMIT 1")
        conn.close()
    except sqlite3.DatabaseError:
        raise HTTPException(status_code=400, detail="El archivo está corrupto o no es una BD válida")

    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    safety = BACKUP_DIR / f"gestionmgd_{ts}_antes_restauracion.db"
    if DB_PATH.exists():
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(safety)
        src.backup(dst)
        dst.close()
        src.close()

    from app.db.database import engine
    engine.dispose()

    dst_conn = sqlite3.connect(DB_PATH)
    src_conn = sqlite3.connect(origen)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()

    return safety.name


@router.post("/restaurar")
async def restaurar_backup(archivo: UploadFile = File(...)):
    if not archivo.filename.lower().endswith(".db"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .db")

    contenido = await archivo.read()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp_path.write_bytes(contenido)

    try:
        safety_name = _restaurar_desde_path(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"ok": True, "safety_backup": safety_name}


@router.post("/restaurar-backup/{nombre}")
def restaurar_backup_existente(nombre: str):
    if not _FILENAME_RE.match(nombre):
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido")
    path = BACKUP_DIR / nombre
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backup no encontrado")
    safety_name = _restaurar_desde_path(path)
    return {"ok": True, "safety_backup": safety_name}
