from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.facturacion import Articulo
from app.schemas.facturacion import ArticuloCreate, ArticuloUpdate
from app.services.sync import registrar_operacion


def get_articulos(db: Session, empresa_id: int, q: str = "", familia: int = None,
                  skip: int = 0, limit: int = 50):
    query = db.query(Articulo).filter(Articulo.empresa_id == empresa_id)
    if q:
        t = f"%{q.upper()}%"
        query = query.filter(
            or_(
                func.upper(Articulo.nombre).like(t),
                func.upper(Articulo.codigo).like(t),
                func.upper(Articulo.ean13).like(t),
            )
        )
    if familia is not None:
        query = query.filter(Articulo.familia == familia)
    total = query.count()
    items = query.order_by(Articulo.nombre).offset(skip).limit(limit).all()
    return items, total


def get_articulo(db: Session, articulo_id: int):
    return db.query(Articulo).filter(Articulo.id == articulo_id).first()


def create_articulo(db: Session, data: ArticuloCreate) -> Articulo:
    ultimo = db.query(func.max(Articulo.numero)).filter(
        Articulo.empresa_id == data.empresa_id
    ).scalar() or 0
    articulo = Articulo(**data.model_dump(), numero=ultimo + 1)
    db.add(articulo)
    db.flush()
    registrar_operacion(db, data.empresa_id, 'articulos', articulo.uuid, 'C', data.model_dump(mode='json'))
    db.commit()
    db.refresh(articulo)
    return articulo


def update_articulo(db: Session, articulo_id: int, data: ArticuloUpdate) -> Articulo | None:
    articulo = get_articulo(db, articulo_id)
    if not articulo:
        return None
    articulo.version = (articulo.version or 1) + 1
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(articulo, campo, valor)
    registrar_operacion(db, articulo.empresa_id, 'articulos', articulo.uuid, 'U',
                        data.model_dump(exclude_unset=True, mode='json'))
    db.commit()
    db.refresh(articulo)
    return articulo


def delete_articulo(db: Session, articulo_id: int) -> bool:
    articulo = get_articulo(db, articulo_id)
    if not articulo:
        return False
    entidad_uuid, empresa_id = articulo.uuid, articulo.empresa_id
    db.delete(articulo)
    registrar_operacion(db, empresa_id, 'articulos', entidad_uuid, 'D')
    db.commit()
    return True
