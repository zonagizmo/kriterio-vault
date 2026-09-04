from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.schemas.facturacion import (
    AlbaranEmiRead, AlbaranEmiCreate, AlbaranEmiUpdate,
    AlbaranRecRead, AlbaranRecCreate, AlbaranRecUpdate,
)
from app.services import albaranes as svc

router = APIRouter(prefix="/api/albaranes", tags=["albaranes"])


# ─── Emitidos ─────────────────────────────────────────────────────────────────

@router.get("/emitidos", response_model=dict)
def listar_emi(
    empresa_id: int, q: str = Query(""),
    cliente: Optional[int] = None, skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
):
    items, total = svc.get_albaranes_emi(db, empresa_id, q, cliente, skip, limit)
    return {"total": total, "items": [AlbaranEmiRead.model_validate(i) for i in items]}


@router.get("/emitidos/{albaran_id}", response_model=AlbaranEmiRead)
def obtener_emi(albaran_id: int, db: Session = Depends(get_db)):
    alb = svc.get_albaran_emi(db, albaran_id)
    if not alb:
        raise HTTPException(404, "Albarán no encontrado")
    return alb


@router.post("/emitidos", response_model=AlbaranEmiRead, status_code=201)
def crear_emi(data: AlbaranEmiCreate, db: Session = Depends(get_db)):
    return svc.create_albaran_emi(db, data)


@router.put("/emitidos/{albaran_id}", response_model=AlbaranEmiRead)
def actualizar_emi(albaran_id: int, data: AlbaranEmiUpdate, db: Session = Depends(get_db)):
    alb = svc.update_albaran_emi(db, albaran_id, data)
    if not alb:
        raise HTTPException(404, "Albarán no encontrado")
    return alb


@router.delete("/emitidos/{albaran_id}", status_code=204)
def eliminar_emi(albaran_id: int, db: Session = Depends(get_db)):
    if not svc.delete_albaran_emi(db, albaran_id):
        raise HTTPException(404, "Albarán no encontrado")


# ─── Recibidos ────────────────────────────────────────────────────────────────

@router.get("/recibidos", response_model=dict)
def listar_rec(
    empresa_id: int, q: str = Query(""),
    proveedor: Optional[int] = None, skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
):
    items, total = svc.get_albaranes_rec(db, empresa_id, q, proveedor, skip, limit)
    return {"total": total, "items": [AlbaranRecRead.model_validate(i) for i in items]}


@router.get("/recibidos/{albaran_id}", response_model=AlbaranRecRead)
def obtener_rec(albaran_id: int, db: Session = Depends(get_db)):
    alb = svc.get_albaran_rec(db, albaran_id)
    if not alb:
        raise HTTPException(404, "Albarán no encontrado")
    return alb


@router.post("/recibidos", response_model=AlbaranRecRead, status_code=201)
def crear_rec(data: AlbaranRecCreate, db: Session = Depends(get_db)):
    return svc.create_albaran_rec(db, data)


@router.put("/recibidos/{albaran_id}", response_model=AlbaranRecRead)
def actualizar_rec(albaran_id: int, data: AlbaranRecUpdate, db: Session = Depends(get_db)):
    alb = svc.update_albaran_rec(db, albaran_id, data)
    if not alb:
        raise HTTPException(404, "Albarán no encontrado")
    return alb


@router.delete("/recibidos/{albaran_id}", status_code=204)
def eliminar_rec(albaran_id: int, db: Session = Depends(get_db)):
    if not svc.delete_albaran_rec(db, albaran_id):
        raise HTTPException(404, "Albarán no encontrado")
