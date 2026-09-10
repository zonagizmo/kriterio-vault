from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.contabilidad import Extra, ExApunte
from app.models.clientes_proveedores import Vencimiento
from app.schemas.extras import ExtraCreate, ExtraUpdate, ExtraPagoInfo
from app.services.sync import registrar_operacion


def _cargar_apuntes(db, empresa_id, extra_numero):
    return db.query(ExApunte).filter(
        ExApunte.empresa_id == empresa_id,
        ExApunte.extra == extra_numero,
    ).order_by(ExApunte.numero).all()


def _cargar_pago_info(db, empresa_id, extra_numero):
    from app.models.bancos import Banco, MovBanco, Pago
    # Puede haber más de un vencimiento por extra (ej. migración + pago nuevo).
    # Recorremos de más reciente a más antiguo y devolvemos el primero con pago real.
    vtos = db.query(Vencimiento).filter(
        Vencimiento.empresa_id == empresa_id,
        Vencimiento.tipo == 'X',
        Vencimiento.tpnumero == extra_numero,
    ).order_by(Vencimiento.id.desc()).all()
    for vto in vtos:
        pago = db.query(Pago).filter(
            Pago.empresa_id == empresa_id,
            Pago.vto == vto.numero,
        ).first()
        if not pago:
            continue
        banco = db.query(Banco).filter(
            Banco.empresa_id == empresa_id,
            Banco.numero == pago.banco,
        ).first()
        if not banco:
            continue
        mov = db.query(MovBanco).filter(
            MovBanco.empresa_id == empresa_id,
            MovBanco.banco == pago.banco,
            MovBanco.numero == pago.numero,
        ).first()
        return ExtraPagoInfo(
            banco_nombre=banco.nombre or '',
            fecha=mov.fecha if mov else None,
            importe=float(abs(pago.importe or 0)),
        )
    return None


def _cargar_fecha_vto(db, empresa_id, extra_numero):
    vto = db.query(Vencimiento).filter(
        Vencimiento.empresa_id == empresa_id,
        Vencimiento.tipo == 'X',
        Vencimiento.tpnumero == extra_numero,
    ).order_by(Vencimiento.id.desc()).first()
    return vto.fecha if vto else None


def _tiene_vencimiento(db, empresa_id, extra_numero):
    return db.query(Vencimiento.id).filter(
        Vencimiento.empresa_id == empresa_id,
        Vencimiento.tipo == 'X',
        Vencimiento.tpnumero == extra_numero,
    ).first() is not None


def get_extras(db: Session, empresa_id: int, tipo: str = None,
               fecha_desde=None, fecha_hasta=None, estado: str = None, q: str = None,
               skip: int = 0, limit: int = 50):
    query = db.query(Extra).filter(Extra.empresa_id == empresa_id)
    if tipo:
        query = query.filter(Extra.tipo == tipo)
    if fecha_desde:
        query = query.filter(Extra.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Extra.fecha <= fecha_hasta)
    if estado:
        query = query.filter(Extra.estado == estado)
    if q:
        query = query.filter(Extra.texto.ilike(f"%{q}%"))
    total = query.count()
    items = query.order_by(Extra.fecha.desc(), Extra.numero.desc()) \
                 .offset(skip).limit(limit).all()
    for e in items:
        e.apuntes = _cargar_apuntes(db, empresa_id, e.numero)
        e.pago_info = _cargar_pago_info(db, empresa_id, e.numero) if e.estado == 'C' else None
        e.fecha_vto = _cargar_fecha_vto(db, empresa_id, e.numero) if e.estado != 'C' else None
        e.tiene_vencimiento = _tiene_vencimiento(db, empresa_id, e.numero)
    return items, total


def get_extra(db: Session, extra_id: int):
    e = db.query(Extra).filter(Extra.id == extra_id).first()
    if e:
        e.apuntes = _cargar_apuntes(db, e.empresa_id, e.numero)
        e.pago_info = _cargar_pago_info(db, e.empresa_id, e.numero) if e.estado == 'C' else None
        e.fecha_vto = _cargar_fecha_vto(db, e.empresa_id, e.numero) if e.estado != 'C' else None
        e.tiene_vencimiento = _tiene_vencimiento(db, e.empresa_id, e.numero)
    return e


