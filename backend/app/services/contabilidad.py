from collections import defaultdict
import time
import logging
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_
from app.models.contabilidad import Cuenta, Diario
from app.schemas.contabilidad import CuentaCreate, CuentaUpdate, AsientoCreate
from app.services.sync import registrar_operacion
import datetime

logger = logging.getLogger(__name__)


# ─── Plan de cuentas ─────────────────────────────────────────────────────────

def get_cuentas(db: Session, empresa_id: int, q: str = None, skip: int = 0, limit: int = 100, solo_con_saldo: bool = False):
    from sqlalchemy import text as _text
    # Calcular debe/haber desde diario (fuente de verdad) para evitar que la caché de cuentas quede desfasada
    where_q = ""
    params: dict = {"e": empresa_id}
    if q:
        where_q = " AND (c.cuenta LIKE :q_code OR LOWER(c.texto) LIKE LOWER(:q_text))"
        params["q_code"] = f"{q}%"
        params["q_text"] = f"%{q}%"

    # solo_con_saldo: filtrar en subquery exterior para evitar HAVING sin GROUP BY (SQLite)
    where_saldo = " AND ABS(COALESCE(d.debe,0) - COALESCE(d.haber,0)) > 0.004" if solo_con_saldo else ""

    agg_subq = """
        LEFT JOIN (
            SELECT cuenta,
                   ROUND(SUM(CASE WHEN importe>0 THEN importe ELSE 0 END),2) AS debe,
                   ROUND(SUM(CASE WHEN importe<0 THEN ABS(importe) ELSE 0 END),2) AS haber
            FROM diario WHERE empresa_id=:e GROUP BY cuenta
        ) d ON d.cuenta = c.cuenta"""

    sql_count = _text(f"""
        SELECT COUNT(*) FROM cuentas c
        {agg_subq}
        WHERE c.empresa_id=:e{where_q}{where_saldo}
    """)
    total = db.execute(sql_count, params).scalar() or 0

    sql_items = _text(f"""
        SELECT c.id, c.empresa_id, c.cuenta, c.texto, c.marca,
               COALESCE(d.debe,0)  AS debe,
               COALESCE(d.haber,0) AS haber
        FROM cuentas c
        {agg_subq}
        WHERE c.empresa_id=:e{where_q}{where_saldo}
        ORDER BY c.cuenta
        LIMIT :lim OFFSET :off
    """)
    params["lim"] = limit
    params["off"] = skip
    rows = db.execute(sql_items, params).fetchall()
    items = [
        {"id": r[0], "empresa_id": r[1], "cuenta": r[2], "texto": r[3],
         "marca": r[4], "debe": r[5] or 0, "haber": r[6] or 0}
        for r in rows
    ]
    return items, total


def get_cuenta(db: Session, cuenta_id: int):
    return db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()


def create_cuenta(db: Session, data: CuentaCreate) -> Cuenta:
    c = Cuenta(**data.model_dump())
    db.add(c)
    db.flush()
    registrar_operacion(db, data.empresa_id, 'cuentas', c.uuid, 'C', data.model_dump(mode='json'))
    db.commit()
    db.refresh(c)
    return c


def update_cuenta(db: Session, cuenta_id: int, data: CuentaUpdate) -> Cuenta | None:
    c = get_cuenta(db, cuenta_id)
    if not c:
        return None
    c.version = (c.version or 1) + 1
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    registrar_operacion(db, c.empresa_id, 'cuentas', c.uuid, 'U',
                        data.model_dump(exclude_unset=True, mode='json'))
    db.commit()
    db.refresh(c)
    return c


def delete_cuenta(db: Session, cuenta_id: int) -> bool:
    c = get_cuenta(db, cuenta_id)
    if not c:
        return False
    n_apuntes = db.query(Diario).filter(
        Diario.empresa_id == c.empresa_id,
        Diario.cuenta == c.cuenta,
    ).count()
    if n_apuntes:
        raise ValueError(
            f"No se puede eliminar la cuenta {c.cuenta}: tiene {n_apuntes} apuntes en el diario."
        )
    entidad_uuid, empresa_id = c.uuid, c.empresa_id
    db.delete(c)
    registrar_operacion(db, empresa_id, 'cuentas', entidad_uuid, 'D')
    db.commit()
    return True


# ─── Asientos del diario ──────────────────────────────────────────────────────

def _siguiente_asiento(db: Session, empresa_id: int) -> int:
    """Siguiente número de asiento con protección contra race conditions."""
    from sqlalchemy.exc import IntegrityError
    for intento in range(5):
        try:
            return (db.query(func.max(Diario.asiento)).filter(
                Diario.empresa_id == empresa_id
            ).scalar() or 0) + 1
        except IntegrityError:
            db.rollback()
            if intento < 4:
                time.sleep(0.05 * (2 ** intento))
                continue
            raise


def _build_asiento(lines: list) -> dict:
    if not lines:
        return None
    first = lines[0]
    debe = sum((l.importe or 0) for l in lines if (l.importe or 0) > 0)
    haber = abs(sum((l.importe or 0) for l in lines if (l.importe or 0) < 0))
    return {
        'asiento': first.asiento,
        'empresa_id': first.empresa_id,
        'fecha': first.fecha,
        'tpasiento': first.tpasiento,
        'clave': first.clave,
        'tipo': first.tipo,
        'numero': first.numero,
        'lineas': lines,
        'total_debe': round(debe, 2),
        'total_haber': round(haber, 2),
        'cuadrado': abs(debe - haber) < 0.01,
    }


def get_asientos(db: Session, empresa_id: int, fecha_desde=None, fecha_hasta=None,
                 cuenta: str = None, skip: int = 0, limit: int = 50, orden: str = 'fecha'):
    base = db.query(Diario.asiento, func.max(Diario.fecha).label('fecha_max')).filter(
        Diario.empresa_id == empresa_id
    )
    if fecha_desde:
        base = base.filter(Diario.fecha >= fecha_desde)
    if fecha_hasta:
        base = base.filter(Diario.fecha <= fecha_hasta)
    if cuenta:
        base = base.filter(Diario.cuenta.ilike(f'{cuenta}%'))
    base = base.group_by(Diario.asiento)

    total = base.count()

    if orden == 'asiento':
        base = base.order_by(Diario.asiento.desc())
    else:
        base = base.order_by(func.max(Diario.fecha).desc(), Diario.asiento.desc())

    nums_rows = base.offset(skip).limit(limit).all()
    nums = [r[0] for r in nums_rows]

    if not nums:
        return [], total

    lines = (db.query(Diario)
             .filter(Diario.empresa_id == empresa_id, Diario.asiento.in_(nums))
             .order_by(Diario.asiento.desc(), Diario.id)
             .all())

    by_asiento = defaultdict(list)
    for l in lines:
        by_asiento[l.asiento].append(l)

    result = [_build_asiento(by_asiento[n]) for n in nums if by_asiento[n]]
    return result, total


def get_asiento(db: Session, empresa_id: int, asiento_num: int):
    lines = (db.query(Diario)
             .filter(Diario.empresa_id == empresa_id, Diario.asiento == asiento_num)
             .order_by(Diario.id).all())
    return _build_asiento(lines)


def create_asiento(db: Session, data: AsientoCreate) -> dict:
    num = _siguiente_asiento(db, data.empresa_id)
    lineas = []
    for ld in data.lineas:
        linea = Diario(
            empresa_id=data.empresa_id,
            asiento=num,
            fecha=data.fecha,
            tpasiento=data.tpasiento,
            clave=data.clave,
            clave_ori=data.clave,
            tipo=data.tipo,
            numero=data.numero,
            cuenta=ld.cuenta,
            importe=ld.importe,
            multi=ld.multi,
            saldo=0,
        )
        db.add(linea)
        lineas.append(linea)
        # Actualizar debe/haber de la cuenta
        cuenta_obj = db.query(Cuenta).filter(
            Cuenta.empresa_id == data.empresa_id,
            Cuenta.cuenta == ld.cuenta,
        ).first()
        if cuenta_obj:
            if ld.importe > 0:
                cuenta_obj.debe = round((cuenta_obj.debe or 0) + ld.importe, 2)
            else:
                cuenta_obj.haber = round((cuenta_obj.haber or 0) + abs(ld.importe), 2)

    db.commit()
    for l in lineas:
        db.refresh(l)
    return _build_asiento(lineas)


