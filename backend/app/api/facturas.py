from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.db.database import get_db
from app.schemas.facturacion import (
    FacturaEmiRead, FacturaEmiCreate, FacturaEmiUpdate,
    FacturaRecRead, FacturaRecCreate, FacturaRecUpdate,
)
from app.services import facturas as svc


class RenumerarBody(BaseModel):
    empresa_id: int
    desde_id: Optional[int] = None

router = APIRouter(prefix="/api/facturas", tags=["facturas"])


def _detalle_duplicado(fac, total_nuevo):
    fecha_txt = fac.fecha.strftime('%d/%m/%Y') if fac.fecha else 'sin fecha'
    total_existente = float(fac.total or 0)
    if abs(total_existente - (total_nuevo or 0)) < 0.005:
        aviso_total = f"y el mismo total ({total_existente:.2f} €)"
    else:
        aviso_total = f"pero con distinto total (existente: {total_existente:.2f} €, nuevo: {total_nuevo:.2f} €)"
    return {
        "duplicado": True,
        "mensaje": (
            f"Ya existe la factura nº {fac.numero} de este proveedor con el mismo "
            f"nº de factura, {aviso_total}, fechada el {fecha_txt}."
        ),
        "factura_id": fac.id,
        "numero": fac.numero,
        "fecha": fac.fecha.isoformat() if fac.fecha else None,
        "total": total_existente,
    }


# ─── Emitidas ─────────────────────────────────────────────────────────────────

@router.get("/emitidas", response_model=dict)
def listar_emi(
    empresa_id: int, q: str = Query(""),
    cliente: Optional[int] = None,
    fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None,
    estado: Optional[str] = None,
    skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
):
    items, total = svc.get_facturas_emi(db, empresa_id, q, cliente, skip, limit, fecha_desde, fecha_hasta, estado)
    return {"total": total, "items": [FacturaEmiRead.model_validate(i) for i in items]}


@router.get("/emitidas/{factura_id}", response_model=FacturaEmiRead)
def obtener_emi(factura_id: int, db: Session = Depends(get_db)):
    fac = svc.get_factura_emi(db, factura_id)
    if not fac:
        raise HTTPException(404, "Factura no encontrada")
    return fac


@router.post("/emitidas", response_model=FacturaEmiRead, status_code=201)
def crear_emi(data: FacturaEmiCreate, db: Session = Depends(get_db)):
    return svc.create_factura_emi(db, data)


@router.put("/emitidas/{factura_id}", response_model=FacturaEmiRead)
def actualizar_emi(factura_id: int, data: FacturaEmiUpdate, db: Session = Depends(get_db)):
    fac = svc.update_factura_emi(db, factura_id, data)
    if not fac:
        raise HTTPException(404, "Factura no encontrada")
    return fac


@router.delete("/emitidas/{factura_id}", status_code=204)
def eliminar_emi(factura_id: int, db: Session = Depends(get_db)):
    try:
        if not svc.delete_factura_emi(db, factura_id):
            raise HTTPException(404, "Factura no encontrada")
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.post("/emitidas/renumerar")
def renumerar_emi(body: RenumerarBody, db: Session = Depends(get_db)):
    count = svc.renumerar_facturas_emi(db, body.empresa_id, body.desde_id)
    return {"renumeradas": count}


# ─── Recibidas ────────────────────────────────────────────────────────────────

@router.get("/recibidas", response_model=dict)
def listar_rec(
    empresa_id: int, q: str = Query(""),
    proveedor: Optional[int] = None,
    fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None,
    estado: Optional[str] = None,
    skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
):
    items, total = svc.get_facturas_rec(db, empresa_id, q, proveedor, skip, limit, fecha_desde, fecha_hasta, estado)
    return {"total": total, "items": [FacturaRecRead.model_validate(i) for i in items]}


@router.get("/recibidas/{factura_id}", response_model=FacturaRecRead)
def obtener_rec(factura_id: int, db: Session = Depends(get_db)):
    fac = svc.get_factura_rec(db, factura_id)
    if not fac:
        raise HTTPException(404, "Factura no encontrada")
    return fac


@router.post("/recibidas", response_model=FacturaRecRead, status_code=201)
def crear_rec(data: FacturaRecCreate, db: Session = Depends(get_db)):
    try:
        return svc.create_factura_rec(db, data)
    except svc.FacturaDuplicadaError as e:
        raise HTTPException(409, detail=_detalle_duplicado(e.factura, e.total_nuevo))


@router.put("/recibidas/{factura_id}", response_model=FacturaRecRead)
def actualizar_rec(factura_id: int, data: FacturaRecUpdate, db: Session = Depends(get_db)):
    try:
        fac = svc.update_factura_rec(db, factura_id, data)
    except svc.FacturaDuplicadaError as e:
        raise HTTPException(409, detail=_detalle_duplicado(e.factura, e.total_nuevo))
    if not fac:
        raise HTTPException(404, "Factura no encontrada")
    return fac


@router.delete("/recibidas/{factura_id}", status_code=204)
def eliminar_rec(factura_id: int, db: Session = Depends(get_db)):
    try:
        if not svc.delete_factura_rec(db, factura_id):
            raise HTTPException(404, "Factura no encontrada")
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.post("/recibidas/renumerar")
def renumerar_rec(body: RenumerarBody, db: Session = Depends(get_db)):
    count = svc.renumerar_facturas_rec(db, body.empresa_id, body.desde_id)
    return {"renumeradas": count}
