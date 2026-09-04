from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.bancos import Banco, MovBanco, Pago
from app.models.clientes_proveedores import Vencimiento
from app.models.facturacion import FacturaEmitida, FacturaRecibida
from app.schemas.bancos import BancoCreate, BancoUpdate, MovimientoCreate, MovimientoUpdate, VencimientoCreate, VencimientoUpdate
from app.services import contabilidad as cont_svc
import datetime


def siguiente_numero_vencimiento(db: Session, empresa_id: int) -> int:
    """Siguiente número de vencimiento para la empresa.
    Considera también los pagos que referencian vencimientos ya borrados: si se
    reutilizara uno de esos números, el vencimiento nuevo 'heredaría' pagos de un
    documento distinto y nacería total o parcialmente pagado."""
    max_vto = db.query(func.max(Vencimiento.numero)).filter(
        Vencimiento.empresa_id == empresa_id,
    ).scalar() or 0
    max_pago = db.query(func.max(Pago.vto)).filter(
        Pago.empresa_id == empresa_id,
        Pago.vto.isnot(None),
    ).scalar() or 0
    return max(int(max_vto), int(max_pago)) + 1


def _aplicar_pago_pendiente(vto, importe_pago):
    """Reduce el pendiente del vencimiento en la magnitud del pago, hacia 0.
    Respeta el signo: los abonos (importe negativo) tienen pendiente negativo y
    también deben poder compensarse hasta 0."""
    base = float(vto.pendiente if vto.pendiente is not None else (vto.importe or 0))
    signo = -1 if base < 0 else 1
    restante = max(0.0, abs(base) - abs(float(importe_pago or 0)))
    vto.pendiente = round(signo * restante, 2)


def _restaurar_pendiente(vto, importe_pago):
    """Devuelve el pago al pendiente sin superar la magnitud del importe.
    Simétrico a `_aplicar_pago_pendiente` (que recorta a 0): al revertir un pago
    mayor que el pendiente hay que recortar también por arriba. Respeta el signo
    de los abonos."""
    tope = abs(float(vto.importe or 0))
    signo = -1 if float(vto.importe or 0) < 0 else 1
    nuevo = abs(float(vto.pendiente or 0)) + abs(float(importe_pago or 0))
    if tope > 0:
        nuevo = min(nuevo, tope)
    vto.pendiente = round(signo * nuevo, 2)


def _sync_estado_factura(db, empresa_id, vto):
    """Sincroniza el estado de la factura según si el vencimiento está pagado o no."""
    if vto is None:
        return
    # Pagado = pendiente a 0 en magnitud (los abonos tienen pendiente negativo)
    pagado = abs(vto.pendiente or 0) < 0.005
    if vto.tipo == 'R':
        fac = db.query(FacturaRecibida).filter(
            FacturaRecibida.empresa_id == empresa_id,
            FacturaRecibida.numero == vto.tpnumero,
        ).first()
        if fac:
            fac.estado = 'C' if pagado else 'P'
    elif vto.tipo == 'F':
        fac = db.query(FacturaEmitida).filter(
            FacturaEmitida.empresa_id == empresa_id,
            FacturaEmitida.numero == vto.tpnumero,
        ).first()
        if fac:
            fac.estado = 'C' if pagado else 'P'
    elif vto.tipo == 'X':
        from app.models.contabilidad import Extra
        extra = db.query(Extra).filter(
            Extra.empresa_id == empresa_id,
            Extra.numero == vto.tpnumero,
        ).first()
        if extra:
            extra.estado = 'C' if pagado else 'P'


# ─── Bancos ──────────────────────────────────────────────────────────────────

def get_bancos(db: Session, empresa_id: int):
    return db.query(Banco).filter(
        Banco.empresa_id == empresa_id
    ).order_by(Banco.numero).all()


def get_banco(db: Session, banco_id: int):
    return db.query(Banco).filter(Banco.id == banco_id).first()