_TIPOS_DOCUMENTO = {'R': 'factura recibida', 'F': 'factura emitida', 'X': 'extra',
                    'B': 'movimiento bancario', 'P': 'paga NNA'}


def delete_asiento(db: Session, empresa_id: int, asiento_num: int, force: bool = False) -> bool:
    lines = (db.query(Diario)
             .filter(Diario.empresa_id == empresa_id, Diario.asiento == asiento_num)
             .all())
    if not lines:
        return False
    if not force:
        # Aviso si el asiento pertenece a un documento (factura/extra/banco/paga):
        # borrarlo deja el documento sin contabilizar y descuadra la conciliación.
        vinculos = {(_TIPOS_DOCUMENTO[l.tipo], l.numero) for l in lines
                    if l.tipo in _TIPOS_DOCUMENTO and l.numero is not None}
        if vinculos:
            desc = ', '.join(f"{t} nº{n}" for t, n in sorted(vinculos))
            raise ValueError(
                f"El asiento {asiento_num} está vinculado a: {desc}. "
                "Borrarlo dejará el documento sin contabilizar."
            )
    for l in lines:
        if l.cuenta:
            cuenta_obj = db.query(Cuenta).filter(
                Cuenta.empresa_id == empresa_id,
                Cuenta.cuenta == l.cuenta,
            ).first()
            if cuenta_obj:
                if (l.importe or 0) > 0:
                    cuenta_obj.debe = round((cuenta_obj.debe or 0) - (l.importe or 0), 2)
                else:
                    cuenta_obj.haber = round((cuenta_obj.haber or 0) - abs(l.importe or 0), 2)
        db.delete(l)
    db.commit()
    return True


def update_asiento(db: Session, empresa_id: int, asiento_num: int, data: AsientoCreate) -> dict | None:
    lines = db.query(Diario).filter(
        Diario.empresa_id == empresa_id,
        Diario.asiento == asiento_num,
    ).all()
    if not lines:
        return None
    # Preservar el vínculo con el documento origen (tipo/numero) y los metadatos
    # cuando el cliente no los envía: si se perdieran, el documento aparecería
    # como "sin asiento" y una regeneración crearía un duplicado
    old = lines[0]
    tipo      = data.tipo      if data.tipo      is not None else old.tipo
    numero    = data.numero    if data.numero    is not None else old.numero
    tpasiento = data.tpasiento if data.tpasiento is not None else old.tpasiento
    clave     = data.clave     if data.clave     is not None else old.clave
    # Revertir saldos de cuentas
    for l in lines:
        if l.cuenta:
            cuenta_obj = db.query(Cuenta).filter(
                Cuenta.empresa_id == empresa_id,
                Cuenta.cuenta == l.cuenta,
            ).first()
            if cuenta_obj:
                if (l.importe or 0) > 0:
                    cuenta_obj.debe = round((cuenta_obj.debe or 0) - (l.importe or 0), 2)
                else:
                    cuenta_obj.haber = round((cuenta_obj.haber or 0) - abs(l.importe or 0), 2)
        db.delete(l)
    db.flush()
    # Recrear líneas con el mismo número de asiento
    nuevas = []
    for ld in data.lineas:
        linea = Diario(
            empresa_id=empresa_id,
            asiento=asiento_num,
            fecha=data.fecha,
            tpasiento=tpasiento,
            clave=clave,
            clave_ori=clave,
            tipo=tipo,
            numero=numero,
            cuenta=ld.cuenta,
            importe=ld.importe,
            multi=ld.multi,
            saldo=0,
        )
        db.add(linea)
        nuevas.append(linea)
        cuenta_obj = db.query(Cuenta).filter(
            Cuenta.empresa_id == empresa_id,
            Cuenta.cuenta == ld.cuenta,
        ).first()
        if cuenta_obj:
            if ld.importe > 0:
                cuenta_obj.debe = round((cuenta_obj.debe or 0) + ld.importe, 2)
            else:
                cuenta_obj.haber = round((cuenta_obj.haber or 0) + abs(ld.importe), 2)
    db.commit()
    for l in nuevas:
        db.refresh(l)
    return _build_asiento(nuevas)


# ─── Libro mayor ─────────────────────────────────────────────────────────────

def get_mayor(db: Session, empresa_id: int, cuenta: str,
              fecha_desde=None, fecha_hasta=None, skip: int = 0, limit: int = 200):
    query = db.query(Diario).filter(
        Diario.empresa_id == empresa_id,
        Diario.cuenta == cuenta,
    )
    if fecha_desde:
        query = query.filter(Diario.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Diario.fecha <= fecha_hasta)
    total = query.count()

    # Suma de importes de las filas anteriores a esta página (para saldo continuo entre páginas)
    saldo_anterior = 0.0
    if skip > 0:
        ids_previos = query.order_by(Diario.fecha, Diario.asiento).limit(skip).with_entities(Diario.id)
        saldo_raw = db.query(func.sum(Diario.importe)).filter(Diario.id.in_(ids_previos)).scalar() or 0
        saldo_anterior = saldo_raw or 0

    items = query.order_by(Diario.fecha, Diario.asiento).offset(skip).limit(limit).all()
    return items, total, saldo_anterior


# ─── Conciliación bancos vs contabilidad ─────────────────────────────────────

def _calcular_saldos_banco(db: Session, empresa_id: int, banco) -> dict:
    """Calcula saldo banco vs saldo libro mayor para un banco concreto."""
    saldo_banco = (banco.saldoini or 0) + (banco.saldoact or 0)

    saldo_lm_raw = db.query(func.sum(Diario.importe)).filter(
        Diario.empresa_id == empresa_id,
        Diario.cuenta == banco.cuenta,
        or_(Diario.tpasiento != 'Z', Diario.tpasiento.is_(None)),
    ).scalar() or 0
    saldo_lm = saldo_lm_raw or 0

    base_lm_raw = db.query(func.sum(Diario.importe)).filter(
        Diario.empresa_id == empresa_id,
        Diario.cuenta == banco.cuenta,
        Diario.tipo != 'B',
    ).scalar() or 0
    base_lm = base_lm_raw or 0

    diferencia = round(saldo_banco - saldo_lm, 2)
    return {
        'saldo_banco': saldo_banco,
        'saldo_lm': saldo_lm,
        'base_lm': base_lm,
        'diferencia': diferencia,
        'ok': abs(diferencia) < 0.01,
    }


def _emparejar_por_numero(movs, lm_por_numero):
    """Paso 1: empareja movimientos bancarios con entradas LM por numero exacto."""
    matched_mov_nums: set[int] = set()
    matched_lm_ids: set[int] = set()
    detalle = []

    for mov in movs:
        entries = lm_por_numero.get(mov.numero, [])
        if entries:
            total_b = mov.total or 0
            total_lm = sum(l.importe or 0 for l in entries)
            matched_mov_nums.add(mov.numero)
            for l in entries:
                matched_lm_ids.add(l.id)
            dif = round(total_b - total_lm, 2)
            if abs(dif) >= 0.01:
                detalle.append({
                    'tipo': 'importe_diff',
                    'numero': mov.numero,
                    'fecha': str(mov.fecha),
                    'texto': mov.texto or '',
                    'total_banco': total_b,
                    'total_lm': total_lm,
                    'diferencia': dif,
                    'saldo_banco': mov.saldonue or 0,
                })

    return matched_mov_nums, matched_lm_ids, detalle


def _emparejar_por_fecha_importe(movs, lm_entries_b, matched_lm_ids, matched_mov_nums):
    """Paso 2: fallback por (fecha, importe) para movimientos sin emparejar por numero."""
    lm_by_fi: dict = {}
    for l in lm_entries_b:
        if l.id not in matched_lm_ids:
            key = (str(l.fecha), l.importe or 0)
            lm_by_fi.setdefault(key, []).append(l)

    sin_asiento_candidatos = []
    for mov in movs:
        if mov.numero in matched_mov_nums:
            continue
        total_b = mov.total or 0
        key = (str(mov.fecha), total_b)
        if key in lm_by_fi and lm_by_fi[key]:
            matched_lm = lm_by_fi[key].pop(0)
            matched_mov_nums.add(mov.numero)
            matched_lm_ids.add(matched_lm.id)
        else:
            sin_asiento_candidatos.append(mov)

    return sin_asiento_candidatos


