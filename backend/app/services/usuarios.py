from sqlalchemy.orm import Session
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from app.models.usuarios import UsuarioNNA, PagaNNA
from app.models.clientes_proveedores import Vencimiento
from app.models.contabilidad import Diario, Cuenta
from app.schemas.usuarios import UsuarioCreate, UsuarioUpdate, PagaCreate, RegistroMensualCreate
from app.services.sync import registrar_operacion
import time
import logging
import datetime
import uuid as uuid_lib

logger = logging.getLogger(__name__)


def _cuenta_nna(numero: int) -> str:
    return f"4001{numero:03d}"


# ─── Usuarios NNA ─────────────────────────────────────────────────────────────

def get_usuarios(db: Session, empresa_id: int, activo: bool = None, skip: int = 0, limit: int = 100):
    query = db.query(UsuarioNNA).filter(UsuarioNNA.empresa_id == empresa_id)
    if activo is not None:
        query = query.filter(UsuarioNNA.activo == activo)
    total = query.count()
    items = query.order_by(UsuarioNNA.nombre).offset(skip).limit(limit).all()
    return items, total


def get_usuario(db: Session, usuario_id: int):
    return db.query(UsuarioNNA).filter(UsuarioNNA.id == usuario_id).first()


def get_saldos_nna(db: Session, empresa_id: int) -> dict:
    """Devuelve {numero: saldo} calculado desde diario para todas las cuentas 4001xxx."""
    rows = (
        db.query(
            func.substr(Diario.cuenta, 5),
            func.round(func.sum(Diario.importe), 2),
        )
        .filter(
            Diario.empresa_id == empresa_id,
            Diario.cuenta.like('4001%'),
        )
        .group_by(Diario.cuenta)
        .all()
    )
    return {int(r[0]): float(r[1] or 0) for r in rows}


def create_usuario(db: Session, data: UsuarioCreate) -> dict:
    for intento in range(5):
        try:
            numero = (db.query(func.coalesce(func.max(UsuarioNNA.numero), 0)).filter(
                UsuarioNNA.empresa_id == data.empresa_id
            ).scalar() or 0) + 1
            cuenta = _cuenta_nna(numero)
            nombre = (data.nombre or '').strip()

            nuevo = UsuarioNNA(
                empresa_id=data.empresa_id,
                numero=numero,
                nombre=nombre,
                apellidos=getattr(data, 'apellidos', None),
                fecha_nacimiento=getattr(data, 'fecha_nacimiento', None),
                fecha_ingreso=getattr(data, 'fecha_ingreso', None),
                fecha_salida=getattr(data, 'fecha_salida', None),
                paga_mensual=data.paga_mensual or 0,
                activo=getattr(data, 'activo', True),
                notas=getattr(data, 'notas', None),
                uuid=str(uuid_lib.uuid4()),
                version=1,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            )
            db.add(nuevo)

            # Crear la cuenta 4001xxx si no existe
            existe_cuenta = db.query(Cuenta).filter(
                Cuenta.empresa_id == data.empresa_id,
                Cuenta.cuenta == cuenta,
            ).first()
            if not existe_cuenta:
                db.add(Cuenta(
                    empresa_id=data.empresa_id,
                    cuenta=cuenta,
                    texto=nombre,
                    debe=0,
                    haber=0,
                ))

            registrar_operacion(db, data.empresa_id, 'usuarios_nna', nuevo.uuid, 'C', data.model_dump(mode='json'))
            db.commit()
            db.refresh(nuevo)

            return {
                "id": nuevo.id, "empresa_id": nuevo.empresa_id, "numero": nuevo.numero,
                "nombre": nuevo.nombre, "apellidos": nuevo.apellidos,
                "fecha_nacimiento": nuevo.fecha_nacimiento,
                "fecha_ingreso": nuevo.fecha_ingreso, "fecha_salida": nuevo.fecha_salida,
                "paga_mensual": nuevo.paga_mensual, "activo": nuevo.activo,
                "notas": nuevo.notas,
            }
        except IntegrityError:
            db.rollback()
            if intento < 4:
                time.sleep(0.05 * (2 ** intento))
                continue
            raise