def create_banco(db: Session, data: BancoCreate) -> Banco:
    ultimo = db.query(func.max(Banco.numero)).filter(
        Banco.empresa_id == data.empresa_id
    ).scalar() or 0
    banco = Banco(
        **data.model_dump(exclude={'saldoini'}),
        numero=ultimo + 1,
        saldoini=data.saldoini or 0,
        saldoact=0,
    )
    db.add(banco)
    db.commit()
    db.refresh(banco)
    return banco


def update_banco(db: Session, banco_id: int, data: BancoUpdate) -> Banco | None:
    banco = get_banco(db, banco_id)
    if not banco:
        return None

    nuevo_numero = data.numero
    old_numero = banco.numero

    if nuevo_numero is not None and nuevo_numero != old_numero:
        conflicto = db.query(Banco).filter(
            Banco.empresa_id == banco.empresa_id,
            Banco.numero == nuevo_numero,
            Banco.id != banco_id,
        ).first()
        if conflicto:
            raise ValueError(f"Ya existe una cuenta con el número {nuevo_numero}")
        db.query(MovBanco).filter(
            MovBanco.empresa_id == banco.empresa_id,
            MovBanco.banco == old_numero,
        ).update({'banco': nuevo_numero})
        db.query(Pago).filter(
            Pago.empresa_id == banco.empresa_id,
            Pago.banco == old_numero,
        ).update({'banco': nuevo_numero})
        db.query(Pago).filter(
            Pago.empresa_id == banco.empresa_id,
            Pago.bancot == old_numero,
        ).update({'bancot': nuevo_numero})
        # Actualizar los asientos generados por este banco: los chequeos de
        # "asiento propio" y la conciliación emparejan por tpasiento='B{numero}'
        from app.models.contabilidad import Diario
        db.query(Diario).filter(
            Diario.empresa_id == banco.empresa_id,
            Diario.tpasiento == f'B{old_numero}',
        ).update({'tpasiento': f'B{nuevo_numero}'})

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(banco, campo, valor)
    db.commit()
    db.refresh(banco)
    return banco


def delete_banco(db: Session, banco_id: int) -> bool:
    banco = get_banco(db, banco_id)
    if not banco:
        return False
    n_movs = db.query(MovBanco).filter(
        MovBanco.empresa_id == banco.empresa_id,
        MovBanco.banco == banco.numero,
    ).count()
    if n_movs:
        raise ValueError(
            f"No se puede eliminar el banco '{banco.nombre}': tiene {n_movs} movimientos. "
            "Elimina primero sus movimientos."
        )
    db.delete(banco)
    db.commit()
    return True


# ─── Movimientos ──────────────────────────────────────────────────────────────

def get_movimientos(db: Session, empresa_id: int, banco: int = None,
                    skip: int = 0, limit: int = 50,
                    solo_no_conciliados: bool = False):
    from sqlalchemy import or_
    query = db.query(MovBanco).filter(MovBanco.empresa_id == empresa_id)
    if banco is not None:
        query = query.filter(MovBanco.banco == banco)
    if solo_no_conciliados:
        # Filtrar en servidor: hacerlo en cliente tras paginar dejaba páginas
        # incompletas y un contador total incorrecto
        query = query.filter(or_(MovBanco.conciliado.is_(None),
                                 MovBanco.conciliado == False))  # noqa: E712
    total = query.count()
    items = query.order_by(MovBanco.fecha.asc(), MovBanco.numero.asc()) \
                 .offset(skip).limit(limit).all()
    # Pagos de toda la página en una sola consulta (antes: una por movimiento)
    if items:
        from collections import defaultdict
        pagos_pagina = db.query(Pago).filter(
            Pago.empresa_id == empresa_id,
            Pago.banco.in_({m.banco for m in items}),
            Pago.numero.in_({m.numero for m in items}),
        ).all()
        por_mov = defaultdict(list)
        for p in pagos_pagina:
            por_mov[(p.banco, p.numero)].append(p)
        for mov in items:
            mov.pagos = por_mov.get((mov.banco, mov.numero), [])
    return items, total


def get_movimiento(db: Session, mov_id: int):
    mov = db.query(MovBanco).filter(MovBanco.id == mov_id).first()
    if mov:
        mov.pagos = db.query(Pago).filter(
            Pago.empresa_id == mov.empresa_id,
            Pago.banco == mov.banco,
            Pago.numero == mov.numero,
        ).all()
    return mov