def _emparejar_transferencias(db, empresa_id, banco, sin_asiento_candidatos,
                               matched_lm_ids, matched_mov_nums):
    """Paso 3: resuelve transferencias receptor/emisor entre bancos."""
    from app.models.bancos import Banco as BancoM, Pago as PagoM

    all_pagos_banco = db.query(PagoM).filter(
        PagoM.empresa_id == empresa_id,
        PagoM.banco == banco.numero,
    ).all()
    pagos_x_numero: dict = {}
    for p in all_pagos_banco:
        pagos_x_numero.setdefault(p.numero, []).append(p)

    detalle = []
    for mov in sin_asiento_candidatos:
        pags = pagos_x_numero.get(mov.numero, [])
        receptor_pagos = [p for p in pags if p.dirsubcta == banco.cuenta and p.bancot and p.numerot]
        matched = False

        # Caso A: lado RECEPTOR
        for p in receptor_pagos:
            banco_t_obj = db.query(BancoM).filter(
                BancoM.empresa_id == empresa_id,
                BancoM.numero == p.bancot,
            ).first()
            if not banco_t_obj or not banco_t_obj.cuenta:
                continue
            entrada_origen = db.query(Diario).filter(
                Diario.empresa_id == empresa_id,
                Diario.tipo == 'B',
                Diario.numero == p.numerot,
                Diario.cuenta == banco_t_obj.cuenta,
            ).first()
            if not entrada_origen:
                continue
            entrada_receptor = db.query(Diario).filter(
                Diario.empresa_id == empresa_id,
                Diario.asiento == entrada_origen.asiento,
                Diario.cuenta == banco.cuenta,
            ).first()
            if entrada_receptor and entrada_receptor.id not in matched_lm_ids:
                matched_mov_nums.add(mov.numero)
                matched_lm_ids.add(entrada_receptor.id)
                matched = True
                break

        # Caso B: lado EMISOR
        if not matched:
            envio_pagos = [p for p in pags if p.bancot and p.numerot
                           and p.dirsubcta and p.dirsubcta != banco.cuenta]
            for p in envio_pagos:
                banco_t_obj = db.query(BancoM).filter(
                    BancoM.empresa_id == empresa_id,
                    BancoM.numero == p.bancot,
                ).first()
                if not banco_t_obj or not banco_t_obj.cuenta:
                    continue
                entrada_otro = db.query(Diario).filter(
                    Diario.empresa_id == empresa_id,
                    Diario.tipo == 'B',
                    Diario.numero == p.numerot,
                    Diario.cuenta == banco_t_obj.cuenta,
                ).first()
                if not entrada_otro:
                    continue
                mi_linea = db.query(Diario).filter(
                    Diario.empresa_id == empresa_id,
                    Diario.asiento == entrada_otro.asiento,
                    Diario.cuenta == banco.cuenta,
                ).first()
                if mi_linea and mi_linea.id not in matched_lm_ids:
                    matched_mov_nums.add(mov.numero)
                    matched_lm_ids.add(mi_linea.id)
                    matched = True
                    break

        if not matched:
            total_b = mov.total or 0
            detalle.append({
                'tipo': 'sin_asiento',
                'numero': mov.numero,
                'fecha': str(mov.fecha),
                'texto': mov.texto or '',
                'total_banco': total_b,
                'total_lm': None,
                'diferencia': total_b,
                'saldo_banco': mov.saldonue or 0,
                'es_transferencia': bool(receptor_pagos),
            })

    return detalle


def _detectar_asientos_huerfanos(lm_entries_b, matched_lm_ids):
    """Detecta asientos en LM sin ningún movimiento bancario equivalente."""
    detalle = []
    for l in lm_entries_b:
        if l.id not in matched_lm_ids:
            importe_l = l.importe or 0
            detalle.append({
                'tipo': 'asiento_huerfano',
                'numero': l.numero,
                'fecha': str(l.fecha),
                'texto': 'Asiento sin movimiento bancario',
                'total_banco': None,
                'total_lm': importe_l,
                'diferencia': -importe_l,
                'saldo_banco': None,
            })
    return detalle


def get_conciliacion_bancos(db: Session, empresa_id: int) -> list:
    from app.models.bancos import Banco, MovBanco

    bancos = db.query(Banco).filter(
        Banco.empresa_id == empresa_id,
        Banco.cuenta.isnot(None),
        Banco.cuenta != '',
    ).order_by(Banco.numero).all()

    resultado = []

    for banco in bancos:
        saldos = _calcular_saldos_banco(db, empresa_id, banco)

        if saldos['ok']:
            resultado.append({
                'banco': banco.numero,
                'nombre': banco.nombre or '',
                'cuenta': banco.cuenta,
                **saldos,
                'detalle': [],
            })
            continue

        movs = db.query(MovBanco).filter(
            MovBanco.empresa_id == empresa_id,
            MovBanco.banco == banco.numero,
        ).order_by(MovBanco.fecha, MovBanco.numero).all()

        lm_entries_b = db.query(Diario).filter(
            Diario.empresa_id == empresa_id,
            Diario.cuenta == banco.cuenta,
            Diario.tipo == 'B',
        ).order_by(Diario.fecha, Diario.id).all()

        my_tpasiento = f'B{banco.numero}'
        lm_por_numero: dict[int, list] = {}
        for l in lm_entries_b:
            if l.numero is not None and (not l.tpasiento or l.tpasiento == my_tpasiento):
                lm_por_numero.setdefault(l.numero, []).append(l)

        matched_mov_nums, matched_lm_ids, detalle = _emparejar_por_numero(movs, lm_por_numero)

        sin_asiento_candidatos = _emparejar_por_fecha_importe(
            movs, lm_entries_b, matched_lm_ids, matched_mov_nums)

        detalle.extend(_emparejar_transferencias(
            db, empresa_id, banco, sin_asiento_candidatos,
            matched_lm_ids, matched_mov_nums))

        detalle.extend(_detectar_asientos_huerfanos(lm_entries_b, matched_lm_ids))

        detalle.sort(key=lambda x: (x['fecha'] or '9999', x['numero']))

        resultado.append({
            'banco': banco.numero,
            'nombre': banco.nombre or '',
            'cuenta': banco.cuenta,
            **saldos,
            'detalle': detalle,
        })

    return resultado


# ─── Balance de sumas y saldos ───────────────────────────────────────────────

def get_sumas_saldos(db: Session, empresa_id: int, fecha_desde=None, fecha_hasta=None,
                     nivel: int = None, excluir_tipos: list = None):
    """Devuelve el balance de sumas y saldos por cuenta, opcionalmente agrupado por nivel."""
    query = db.query(Diario.cuenta, Diario.importe).filter(
        Diario.empresa_id == empresa_id,
        Diario.cuenta.isnot(None),
    )
    if fecha_desde:
        query = query.filter(Diario.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Diario.fecha <= fecha_hasta)
    if excluir_tipos:
        # NOT IN con NULL en SQL excluye también las filas con tpasiento NULL
        # (la comparación devuelve NULL, no TRUE): incluirlas explícitamente
        from sqlalchemy import or_
        query = query.filter(or_(
            Diario.tpasiento.is_(None),
            ~Diario.tpasiento.in_(excluir_tipos),
        ))

    agg = defaultdict(lambda: {'debe': Decimal('0'), 'haber': Decimal('0')})
    for cuenta_code, importe in query.all():
        key = cuenta_code[:nivel] if nivel and len(cuenta_code) > nivel else cuenta_code
        imp = importe or 0
        if imp > 0:
            agg[key]['debe'] += imp
        else:
            agg[key]['haber'] += abs(imp)

    cuentas_map = {c.cuenta: c.texto for c in db.query(Cuenta).filter(Cuenta.empresa_id == empresa_id).all()}

    result = []
    tot_debe = tot_haber = tot_sd = tot_sa = 0.0
    for cc in sorted(agg.keys()):
        debe = round(float(agg[cc]['debe']), 2)
        haber = round(float(agg[cc]['haber']), 2)
        saldo = round(debe - haber, 2)
        sd = round(saldo, 2) if saldo > 0 else 0.0
        sa = round(-saldo, 2) if saldo < 0 else 0.0
        tot_debe += debe; tot_haber += haber; tot_sd += sd; tot_sa += sa
        result.append({
            'cuenta': cc,
            'texto': cuentas_map.get(cc, ''),
            'debe': debe,
            'haber': haber,
            'saldo_deudor': sd,
            'saldo_acreedor': sa,
        })

    return result, round(tot_debe, 2), round(tot_haber, 2), round(tot_sd, 2), round(tot_sa, 2)


