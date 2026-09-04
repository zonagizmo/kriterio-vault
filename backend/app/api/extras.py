import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.db.database import get_db
from app.schemas.extras import ExtraRead, ExtraCreate, ExtraUpdate
from app.services import extras as svc


class RenumerarBody(BaseModel):
    empresa_id: int
    desde_id: Optional[int] = None

router = APIRouter(prefix="/api/extras", tags=["extras"])


@router.get("", response_model=dict)
def listar(
    empresa_id: int,
    tipo: Optional[str] = None,
    fecha_desde: Optional[datetime.date] = None,
    fecha_hasta: Optional[datetime.date] = None,
    estado: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    items, total = svc.get_extras(db, empresa_id, tipo, fecha_desde, fecha_hasta, estado, q, skip, limit)
    return {"total": total, "items": [ExtraRead.model_validate(i) for i in items]}


@router.get("/{extra_id}", response_model=ExtraRead)
def obtener(extra_id: int, db: Session = Depends(get_db)):
    e = svc.get_extra(db, extra_id)
    if not e:
        raise HTTPException(404, "Extra no encontrado")
    return e


@router.post("", response_model=ExtraRead, status_code=201)
def crear(data: ExtraCreate, db: Session = Depends(get_db)):
    return svc.create_extra(db, data)


@router.put("/{extra_id}", response_model=ExtraRead)
def actualizar(extra_id: int, data: ExtraUpdate, db: Session = Depends(get_db)):
    e = svc.update_extra(db, extra_id, data)
    if not e:
        raise HTTPException(404, "Extra no encontrado")
    return e


@router.post("/renumerar")
def renumerar(body: RenumerarBody, db: Session = Depends(get_db)):
    count = svc.renumerar_extras(db, body.empresa_id, body.desde_id)
    return {"renumeradas": count}


@router.delete("/{extra_id}", status_code=204)
def eliminar(extra_id: int, db: Session = Depends(get_db)):
    try:
        if not svc.delete_extra(db, extra_id):
            raise HTTPException(404, "Extra no encontrado")
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