def _crear_apuntes(db, empresa_id, extra_numero, apuntes_data):
    for i, ap in enumerate(apuntes_data, start=1):
        db.add(ExApunte(
            empresa_id=empresa_id,
            numero=i,
            extra=extra_numero,
            cuenta=ap.cuenta,
            ayuda=ap.ayuda,
            dh=ap.dh,
            importe=ap.importe,
            declterc=ap.declterc,
        ))


def create_extra(db: Session, data: ExtraCreate) -> Extra:
    ultimo = db.query(func.max(Extra.numero)).filter(
        Extra.empresa_id == data.empresa_id
    ).scalar() or 0

    extra = Extra(
        empresa_id=data.empresa_id,
        numero=ultimo + 1,
        fecha=data.fecha,
        tipo=data.tipo,
        texto=data.texto,
        grupo=data.grupo,
        clave=data.clave,
        estado=data.estado,
        notas=data.notas,
    )
    db.add(extra)
    db.flush()

    _crear_apuntes(db, data.empresa_id, extra.numero, data.apuntes)
    db.flush()  # necesario: autoflush=False, generar_asiento_extra hace query de ExApuntes

    if data.generar_vto and data.vto_importe:
        from app.services.bancos import siguiente_numero_vencimiento
        vto = Vencimiento(
            empresa_id=data.empresa_id,
            numero=siguiente_numero_vencimiento(db, data.empresa_id),
            tipo='X',
            tpnumero=extra.numero,
            fecha=data.vto_fecha or data.fecha,
            importe=data.vto_importe,
            pendiente=data.vto_importe,
            cuentadef=data.vto_cuenta,
        )
        db.add(vto)

    from app.services.contabilidad import generar_asiento_extra
    generar_asiento_extra(db, data.empresa_id, extra)

    registrar_operacion(db, data.empresa_id, 'extras', extra.uuid, 'C', data.model_dump(mode='json'))
    db.commit()
    db.refresh(extra)
    extra.apuntes = _cargar_apuntes(db, data.empresa_id, extra.numero)
    extra.pago_info = _cargar_pago_info(db, data.empresa_id, extra.numero) if extra.estado == 'C' else None
    extra.fecha_vto = _cargar_fecha_vto(db, data.empresa_id, extra.numero) if extra.estado != 'C' else None
    extra.tiene_vencimiento = _tiene_vencimiento(db, data.empresa_id, extra.numero)
    return extra