# ─── Pérdidas y ganancias ────────────────────────────────────────────────────

def get_pyg(db: Session, empresa_id: int, fecha_desde=None, fecha_hasta=None) -> dict:
    """PyG del periodo. Única fuente para la pantalla y el export (antes divergían:
    el export no excluía apertura ni incluía el saldo inicial de bancos)."""
    from sqlalchemy import text as _text
    # Excluye regularización ('R'), cierre ('Z') y apertura ('A')
    filas, *_ = get_sumas_saldos(db, empresa_id, fecha_desde, fecha_hasta,
                                  excluir_tipos=['R', 'Z', 'A'])
    gastos   = [f for f in filas if f['cuenta'] and f['cuenta'].startswith('6')]
    ingresos = [f for f in filas if f['cuenta'] and f['cuenta'].startswith('7')]
    # Importe neto por cuenta (una cuenta 6 con saldo acreedor resta a los gastos)
    for f in gastos:
        f['importe'] = round(f['saldo_deudor'] - f['saldo_acreedor'], 2)
    for f in ingresos:
        f['importe'] = round(f['saldo_acreedor'] - f['saldo_deudor'], 2)
    tg = round(sum(f['importe'] for f in gastos), 2)
    ti = round(sum(f['importe'] for f in ingresos), 2)

    # Saldo inicial de bancos (cuentas 57xxxx del asiento de apertura, tpasiento='A')
    saldo_query = db.query(func.coalesce(func.sum(Diario.importe), 0)).filter(
        Diario.empresa_id == empresa_id,
        Diario.cuenta.like('57%'),
        Diario.tpasiento == 'A',
    )
    if fecha_desde:
        saldo_query = saldo_query.filter(Diario.fecha >= fecha_desde)
    if fecha_hasta:
        saldo_query = saldo_query.filter(Diario.fecha <= fecha_hasta)
    # float(): func.sum() devuelve Decimal (importe es Numeric) y ti/tg son
    # float — sin el cast, float + Decimal → TypeError (500 en PyG, v1.13.08)
    saldo_inicial = float(saldo_query.scalar() or 0)

    return {
        'gastos': gastos,
        'ingresos': ingresos,
        'total_gastos': tg,
        'total_ingresos': ti,
        'resultado': round(ti - tg, 2),
        'saldo_inicial_bancos': saldo_inicial,
        'resultado_con_saldo_inicial': round(ti - tg + saldo_inicial, 2),
    }


# ─── Auto-generación de asientos ─────────────────────────────────────────────

def _ya_tiene_asiento(db: Session, empresa_id: int, tipo: str, numero: int) -> bool:
    return db.query(Diario).filter(
        Diario.empresa_id == empresa_id,
        Diario.tipo == tipo,
        Diario.numero == numero,
    ).first() is not None


def _ya_tiene_asiento_banco(db: Session, empresa_id: int, banco_cuenta: str, numero: int,
                           banco_num: int | None = None,
                           fecha=None, importe: float | None = None) -> bool:
    """Para movimientos bancarios: verifica por cuenta+numero.
    Si banco_num se provee, descarta entradas atribuidas a OTRO banco (tpasiento='B{X}' donde X != banco_num),
    pero acepta entradas migradas/manuales (tpasiento='M', 'EXT', None, etc.) como válidas.
    Esto evita falsos positivos con asientos del banco contraparte que comparten numero.

    Fallback por fecha+importe: detecta asientos de migración cuyo numero quedó NULL (p.ej. asiento 3).
    Solo activa cuando no hay coincidencia por numero y se pasan fecha e importe del movimiento."""
    entries = db.query(Diario).filter(
        Diario.empresa_id == empresa_id,
        Diario.tipo == 'B',
        Diario.numero == numero,
        Diario.cuenta == banco_cuenta,
    ).all()
    # Fallback: asientos migrados con numero=NULL — buscar por fecha+importe exacto
    if not entries and fecha is not None and importe is not None:
        entries = db.query(Diario).filter(
            Diario.empresa_id == empresa_id,
            Diario.cuenta == banco_cuenta,
            Diario.tipo == 'B',
            Diario.numero == None,
            Diario.fecha == fecha,
            Diario.importe == importe,
        ).all()
    if not entries:
        return False
    if banco_num is None:
        return True
    own_tp = f'B{banco_num}'
    for e in entries:
        tp = e.tpasiento or ''
        # Aceptar: es nuestro banco, o es un asiento migrado/manual (no empieza por 'B' + dígito)
        if tp == own_tp or not (tp.startswith('B') and tp[1:].isdigit()):
            return True
    return False


def _crear_lineas_raw(db: Session, empresa_id: int, asiento_num: int,
                      fecha, tipo: str, numero: int, tpasiento: str, clave: str,
                      lineas_data: list) -> list:
    from sqlalchemy import text as _text
    lineas = []
    for ld in lineas_data:
        if not ld.get('cuenta'):
            continue
        imp = ld['importe']
        # Raw SQL insert — evita el FK sort error de SQLAlchemy con diario.empresa_id → empresas
        db.execute(_text(
            "INSERT INTO diario (empresa_id, asiento, fecha, tpasiento, clave, clave_ori, tipo, numero, cuenta, importe, multi, saldo)"
            " VALUES (:e, :a, :f, :tp, :cl, :cl, :ti, :nu, :cu, :im, :mu, 0)"
        ), {"e": empresa_id, "a": asiento_num, "f": fecha, "tp": tpasiento,
            "cl": clave, "ti": tipo, "nu": numero, "cu": ld['cuenta'],
            "im": imp, "mu": ld.get('multi')})
        # Objeto sin sesión para que _build_asiento lea los atributos
        linea = Diario(
            empresa_id=empresa_id, asiento=asiento_num, fecha=fecha,
            tpasiento=tpasiento, clave=clave, clave_ori=clave,
            tipo=tipo, numero=numero, cuenta=ld['cuenta'],
            importe=imp, multi=ld.get('multi'), saldo=0,
        )
        lineas.append(linea)
        if imp > 0:
            db.execute(_text("UPDATE cuentas SET debe=ROUND(debe+:v,2) WHERE empresa_id=:e AND cuenta=:c"),
                       {"v": imp, "e": empresa_id, "c": ld['cuenta']})
        else:
            db.execute(_text("UPDATE cuentas SET haber=ROUND(haber+:v,2) WHERE empresa_id=:e AND cuenta=:c"),
                       {"v": abs(imp), "e": empresa_id, "c": ld['cuenta']})
    return lineas


def _eliminar_asiento_documento(db: Session, empresa_id: int, tipo: str, numero: int):
    """Elimina las líneas de diario de un documento y revierte saldos de cuentas."""
    lines = db.query(Diario).filter(
        Diario.empresa_id == empresa_id,
        Diario.tipo == tipo,
        Diario.numero == numero,
    ).all()
    for l in lines:
        if l.cuenta:
            cuenta_obj = db.query(Cuenta).filter(
                Cuenta.empresa_id == empresa_id,
                Cuenta.cuenta == l.cuenta,
            ).first()
            if cuenta_obj:
                if (l.importe or 0) > 0:
                    cuenta_obj.debe = round((cuenta_obj.debe or 0) - (l.importe or 0), 2)
                else:
                    cuenta_obj.haber = round((cuenta_obj.haber or 0) - abs(l.importe or 0), 2)
        db.delete(l)


