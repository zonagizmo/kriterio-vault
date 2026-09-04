from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.clientes_proveedores import ClienteRead, ClienteCreate, ClienteUpdate
from app.services import clientes as svc

router = APIRouter(prefix="/api/clientes", tags=["clientes"])


@router.get("", response_model=dict)
def listar(
    empresa_id: int,
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
def obtener(cliente_id: int, db: Session = Depends(get_db)):
    cliente = svc.get_cliente(db, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.post("", response_model=ClienteRead, status_code=201)
def crear(data: ClienteCreate, db: Session = Depends(get_db)):
    return svc.create_cliente(db, data)


@router.put("/{cliente_id}", response_model=ClienteRead)
def actualizar(cliente_id: int, data: ClienteUpdate, db: Session = Depends(get_db)):
    cliente = svc.update_cliente(db, cliente_id, data)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.delete("/{cliente_id}", status_code=204)
def eliminar(cliente_id: int, db: Session = Depends(get_db)):
    if not svc.delete_cliente(db, cliente_id):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
