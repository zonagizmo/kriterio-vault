from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.auth import get_current_user
from app.services.permissions import require_method_permission, empresa_query, exigir_empresa, puede_ver_empresa
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.clientes_proveedores import ProveedorRead, ProveedorCreate, ProveedorUpdate
from app.services import proveedores as svc
router = APIRouter(prefix="/api/proveedores", tags=["proveedores"], dependencies=[Depends(require_method_permission)])


@router.get("", response_model=dict)
def listar(
    empresa_id: int = Depends(empresa_query),
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
def obtener(proveedor_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    proveedor = svc.get_proveedor(db, proveedor_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    exigir_empresa(user, proveedor)
    return proveedor


@router.post("", response_model=ProveedorRead, status_code=201)
def crear(data: ProveedorCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    exigir_empresa(user, data)
    return svc.create_proveedor(db, data)


@router.put("/{proveedor_id}", response_model=ProveedorRead)
def actualizar(proveedor_id: int, data: ProveedorUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    previo = svc.get_proveedor(db, proveedor_id)
    if not previo:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    exigir_empresa(user, previo)
    exigir_empresa(user, data)
    proveedor = svc.update_proveedor(db, proveedor_id, data)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return proveedor


@router.delete("/{proveedor_id}", status_code=204)
def eliminar(proveedor_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    actual = svc.get_proveedor(db, proveedor_id)
    if not actual:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    exigir_empresa(user, actual)
    if not svc.delete_proveedor(db, proveedor_id):
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