def _find_counterpart(db, empresa_id, pd, banco_origen, numero_origen):
    """Localiza el movimiento espejo de una transferencia."""
    if pd is None:
        return None
    mov_contra = None
    if pd.numerot:
        mov_contra = db.query(MovBanco).filter(
            MovBanco.empresa_id == empresa_id,
            MovBanco.banco == pd.bancot,
            MovBanco.numero == pd.numerot,
        ).first()
    if mov_contra is None:
        pago_rev = db.query(Pago).filter(
            Pago.empresa_id == empresa_id,
            Pago.banco == pd.bancot,
            Pago.bancot == banco_origen,
            Pago.numerot == numero_origen,
        ).first()
        if pago_rev:
            mov_contra = db.query(MovBanco).filter(
                MovBanco.empresa_id == empresa_id,
                MovBanco.banco == pd.bancot,
                MovBanco.numero == pago_rev.numero,
            ).first()
    return mov_contra


def _crear_mov_contraparte(db, empresa_id, banco_origen, numero_origen,
                           dest_banco, fecha, texto, importe_dest, notas, estado):
    """Crea el movimiento espejo en el banco destino de una transferencia."""
    ultimo = db.query(func.max(MovBanco.numero)).filter(
        MovBanco.empresa_id == empresa_id,
        MovBanco.banco == dest_banco,
    ).scalar() or 0

    saldo_prev = float(db.query(MovBanco.saldonue).filter(
        MovBanco.empresa_id == empresa_id,
        MovBanco.banco == dest_banco,
        MovBanco.numero <= ultimo,
    ).order_by(MovBanco.numero.desc()).limit(1).scalar() or 0)

    tiponum, cnumero = _cnumero_mov(db, empresa_id, dest_banco, fecha, importe_dest)

    mov = MovBanco(
        empresa_id=empresa_id,
        banco=dest_banco,
        numero=ultimo + 1,
        cnumero=cnumero,
        tiponum=tiponum,
        fecha=fecha,
        texto=texto,
        total=importe_dest,
        saldonue=round(saldo_prev + importe_dest, 2),
        clave='ZZZ',
        notas=notas,
        estado=estado,
    )
    db.add(mov)
    db.flush()

    banco_obj = db.query(Banco).filter(
        Banco.empresa_id == empresa_id,
        Banco.numero == dest_banco,
    ).first()
    if banco_obj:
        banco_obj.saldoact = round(float(banco_obj.saldoact or 0) + importe_dest, 2)

    db.add(Pago(
        empresa_id=empresa_id,
        banco=dest_banco,
        numero=mov.numero,
        importe=importe_dest,
        bancot=banco_origen,
        numerot=numero_origen,
    ))
    return mov


def _cnumero_mov(db, empresa_id, banco, fecha, total):
    anio = fecha.year
    tiponum = 'I' if total >= 0 else 'O'
    fecha_ini = datetime.date(anio, 1, 1)
    fecha_fin = datetime.date(anio, 12, 31)
    ultimo = db.query(func.max(MovBanco.cnumero)).filter(
        MovBanco.empresa_id == empresa_id,
        MovBanco.banco == banco,
        MovBanco.tiponum == tiponum,
        MovBanco.fecha >= fecha_ini,
        MovBanco.fecha <= fecha_fin,
    ).scalar() or 0
    return tiponum, ultimo + 1


