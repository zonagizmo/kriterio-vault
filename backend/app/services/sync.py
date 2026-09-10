"""Identidad de instalación y registro de operaciones para la futura
sincronización con el servidor central. Ver docs/sincronizacion.md."""
import json
import uuid
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.sync import SyncLog

INSTALACION_PATH = Path("./instalacion.json")

_instalacion_id_cache = None


def obtener_instalacion_id() -> str:
    """UUID propio de esta instalación, generado una sola vez y persistido en
    disco (no depende del hardware, igual de espíritu que backup_config.json)."""
    global _instalacion_id_cache
    if _instalacion_id_cache:
        return _instalacion_id_cache
    if INSTALACION_PATH.exists():
        _instalacion_id_cache = json.loads(INSTALACION_PATH.read_text())["instalacion_id"]
    else:
        _instalacion_id_cache = str(uuid.uuid4())
        INSTALACION_PATH.write_text(json.dumps({"instalacion_id": _instalacion_id_cache}))
    return _instalacion_id_cache


def registrar_operacion(db: Session, empresa_id: int, tabla: str, entidad_uuid: str,
                        operacion: str, payload: dict = None):
    """Añade una entrada al log de operaciones dentro de la misma transacción
    que el cambio de negocio (se hace `db.add`, no `db.commit`: lo confirma
    el commit de la operación que la originó)."""
    db.add(SyncLog(
        empresa_id=empresa_id,
        tabla=tabla,
        entidad_uuid=entidad_uuid,
        operacion=operacion,
        payload=json.dumps(payload) if payload is not None else None,
        origen_instalacion=obtener_instalacion_id(),
    ))