def _debe_generar_asiento_banco(db: Session, empresa_id: int, mov, banco, pagos) -> bool:
    """Verifica si un movimiento bancario debe generar asiento contable.
    Retorna False si debe saltarse (contraparte, duplicado, transferencia simétrica)."""
    from app.models.bancos import Banco as BancoModel, MovBanco as MovBancoModel, Pago as PagoModel

    if not banco or not banco.cuenta:
        return False

    # Contraparte primaria: algún pago tiene dirsubcta == cuenta propia del banco
    if pagos and any(p.dirsubcta == banco.cuenta for p in pagos):
        return False

    # Receptor sin pago propio de transferencia
    es_origen = pagos and any(p.bancot for p in pagos)
    if not es_origen:
        pago_entrante = db.query(PagoModel).filter(
            PagoModel.empresa_id == empresa_id,
            PagoModel.bancot == banco.numero,
            PagoModel.numerot == mov.numero,
            PagoModel.banco != banco.numero,
        ).first()
        if pago_entrante:
            return False

    # Transferencia sin dirsubcta: solo el lado PAGADOR (total negativo) genera asiento
    if pagos and any(p.bancot and p.numerot and not p.dirsubcta for p in pagos):
        if mov.total or 0 >= 0:
            return False

    # Verificar si el banco ORIGEN ya generó el asiento por contraparte
    for p in pagos:
        if p.bancot and p.numerot:
            banco_t = db.query(BancoModel).filter(
                BancoModel.empresa_id == empresa_id,
                BancoModel.numero == p.bancot,
            ).first()
            if banco_t and banco_t.cuenta:
                def _es_transferencia_de_otro_banco(tp):
                    return bool(tp) and tp.startswith('B') and tp[1:].isdigit() and tp != f'B{p.bancot}'

                candidatos_origen = db.query(Diario).filter(
                    Diario.empresa_id == empresa_id,
                    Diario.tipo == 'B',
                    Diario.numero == p.numerot,
                    Diario.cuenta == banco_t.cuenta,
                ).all()
                entrada_origen = next(
                    (c for c in candidatos_origen if not _es_transferencia_de_otro_banco(c.tpasiento)),
                    None,
                )
                if not entrada_origen:
                    mov_t = db.query(MovBancoModel).filter(
                        MovBancoModel.empresa_id == empresa_id,
                        MovBancoModel.banco == p.bancot,
                        MovBancoModel.numero == p.numerot,
                    ).first()
                    if mov_t:
                        candidatos_fecha = db.query(Diario).filter(
                            Diario.empresa_id == empresa_id,
                            Diario.tipo == 'B',
                            Diario.cuenta == banco_t.cuenta,
                            Diario.fecha == mov_t.fecha,
                            Diario.importe == (mov_t.total or 0),
                        ).all()
                        entrada_origen = next(
                            (c for c in candidatos_fecha if not _es_transferencia_de_otro_banco(c.tpasiento)),
                            None,
                        )
                if entrada_origen:
                    if db.query(Diario).filter(
                        Diario.empresa_id == empresa_id,
                        Diario.asiento == entrada_origen.asiento,
                        Diario.cuenta == banco.cuenta,
                    ).first():
                        return False

    if _ya_tiene_asiento_banco(db, empresa_id, banco.cuenta, mov.numero, banco.numero,
                              fecha=mov.fecha, importe=mov.total or 0):
        return False

    return True


def _resolver_cuenta_pago(db: Session, empresa_id: int, p, banco) -> str | None:
    """Resuelve la cuenta contable de un pago con fallbacks:
    dirsubcta → bancot → vto.cuentadef → factura/extra → proveedor."""
    from app.models.bancos import Banco as BancoModel

    subcta = p.dirsubcta

    # Fallback 1: banco contraparte (transferencia interna)
    if not subcta and p.bancot:
        banco_t = db.query(BancoModel).filter(
            BancoModel.empresa_id == empresa_id,
            BancoModel.numero == p.bancot,
        ).first()
        if banco_t:
            subcta = banco_t.cuenta

    # Fallback 2: vencimiento → factura/extra → proveedor
    if not subcta and p.vto:
        from app.models.clientes_proveedores import Vencimiento, Proveedor
        from app.models.facturacion import FacturaRecibida
        vto = db.query(Vencimiento).filter(
            Vencimiento.empresa_id == empresa_id,
            Vencimiento.numero == p.vto,
        ).first()
        if vto:
            subcta = vto.cuentadef
            if not subcta and vto.tpnumero and vto.tipo == 'R':
                fac = db.query(FacturaRecibida).filter(
                    FacturaRecibida.empresa_id == empresa_id,
                    FacturaRecibida.numero == vto.tpnumero,
                ).first()
                if fac:
                    subcta = fac.prcuenta
                    if not subcta and fac.proveedor:
                        prov = db.query(Proveedor).filter(
                            Proveedor.empresa_id == empresa_id,
                            Proveedor.numero == fac.proveedor,
                        ).first()
                        if prov:
                            subcta = prov.cuenta
            if not subcta and vto.tpnumero and vto.tipo == 'X':
                from app.models.contabilidad import Extra, ExApunte
                extra = db.query(Extra).filter(
                    Extra.empresa_id == empresa_id,
                    Extra.numero == vto.tpnumero,
                ).first()
                if extra:
                    apuntes = db.query(ExApunte).filter(
                        ExApunte.empresa_id == empresa_id,
                        ExApunte.extra == extra.numero,
                    ).all()
                    h_ap = next((a for a in apuntes if a.dh == 'H' and a.cuenta), None)
                    d_ap = next((a for a in apuntes if a.dh == 'D' and a.cuenta), None)
                    ap = h_ap or d_ap
                    if ap:
                        subcta = ap.cuenta

    return subcta


def _construir_lineas_asiento(db: Session, empresa_id: int, mov, banco, pagos) -> list | None:
    """Construye la lista de lineas_data para el asiento. Retorna None si no hay contrapartida."""
    lineas_data = [{'cuenta': banco.cuenta, 'importe': mov.total or 0}]
    for p in pagos:
        subcta = _resolver_cuenta_pago(db, empresa_id, p, banco)
        if subcta:
            lineas_data.append({'cuenta': subcta, 'importe': -(p.importe or 0)})

    if len(lineas_data) < 2:
        return None
    return lineas_data


def _detectar_asiento_migrado(db: Session, empresa_id: int, mov, lineas_data) -> bool:
    """Red de seguridad: detecta asientos migrados duplicados por fecha+importe sin numero fiable.
    Retorna True si ya existe un asiento candidato (no generar)."""
    asientos_candidatos = None
    for ld in lineas_data:
        ids_cuenta = {
            row.asiento for row in db.query(Diario.asiento).filter(
                Diario.empresa_id == empresa_id,
                Diario.tipo == 'B',
                Diario.numero.is_(None),
                Diario.fecha == mov.fecha,
                Diario.cuenta == ld['cuenta'],
                Diario.importe == ld['importe'],
            ).all()
        }
        asientos_candidatos = ids_cuenta if asientos_candidatos is None else (asientos_candidatos & ids_cuenta)
        if not asientos_candidatos:
            break
    return bool(asientos_candidatos)


def generar_asiento_banco(db: Session, empresa_id: int, mov, banco, pagos) -> dict | None:
    """Genera el asiento contable para un movimiento bancario (no contraparte)."""
    if not _debe_generar_asiento_banco(db, empresa_id, mov, banco, pagos):
        return None

    lineas_data = _construir_lineas_asiento(db, empresa_id, mov, banco, pagos)
    if not lineas_data:
        return None

    if _detectar_asiento_migrado(db, empresa_id, mov, lineas_data):
        return None

    num = _siguiente_asiento(db, empresa_id)
    lineas = _crear_lineas_raw(
        db, empresa_id, num, mov.fecha, 'B', mov.numero,
        f'B{banco.numero}', mov.clave or 'ZZZ', lineas_data,
    )
    if not lineas:
        return None
    db.flush()
    return _build_asiento(lineas)


