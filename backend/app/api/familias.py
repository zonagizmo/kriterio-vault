from fastapi import APIRouter, Depends, HTTPException
from app.services.auth import get_current_user
from app.services.permissions import require_method_permission, empresa_query, exigir_empresa, puede_ver_empresa
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.facturacion import FamiliaRead, FamiliaCreate, FamiliaUpdate
from app.services import familias as svc
router = APIRouter(prefix="/api/familias", tags=["familias"], dependencies=[Depends(require_method_permission)])


@router.get("", response_model=list[FamiliaRead])
def listar(empresa_id: int = Depends(empresa_query), db: Session = Depends(get_db)):
    return svc.get_familias(db, empresa_id)


@router.get("/{familia_id}", response_model=FamiliaRead)
def obtener(familia_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    f = svc.get_familia(db, familia_id)
    if not f:
        raise HTTPException(404, "Familia no encontrada")
    exigir_empresa(user, f)
    return f


@router.post("", response_model=FamiliaRead, status_code=201)
def crear(data: FamiliaCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    exigir_empresa(user, data)
    return svc.create_familia(db, data)


@router.put("/{familia_id}", response_model=FamiliaRead)
def actualizar(familia_id: int, data: FamiliaUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    previo = svc.get_familia(db, familia_id)
    if not previo:
        raise HTTPException(404, "Familia no encontrada")
    exigir_empresa(user, previo)
    exigir_empresa(user, data)
    f = svc.update_familia(db, familia_id, data)
    if not f:
        raise HTTPException(404, "Familia no encontrada")
    return f


@router.delete("/{familia_id}", status_code=204)
def eliminar(familia_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    actual = svc.get_familia(db, familia_id)
    if not actual:
        raise HTTPException(status_code=404, detail="Familia no encontrado")
    exigir_empresa(user, actual)
    if not svc.delete_familia(db, familia_id):
        raise HTTPException(404, "Familia no encontrada")