def update_usuario(db: Session, usuario_id: int, data: UsuarioUpdate) -> UsuarioNNA | None:
    u = get_usuario(db, usuario_id)
    if not u:
        return None
    updates = data.model_dump(exclude_unset=True)
    # No permitir vaciar el nombre (columna NOT NULL y rompería el .strip())
    nombre = (updates.get('nombre') or '').strip() if 'nombre' in updates else ''
    if 'nombre' in updates and not nombre:
        updates.pop('nombre')
    u.version = (u.version or 1) + 1
    for k, v in updates.items():
        setattr(u, k, v)
    # Sincronizar nombre en la cuenta contable si cambió
    if nombre:
        cuenta_obj = db.query(Cuenta).filter(
            Cuenta.empresa_id == u.empresa_id,
            Cuenta.cuenta == _cuenta_nna(u.numero),
        ).first()
        if cuenta_obj:
            cuenta_obj.texto = nombre
    registrar_operacion(db, u.empresa_id, 'usuarios_nna', u.uuid, 'U',
                        data.model_dump(exclude_unset=True, mode='json'))
    db.commit()
    db.refresh(u)
    return u


def delete_usuario(db: Session, usuario_id: int) -> bool:
    u = get_usuario(db, usuario_id)
    if not u:
        return False
    n_pagas = db.query(PagaNNA).filter(
        PagaNNA.empresa_id == u.empresa_id,
        PagaNNA.usuario == u.numero,
    ).count()
    if n_pagas:
        raise ValueError(
            f"No se puede eliminar a {u.nombre}: tiene {n_pagas} pagas registradas. "
            "Elimina primero sus pagas."
        )
    n_diario = db.query(func.count(Diario.id)).filter(
        Diario.empresa_id == u.empresa_id,
        Diario.cuenta == _cuenta_nna(u.numero),
    ).scalar()
    if n_diario:
        raise ValueError(
            f"No se puede eliminar a {u.nombre}: su cuenta {_cuenta_nna(u.numero)} "
            f"tiene {n_diario} apuntes en el diario."
        )
    entidad_uuid, empresa_id = u.uuid, u.empresa_id
    db.delete(u)
    registrar_operacion(db, empresa_id, 'usuarios_nna', entidad_uuid, 'D')
    db.commit()
    return True


# ─── Pagas ────────────────────────────────────────────────────────────────────