def _eliminar_asiento_banco(db: Session, empresa_id: int, banco_cuenta: str, numero: int, banco_num: int | None = None):
    """Elimina las líneas del asiento de un movimiento bancario específico.
    banco_num filtra por tpasiento='B{banco_num}' para no borrar asientos de otros bancos
    que compartan el mismo numero de movimiento.

    Si el asiento tiene líneas no-B (asiento de migración mixto), solo se eliminan las
    entradas B del banco actual para preservar las entradas contables no bancarias.
    Usa raw SQL para evitar el error de FK de SQLAlchemy al hacer flush."""
    from sqlalchemy import text as _text
    q = db.query(Diario).filter(
        Diario.empresa_id == empresa_id,
        Diario.tipo == 'B',
        Diario.numero == numero,
        Diario.cuenta == banco_cuenta,
    )
    anchor_lines = q.all()
    if banco_num is not None:
        # Aceptar el asiento propio ('B{banco_num}') y los migrados/manuales
        # ('M', 'EXT', None...); descartar solo los de OTRO banco ('B{X}', X != banco_num)
        own_tp = f'B{banco_num}'
        def _es_propio_o_migrado(l):
            tp = l.tpasiento or ''
            return tp == own_tp or not (tp.startswith('B') and tp[1:].isdigit())
        anchor_lines = [l for l in anchor_lines if _es_propio_o_migrado(l)]
    if not anchor_lines:
        return
    asiento_num = anchor_lines[0].asiento
    all_lines = db.query(Diario).filter(
        Diario.empresa_id == empresa_id,
        Diario.asiento == asiento_num,
    ).all()
    # Asiento mixto (tiene entradas no-B): solo borrar las entradas B de este banco
    non_b = [l for l in all_lines if l.tipo != 'B']
    if non_b:
        own_tp = f'B{banco_num}' if banco_num is not None else None
        lines_to_delete = [l for l in all_lines
                           if l.tipo == 'B' and (own_tp is None or l.tpasiento == own_tp)]
    else:
        lines_to_delete = all_lines
    ids_to_delete = [l.id for l in lines_to_delete]
    for l in lines_to_delete:
        if l.cuenta:
            imp = l.importe or 0
            cuenta_obj = db.query(Cuenta).filter(
                Cuenta.empresa_id == empresa_id,
                Cuenta.cuenta == l.cuenta,
            ).first()
            if cuenta_obj:
                if imp > 0:
                    cuenta_obj.debe = round((cuenta_obj.debe or 0) - imp, 2)
                else:
                    cuenta_obj.haber = round((cuenta_obj.haber or 0) - abs(imp), 2)
    if ids_to_delete:
        db.query(Diario).filter(Diario.id.in_(ids_to_delete)).delete(synchronize_session='fetch')
    # Volcar cambios ORM pendientes ANTES de expirar: expire_all() descarta las
    # modificaciones no flusheadas (p.ej. conciliado/texto del movimiento en edición)
    db.flush()
    db.expire_all()  # Limpiar caché ORM tras borrados raw para evitar inconsistencias


def regenerar_asiento_banco(db: Session, empresa_id: int, mov, banco, pagos):
    """Elimina el asiento existente y genera uno nuevo para un movimiento bancario."""
    _eliminar_asiento_banco(db, empresa_id, banco.cuenta, mov.numero, banco.numero)
    db.flush()
    return generar_asiento_banco(db, empresa_id, mov, banco, pagos)


CUENTA_GASTO_DEFAULT = '6780000'


def generar_asiento_factura_rec(db: Session, empresa_id: int, fac, apuntes) -> dict | None:
    """Genera el asiento contable para una factura recibida."""
    if not fac.prcuenta:
        return None
    if _ya_tiene_asiento(db, empresa_id, 'R', fac.numero):
        return None

    lineas_data = [{'cuenta': fac.prcuenta, 'importe': -(fac.total or 0)}]
    for ap in apuntes:
        # Fallback a cuenta de gasto genérica si el apunte no tiene cuenta asignada
        cuenta_ap = ap.cuenta or CUENTA_GASTO_DEFAULT
        lineas_data.append({'cuenta': cuenta_ap, 'importe': ap.importe or 0})

    if len(lineas_data) < 2:
        return None

    num = _siguiente_asiento(db, empresa_id)
    lineas = _crear_lineas_raw(
        db, empresa_id, num, fac.fecha, 'R', fac.numero,
        'REC', fac.prcuenta, lineas_data,
    )
    if not lineas:
        return None
    db.flush()
    return _build_asiento(lineas)


def generar_asiento_extra(db: Session, empresa_id: int, extra) -> dict | None:
    """Genera el asiento contable para un extra a partir de sus ExApuntes D/H."""
    from app.models.contabilidad import ExApunte, DiarioTxt
    if _ya_tiene_asiento(db, empresa_id, 'X', extra.numero):
        return None
    apuntes = db.query(ExApunte).filter(
        ExApunte.empresa_id == empresa_id,
        ExApunte.extra == extra.numero,
    ).all()
    d_aps = [ap for ap in apuntes if ap.dh == 'D' and ap.cuenta]
    h_aps = [ap for ap in apuntes if ap.dh == 'H' and ap.cuenta]
    if not d_aps or not h_aps:
        return None
    clave = d_aps[0].cuenta
    lineas_data = (
        [{'cuenta': ap.cuenta, 'importe': ap.importe or 0} for ap in d_aps] +
        [{'cuenta': ap.cuenta, 'importe': -(ap.importe or 0)} for ap in h_aps]
    )
    num = _siguiente_asiento(db, empresa_id)
    lineas = _crear_lineas_raw(
        db, empresa_id, num, extra.fecha, 'X', extra.numero, 'EXT', clave, lineas_data,
    )
    if not lineas:
        return None

    # Upsert DiarioTxt
    from app.models.contabilidad import DiarioTxt
    existente = db.query(DiarioTxt).filter(
        DiarioTxt.empresa_id == empresa_id,
        DiarioTxt.tipo == 'X',
        DiarioTxt.numero == extra.numero,
    ).first()
    if existente:
        existente.texto = extra.texto or None
        existente.notas = extra.notas or None
        existente.fecha = extra.fecha
    else:
        db.add(DiarioTxt(
            empresa_id=empresa_id, tipo='X', numero=extra.numero,
            texto=extra.texto or None, notas=extra.notas or None,
            fecha=extra.fecha,
        ))
    return _build_asiento(lineas)


def generar_asiento_factura_emi(db: Session, empresa_id: int, fac, apuntes) -> dict | None:
    """Genera el asiento contable para una factura emitida."""
    if not fac.clcuenta:
        return None
    if _ya_tiene_asiento(db, empresa_id, 'F', fac.numero):
        return None

    lineas_data = [{'cuenta': fac.clcuenta, 'importe': fac.total or 0}]
    for ap in apuntes:
        if ap.cuenta:
            lineas_data.append({'cuenta': ap.cuenta, 'importe': -(ap.importe or 0)})

    if len(lineas_data) < 2:
        return None

    num = _siguiente_asiento(db, empresa_id)
    lineas = _crear_lineas_raw(
        db, empresa_id, num, fac.fecha, 'F', fac.numero,
        'ENV', fac.clcuenta, lineas_data,
    )
    if not lineas:
        return None
    db.flush()
    return _build_asiento(lineas)


def regenerar_asiento_movimiento(db: Session, empresa_id: int, banco_num: int, mov_numero: int) -> dict:
    """Fuerza la regeneración del asiento de un movimiento bancario concreto."""
    from app.models.bancos import Banco, MovBanco, Pago

    banco = db.query(Banco).filter(
        Banco.empresa_id == empresa_id,
        Banco.numero == banco_num,
    ).first()
    if not banco or not banco.cuenta:
        raise ValueError('Banco no encontrado o sin cuenta contable')

    mov = db.query(MovBanco).filter(
        MovBanco.empresa_id == empresa_id,
        MovBanco.banco == banco_num,
        MovBanco.numero == mov_numero,
    ).first()
    if not mov:
        raise ValueError('Movimiento no encontrado')

    pagos = db.query(Pago).filter(
        Pago.empresa_id == empresa_id,
        Pago.banco == banco_num,
        Pago.numero == mov_numero,
    ).all()

    es_receptor = pagos and any(p.dirsubcta == banco.cuenta for p in pagos)
    resultado = regenerar_asiento_banco(db, empresa_id, mov, banco, pagos)
    db.commit()
    if resultado:
        return {'regenerado': True, 'asiento': resultado['asiento']}
    if es_receptor:
        return {
            'regenerado': False,
            'codigo': 'transferencia_receptor',
            'motivo': 'Lado receptor de una transferencia entre bancos. El asiento lo genera el banco de origen.',
        }
    return {'regenerado': False, 'codigo': 'sin_contrapartida', 'motivo': 'Sin contrapartida contable disponible'}


