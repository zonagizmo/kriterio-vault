from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.facturacion import FacturaEmitida, FacturaRecibida, Apunte
from app.models.clientes_proveedores import Vencimiento
from app.schemas.facturacion import (
    FacturaEmiCreate, FacturaEmiUpdate,
    FacturaRecCreate, FacturaRecUpdate,
    FacturaPagoInfo,
)
from app.services.documentos import (
    siguiente_numero, siguiente_cnumero, guardar_lineas, get_lineas, total_lineas,
    calcular_importe_linea,
)
from app.services import contabilidad as cont_svc
from app.services.sync import registrar_operacion

TALBARAN_FEMI = 'F'
TALBARAN_FREC = 'C'


class FacturaDuplicadaError(Exception):
    """Ya existe otra factura recibida del mismo proveedor con el mismo nº de
    factura de proveedor. Se usa para avisar al usuario, no bloquea por sí sola."""
    def __init__(self, factura: FacturaRecibida, total_nuevo: float):
        self.factura = factura
        self.total_nuevo = total_nuevo


def _total_previsto(lineas_data) -> float:
    return round(sum(
        calcular_importe_linea(l.cantidad or 1, l.precio or 0, l.dcto1 or 0, l.dcto2 or 0, l.dcto3 or 0)
        for l in lineas_data
    ), 2)


def _buscar_duplicado_rec(db: Session, empresa_id: int, proveedor: int,
                          prfactura: str, excluir_id: int = None):
    """Detecta otra factura recibida del mismo proveedor con el mismo nº de
    factura de proveedor, sea cual sea su total: un nº de factura repetido ya es
    indicio de duplicado aunque el importe introducido no coincida (p. ej. error
    al teclear cantidades)."""
    prfactura = (prfactura or '').strip()
    if not proveedor or not prfactura:
        return None
    query = db.query(FacturaRecibida).filter(
        FacturaRecibida.empresa_id == empresa_id,
        FacturaRecibida.proveedor == proveedor,
        FacturaRecibida.prfactura == prfactura,
    )
    if excluir_id:
        query = query.filter(FacturaRecibida.id != excluir_id)
    return query.first()


def _cargar_pago_info(db, empresa_id, tipo_vto, fac_numero):
    from app.models.bancos import Banco, MovBanco, Pago
    vto = db.query(Vencimiento).filter(
        Vencimiento.empresa_id == empresa_id,
        Vencimiento.tipo == tipo_vto,
        Vencimiento.tpnumero == fac_numero,
    ).first()
    if not vto:
        return None
    pago = db.query(Pago).filter(
        Pago.empresa_id == empresa_id,
        Pago.vto == vto.numero,
    ).first()
    if not pago:
        return None
    banco = db.query(Banco).filter(
        Banco.empresa_id == empresa_id,
        Banco.numero == pago.banco,
    ).first()
    if not banco:
        return None
    mov = db.query(MovBanco).filter(
        MovBanco.empresa_id == empresa_id,
        MovBanco.banco == pago.banco,
        MovBanco.numero == pago.numero,
    ).first()
    return FacturaPagoInfo(
        banco_nombre=banco.nombre or '',
        fecha=mov.fecha if mov else None,
        importe=float(abs(pago.importe or 0)),
    )


def _crear_vencimiento(db, empresa_id, tipo, tpnumero, fecha, importe, cuentadef):
    """Crea un vencimiento asociado a una factura.
    La numeración evita reutilizar números referenciados por pagos de vencimientos
    borrados (el vencimiento nuevo heredaría esos pagos y nacería 'pagado')."""
    if not importe:
        return
    from app.services.bancos import siguiente_numero_vencimiento
    vto = Vencimiento(
        empresa_id=empresa_id,
        numero=siguiente_numero_vencimiento(db, empresa_id),
        tipo=tipo,
        tpnumero=tpnumero,
        fecha=fecha,
        importe=importe,
        pendiente=importe,
        cuentadef=cuentadef,
    )
    db.add(vto)