def get_pagas(db: Session, empresa_id: int, usuario: int = None,
              fecha_desde: datetime.date = None, fecha_hasta: datetime.date = None,
              skip: int = 0, limit: int = 100,
              sort_by: str = 'fecha', sort_dir: str = 'desc'):
    query = db.query(PagaNNA).filter(PagaNNA.empresa_id == empresa_id)
    if usuario is not None:
        query = query.filter(PagaNNA.usuario == usuario)
    if fecha_desde:
        query = query.filter(PagaNNA.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(PagaNNA.fecha <= fecha_hasta)
    total = query.count()

    query = query.outerjoin(
        UsuarioNNA,
        (UsuarioNNA.empresa_id == PagaNNA.empresa_id) & (UsuarioNNA.numero == PagaNNA.usuario),
    )
    asc = sort_dir != 'desc'
    if sort_by == 'usuario':
        criterios = [UsuarioNNA.nombre, UsuarioNNA.apellidos] if asc else \
                    [UsuarioNNA.nombre.desc(), UsuarioNNA.apellidos.desc()]
        criterios += [PagaNNA.fecha.desc(), PagaNNA.id.desc()]
    elif sort_by == 'importe':
        criterios = [PagaNNA.importe.asc() if asc else PagaNNA.importe.desc(),
                     PagaNNA.fecha.desc(), PagaNNA.id.desc()]
    else:  # 'fecha' (por defecto)
        criterios = [PagaNNA.fecha.asc() if asc else PagaNNA.fecha.desc(),
                     UsuarioNNA.nombre, UsuarioNNA.apellidos, PagaNNA.id.desc()]
    items = query.order_by(*criterios).offset(skip).limit(limit).all()
    return items, total


def _crear_diario_paga(db: Session, empresa_id: int, paga_id: int,
                       usuario_numero: int, fecha: datetime.date, importe: float):
    """Crea las dos líneas de diario para una paga NNA: DR 6780007 / CR 4001xxx.
    Actualiza también la caché debe/haber de cuentas (usada por el diagnóstico).
    Protegido contra race conditions con reintento automático."""
    for intento in range(5):
        try:
            asiento = (db.query(func.coalesce(func.max(Diario.asiento), 0)).filter(
                Diario.empresa_id == empresa_id
            ).scalar() or 0) + 1
            cuenta_nna = _cuenta_nna(usuario_numero)
            clave = f"PAG{paga_id}"
            imp = round(importe, 2)

            db.add(Diario(
                empresa_id=empresa_id, asiento=asiento, fecha=fecha,
                tpasiento='PAG', clave=clave, tipo='P', numero=paga_id,
                importe=imp, cuenta='6780007', saldo=0,
            ))
            cuenta_678 = db.query(Cuenta).filter(
                Cuenta.empresa_id == empresa_id,
                Cuenta.cuenta == '6780007',
            ).first()
            if cuenta_678:
                cuenta_678.debe = round((cuenta_678.debe or 0) + imp, 2)

            db.add(Diario(
                empresa_id=empresa_id, asiento=asiento, fecha=fecha,
                tpasiento='PAG', clave=clave, tipo='P', numero=paga_id,
                importe=round(-importe, 2), cuenta=cuenta_nna, saldo=0,
            ))
            cuenta_nna_obj = db.query(Cuenta).filter(
                Cuenta.empresa_id == empresa_id,
                Cuenta.cuenta == cuenta_nna,
            ).first()
            if cuenta_nna_obj:
                cuenta_nna_obj.haber = round((cuenta_nna_obj.haber or 0) + imp, 2)
            return
        except IntegrityError:
            db.rollback()
            if intento < 4:
                time.sleep(0.05 * (2 ** intento))
                continue
            raise


def _borrar_diario_paga(db: Session, empresa_id: int, paga_id: int):
    """Elimina las entradas de diario de una paga NNA y revierte la caché de cuentas."""
    lineas = db.query(Diario).filter(
        Diario.empresa_id == empresa_id,
        Diario.tipo == 'P',
        Diario.numero == paga_id,
    ).all()
    for l in lineas:
        if not l.cuenta:
            continue
        imp = round(float(l.importe or 0), 2)
        cuenta_obj = db.query(Cuenta).filter(
            Cuenta.empresa_id == empresa_id,
            Cuenta.cuenta == l.cuenta,
        ).first()
        if cuenta_obj and imp > 0:
            cuenta_obj.debe = round((cuenta_obj.debe or 0) - imp, 2)
        elif cuenta_obj and imp < 0:
            cuenta_obj.haber = round((cuenta_obj.haber or 0) - abs(imp), 2)
        db.delete(l)


def _crear_vencimiento_paga(db: Session, empresa_id: int, paga_id: int,
                             usuario_numero: int, fecha: datetime.date, importe: float):
    """Crea un vencimiento tipo 'N' para que la paga pueda pagarse desde un banco."""
    from app.services.bancos import siguiente_numero_vencimiento
    vto = Vencimiento(
        empresa_id=empresa_id,
        numero=siguiente_numero_vencimiento(db, empresa_id),
        tipo='N',
        tpnumero=paga_id,
        fecha=fecha,
        importe=round(importe, 2),
        pendiente=round(importe, 2),
        cuentadef=_cuenta_nna(usuario_numero),
    )
    db.add(vto)


def _borrar_vencimiento_paga(db: Session, empresa_id: int, paga_id: int):
    """Elimina el vencimiento asociado a una paga NNA.
    Lanza ValueError si tiene pagos bancarios asociados (borraría el rastro del pago)."""
    from app.models.bancos import Pago
    vtos = db.query(Vencimiento).filter(
        Vencimiento.empresa_id == empresa_id,
        Vencimiento.tipo == 'N',
        Vencimiento.tpnumero == paga_id,
    ).all()
    for vto in vtos:
        pago = db.query(Pago).filter(
            Pago.empresa_id == empresa_id,
            Pago.vto == vto.numero,
        ).first()
        if pago:
            raise ValueError(
                f"No se puede eliminar la paga: su vencimiento nº {vto.numero} está pagado "
                f"por el banco {pago.banco} (movimiento {pago.numero}). "
                "Elimina primero ese movimiento bancario."
            )
        db.delete(vto)


def create_paga(db: Session, data: PagaCreate) -> PagaNNA:
    nuevo_uuid = str(uuid_lib.uuid4())
    ahora = datetime.datetime.utcnow()
    paga = PagaNNA(
        empresa_id=data.empresa_id,
        usuario=data.usuario,
        fecha=data.fecha,
        importe=round(data.importe, 2),
        notas=data.notas,
        uuid=nuevo_uuid,
        version=1,
        created_at=ahora,
        updated_at=ahora,
    )
    db.add(paga)
    db.flush()
    paga_id = paga.id

    _crear_diario_paga(db, data.empresa_id, paga_id, data.usuario, data.fecha, data.importe)
    _crear_vencimiento_paga(db, data.empresa_id, paga_id, data.usuario, data.fecha, data.importe)
    registrar_operacion(db, data.empresa_id, 'pagas_nna', nuevo_uuid, 'C', data.model_dump(mode='json'))
    db.commit()

    return db.query(PagaNNA).filter(PagaNNA.id == paga_id).first()


def delete_paga(db: Session, paga_id: int) -> bool:
    p = db.query(PagaNNA).filter(PagaNNA.id == paga_id).first()
    if not p:
        return False
    entidad_uuid, empresa_id = p.uuid, p.empresa_id
    _borrar_vencimiento_paga(db, p.empresa_id, paga_id)  # lanza ValueError si está pagada por banco
    _borrar_diario_paga(db, p.empresa_id, paga_id)
    db.delete(p)
    registrar_operacion(db, empresa_id, 'pagas_nna', entidad_uuid, 'D')
    db.commit()
    return True


def registrar_mes(db: Session, data: RegistroMensualCreate) -> list[PagaNNA]:
    """Registra las pagas mensuales para varios usuarios y crea entradas de diario.
    Guarda anti-duplicados: se omiten los usuarios que ya tienen una paga registrada
    en el mismo mes (evita dobles registros por doble clic o reintento). Las pagas
    extra dentro del mes pueden registrarse individualmente."""
    # Usuarios con paga ya registrada en el mes de data.fecha
    ya_pagados = {
        r[0] for r in db.query(PagaNNA.usuario).filter(
            PagaNNA.empresa_id == data.empresa_id,
            func.strftime('%Y-%m', PagaNNA.fecha) == data.fecha.strftime('%Y-%m'),
        ).distinct().all()
    }
    pagas = []
    for item in data.items:
        if item.importe <= 0:
            continue
        if item.usuario in ya_pagados:
            continue
        nuevo_uuid = str(uuid_lib.uuid4())
        ahora = datetime.datetime.utcnow()
        paga = PagaNNA(
            empresa_id=data.empresa_id,
            usuario=item.usuario,
            fecha=data.fecha,
            importe=round(item.importe, 2),
            notas=item.notas,
            uuid=nuevo_uuid,
            version=1,
            created_at=ahora,
            updated_at=ahora,
        )
        db.add(paga)
        db.flush()
        paga_id = paga.id
        _crear_diario_paga(db, data.empresa_id, paga_id, item.usuario, data.fecha, item.importe)
        _crear_vencimiento_paga(db, data.empresa_id, paga_id, item.usuario, data.fecha, item.importe)
        registrar_operacion(db, data.empresa_id, 'pagas_nna', nuevo_uuid, 'C', {
            'empresa_id': data.empresa_id, 'usuario': item.usuario,
            'fecha': data.fecha.isoformat(), 'importe': item.importe, 'notas': item.notas,
        })
        pagas.append(paga_id)

    db.commit()
    return db.query(PagaNNA).filter(PagaNNA.id.in_(pagas)).order_by(PagaNNA.id).all()


def get_activos_con_paga(db: Session, empresa_id: int) -> list[UsuarioNNA]:
    """Devuelve usuarios activos que tienen paga mensual configurada."""
    return (db.query(UsuarioNNA)
            .filter(
                UsuarioNNA.empresa_id == empresa_id,
                UsuarioNNA.activo == True,
                UsuarioNNA.paga_mensual > 0,
            )
            .order_by(UsuarioNNA.nombre)
            .all())


def resumen_pagas(db: Session, empresa_id: int, fecha_desde: datetime.date, fecha_hasta: datetime.date):
    """Total pagado por usuario en un rango de fechas."""
    rows = (db.query(PagaNNA.usuario, func.sum(PagaNNA.importe).label('total'))
            .filter(
                PagaNNA.empresa_id == empresa_id,
                PagaNNA.fecha >= fecha_desde,
                PagaNNA.fecha <= fecha_hasta,
            )
            .group_by(PagaNNA.usuario)
            .all())
    return {r.usuario: float(r.total) for r in rows}


def anios_pagas(db: Session, empresa_id: int) -> list:
    """Años con al menos una paga registrada (módulo dedicado o Extras 'M'
    migrados), más recientes primero."""
    from app.models.contabilidad import Extra

    rows = db.query(func.strftime('%Y', PagaNNA.fecha)).filter(
        PagaNNA.empresa_id == empresa_id,
    ).distinct().all()
    rows_legacy = db.query(func.strftime('%Y', Extra.fecha)).filter(
        Extra.empresa_id == empresa_id, Extra.tipo == 'M',
    ).distinct().all()
    anios = sorted({int(r[0]) for r in rows + rows_legacy if r[0]}, reverse=True)
    if not anios:
        anios = [datetime.date.today().year]
    return anios


def resumen_pagas_anual(db: Session, empresa_id: int, anio: int) -> dict:
    """Para cada usuario NNA (incluye de baja si tuvo pagas ese año): nombre,
    importe de cada uno de los 12 meses y total anual. También el total por mes
    sumando todos los usuarios.

    Combina las pagas del módulo dedicado (tabla PagaNNA, activo desde
    2026-06-30) con las pagas anteriores a esa fecha, que se registraban como
    Extras tipo 'M' con un apunte en Haber a la cuenta 4001xxx del NNA — sin
    esto, el resumen se queda corto en cualquier periodo anterior a esa fecha."""
    from app.models.contabilidad import Extra, ExApunte

    por_usuario: dict[int, list] = {}

    mes_expr = func.strftime('%m', PagaNNA.fecha)
    rows = (db.query(PagaNNA.usuario, mes_expr.label('mes'), func.sum(PagaNNA.importe).label('total'))
            .filter(
                PagaNNA.empresa_id == empresa_id,
                func.strftime('%Y', PagaNNA.fecha) == str(anio),
            )
            .group_by(PagaNNA.usuario, mes_expr)
            .all())
    for usuario, mes, total in rows:
        meses = por_usuario.setdefault(usuario, [0.0] * 12)
        meses[int(mes) - 1] += float(total)

    mes_expr_ex = func.strftime('%m', Extra.fecha)
    rows_legacy = (db.query(ExApunte.cuenta, mes_expr_ex.label('mes'), func.sum(ExApunte.importe).label('total'))
            .join(Extra, (Extra.empresa_id == ExApunte.empresa_id) & (Extra.numero == ExApunte.extra))
            .filter(
                Extra.empresa_id == empresa_id,
                Extra.tipo == 'M',
                ExApunte.dh == 'H',
                ExApunte.cuenta.like('4001%'),
                func.strftime('%Y', Extra.fecha) == str(anio),
            )
            .group_by(ExApunte.cuenta, mes_expr_ex)
            .all())
    for cuenta, mes, total in rows_legacy:
        usuario = int(cuenta[4:])
        meses = por_usuario.setdefault(usuario, [0.0] * 12)
        meses[int(mes) - 1] += float(total)

    numeros = list(por_usuario.keys())
    nombres = {u.numero: f"{u.nombre} {u.apellidos or ''}".strip() for u in db.query(UsuarioNNA).filter(
        UsuarioNNA.empresa_id == empresa_id, UsuarioNNA.numero.in_(numeros),
    ).all()} if numeros else {}

    usuarios = []
    for numero, meses in por_usuario.items():
        usuarios.append({
            "usuario": numero,
            "nombre": nombres.get(numero) or f"#{numero}",
            "meses": [round(m, 2) for m in meses],
            "total": round(sum(meses), 2),
        })
    usuarios.sort(key=lambda u: u["nombre"])

    totales_mes = [round(sum(u["meses"][i] for u in usuarios), 2) for i in range(12)]
    total_anual = round(sum(totales_mes), 2)

    return {"usuarios": usuarios, "totales_mes": totales_mes, "total_anual": total_anual}
