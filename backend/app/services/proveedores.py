from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.clientes_proveedores import Proveedor
from app.models.contabilidad import Cuenta
from app.schemas.clientes_proveedores import ProveedorCreate, ProveedorUpdate
from app.services.sync import registrar_operacion


def _cuenta_proveedor(db: Session, empresa_id: int, numero: int) -> str:
    """Genera la cuenta contable 400xxxx para un proveedor nuevo, evitando
    colisionar con cuentas ya usadas por proveedores migrados de datos antiguos."""
    cuenta = f"400{numero:04d}"
    while db.query(Proveedor).filter(
        Proveedor.empresa_id == empresa_id, Proveedor.cuenta == cuenta
    ).first():
        numero += 1
        cuenta = f"400{numero:04d}"
    return cuenta


def get_proveedores(db: Session, empresa_id: int, q: str = "", skip: int = 0, limit: int = 50):
    query = db.query(Proveedor).filter(Proveedor.empresa_id == empresa_id)
    if q:
        termino = f"%{q.upper()}%"
        query = query.filter(
            or_(
                func.upper(Proveedor.nombre).like(termino),
                func.upper(Proveedor.comercial).like(termino),
                func.upper(Proveedor.nif).like(termino),
                func.upper(Proveedor.localidad).like(termino),
            )
        )
    total = query.count()
    items = query.order_by(Proveedor.nombre).offset(skip).limit(limit).all()
    return items, total


def get_proveedor(db: Session, proveedor_id: int):
    return db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()


def create_proveedor(db: Session, data: ProveedorCreate) -> Proveedor:
    ultimo = db.query(func.max(Proveedor.numero)).filter(
        Proveedor.empresa_id == data.empresa_id
    ).scalar() or 0
    numero = ultimo + 1

    payload = data.model_dump()
    if not payload.get("cuenta"):
        payload["cuenta"] = _cuenta_proveedor(db, data.empresa_id, numero)

    proveedor = Proveedor(**payload, numero=numero)
    db.add(proveedor)

    existe = db.query(Cuenta).filter(
        Cuenta.empresa_id == data.empresa_id, Cuenta.cuenta == proveedor.cuenta
    ).first()
    if not existe:
        db.add(Cuenta(empresa_id=data.empresa_id, cuenta=proveedor.cuenta, texto=(data.nombre or "").strip()))

    db.flush()
    registrar_operacion(db, data.empresa_id, 'proveedores', proveedor.uuid, 'C', data.model_dump(mode='json'))
    db.commit()
    db.refresh(proveedor)
    return proveedor


def update_proveedor(db: Session, proveedor_id: int, data: ProveedorUpdate) -> Proveedor | None:
    proveedor = get_proveedor(db, proveedor_id)
    if not proveedor:
        return None
    proveedor.version = (proveedor.version or 1) + 1
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(proveedor, campo, valor)
    registrar_operacion(db, proveedor.empresa_id, 'proveedores', proveedor.uuid, 'U',
                        data.model_dump(exclude_unset=True, mode='json'))
    db.commit()
    db.refresh(proveedor)
    return proveedor


def delete_proveedor(db: Session, proveedor_id: int) -> bool:
    proveedor = get_proveedor(db, proveedor_id)
    if not proveedor:
        return False
    entidad_uuid, empresa_id = proveedor.uuid, proveedor.empresa_id
    db.delete(proveedor)
    registrar_operacion(db, empresa_id, 'proveedores', entidad_uuid, 'D')
    db.commit()
    return True
