from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.facturacion import Familia
from app.schemas.facturacion import FamiliaCreate, FamiliaUpdate


def get_familias(db: Session, empresa_id: int):
    return db.query(Familia).filter(
        Familia.empresa_id == empresa_id
    ).order_by(Familia.texto).all()


def get_familia(db: Session, familia_id: int):
    return db.query(Familia).filter(Familia.id == familia_id).first()


def create_familia(db: Session, data: FamiliaCreate) -> Familia:
    ultimo = db.query(func.max(Familia.numero)).filter(
        Familia.empresa_id == data.empresa_id
    ).scalar() or 0
    familia = Familia(**data.model_dump(), numero=ultimo + 1)
    db.add(familia)
    db.commit()
    db.refresh(familia)
    return familia


def update_familia(db: Session, familia_id: int, data: FamiliaUpdate) -> Familia | None:
    familia = get_familia(db, familia_id)
    if not familia:
        return None
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(familia, campo, valor)
    db.commit()
    db.refresh(familia)
    return familia


def delete_familia(db: Session, familia_id: int) -> bool:
    familia = get_familia(db, familia_id)
    if not familia:
        return False
    db.delete(familia)
    db.commit()
    return True