def generar_asientos_pendientes(db: Session, empresa_id: int) -> dict:
    """Genera asientos para todos los documentos que aún no los tienen."""
    from app.models.bancos import Banco, MovBanco, Pago
    from app.models.facturacion import FacturaRecibida, FacturaEmitida, Apunte

    bancos_map = {
        b.numero: b
        for b in db.query(Banco).filter(Banco.empresa_id == empresa_id).all()
    }

    creados_banco = 0
    for mov in db.query(MovBanco).filter(MovBanco.empresa_id == empresa_id).all():
        banco = bancos_map.get(mov.banco)
        if not banco or not banco.cuenta:
            continue
        pagos = db.query(Pago).filter(
            Pago.empresa_id == empresa_id,
            Pago.banco == mov.banco,
            Pago.numero == mov.numero,
        ).all()
        if generar_asiento_banco(db, empresa_id, mov, banco, pagos):
            creados_banco += 1

    creados_rec = 0
    for fac in db.query(FacturaRecibida).filter(FacturaRecibida.empresa_id == empresa_id).all():
        apuntes = db.query(Apunte).filter(
            Apunte.empresa_id == empresa_id,
            Apunte.albaran == fac.numero,
            Apunte.talbaran == 'C',
        ).all()
        if generar_asiento_factura_rec(db, empresa_id, fac, apuntes):
            creados_rec += 1

    creados_emi = 0
    for fac in db.query(FacturaEmitida).filter(FacturaEmitida.empresa_id == empresa_id).all():
        apuntes = db.query(Apunte).filter(
            Apunte.empresa_id == empresa_id,
            Apunte.albaran == fac.numero,
            Apunte.talbaran == 'F',
        ).all()
        if generar_asiento_factura_emi(db, empresa_id, fac, apuntes):
            creados_emi += 1

    from app.models.contabilidad import Extra
    creados_extras = 0
    for extra in db.query(Extra).filter(Extra.empresa_id == empresa_id).all():
        if generar_asiento_extra(db, empresa_id, extra):
            creados_extras += 1

    db.commit()
    return {
        'banco': creados_banco,
        'facturas_rec': creados_rec,
        'facturas_emi': creados_emi,
        'extras': creados_extras,
        'total': creados_banco + creados_rec + creados_emi + creados_extras,
    }


# ─── Diagnóstico contable ────────────────────────────────────────────────────

def get_diagnostico(db: Session, empresa_id: int) -> dict:
    """Detecta inconsistencias contables: extras sin asiento, movimientos bancarios
    sin asiento con contraparte conocida, y cuentas de proveedor/acreedor con saldo
    opuesto al esperado (síntoma de asientos incompletos)."""
    from app.models.bancos import Banco, MovBanco, Pago
    from app.models.contabilidad import Extra, ExApunte, Cuenta as CuentaM

    # ── 1. Extras con apuntes D+H completos pero sin asiento EXT ──────────────
    extras_sin_asiento = []
    for x in db.query(Extra).filter(Extra.empresa_id == empresa_id).all():
        aps = db.query(ExApunte).filter(
            ExApunte.empresa_id == empresa_id,
            ExApunte.extra == x.numero,
        ).all()
        d_ok = any(a.dh == 'D' and a.cuenta for a in aps)
        h_ok = any(a.dh == 'H' and a.cuenta for a in aps)
        if d_ok and h_ok:
            tiene = db.query(Diario).filter(
                Diario.empresa_id == empresa_id,
                Diario.tipo == 'X',
                Diario.numero == x.numero,
            ).first()
            if not tiene:
                extras_sin_asiento.append({
                    'numero': x.numero,
                    'texto': x.texto or '',
                    'fecha': str(x.fecha) if x.fecha else None,
                    'estado': x.estado,
                })

    # ── 2. Movimientos bancarios sin asiento con contraparte conocida y directa ─
    # Solo incluye movimientos donde al menos un pago tiene dirsubcta o vto con
    # cuentadef resuelto — excluyendo lados receptores y movimientos sin cuenta.
    # Se muestran los 50 más recientes para evitar listas históricas masivas.
    from app.models.clientes_proveedores import Vencimiento
    bancos_map = {b.numero: b for b in db.query(Banco).filter(
        Banco.empresa_id == empresa_id, Banco.cuenta.isnot(None), Banco.cuenta != '',
    ).all()}
    movs_sin_asiento = []
    movs_ordered = (
        db.query(MovBanco)
        .filter(MovBanco.empresa_id == empresa_id)
        .order_by(MovBanco.fecha.desc(), MovBanco.numero.desc())
        .all()
    )
    for mov in movs_ordered:
        banco = bancos_map.get(mov.banco)
        if not banco:
            continue
        if _ya_tiene_asiento_banco(db, empresa_id, banco.cuenta, mov.numero, banco.numero):
            continue
        pagos = db.query(Pago).filter(
            Pago.empresa_id == empresa_id,
            Pago.banco == mov.banco,
            Pago.numero == mov.numero,
        ).all()
        if not pagos:
            continue
        # Descartar lados receptores de transferencias (dirsubcta == banco.cuenta)
        es_receptor_puro = all(
            (p.dirsubcta == banco.cuenta) or (p.bancot and p.numerot and not p.dirsubcta)
            for p in pagos
        )
        if es_receptor_puro:
            continue
        # Descartar movimientos cubiertos por el asiento del banco contraparte
        # (mismo chequeo que generar_asiento_banco para evitar falsos positivos).
        # Incluye el fallback por fecha+importe: en datos migrados el asiento a
        # veces queda etiquetado con el numero del OTRO lado de la transferencia,
        # no con p.numerot — buscar solo por numero exacto da falsos positivos
        # aquí (el asiento existe pero no se detecta, y se reporta como faltante).
        cubierto_por_otro = False
        for p in pagos:
            if p.bancot and p.numerot:
                banco_t = bancos_map.get(p.bancot)
                if not banco_t or not banco_t.cuenta:
                    continue
                entrada_origen = db.query(Diario).filter(
                    Diario.empresa_id == empresa_id,
                    Diario.tipo == 'B',
                    Diario.numero == p.numerot,
                    Diario.cuenta == banco_t.cuenta,
                ).first()
                if not entrada_origen:
                    mov_t = db.query(MovBanco).filter(
                        MovBanco.empresa_id == empresa_id,
                        MovBanco.banco == p.bancot,
                        MovBanco.numero == p.numerot,
                    ).first()
                    if mov_t:
                        entrada_origen = db.query(Diario).filter(
                            Diario.empresa_id == empresa_id,
                            Diario.tipo == 'B',
                            Diario.cuenta == banco_t.cuenta,
                            Diario.fecha == mov_t.fecha,
                            Diario.importe == (mov_t.total or 0),
                        ).first()
                if entrada_origen and db.query(Diario).filter(
                    Diario.empresa_id == empresa_id,
                    Diario.asiento == entrada_origen.asiento,
                    Diario.cuenta == banco.cuenta,
                ).first():
                    cubierto_por_otro = True
                    break
        if cubierto_por_otro:
            continue

        # Verificar que al menos un pago tiene contrapartida resoluble
        tiene_contra = False
        for p in pagos:
            if p.dirsubcta and p.dirsubcta != banco.cuenta:
                tiene_contra = True
                break
            if p.vto:
                vto = db.query(Vencimiento).filter(
                    Vencimiento.empresa_id == empresa_id,
                    Vencimiento.numero == p.vto,
                ).first()
                if vto and vto.cuentadef:
                    tiene_contra = True
                    break
        if not tiene_contra:
            continue
        movs_sin_asiento.append({
            'banco': mov.banco,
            'banco_nombre': banco.nombre,
            'numero': mov.numero,
            'fecha': str(mov.fecha) if mov.fecha else None,
            'texto': mov.texto or '',
            'total': mov.total or 0,
        })
        if len(movs_sin_asiento) >= 50:
            break

    # ── 3. Cuentas de proveedor/acreedor (40xxxx) con saldo deudor ────────────
    # Saldo deudor en cuenta de proveedor (cta 40xxx) indica que se ha pagado más
    # de lo que se ha registrado como deuda → probable asiento EXT faltante.
    # Se excluyen las cuentas de cliente (43xxxx): ahí un saldo deudor es normal
    # (el cliente nos debe dinero), no un síntoma de asiento incompleto.
    cuentas_desequilibradas = []
    for cta in db.query(CuentaM).filter(
        CuentaM.empresa_id == empresa_id,
        CuentaM.cuenta.like('4%'),
        ~CuentaM.cuenta.like('43%'),
    ).all():
        saldo = (cta.debe or 0) - (cta.haber or 0)
        if saldo > 0.01:
            cuentas_desequilibradas.append({
                'cuenta': cta.cuenta,
                'texto': cta.texto or '',
                'saldo_deudor': saldo,
            })

    return {
        'extras_sin_asiento': extras_sin_asiento,
        'movimientos_sin_asiento': movs_sin_asiento,
        'cuentas_desequilibradas': cuentas_desequilibradas,
        'total_problemas': len(extras_sin_asiento) + len(movs_sin_asiento) + len(cuentas_desequilibradas),
    }