def _borrar_vencimiento(db, empresa_id, tipo, tpnumero):
    """Elimina los vencimientos de un documento.
    Si alguno tiene pagos bancarios asociados lanza ValueError: borrar el documento
    dejaría pagos colgantes y descuadraría la cuenta del tercero. Hay que eliminar
    (o desvincular) primero el movimiento bancario que lo paga."""
    from app.models.bancos import Pago
    vtos = db.query(Vencimiento).filter(
        Vencimiento.empresa_id == empresa_id,
        Vencimiento.tipo == tipo,
        Vencimiento.tpnumero == tpnumero,
    ).all()
    for vto in vtos:
        pago = db.query(Pago).filter(
            Pago.empresa_id == empresa_id,
            Pago.vto == vto.numero,
        ).first()
        if pago:
            raise ValueError(
                f"No se puede eliminar: el vencimiento nº {vto.numero} tiene un pago "
                f"asociado en el banco {pago.banco} (movimiento {pago.numero}). "
                "Elimina primero ese movimiento bancario."
            )
        db.delete(vto)


def _ajustar_vencimiento_delta(db, empresa_id, vto, delta):
    """Aplica un cambio de total de factura al vencimiento: ajusta importe y
    pendiente, mantiene el pendiente dentro de [0, importe] (o [importe, 0] para
    abonos) y sincroniza el estado del documento — antes una factura podía quedar
    'Pendiente' estando pagada, o con pendiente negativo."""
    from app.services.bancos import _sync_estado_factura
    vto.importe = round((vto.importe or 0) + delta, 2)
    vto.pendiente = round((vto.pendiente or 0) + delta, 2)
    if vto.importe >= 0:
        vto.pendiente = min(max(vto.pendiente, 0), vto.importe)
    else:
        vto.pendiente = max(min(vto.pendiente, 0), vto.importe)
    _sync_estado_factura(db, empresa_id, vto)


def _lineas(db, fac, talbaran):
    fac.lineas = get_lineas(db, fac.empresa_id, fac.numero, talbaran)
    return fac


# ─── Facturas emitidas ────────────────────────────────────────────────────────

def _cargar_fecha_vto(db, empresa_id, tipo_vto, fac_numero):
    vto = db.query(Vencimiento).filter(
        Vencimiento.empresa_id == empresa_id,
        Vencimiento.tipo == tipo_vto,
        Vencimiento.tpnumero == fac_numero,
    ).order_by(Vencimiento.fecha).first()
    return vto.fecha if vto else None


