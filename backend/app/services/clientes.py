from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.clientes_proveedores import Cliente
from app.models.contabilidad import Cuenta
from app.schemas.clientes_proveedores import ClienteCreate, ClienteUpdate
from app.services.sync import registrar_operacion


def _cuenta_cliente(db: Session, empresa_id: int, numero: int) -> str:
    """Genera la cuenta contable 430xxxx para un cliente nuevo, evitando
    colisionar con cuentas ya usadas por clientes migrados de datos antiguos."""
    cuenta = f"430{numero:04d}"
    while db.query(Cliente).filter(
        Cliente.empresa_id == empresa_id, Cliente.cuenta == cuenta
    ).first():
        numero += 1
        cuenta = f"430{numero:04d}"
    return cuenta


def get_clientes(db: Session, empresa_id: int, q: str = "", skip: int = 0, limit: int = 50):
    query = db.query(Cliente).filter(Cliente.empresa_id == empresa_id)
    if q:
        termino = f"%{q.upper()}%"
        query = query.filter(
            or_(
                func.upper(Cliente.nombre).like(termino),
                func.upper(Cliente.comercial).like(termino),
                func.upper(Cliente.nif).like(termino),
                func.upper(Cliente.localidad).like(termino),
            )
        )
    total = query.count()
    items = query.order_by(Cliente.nombre).offset(skip).limit(limit).all()
    return items, total


def get_cliente(db: Session, cliente_id: int):
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()


def create_cliente(db: Session, data: ClienteCreate) -> Cliente:
    ultimo = db.query(func.max(Cliente.numero)).filter(
        Cliente.empresa_id == data.empresa_id
    ).scalar() or 0
    numero = ultimo + 1

    payload = data.model_dump()
    if not payload.get("cuenta"):
        payload["cuenta"] = _cuenta_cliente(db, data.empresa_id, numero)

    cliente = Cliente(**payload, numero=numero)
    db.add(cliente)

    existe = db.query(Cuenta).filter(
        Cuenta.empresa_id == data.empresa_id, Cuenta.cuenta == cliente.cuenta
    ).first()
    if not existe:
        db.add(Cuenta(empresa_id=data.empresa_id, cuenta=cliente.cuenta, texto=(data.nombre or "").strip()))

    db.flush()
    registrar_operacion(db, data.empresa_id, 'clientes', cliente.uuid, 'C', data.model_dump(mode='json'))
    db.commit()
    db.refresh(cliente)
    return cliente


def update_cliente(db: Session, cliente_id: int, data: ClienteUpdate) -> Cliente | None:
    cliente = get_cliente(db, cliente_id)
    if not cliente:
        return None
    cliente.version = (cliente.version or 1) + 1
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    registrar_operacion(db, cliente.empresa_id, 'clientes', cliente.uuid, 'U',
                        data.model_dump(exclude_unset=True, mode='json'))
    db.commit()
    db.refresh(cliente)
    return cliente


def delete_cliente(db: Session, cliente_id: int) -> bool:
    cliente = get_cliente(db, cliente_id)
    if not cliente:
        return False
    entidad_uuid, empresa_id = cliente.uuid, cliente.empresa_id
    db.delete(cliente)
    registrar_operacion(db, empresa_id, 'clientes', entidad_uuid, 'D')
    db.commit()
    return True