def create_movimiento(db: Session, data: MovimientoCreate) -> MovBanco:
    ultimo = db.query(func.max(MovBanco.numero)).filter(
        MovBanco.empresa_id == data.empresa_id,
        MovBanco.banco == data.banco,
    ).scalar() or 0

    tiponum, cnumero = _cnumero_mov(db, data.empresa_id, data.banco, data.fecha, data.total)

    # Saldo anterior
    saldo_prev = db.query(MovBanco.saldonue).filter(
        MovBanco.empresa_id == data.empresa_id,
        MovBanco.banco == data.banco,
        MovBanco.numero < ultimo + 1,
    ).order_by(MovBanco.numero.desc()).limit(1).scalar()

    if saldo_prev is None:
        saldo_prev = 0.0

    saldonue = round(float(saldo_prev or 0) + data.total, 2)

    mov = MovBanco(
        empresa_id=data.empresa_id,
        banco=data.banco,
        numero=ultimo + 1,
        cnumero=cnumero,
        tiponum=tiponum,
        fecha=data.fecha,
        texto=data.texto,
        total=data.total,
        saldonue=saldonue,
        clave=data.clave or 'ZZZ',
        notas=data.notas,
        estado=data.estado,
    )
    db.add(mov)
    db.flush()

    # Actualizar saldo del banco
    banco_obj = db.query(Banco).filter(
        Banco.empresa_id == data.empresa_id,
        Banco.numero == data.banco,
    ).first()
    if banco_obj:
        banco_obj.saldoact = round(float(banco_obj.saldoact or 0) + data.total, 2)

    # Pagos asociados
    for pd in data.pagos:
        pago = Pago(
            empresa_id=data.empresa_id,
            banco=data.banco,
            numero=mov.numero,
            importe=pd.importe,
            vto=pd.vto,
            dirsubcta=pd.dirsubcta,
            declterc=pd.declterc,
            bancot=pd.bancot,
        )
        db.add(pago)
        db.flush()

        # Transferencia a otro banco: crear movimiento espejo
        if pd.bancot:
            mov_contra = _crear_mov_contraparte(
                db,
                empresa_id=data.empresa_id,
                banco_origen=data.banco,
                numero_origen=mov.numero,
                dest_banco=pd.bancot,
                fecha=data.fecha,
                texto=data.texto,
                importe_dest=round(-pd.importe, 2),
                notas=data.notas,
                estado=data.estado,
            )
            pago.numerot = mov_contra.numero

        # Si tiene vencimiento, reducir pendiente
        if pd.vto:
            vto = db.query(Vencimiento).filter(
                Vencimiento.empresa_id == data.empresa_id,
                Vencimiento.numero == pd.vto,
            ).first()
            if vto:
                _aplicar_pago_pendiente(vto, pd.importe)
                _sync_estado_factura(db, data.empresa_id, vto)

    # Generar asiento contable (no para contrapartes de transferencias)
    todos_pagos = db.query(Pago).filter(
        Pago.empresa_id == data.empresa_id,
        Pago.banco == data.banco,
        Pago.numero == mov.numero,
    ).all()
    cont_svc.generar_asiento_banco(db, data.empresa_id, mov, banco_obj, todos_pagos)

    # Recalcular saldos en orden (fecha, numero) — igual que la pantalla
    bancos_a_recalc = {data.banco}
    for pd in data.pagos:
        if pd.bancot:
            bancos_a_recalc.add(pd.bancot)
    for banco_num in bancos_a_recalc:
        _recalcular_saldos(db, data.empresa_id, banco_num)

    db.commit()
    db.refresh(mov)
    mov.pagos = db.query(Pago).filter(
        Pago.empresa_id == data.empresa_id,
        Pago.banco == mov.banco,
        Pago.numero == mov.numero,
    ).all()
    return mov


def _recalcular_saldos(db, empresa_id, banco_num):
    """Recalcula saldonue de TODOS los movimientos del banco en orden (fecha, numero)
    — igual que la pantalla — y actualiza saldoact."""
    movs = db.query(MovBanco).filter(
        MovBanco.empresa_id == empresa_id,
        MovBanco.banco == banco_num,
    ).order_by(MovBanco.fecha, MovBanco.numero).all()
    saldo = 0.0
    for m in movs:
        saldo = round(saldo + float(m.total or 0), 2)
        m.saldonue = saldo
    banco_obj = db.query(Banco).filter(
        Banco.empresa_id == empresa_id,
        Banco.numero == banco_num,
    ).first()
    if banco_obj:
        banco_obj.saldoact = saldo


