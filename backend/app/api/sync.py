import datetime
import hashlib

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.middleware.rate_limit import limiter
from app.models.sync import Instalacion
from app.schemas.sync import SyncPushItem, SyncPushResponse, SyncPushResult
from app.services.sync_replay import replay_operacion, ReplayError
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/sync", tags=["sync"])


def _hash_clave(clave: str) -> str:
    return hashlib.sha256(clave.encode()).hexdigest()


def verificar_instalacion(x_sync_key: str = Header(...), db: Session = Depends(get_db)) -> Instalacion:
    inst = db.query(Instalacion).filter(
        Instalacion.api_key_hash == _hash_clave(x_sync_key),
        Instalacion.activo == True,  # noqa: E712
    ).first()
    if not inst:
        raise HTTPException(401, "Instalación no autorizada")
    return inst


def _sync_key(request: Request):
    return request.headers.get("x-sync-key", "anonymous")


@router.post("/push", response_model=SyncPushResponse)
@limiter.limit("60/minute", key_func=_sync_key)
def push(request: Request, items: list[SyncPushItem], inst: Instalacion = Depends(verificar_instalacion),
        db: Session = Depends(get_db)):
    permitidas = {int(e) for e in inst.empresas.split(',')} if inst.empresas else None
    resultados = []
    for item in items:
        if permitidas is not None and item.empresa_id not in permitidas:
            resultados.append(SyncPushResult(ok=False, error="Empresa no autorizada para esta instalación"))
            continue
        try:
            replay_operacion(db, item.tabla, item.entidad_uuid, item.operacion,
                             item.empresa_id, item.payload)
            resultados.append(SyncPushResult(ok=True))
        except (ReplayError, ValueError) as e:
            db.rollback()
            resultados.append(SyncPushResult(ok=False, error=str(e)))
        except Exception as e:
            db.rollback()
            resultados.append(SyncPushResult(ok=False, error=f"Error inesperado: {e}"))

    inst.ultima_sincronizacion = datetime.datetime.utcnow()
    db.commit()
    return SyncPushResponse(resultados=resultados)


@router.post("/ejecutar")
def ejecutar(db: Session = Depends(get_db),
             _user=Depends(get_current_user)):
    """Disparo manual desde la propia instalación.
    Requiere autenticación JWT."""
    from app.services.sync_push import sincronizar_con_servidor
    return sincronizar_con_servidor(db)
