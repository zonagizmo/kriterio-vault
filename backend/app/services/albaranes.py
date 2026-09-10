from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.facturacion import AlbaranEmitido, AlbaranRecibido, Apunte
from app.schemas.facturacion import (
    AlbaranEmiCreate, AlbaranEmiUpdate,
    AlbaranRecCreate, AlbaranRecUpdate,
)
from app.services.documentos import (
    siguiente_numero, siguiente_cnumero, guardar_lineas, get_lineas, total_lineas,
)
from app.services.sync import registrar_operacion


# ─── Albaranes emitidos ───────────────────────────────────────────────────────

TALBARAN_EMI = 'E'

def _cargar_lineas_emi(db, alb):
    alb.lineas = get_lineas(db, alb.empresa_id, alb.numero, TALBARAN_EMI)
    return alb


def get_albaranes_emi(db: Session, empresa_id: int, q: str = "",
                      cliente: int = None, skip: int = 0, limit: int = 50):
    query = db.query(AlbaranEmitido).filter(AlbaranEmitido.empresa_id == empresa_id)
    if cliente:
        query = query.filter(AlbaranEmitido.cliente == cliente)
    if q:
        t = f"%{q}%"
        query = query.filter(AlbaranEmitido.cnumalt.like(t))
    total = query.count()
    items = query.order_by(AlbaranEmitido.fecha.desc(), AlbaranEmitido.numero.desc()) \
                 .offset(skip).limit(limit).all()
    return items, total


def get_albaran_emi(db: Session, albaran_id: int):
    alb = db.query(AlbaranEmitido).filter(AlbaranEmitido.id == albaran_id).first()
    if alb:
        _cargar_lineas_emi(db, alb)
    return alb


def create_albaran_emi(db: Session, data: AlbaranEmiCreate) -> AlbaranEmitido:
    numero = siguiente_numero(db, AlbaranEmitido, data.empresa_id)
    tiponum, cnumero = siguiente_cnumero(db, AlbaranEmitido, data.empresa_id, data.fecha)

    alb = AlbaranEmitido(
        empresa_id=data.empresa_id,
        numero=numero, cnumero=cnumero, tiponum=tiponum,
        fecha=data.fecha, cliente=data.cliente,
        cnumalt=data.cnumalt, cpi=data.cpi,
        estado=data.estado or 'P', notas=data.notas,
    )
    db.add(alb)
    db.flush()

    lineas = guardar_lineas(db, data.empresa_id, numero, TALBARAN_EMI, data.fecha, data.lineas)
    alb.importe = total_lineas(lineas)
    alb.apuntes = len(lineas)
    registrar_operacion(db, data.empresa_id, 'albaranes_emitidos', alb.uuid, 'C', data.model_dump(mode='json'))
    db.commit()
    db.refresh(alb)
    _cargar_lineas_emi(db, alb)
    return alb


def update_albaran_emi(db: Session, albaran_id: int, data: AlbaranEmiUpdate) -> AlbaranEmitido | None:
    alb = db.query(AlbaranEmitido).filter(AlbaranEmitido.id == albaran_id).first()
    if not alb:
        return None
    alb.version = (alb.version or 1) + 1
    for campo, valor in data.model_dump(exclude={'lineas'}, exclude_unset=True).items():
        setattr(alb, campo, valor)
    if data.lineas is not None:
        lineas = guardar_lineas(db, alb.empresa_id, alb.numero, TALBARAN_EMI,
                                alb.fecha, data.lineas)
        alb.importe = total_lineas(lineas)
        alb.apuntes = len(lineas)
    registrar_operacion(db, alb.empresa_id, 'albaranes_emitidos', alb.uuid, 'U',
                        data.model_dump(exclude_unset=True, mode='json'))
    db.commit()
    db.refresh(alb)
    _cargar_lineas_emi(db, alb)
    return alb


def delete_albaran_emi(db: Session, albaran_id: int) -> bool:
    alb = db.query(AlbaranEmitido).filter(AlbaranEmitido.id == albaran_id).first()
    if not alb:
        return False
    entidad_uuid, empresa_id = alb.uuid, alb.empresa_id
    db.query(Apunte).filter(
        Apunte.empresa_id == alb.empresa_id,
        Apunte.albaran == alb.numero,
        Apunte.talbaran == TALBARAN_EMI,
    ).delete()
    db.delete(alb)
    registrar_operacion(db, empresa_id, 'albaranes_emitidos', entidad_uuid, 'D')
    db.commit()
    return True


