from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.clientes_proveedores import ProveedorRead, ProveedorCreate, ProveedorUpdate
from app.services import proveedores as svc

router = APIRouter(prefix="/api/proveedores", tags=["proveedores"])


@router.get("", response_model=dict)
def listar(
    empresa_id: int,
    q: str = Query("", description="Buscar por nombre, NIF o localidad"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    items, total = svc.get_proveedores(db, empresa_id, q, skip, limit)
    return {
        "total": total,
        "items": [ProveedorRead.model_validate(i) for i in items],
    }


@router.get("/{proveedor_id}", response_model=ProveedorRead)
def obtener(proveedor_id: int, db: Session = Depends(get_db)):
    proveedor = svc.get_proveedor(db, proveedor_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor


@router.post("", response_model=ProveedorRead, status_code=201)
def crear(data: ProveedorCreate, db: Session = Depends(get_db)):
    return svc.create_proveedor(db, data)


@router.put("/{proveedor_id}", response_model=ProveedorRead)
def actualizar(proveedor_id: int, data: ProveedorUpdate, db: Session = Depends(get_db)):
    proveedor = svc.update_proveedor(db, proveedor_id, data)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor


@router.delete("/{proveedor_id}", status_code=204)
def eliminar(proveedor_id: int, db: Session = Depends(get_db)):
    if not svc.delete_proveedor(db, proveedor_id):
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