def update_movimiento(db: Session, mov_id: int, data: MovimientoUpdate) -> MovBanco | None:
    mov = db.query(MovBanco).filter(MovBanco.id == mov_id).first()
    if not mov:
        return None

    total_anterior = float(mov.total or 0)
    fecha_anterior = mov.fecha
    clave_anterior = mov.clave
    empresa_id = mov.empresa_id
    banco_num = mov.banco

    for campo in ('fecha', 'texto', 'clave', 'notas', 'estado'):
        val = getattr(data, campo, None)
        if val is not None:
            setattr(mov, campo, val)
    if getattr(data, 'conciliado', None) is not None:
        mov.conciliado = data.conciliado

    # Solo regenerar el asiento si cambió algo que se refleja en él (importe, pagos,
    # fecha o clave): regenerarlo en cada guardado renumeraba el asiento sin motivo
    cambio_contable = (
        data.pagos is not None
        or (data.total is not None and round(float(data.total), 2) != round(total_anterior, 2))
        or (data.fecha is not None and data.fecha != fecha_anterior)
        or (data.clave is not None and data.clave != clave_anterior)
    )

    if data.total is not None:
        diff = data.total - total_anterior
        mov.total = data.total
        banco_obj = db.query(Banco).filter(
            Banco.empresa_id == empresa_id,
            Banco.numero == banco_num,
        ).first()
        if banco_obj:
            banco_obj.saldoact = round(float(banco_obj.saldoact or 0) + diff, 2)
        _recalcular_saldos(db, empresa_id, banco_num)

    if data.pagos is not None:
        old_pagos = db.query(Pago).filter(
            Pago.empresa_id == empresa_id,
            Pago.banco == banco_num,
            Pago.numero == mov.numero,
        ).all()

        # Bancos destino que siguen existiendo en los nuevos pagos
        new_bancots = {pd.bancot for pd in data.pagos if pd.bancot}
        # Mapa bancot → pago antiguo (para reutilizar contraparte)
        old_transfer_map = {pd.bancot: pd for pd in old_pagos if pd.bancot}

        # Paso 1: restaurar vencimientos y tratar contrapartes de pagos eliminados
        for pd in old_pagos:
            if pd.vto:
                vto = db.query(Vencimiento).filter(
                    Vencimiento.empresa_id == empresa_id,
                    Vencimiento.numero == pd.vto,
                ).first()
                if vto:
                    _restaurar_pendiente(vto, pd.importe)
                    _sync_estado_factura(db, empresa_id, vto)
            if pd.bancot and pd.bancot not in new_bancots:
                # El banco destino desaparece: eliminar contraparte
                mov_contra = _find_counterpart(db, empresa_id, pd, banco_num, mov.numero)
                if mov_contra:
                    banco_contra = db.query(Banco).filter(
                        Banco.empresa_id == empresa_id,
                        Banco.numero == pd.bancot,
                    ).first()
                    if banco_contra:
                        banco_contra.saldoact = round(float(banco_contra.saldoact or 0) - float(mov_contra.total), 2)
                    numero_desde = mov_contra.numero
                    db.query(Pago).filter(
                        Pago.empresa_id == empresa_id,
                        Pago.banco == pd.bancot,
                        Pago.numero == mov_contra.numero,
                    ).delete()
                    db.delete(mov_contra)
                    db.flush()
                    _recalcular_saldos(db, empresa_id, pd.bancot)
            db.delete(pd)
        db.flush()

        # Paso 2: crear nuevos pagos; actualizar contraparte si ya existía, crear si no
        for pd in data.pagos:
            pago = Pago(
                empresa_id=empresa_id,
                banco=banco_num,
                numero=mov.numero,
                importe=pd.importe,
                vto=pd.vto,
                dirsubcta=pd.dirsubcta,
                declterc=pd.declterc,
                bancot=pd.bancot,
            )
            db.add(pago)
            db.flush()

            if pd.bancot:
                old_pd = old_transfer_map.get(pd.bancot)
                mov_contra = _find_counterpart(db, empresa_id, old_pd, banco_num, mov.numero) if old_pd else None

                if mov_contra:
                    # Actualizar movimiento espejo existente sin eliminarlo
                    new_total = round(-float(pd.importe), 2)
                    diff_contra = new_total - float(mov_contra.total or 0)
                    mov_contra.total = new_total
                    mov_contra.fecha = mov.fecha
                    mov_contra.texto = mov.texto
                    mov_contra.notas = mov.notas
                    mov_contra.estado = mov.estado
                    banco_contra = db.query(Banco).filter(
                        Banco.empresa_id == empresa_id,
                        Banco.numero == pd.bancot,
                    ).first()
                    if banco_contra:
                        banco_contra.saldoact = round(float(banco_contra.saldoact or 0) + diff_contra, 2)
                    pago_contra = db.query(Pago).filter(
                        Pago.empresa_id == empresa_id,
                        Pago.banco == pd.bancot,
                        Pago.numero == mov_contra.numero,
                    ).first()
                    if pago_contra:
                        pago_contra.importe = new_total
                    pago.numerot = mov_contra.numero
                    db.flush()
                    _recalcular_saldos(db, empresa_id, pd.bancot)
                else:
                    # Banco destino nuevo: crear contraparte
                    mov_contra = _crear_mov_contraparte(
                        db,
                        empresa_id=empresa_id,
                        banco_origen=banco_num,
                        numero_origen=mov.numero,
                        dest_banco=pd.bancot,
                        fecha=mov.fecha,
                        texto=mov.texto,
                        importe_dest=round(-float(pd.importe), 2),
                        notas=mov.notas,
                        estado=mov.estado,
                    )
                    pago.numerot = mov_contra.numero

            if pd.vto:
                vto = db.query(Vencimiento).filter(
                    Vencimiento.empresa_id == empresa_id,
                    Vencimiento.numero == pd.vto,
                ).first()
                if vto:
                    _aplicar_pago_pendiente(vto, pd.importe)
                    _sync_estado_factura(db, empresa_id, vto)

    # Regenerar asiento contable solo si hubo cambio contable, o generarlo si falta
    # (auto-reparación de movimientos que quedaron sin asiento)
    banco_obj_reload = db.query(Banco).filter(
        Banco.empresa_id == empresa_id,
        Banco.numero == banco_num,
    ).first()
    if banco_obj_reload and banco_obj_reload.cuenta:
        todos_pagos = db.query(Pago).filter(
            Pago.empresa_id == empresa_id,
            Pago.banco == banco_num,
            Pago.numero == mov.numero,
        ).all()
        if cambio_contable:
            cont_svc.regenerar_asiento_banco(db, empresa_id, mov, banco_obj_reload, todos_pagos)
        elif not cont_svc._ya_tiene_asiento_banco(
                db, empresa_id, banco_obj_reload.cuenta, mov.numero, banco_num,
                fecha=mov.fecha, importe=float(mov.total or 0)):
            cont_svc.generar_asiento_banco(db, empresa_id, mov, banco_obj_reload, todos_pagos)

    db.commit()
    db.refresh(mov)
    mov.pagos = db.query(Pago).filter(
        Pago.empresa_id == empresa_id,
        Pago.banco == banco_num,
        Pago.numero == mov.numero,
    ).all()
    return mov