# ─── Albaranes recibidos ──────────────────────────────────────────────────────

TALBARAN_REC = 'R'

def _cargar_lineas_rec(db, alb):
    alb.lineas = get_lineas(db, alb.empresa_id, alb.numero, TALBARAN_REC)
    return alb


def get_albaranes_rec(db: Session, empresa_id: int, q: str = "",
                      proveedor: int = None, skip: int = 0, limit: int = 50):
    query = db.query(AlbaranRecibido).filter(AlbaranRecibido.empresa_id == empresa_id)
    if proveedor:
        query = query.filter(AlbaranRecibido.proveedor == proveedor)
    if q:
        query = query.filter(AlbaranRecibido.pralbaran.like(f"%{q}%"))
    total = query.count()
    items = query.order_by(AlbaranRecibido.fecha.desc(), AlbaranRecibido.numero.desc()) \
                 .offset(skip).limit(limit).all()
    return items, total


def get_albaran_rec(db: Session, albaran_id: int):
    alb = db.query(AlbaranRecibido).filter(AlbaranRecibido.id == albaran_id).first()
    if alb:
        _cargar_lineas_rec(db, alb)
    return alb


def create_albaran_rec(db: Session, data: AlbaranRecCreate) -> AlbaranRecibido:
    numero = siguiente_numero(db, AlbaranRecibido, data.empresa_id)
    tiponum, cnumero = siguiente_cnumero(db, AlbaranRecibido, data.empresa_id, data.fecha)

    alb = AlbaranRecibido(
        empresa_id=data.empresa_id,
        numero=numero, cnumero=cnumero, tiponum=tiponum,
        fecha=data.fecha, proveedor=data.proveedor,
        pralbaran=data.pralbaran, prfecha=data.prfecha,
        cnumalt=data.cnumalt, estado=data.estado or 'P', notas=data.notas,
    )
    db.add(alb)
    db.flush()

    lineas = guardar_lineas(db, data.empresa_id, numero, TALBARAN_REC, data.fecha, data.lineas)
    alb.importe = total_lineas(lineas)
    alb.apuntes = len(lineas)
    registrar_operacion(db, data.empresa_id, 'albaranes_recibidos', alb.uuid, 'C', data.model_dump(mode='json'))
    db.commit()
    db.refresh(alb)
    _cargar_lineas_rec(db, alb)
    return alb


def update_albaran_rec(db: Session, albaran_id: int, data: AlbaranRecUpdate) -> AlbaranRecibido | None:
    alb = db.query(AlbaranRecibido).filter(AlbaranRecibido.id == albaran_id).first()
    if not alb:
        return None
    alb.version = (alb.version or 1) + 1
    for campo, valor in data.model_dump(exclude={'lineas'}, exclude_unset=True).items():
        setattr(alb, campo, valor)
    if data.lineas is not None:
        lineas = guardar_lineas(db, alb.empresa_id, alb.numero, TALBARAN_REC,
                                alb.fecha, data.lineas)
        alb.importe = total_lineas(lineas)
        alb.apuntes = len(lineas)
    registrar_operacion(db, alb.empresa_id, 'albaranes_recibidos', alb.uuid, 'U',
                        data.model_dump(exclude_unset=True, mode='json'))
    db.commit()
    db.refresh(alb)
    _cargar_lineas_rec(db, alb)
    return alb


def delete_albaran_rec(db: Session, albaran_id: int) -> bool:
    alb = db.query(AlbaranRecibido).filter(AlbaranRecibido.id == albaran_id).first()
    if not alb:
        return False
    entidad_uuid, empresa_id = alb.uuid, alb.empresa_id
    db.query(Apunte).filter(
        Apunte.empresa_id == alb.empresa_id,
        Apunte.albaran == alb.numero,
        Apunte.talbaran == TALBARAN_REC,
    ).delete()
    db.delete(alb)
    registrar_operacion(db, empresa_id, 'albaranes_recibidos', entidad_uuid, 'D')
    db.commit()
    return True
