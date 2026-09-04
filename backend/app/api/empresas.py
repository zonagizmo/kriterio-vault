from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.empresas import Empresa
from app.schemas.empresas import EmpresaRead, EmpresaUpdate

router = APIRouter(prefix="/api/empresas", tags=["empresas"])


@router.get("", response_model=list[EmpresaRead])
def listar_empresas(db: Session = Depends(get_db)):
    return db.query(Empresa).filter(Empresa.activa == True).order_by(Empresa.codigo).all()


@router.get("/{empresa_id}", response_model=EmpresaRead)
def obtener_empresa(empresa_id: int, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa no encontrada")
    return empresa


@router.put("/{empresa_id}", response_model=EmpresaRead)
def actualizar_empresa(empresa_id: int, data: EmpresaUpdate, db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Empresa no encontrada")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(empresa, campo, valor)
    db.commit()
    db.refresh(empresa)
    return empresa