def get_facturas_emi(db: Session, empresa_id: int, q: str = "",
                     cliente: int = None, skip: int = 0, limit: int = 50,
                     fecha_desde: str = None, fecha_hasta: str = None,
                     estado: str = None):
    import datetime
    query = db.query(FacturaEmitida).filter(FacturaEmitida.empresa_id == empresa_id)
    if cliente:
        query = query.filter(FacturaEmitida.cliente == cliente)
    if q:
        query = query.filter(FacturaEmitida.cnumalt.like(f"%{q}%"))
    if fecha_desde:
        query = query.filter(FacturaEmitida.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(FacturaEmitida.fecha <= fecha_hasta)
    if estado == 'V':
        hoy = datetime.date.today()
        nums_vencidos = db.query(Vencimiento.tpnumero).filter(
            Vencimiento.empresa_id == empresa_id,
            Vencimiento.tipo == 'F',
            Vencimiento.pendiente > 0,
            Vencimiento.fecha < hoy,
        ).subquery()
        query = query.filter(
            FacturaEmitida.estado == 'P',
            FacturaEmitida.numero.in_(nums_vencidos),
        )
    elif estado in ('P', 'C'):
        query = query.filter(FacturaEmitida.estado == estado)
    total = query.count()
    items = query.order_by(FacturaEmitida.fecha.desc(), FacturaEmitida.numero.desc()) \
                 .offset(skip).limit(limit).all()
    for fac in items:
        fac.pago_info = _cargar_pago_info(db, empresa_id, 'F', fac.numero) if fac.estado == 'C' else None
        fac.fecha_vto = _cargar_fecha_vto(db, empresa_id, 'F', fac.numero) if fac.estado == 'P' else None
    return items, total


def get_factura_emi(db: Session, factura_id: int):
    fac = db.query(FacturaEmitida).filter(FacturaEmitida.id == factura_id).first()
    if fac:
        _lineas(db, fac, TALBARAN_FEMI)
        fac.pago_info = _cargar_pago_info(db, fac.empresa_id, 'F', fac.numero) if fac.estado == 'C' else None
    return fac


def create_factura_emi(db: Session, data: FacturaEmiCreate) -> FacturaEmitida:
    numero = siguiente_numero(db, FacturaEmitida, data.empresa_id)
    tiponum, cnumero = siguiente_cnumero(db, FacturaEmitida, data.empresa_id, data.fecha)

    fac = FacturaEmitida(
        empresa_id=data.empresa_id,
        numero=numero, cnumero=cnumero, tiponum=tiponum,
        fecha=data.fecha, fregistro=data.fecha,
        cliente=data.cliente, clcuenta=data.clcuenta,
        tipoop=data.tipoop, cnumalt=data.cnumalt,
        declterc=data.declterc, ccaja=data.ccaja,
        estado=data.estado or 'P', notas=data.notas,
    )
    db.add(fac)
    db.flush()

    lineas = guardar_lineas(db, data.empresa_id, numero, TALBARAN_FEMI, data.fecha, data.lineas)
    fac.total = total_lineas(lineas)
    fac.totaldecl = fac.total
    _crear_vencimiento(db, data.empresa_id, 'F', numero, data.fecha, fac.total, data.clcuenta)
    cont_svc.generar_asiento_factura_emi(db, data.empresa_id, fac, lineas)
    registrar_operacion(db, data.empresa_id, 'facturas_emitidas', fac.uuid, 'C', data.model_dump(mode='json'))
    db.commit()
    db.refresh(fac)
    _lineas(db, fac, TALBARAN_FEMI)
    fac.pago_info = _cargar_pago_info(db, fac.empresa_id, 'F', fac.numero) if fac.estado == 'C' else None
    return fac


def update_factura_emi(db: Session, factura_id: int, data: FacturaEmiUpdate) -> FacturaEmitida | None:
    fac = db.query(FacturaEmitida).filter(FacturaEmitida.id == factura_id).first()
    if not fac:
        return None
    fecha_anterior = fac.fecha
    campos = data.model_dump(exclude={'lineas'}, exclude_unset=True)
    fac.version = (fac.version or 1) + 1
    for campo, valor in campos.items():
        setattr(fac, campo, valor)

    regenerar = any(c in campos for c in ('clcuenta', 'fecha'))
    lineas_regenerar = None

    vto = None
    if (data.lineas is not None) or ('fecha' in campos and fac.fecha != fecha_anterior):
        vto = db.query(Vencimiento).filter(
            Vencimiento.empresa_id == fac.empresa_id,
            Vencimiento.tipo == 'F',
            Vencimiento.tpnumero == fac.numero,
        ).first()

    # La fecha del vencimiento debe seguir a la de la factura: si no se sincroniza,
    # el vencimiento queda con una fecha obsoleta aunque el asiento sí se regenere.
    if vto and 'fecha' in campos and fac.fecha != fecha_anterior:
        vto.fecha = fac.fecha

    if data.lineas is not None:
        old_total = fac.total or 0
        lineas_regenerar = guardar_lineas(db, fac.empresa_id, fac.numero, TALBARAN_FEMI, fac.fecha, data.lineas)
        fac.total = total_lineas(lineas_regenerar)
        fac.totaldecl = fac.total
        delta = fac.total - old_total
        if delta != 0 and vto:
            _ajustar_vencimiento_delta(db, fac.empresa_id, vto, delta)
        regenerar = True

    if regenerar:
        if lineas_regenerar is None:
            lineas_regenerar = get_lineas(db, fac.empresa_id, fac.numero, TALBARAN_FEMI)
        cont_svc._eliminar_asiento_documento(db, fac.empresa_id, 'F', fac.numero)
        cont_svc.generar_asiento_factura_emi(db, fac.empresa_id, fac, lineas_regenerar)
    else:
        # Auto-reparación: si la factura quedó sin asiento (p. ej. borrado manual
        # desde el Libro Diario), regenerarlo. Idempotente: no duplica si ya existe.
        cont_svc.generar_asiento_factura_emi(
            db, fac.empresa_id, fac, get_lineas(db, fac.empresa_id, fac.numero, TALBARAN_FEMI))

    registrar_operacion(db, fac.empresa_id, 'facturas_emitidas', fac.uuid, 'U',
                        data.model_dump(exclude={'lineas'}, exclude_unset=True, mode='json'))
    db.commit()
    db.refresh(fac)
    _lineas(db, fac, TALBARAN_FEMI)
    fac.pago_info = _cargar_pago_info(db, fac.empresa_id, 'F', fac.numero) if fac.estado == 'C' else None
    return fac


def delete_factura_emi(db: Session, factura_id: int) -> bool:
    fac = db.query(FacturaEmitida).filter(FacturaEmitida.id == factura_id).first()
    if not fac:
        return False
    entidad_uuid, empresa_id = fac.uuid, fac.empresa_id
    # Lanza ValueError si el vencimiento tiene pagos: validar antes de borrar nada
    _borrar_vencimiento(db, fac.empresa_id, 'F', fac.numero)
    db.query(Apunte).filter(
        Apunte.empresa_id == fac.empresa_id,
        Apunte.albaran == fac.numero,
        Apunte.talbaran == TALBARAN_FEMI,
    ).delete()
    cont_svc._eliminar_asiento_documento(db, fac.empresa_id, 'F', fac.numero)
    db.delete(fac)
    registrar_operacion(db, empresa_id, 'facturas_emitidas', entidad_uuid, 'D')
    db.commit()
    return True


# ─── Facturas recibidas ───────────────────────────────────────────────────────

def get_facturas_rec(db: Session, empresa_id: int, q: str = "",
                     proveedor: int = None, skip: int = 0, limit: int = 50,
                     fecha_desde: str = None, fecha_hasta: str = None,
                     estado: str = None):
    import datetime
    query = db.query(FacturaRecibida).filter(FacturaRecibida.empresa_id == empresa_id)
    if proveedor:
        query = query.filter(FacturaRecibida.proveedor == proveedor)
    if q:
        query = query.filter(
            or_(FacturaRecibida.prfactura.like(f"%{q}%"),
                FacturaRecibida.cnumalt.like(f"%{q}%"))
        )
    if fecha_desde:
        query = query.filter(FacturaRecibida.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(FacturaRecibida.fecha <= fecha_hasta)
    if estado == 'V':
        hoy = datetime.date.today()
        nums_vencidos = db.query(Vencimiento.tpnumero).filter(
            Vencimiento.empresa_id == empresa_id,
            Vencimiento.tipo == 'R',
            Vencimiento.pendiente > 0,
            Vencimiento.fecha < hoy,
        ).subquery()
        query = query.filter(
            FacturaRecibida.estado == 'P',
            FacturaRecibida.numero.in_(nums_vencidos),
        )
    elif estado in ('P', 'C'):
        query = query.filter(FacturaRecibida.estado == estado)
    total = query.count()
    items = query.order_by(FacturaRecibida.fecha.desc(), FacturaRecibida.numero.desc()) \
                 .offset(skip).limit(limit).all()
    for fac in items:
        fac.pago_info = _cargar_pago_info(db, empresa_id, 'R', fac.numero) if fac.estado == 'C' else None
        fac.fecha_vto = _cargar_fecha_vto(db, empresa_id, 'R', fac.numero) if fac.estado == 'P' else None
    return items, total


def get_factura_rec(db: Session, factura_id: int):
    fac = db.query(FacturaRecibida).filter(FacturaRecibida.id == factura_id).first()
    if fac:
        _lineas(db, fac, TALBARAN_FREC)
        fac.pago_info = _cargar_pago_info(db, fac.empresa_id, 'R', fac.numero) if fac.estado == 'C' else None
    return fac


def create_factura_rec(db: Session, data: FacturaRecCreate) -> FacturaRecibida:
    if not data.forzar:
        dup = _buscar_duplicado_rec(db, data.empresa_id, data.proveedor, data.prfactura)
        if dup:
            raise FacturaDuplicadaError(dup, _total_previsto(data.lineas))

    numero = siguiente_numero(db, FacturaRecibida, data.empresa_id)
    tiponum, cnumero = siguiente_cnumero(db, FacturaRecibida, data.empresa_id, data.fecha)

    prcuenta = data.prcuenta or ''
    if not prcuenta and data.proveedor:
        from app.models.clientes_proveedores import Proveedor
        prov = db.query(Proveedor).filter(
            Proveedor.empresa_id == data.empresa_id,
            Proveedor.numero == data.proveedor,
        ).first()
        if prov and prov.cuenta:
            prcuenta = prov.cuenta

    fac = FacturaRecibida(
        empresa_id=data.empresa_id,
        numero=numero, cnumero=cnumero, tiponum=tiponum,
        fecha=data.fecha, regfecha=data.fecha,
        proveedor=data.proveedor, prcuenta=prcuenta,
        prfactura=data.prfactura, prfecha=data.prfecha,
        tipoop=data.tipoop, cnumalt=data.cnumalt,
        declterc=data.declterc, ccaja=data.ccaja,
        estado=data.estado or 'P', notas=data.notas,
    )
    db.add(fac)
    db.flush()

    lineas = guardar_lineas(db, data.empresa_id, numero, TALBARAN_FREC, data.fecha, data.lineas)
    fac.total = total_lineas(lineas)
    fac.totaldecl = fac.total
    _crear_vencimiento(db, data.empresa_id, 'R', numero, data.fecha, fac.total, prcuenta)
    cont_svc.generar_asiento_factura_rec(db, data.empresa_id, fac, lineas)
    registrar_operacion(db, data.empresa_id, 'facturas_recibidas', fac.uuid, 'C',
                        data.model_dump(exclude={'forzar'}, mode='json'))
    db.commit()
    db.refresh(fac)
    _lineas(db, fac, TALBARAN_FREC)
    fac.pago_info = _cargar_pago_info(db, fac.empresa_id, 'R', fac.numero) if fac.estado == 'C' else None
    return fac


def update_factura_rec(db: Session, factura_id: int, data: FacturaRecUpdate) -> FacturaRecibida | None:
    fac = db.query(FacturaRecibida).filter(FacturaRecibida.id == factura_id).first()
    if not fac:
        return None
    fecha_anterior = fac.fecha
    campos = data.model_dump(exclude={'lineas', 'forzar'}, exclude_unset=True)

    if not data.forzar:
        proveedor_final = campos.get('proveedor', fac.proveedor)
        prfactura_final = campos.get('prfactura', fac.prfactura)
        dup = _buscar_duplicado_rec(db, fac.empresa_id, proveedor_final, prfactura_final, excluir_id=fac.id)
        if dup:
            total_nuevo = _total_previsto(data.lineas) if data.lineas is not None else fac.total
            raise FacturaDuplicadaError(dup, total_nuevo)

    fac.version = (fac.version or 1) + 1
    for campo, valor in campos.items():
        setattr(fac, campo, valor)

    regenerar = any(c in campos for c in ('prcuenta', 'fecha'))
    lineas_regenerar = None

    vto = None
    if (data.lineas is not None) or ('fecha' in campos and fac.fecha != fecha_anterior):
        vto = db.query(Vencimiento).filter(
            Vencimiento.empresa_id == fac.empresa_id,
            Vencimiento.tipo == 'R',
            Vencimiento.tpnumero == fac.numero,
        ).first()

    # La fecha del vencimiento debe seguir a la de la factura: si no se sincroniza,
    # el vencimiento queda con una fecha obsoleta aunque el asiento sí se regenere.
    if vto and 'fecha' in campos and fac.fecha != fecha_anterior:
        vto.fecha = fac.fecha

    if data.lineas is not None:
        old_total = fac.total or 0
        lineas_regenerar = guardar_lineas(db, fac.empresa_id, fac.numero, TALBARAN_FREC, fac.fecha, data.lineas)
        fac.total = total_lineas(lineas_regenerar)
        fac.totaldecl = fac.total
        delta = fac.total - old_total
        if delta != 0 and vto:
            _ajustar_vencimiento_delta(db, fac.empresa_id, vto, delta)
        regenerar = True

    if regenerar:
        if lineas_regenerar is None:
            lineas_regenerar = get_lineas(db, fac.empresa_id, fac.numero, TALBARAN_FREC)
        cont_svc._eliminar_asiento_documento(db, fac.empresa_id, 'R', fac.numero)
        cont_svc.generar_asiento_factura_rec(db, fac.empresa_id, fac, lineas_regenerar)
    else:
        # Auto-reparación: si la factura quedó sin asiento (p. ej. borrado manual
        # desde el Libro Diario), regenerarlo. Idempotente: no duplica si ya existe.
        cont_svc.generar_asiento_factura_rec(
            db, fac.empresa_id, fac, get_lineas(db, fac.empresa_id, fac.numero, TALBARAN_FREC))

    registrar_operacion(db, fac.empresa_id, 'facturas_recibidas', fac.uuid, 'U',
                        data.model_dump(exclude={'lineas', 'forzar'}, exclude_unset=True, mode='json'))
    db.commit()
    db.refresh(fac)
    _lineas(db, fac, TALBARAN_FREC)
    fac.pago_info = _cargar_pago_info(db, fac.empresa_id, 'R', fac.numero) if fac.estado == 'C' else None
    return fac


def delete_factura_rec(db: Session, factura_id: int) -> bool:
    fac = db.query(FacturaRecibida).filter(FacturaRecibida.id == factura_id).first()
    if not fac:
        return False
    entidad_uuid, empresa_id = fac.uuid, fac.empresa_id
    # Lanza ValueError si el vencimiento tiene pagos: validar antes de borrar nada
    _borrar_vencimiento(db, fac.empresa_id, 'R', fac.numero)
    db.query(Apunte).filter(
        Apunte.empresa_id == fac.empresa_id,
        Apunte.albaran == fac.numero,
        Apunte.talbaran == TALBARAN_FREC,
    ).delete()
    cont_svc._eliminar_asiento_documento(db, fac.empresa_id, 'R', fac.numero)
    db.delete(fac)
    registrar_operacion(db, empresa_id, 'facturas_recibidas', entidad_uuid, 'D')
    db.commit()
    return True


# ─── Renumeración ─────────────────────────────────────────────────────────────

def _renumerar(db: Session, modelo, empresa_id: int, desde_id: int = None) -> int:
    facturas = db.query(modelo).filter(
        modelo.empresa_id == empresa_id
    ).order_by(modelo.fecha.asc(), modelo.id.asc()).all()

    if desde_id:
        idx = next((i for i, f in enumerate(facturas) if f.id == desde_id), None)
        if idx is None:
            return 0
        year = facturas[idx].fecha.year if facturas[idx].fecha else 2000
        # cnumero de arranque = cuántas facturas del mismo año hay antes de idx
        start = sum(1 for f in facturas[:idx] if f.fecha and f.fecha.year == year)
        to_renumber = [f for f in facturas[idx:] if f.fecha and f.fecha.year == year]
        for i, f in enumerate(to_renumber):
            f.cnumero = start + i + 1
        count = len(to_renumber)
    else:
        counters = {}
        for f in facturas:
            year = f.fecha.year if f.fecha else 2000
            counters[year] = counters.get(year, 0) + 1
            f.cnumero = counters[year]
        count = len(facturas)

    db.commit()
    return count


def renumerar_facturas_emi(db: Session, empresa_id: int, desde_id: int = None) -> int:
    return _renumerar(db, FacturaEmitida, empresa_id, desde_id)


def renumerar_facturas_rec(db: Session, empresa_id: int, desde_id: int = None) -> int:
    return _renumerar(db, FacturaRecibida, empresa_id, desde_id)