def delete_movimiento(db: Session, mov_id: int) -> bool:
    mov = db.query(MovBanco).filter(MovBanco.id == mov_id).first()
    if not mov:
        return False

    empresa_id = mov.empresa_id
    banco_num  = mov.banco
    numero_mov = mov.numero

    # Revertir pagos sobre vencimientos y eliminar movimientos espejo
    pagos = db.query(Pago).filter(
        Pago.empresa_id == empresa_id,
        Pago.banco == banco_num,
        Pago.numero == numero_mov,
    ).all()
    contrapartes_a_recalcular = []  # (empresa_id, banco_num, numero)
    for pd in pagos:
        if pd.vto:
            vto = db.query(Vencimiento).filter(
                Vencimiento.empresa_id == empresa_id,
                Vencimiento.numero == pd.vto,
            ).first()
            if vto:
                _restaurar_pendiente(vto, pd.importe)
                _sync_estado_factura(db, empresa_id, vto)

        # Eliminar movimiento espejo si existe
        if pd.bancot and pd.numerot:
            mov_contra = db.query(MovBanco).filter(
                MovBanco.empresa_id == empresa_id,
                MovBanco.banco == pd.bancot,
                MovBanco.numero == pd.numerot,
            ).first()
            if mov_contra:
                numero_contra = mov_contra.numero
                bancot_num = pd.bancot
                # Si el espejo es el ORIGEN de la transferencia (borramos desde el lado
                # receptor), el asiento está numerado con SU número: eliminarlo también
                banco_contra_obj = db.query(Banco).filter(
                    Banco.empresa_id == empresa_id,
                    Banco.numero == bancot_num,
                ).first()
                if banco_contra_obj and banco_contra_obj.cuenta:
                    cont_svc._eliminar_asiento_banco(
                        db, empresa_id, banco_contra_obj.cuenta, numero_contra, bancot_num)
                db.query(Pago).filter(
                    Pago.empresa_id == empresa_id,
                    Pago.banco == bancot_num,
                    Pago.numero == numero_contra,
                ).delete()
                db.delete(mov_contra)
                db.flush()
                contrapartes_a_recalcular.append((empresa_id, bancot_num, numero_contra))

        db.delete(pd)

    # Eliminar asiento contable asociado (filtrando por banco propio para no borrar
    # asientos de otro banco que compartan número de movimiento)
    banco_obj = db.query(Banco).filter(
        Banco.empresa_id == empresa_id,
        Banco.numero == banco_num,
    ).first()
    if banco_obj and banco_obj.cuenta:
        cont_svc._eliminar_asiento_banco(db, empresa_id, banco_obj.cuenta, numero_mov, banco_num)

    db.delete(mov)
    db.flush()

    # Recalcular saldos del banco principal y de contrapartes
    _recalcular_saldos(db, empresa_id, banco_num)
    for emp_id, b_num, num in contrapartes_a_recalcular:
        _recalcular_saldos(db, emp_id, b_num)

    db.commit()
    return True