# ─── Balance de situación ─────────────────────────────────────────────────────

def _clasificar_balance(cuenta: str, saldo: float) -> str | None:
    """Clasifica una cuenta en la sección del balance según PGC.
    saldo > 0 = deudor,  saldo < 0 = acreedor
    Retorna: 'ANC'|'AC'|'PN'|'PNC'|'PC'|None
    """
    if not cuenta:
        return None
    p1 = cuenta[0]
    p2 = cuenta[:2]
    if p1 == '2':
        return 'ANC'
    if p1 == '3':
        return 'AC'
    if p1 == '1':
        return 'PN' if p2 in ('10', '11', '12', '13') else 'PNC'
    if p1 in ('4', '5'):
        return 'AC' if saldo >= 0 else 'PC'
    return None  # grupos 6, 7, 8, 9 → P&G, no van al balance


def get_balance_situacion(db: Session, empresa_id: int,
                           fecha_desde=None, fecha_hasta=None) -> dict:
    """Devuelve el balance de situación agrupado por sección."""
    filas, *_ = get_sumas_saldos(db, empresa_id, fecha_desde, fecha_hasta)

    # Resultado del ejercicio (neto 6xxx y 7xxx, contando también saldos de signo contrario)
    gasto   = sum(f['saldo_deudor'] - f['saldo_acreedor'] for f in filas if f['cuenta'] and f['cuenta'].startswith('6'))
    ingreso = sum(f['saldo_acreedor'] - f['saldo_deudor'] for f in filas if f['cuenta'] and f['cuenta'].startswith('7'))
    resultado = round(ingreso - gasto, 2)

    secciones: dict[str, list] = {'ANC': [], 'AC': [], 'PN': [], 'PNC': [], 'PC': []}
    for f in filas:
        saldo = f['saldo_deudor'] - f['saldo_acreedor']
        sec = _clasificar_balance(f['cuenta'], saldo)
        if sec is None:
            continue
        secciones[sec].append({
            'cuenta': f['cuenta'],
            'texto':  f['texto'],
            'importe': round(abs(saldo), 2),
        })

    def total(sec):
        return round(sum(x['importe'] for x in secciones[sec]), 2)

    t_anc = total('ANC')
    t_ac  = total('AC')
    t_pnc = total('PNC')
    t_pc  = total('PC')
    t_pn  = round(total('PN') + resultado, 2)

    return {
        'activo_no_corriente':  secciones['ANC'],
        'activo_corriente':     secciones['AC'],
        'pasivo_no_corriente':  secciones['PNC'],
        'pasivo_corriente':     secciones['PC'],
        'patrimonio_neto':      secciones['PN'],
        'resultado_ejercicio':  resultado,
        'total_anc':  t_anc,
        'total_ac':   t_ac,
        'total_activo': round(t_anc + t_ac, 2),
        'total_pnc':  t_pnc,
        'total_pc':   t_pc,
        'total_pn':   t_pn,
        'total_pasivo_pn': round(t_pnc + t_pc + t_pn, 2),
    }


# ─── Cierre de ejercicio ──────────────────────────────────────────────────────

def realizar_cierre_ejercicio(db: Session, empresa_id: int, anio: int,
                               crear_apertura: bool = True) -> dict:
    """Genera los asientos de regularización, cierre y apertura del ejercicio."""
    from sqlalchemy import text as _text
    fecha_cierre  = datetime.date(anio,     12, 31)
    fecha_apertura = datetime.date(anio + 1, 1,  1)

    # Verificar que no exista ya el cierre
    ya = db.query(Diario).filter(
        Diario.empresa_id == empresa_id,
        Diario.tpasiento  == 'Z',
        Diario.fecha      == fecha_cierre,
    ).first()
    if ya:
        raise ValueError(f"Ya existe asiento de cierre para {anio}")

    # ── 1. Regularización (cierra 6xxx y 7xxx → 1290000) ──────────
    filas, *_ = get_sumas_saldos(db, empresa_id,
                                  datetime.date(anio, 1, 1), fecha_cierre,
                                  excluir_tipos=['R', 'Z'])
    # Regularizar por saldo NETO: también cierra cuentas 6 con saldo acreedor
    # (abonos, rappels) y cuentas 7 con saldo deudor, que antes quedaban abiertas
    lineas_reg = []
    for f in filas:
        c = f['cuenta'] or ''
        if not c.startswith(('6', '7')):
            continue
        net = round(f['saldo_deudor'] - f['saldo_acreedor'], 2)
        if abs(net) < 0.005:
            continue
        lineas_reg.append({'cuenta': c, 'importe': round(-net, 2)})

    if lineas_reg:
        # La línea de resultado equilibra el asiento: >0 pérdida, <0 beneficio
        resultado_imp = round(-sum(l['importe'] for l in lineas_reg), 2)
        lineas_reg.append({'cuenta': '1290000', 'importe': resultado_imp})
        num_reg = _siguiente_asiento(db, empresa_id)
        _crear_lineas_raw(db, empresa_id, num_reg, fecha_cierre,
                          None, None, 'R', 'REGULARIZACION', lineas_reg)
        db.flush()

    # ── 2. Cierre (cierra todas las cuentas de balance) ───────────
    # Calculamos saldos incluyendo ya la regularización
    filas_post, *_ = get_sumas_saldos(db, empresa_id, None, fecha_cierre)
    lineas_cierre = []
    for f in filas_post:
        c = f['cuenta'] or ''
        if c.startswith(('6', '7', '8', '9')):
            continue
        net = round(f['saldo_deudor'] - f['saldo_acreedor'], 2)
        if abs(net) < 0.01:
            continue
        lineas_cierre.append({'cuenta': c, 'importe': round(-net, 2)})

    if lineas_cierre:
        num_cierre = _siguiente_asiento(db, empresa_id)
        _crear_lineas_raw(db, empresa_id, num_cierre, fecha_cierre,
                          None, None, 'Z', 'CIERRE', lineas_cierre)
        db.flush()

    # ── 3. Apertura del ejercicio siguiente ───────────────────────
    n_apertura = 0
    if crear_apertura and lineas_cierre:
        lineas_ap = [{'cuenta': l['cuenta'], 'importe': -l['importe']}
                     for l in lineas_cierre]
        num_ap = _siguiente_asiento(db, empresa_id)
        _crear_lineas_raw(db, empresa_id, num_ap, fecha_apertura,
                          None, None, 'A', 'APERTURA', lineas_ap)
        db.flush()
        n_apertura = len(lineas_ap)

    db.commit()
    return {
        'regularizacion': len(lineas_reg),
        'cierre':         len(lineas_cierre),
        'apertura':       n_apertura,
    }