def update_extra(db: Session, extra_id: int, data: ExtraUpdate) -> Extra | None:
    from app.services.contabilidad import _eliminar_asiento_documento, generar_asiento_extra
    from app.services.facturas import _ajustar_vencimiento_delta
    extra = db.query(Extra).filter(Extra.id == extra_id).first()
    if not extra:
        return None

    fecha_anterior = extra.fecha
    campos = data.model_dump(exclude={'apuntes'}, exclude_unset=True)
    extra.version = (extra.version or 1) + 1
    for campo, valor in campos.items():
        setattr(extra, campo, valor)

    regenerar = data.apuntes is not None or any(c in campos for c in ('fecha',))

    # El vencimiento (si existe) puede quedar desincronizado del extra: su fecha
    # e importe se fijaron al crearlo y desde entonces nada los actualizaba.
    vto = db.query(Vencimiento).filter(
        Vencimiento.empresa_id == extra.empresa_id,
        Vencimiento.tipo == 'X',
        Vencimiento.tpnumero == extra.numero,
    ).order_by(Vencimiento.id.desc()).first()
    vto_existente = vto is not None

    if vto and 'fecha' in campos and extra.fecha != fecha_anterior:
        vto.fecha = extra.fecha

    # Si el extra no tenía vencimiento (p. ej. se creó sin marcar la casilla), se
    # puede añadir uno ahora desde la edición — antes solo era posible al crear.
    if not vto and data.generar_vto and data.vto_importe:
        from app.services.bancos import siguiente_numero_vencimiento
        vto = Vencimiento(
            empresa_id=extra.empresa_id,
            numero=siguiente_numero_vencimiento(db, extra.empresa_id),
            tipo='X',
            tpnumero=extra.numero,
            fecha=data.vto_fecha or extra.fecha,
            importe=data.vto_importe,
            pendiente=data.vto_importe,
            cuentadef=data.vto_cuenta,
        )
        db.add(vto)

    if data.apuntes is not None:
        # Importe "del documento" = suma del lado Debe (partida doblada y cuadrada,
        # coincide con el Haber) — es lo que se usó como vto_importe al crearlo.
        old_total = sum(
            float(a.importe or 0) for a in db.query(ExApunte).filter(
                ExApunte.empresa_id == extra.empresa_id,
                ExApunte.extra == extra.numero,
                ExApunte.dh == 'D',
            )
        )
        db.query(ExApunte).filter(
            ExApunte.empresa_id == extra.empresa_id,
            ExApunte.extra == extra.numero,
        ).delete()
        _crear_apuntes(db, extra.empresa_id, extra.numero, data.apuntes)

        new_total = sum(float(a.importe or 0) for a in data.apuntes if a.dh == 'D')
        delta = round(new_total - old_total, 2)
        if delta != 0 and vto and vto_existente:
            _ajustar_vencimiento_delta(db, extra.empresa_id, vto, delta)

    if regenerar:
        _eliminar_asiento_documento(db, extra.empresa_id, 'X', extra.numero)
        db.flush()  # necesario: autoflush=False
        generar_asiento_extra(db, extra.empresa_id, extra)
    else:
        # Aunque no haya cambio de apuntes ni fecha, si el extra tiene apuntes completos
        # y no tiene asiento, intentar generarlo ahora (cubre actualizaciones parciales
        # como cambio de estado o texto que antes dejaban el asiento pendiente).
        from app.services.contabilidad import generar_asiento_extra as _gen
        from app.models.contabilidad import Diario
        ya = db.query(Diario).filter(
            Diario.empresa_id == extra.empresa_id,
            Diario.tipo == 'X',
            Diario.numero == extra.numero,
        ).first()
        if not ya:
            db.flush()
            _gen(db, extra.empresa_id, extra)

    registrar_operacion(db, extra.empresa_id, 'extras', extra.uuid, 'U',
                        data.model_dump(exclude={'apuntes'}, exclude_unset=True, mode='json'))
    db.commit()
    db.refresh(extra)
    extra.apuntes = _cargar_apuntes(db, extra.empresa_id, extra.numero)
    extra.pago_info = _cargar_pago_info(db, extra.empresa_id, extra.numero) if extra.estado == 'C' else None
    extra.fecha_vto = _cargar_fecha_vto(db, extra.empresa_id, extra.numero) if extra.estado != 'C' else None
    extra.tiene_vencimiento = _tiene_vencimiento(db, extra.empresa_id, extra.numero)
    return extra


def renumerar_extras(db: Session, empresa_id: int, desde_id: int = None) -> int:
    extras = db.query(Extra).filter(
        Extra.empresa_id == empresa_id
    ).order_by(Extra.fecha.asc(), Extra.id.asc()).all()

    if desde_id:
        idx = next((i for i, e in enumerate(extras) if e.id == desde_id), None)
        if idx is None:
            return 0
        year = extras[idx].fecha.year if extras[idx].fecha else 2000
        start = sum(1 for e in extras[:idx] if e.fecha and e.fecha.year == year)
        to_renumber = [e for e in extras[idx:] if e.fecha and e.fecha.year == year]
        for i, e in enumerate(to_renumber):
            e.cnumero = start + i + 1
        count = len(to_renumber)
    else:
        counters = {}
        for e in extras:
            year = e.fecha.year if e.fecha else 2000
            counters[year] = counters.get(year, 0) + 1
            e.cnumero = counters[year]
        count = len(extras)

    db.commit()
    return count


def delete_extra(db: Session, extra_id: int) -> bool:
    from app.services.contabilidad import _eliminar_asiento_documento
    from app.services.facturas import _borrar_vencimiento
    from app.models.contabilidad import DiarioTxt
    extra = db.query(Extra).filter(Extra.id == extra_id).first()
    if not extra:
        return False
    entidad_uuid, empresa_id = extra.uuid, extra.empresa_id
    # Lanza ValueError si algún vencimiento tiene pagos bancarios asociados
    _borrar_vencimiento(db, extra.empresa_id, 'X', extra.numero)
    _eliminar_asiento_documento(db, extra.empresa_id, 'X', extra.numero)
    db.query(ExApunte).filter(
        ExApunte.empresa_id == extra.empresa_id,
        ExApunte.extra == extra.numero,
    ).delete()
    db.query(DiarioTxt).filter(
        DiarioTxt.empresa_id == extra.empresa_id,
        DiarioTxt.tipo == 'X',
        DiarioTxt.numero == extra.numero,
    ).delete()
    db.delete(extra)
    registrar_operacion(db, empresa_id, 'extras', entidad_uuid, 'D')
    db.commit()
    return True