# ─── Reordenar movimientos ────────────────────────────────────────────────────

def reordenar_movimiento(db: Session, mov_id: int, direccion: str) -> MovBanco | None:
    """Intercambia el número de orden con el movimiento adyacente de la misma fecha."""
    from app.models.contabilidad import Diario as DiarioModel

    mov = db.query(MovBanco).filter(MovBanco.id == mov_id).first()
    if not mov:
        return None

    empresa_id = mov.empresa_id
    banco_num = mov.banco
    fecha = mov.fecha

    if direccion == 'arriba':
        adj = db.query(MovBanco).filter(
            MovBanco.empresa_id == empresa_id,
            MovBanco.banco == banco_num,
            MovBanco.fecha == fecha,
            MovBanco.numero < mov.numero,
        ).order_by(MovBanco.numero.desc()).first()
    else:
        adj = db.query(MovBanco).filter(
            MovBanco.empresa_id == empresa_id,
            MovBanco.banco == banco_num,
            MovBanco.fecha == fecha,
            MovBanco.numero > mov.numero,
        ).order_by(MovBanco.numero.asc()).first()

    if not adj:
        return mov  # ya está en el extremo

    num_a = mov.numero
    num_b = adj.numero
    TEMP = 999999999

    # Cuenta contable del banco (para actualizar asientos del Diario)
    banco_obj = db.query(Banco).filter(
        Banco.empresa_id == empresa_id,
        Banco.numero == banco_num,
    ).first()
    banco_cuenta = banco_obj.cuenta if banco_obj else None

    def _update_diario(de, a):
        """Renumera el asiento del movimiento: TODAS sus líneas (banco y contrapartida),
        anclando por la línea del banco propio para no tocar asientos de otro banco
        que compartan número de movimiento."""
        if not banco_cuenta:
            return
        own_tp = f'B{banco_num}'
        anchors = db.query(DiarioModel).filter(
            DiarioModel.empresa_id == empresa_id,
            DiarioModel.tipo == 'B',
            DiarioModel.cuenta == banco_cuenta,
            DiarioModel.numero == de,
        ).all()
        asientos = []
        for l in anchors:
            tp = l.tpasiento or ''
            # Propio ('B{n}') o migrado/manual ('M', 'EXT', None…); nunca de otro banco
            if tp == own_tp or not (tp.startswith('B') and tp[1:].isdigit()):
                asientos.append(l.asiento)
        if asientos:
            db.query(DiarioModel).filter(
                DiarioModel.empresa_id == empresa_id,
                DiarioModel.asiento.in_(asientos),
                DiarioModel.numero == de,
            ).update({'numero': a}, synchronize_session=False)

    # Paso 1: mov → TEMP
    mov.numero = TEMP
    db.query(Pago).filter(Pago.empresa_id == empresa_id, Pago.banco == banco_num, Pago.numero == num_a).update({'numero': TEMP})
    db.query(Pago).filter(Pago.empresa_id == empresa_id, Pago.bancot == banco_num, Pago.numerot == num_a).update({'numerot': TEMP})
    _update_diario(num_a, TEMP)
    db.flush()

    # Paso 2: adj → num_a
    adj.numero = num_a
    db.query(Pago).filter(Pago.empresa_id == empresa_id, Pago.banco == banco_num, Pago.numero == num_b).update({'numero': num_a})
    db.query(Pago).filter(Pago.empresa_id == empresa_id, Pago.bancot == banco_num, Pago.numerot == num_b).update({'numerot': num_a})
    _update_diario(num_b, num_a)
    db.flush()

    # Paso 3: TEMP → num_b
    mov.numero = num_b
    db.query(Pago).filter(Pago.empresa_id == empresa_id, Pago.banco == banco_num, Pago.numero == TEMP).update({'numero': num_b})
    db.query(Pago).filter(Pago.empresa_id == empresa_id, Pago.bancot == banco_num, Pago.numerot == TEMP).update({'numerot': num_b})
    _update_diario(TEMP, num_b)
    db.flush()

    _recalcular_saldos(db, empresa_id, banco_num)
    db.commit()
    db.refresh(mov)
    mov.pagos = db.query(Pago).filter(
        Pago.empresa_id == empresa_id,
        Pago.banco == banco_num,
        Pago.numero == mov.numero,
    ).all()
    return mov


