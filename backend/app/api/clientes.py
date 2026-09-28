from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.auth import get_current_user
from app.services.permissions import require_method_permission, empresa_query, exigir_empresa, puede_ver_empresa
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.clientes_proveedores import ClienteRead, ClienteCreate, ClienteUpdate
from app.services import clientes as svc
router = APIRouter(prefix="/api/clientes", tags=["clientes"], dependencies=[Depends(require_method_permission)])


@router.get("", response_model=dict)
def listar(
    empresa_id: int = Depends(empresa_query),
    q: str = Query("", description="Buscar por nombre, NIF o localidad"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    items, total = svc.get_clientes(db, empresa_id, q, skip, limit)
    return {
        "total": total,
        "items": [ClienteRead.model_validate(i) for i in items],
    }


@router.get("/{cliente_id}", response_model=ClienteRead)
def obtener(cliente_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    cliente = svc.get_cliente(db, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    exigir_empresa(user, cliente)
    return cliente


@router.post("", response_model=ClienteRead, status_code=201)
def crear(data: ClienteCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    exigir_empresa(user, data)
    return svc.create_cliente(db, data)


@router.put("/{cliente_id}", response_model=ClienteRead)
def actualizar(cliente_id: int, data: ClienteUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    previo = svc.get_cliente(db, cliente_id)
    if not previo:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    exigir_empresa(user, previo)
    exigir_empresa(user, data)
    cliente = svc.update_cliente(db, cliente_id, data)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.delete("/{cliente_id}", status_code=204)
def eliminar(cliente_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    actual = svc.get_cliente(db, cliente_id)
    if not actual:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    exigir_empresa(user, actual)
    if not svc.delete_cliente(db, cliente_id):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
