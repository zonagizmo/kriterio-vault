from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.facturacion import FamiliaRead, FamiliaCreate, FamiliaUpdate
from app.services import familias as svc

router = APIRouter(prefix="/api/familias", tags=["familias"])


@router.get("", response_model=list[FamiliaRead])
def listar(empresa_id: int, db: Session = Depends(get_db)):
    return svc.get_familias(db, empresa_id)


@router.get("/{familia_id}", response_model=FamiliaRead)
def obtener(familia_id: int, db: Session = Depends(get_db)):
    f = svc.get_familia(db, familia_id)
    if not f:
        raise HTTPException(404, "Familia no encontrada")
    return f


@router.post("", response_model=FamiliaRead, status_code=201)
def crear(data: FamiliaCreate, db: Session = Depends(get_db)):
    return svc.create_familia(db, data)


@router.put("/{familia_id}", response_model=FamiliaRead)
def actualizar(familia_id: int, data: FamiliaUpdate, db: Session = Depends(get_db)):
    f = svc.update_familia(db, familia_id, data)
    if not f:
        raise HTTPException(404, "Familia no encontrada")
    return f


@router.delete("/{familia_id}", status_code=204)
def eliminar(familia_id: int, db: Session = Depends(get_db)):
    if not svc.delete_familia(db, familia_id):
        raise HTTPException(404, "Familia no encontrada")