def reparar_saldos_banco(db: Session, banco_id: int) -> Banco | None:
    """Recalcula saldonue de todos los movimientos y sincroniza saldoact."""
    banco = get_banco(db, banco_id)
    if not banco:
        return None
    _recalcular_saldos(db, banco.empresa_id, banco.numero)
    db.commit()
    db.refresh(banco)
    return banco


# ─── Vencimientos ─────────────────────────────────────────────────────────────

def get_vencimientos(db: Session, empresa_id: int, tipo: str = None,
                     solo_pendientes: bool = False, skip: int = 0, limit: int = 100):
    query = db.query(Vencimiento).filter(Vencimiento.empresa_id == empresa_id)
    if tipo:
        query = query.filter(Vencimiento.tipo == tipo)
    if solo_pendientes:
        # Pendiente en magnitud: incluye abonos (pendiente negativo) sin compensar
        query = query.filter(func.abs(Vencimiento.pendiente) > 0.004)
    total = query.count()
    items = query.order_by(Vencimiento.fecha).offset(skip).limit(limit).all()
    return items, total


def get_vencimiento(db: Session, vto_id: int):
    return db.query(Vencimiento).filter(Vencimiento.id == vto_id).first()


def create_vencimiento(db: Session, data: VencimientoCreate) -> Vencimiento:
    vto = Vencimiento(
        **data.model_dump(),
        numero=siguiente_numero_vencimiento(db, data.empresa_id),
        pendiente=data.importe,
    )
    db.add(vto)
    db.commit()
    db.refresh(vto)
    return vto


def update_vencimiento(db: Session, vto_id: int, data: VencimientoUpdate) -> Vencimiento | None:
    vto = get_vencimiento(db, vto_id)
    if not vto:
        return None
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(vto, campo, valor)
    db.commit()
    db.refresh(vto)
    return vto
