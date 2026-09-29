from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.auth import get_current_user
from app.services.permissions import require_method_permission, empresa_query, exigir_empresa
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.schemas.facturacion import (
    AlbaranEmiRead, AlbaranEmiCreate, AlbaranEmiUpdate,
    AlbaranRecRead, AlbaranRecCreate, AlbaranRecUpdate,
)
from app.services import albaranes as svc
from app.services.integridad import ReferenciaInvalida
router = APIRouter(prefix="/api/albaranes", tags=["albaranes"], dependencies=[Depends(require_method_permission)])


# ─── Emitidos ─────────────────────────────────────────────────────────────────

@router.get("/emitidos", response_model=dict)
def listar_emi(
    empresa_id: int = Depends(empresa_query), q: str = Query(""),
    cliente: Optional[int] = None, skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
):
    items, total = svc.get_albaranes_emi(db, empresa_id, q, cliente, skip, limit)
    return {"total": total, "items": [AlbaranEmiRead.model_validate(i) for i in items]}


@router.get("/emitidos/{albaran_id}", response_model=AlbaranEmiRead)
def obtener_emi(albaran_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    alb = svc.get_albaran_emi(db, albaran_id)
    if not alb:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(user, alb)
    return alb


@router.post("/emitidos", response_model=AlbaranEmiRead, status_code=201)
def crear_emi(data: AlbaranEmiCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    exigir_empresa(user, data)
    try:
        return svc.create_albaran_emi(db, data)
    except ReferenciaInvalida as e:
        raise HTTPException(404, str(e))


@router.put("/emitidos/{albaran_id}", response_model=AlbaranEmiRead)
def actualizar_emi(albaran_id: int, data: AlbaranEmiUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    previo = svc.get_albaran_emi(db, albaran_id)
    if not previo:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(user, previo)
    exigir_empresa(user, data)
    try:
        alb = svc.update_albaran_emi(db, albaran_id, data)
    except ReferenciaInvalida as e:
        raise HTTPException(404, str(e))
    if not alb:
        raise HTTPException(404, "Recurso no encontrado")
    return alb


@router.delete("/emitidos/{albaran_id}", status_code=204)
def eliminar_emi(albaran_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    previo = svc.get_albaran_emi(db, albaran_id)
    if not previo:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(user, previo)
    if not svc.delete_albaran_emi(db, albaran_id):
        raise HTTPException(404, "Recurso no encontrado")


# ─── Recibidos ────────────────────────────────────────────────────────────────

@router.get("/recibidos", response_model=dict)
def listar_rec(
    empresa_id: int = Depends(empresa_query), q: str = Query(""),
    proveedor: Optional[int] = None, skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
):
    items, total = svc.get_albaranes_rec(db, empresa_id, q, proveedor, skip, limit)
    return {"total": total, "items": [AlbaranRecRead.model_validate(i) for i in items]}


@router.get("/recibidos/{albaran_id}", response_model=AlbaranRecRead)
def obtener_rec(albaran_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    alb = svc.get_albaran_rec(db, albaran_id)
    if not alb:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(user, alb)
    return alb


@router.post("/recibidos", response_model=AlbaranRecRead, status_code=201)
def crear_rec(data: AlbaranRecCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    exigir_empresa(user, data)
    try:
        return svc.create_albaran_rec(db, data)
    except ReferenciaInvalida as e:
        raise HTTPException(404, str(e))


@router.put("/recibidos/{albaran_id}", response_model=AlbaranRecRead)
def actualizar_rec(albaran_id: int, data: AlbaranRecUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    previo = svc.get_albaran_rec(db, albaran_id)
    if not previo:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(user, previo)
    exigir_empresa(user, data)
    try:
        alb = svc.update_albaran_rec(db, albaran_id, data)
    except ReferenciaInvalida as e:
        raise HTTPException(404, str(e))
    if not alb:
        raise HTTPException(404, "Recurso no encontrado")
    return alb


@router.delete("/recibidos/{albaran_id}", status_code=204)
def eliminar_rec(albaran_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    previo = svc.get_albaran_rec(db, albaran_id)
    if not previo:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(user, previo)
    if not svc.delete_albaran_rec(db, albaran_id):
        raise HTTPException(404, "Recurso no encontrado")
