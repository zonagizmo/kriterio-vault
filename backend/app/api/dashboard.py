import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.db.database import get_db
from app.models.bancos import Banco
from app.models.facturacion import FacturaEmitida, FacturaRecibida
from app.models.clientes_proveedores import Vencimiento
from app.models.contabilidad import Extra, ExApunte
from app.services import estadisticas as svc_estadisticas

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_MESES_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
             'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


@router.get("")
def resumen(empresa_id: int, db: Session = Depends(get_db)):
    hoy = datetime.date.today()
    primer_dia_mes = hoy.replace(day=1)
    if primer_dia_mes.month == 1:
        primer_dia_mes_ant = primer_dia_mes.replace(year=primer_dia_mes.year - 1, month=12)
    else:
        primer_dia_mes_ant = primer_dia_mes.replace(month=primer_dia_mes.month - 1)
    ultimo_dia_mes_ant = primer_dia_mes - datetime.timedelta(days=1)
    if hoy.month == 12:
        primer_dia_mes_sig = hoy.replace(year=hoy.year + 1, month=1, day=1)
    else:
        primer_dia_mes_sig = hoy.replace(month=hoy.month + 1, day=1)
    ultimo_dia_mes = primer_dia_mes_sig - datetime.timedelta(days=1)

    # Saldos bancarios
    bancos = db.query(Banco).filter(Banco.empresa_id == empresa_id).order_by(Banco.numero).all()
    saldos_bancos = [
        {
            "numero": b.numero,
            "nombre": b.nombre,
            "saldo": round((b.saldoini or 0) + (b.saldoact or 0), 2),
        }
        for b in bancos
    ]

    # Facturas emitidas pendientes de cobro
    cobrar = db.query(func.sum(FacturaEmitida.total)).filter(
        FacturaEmitida.empresa_id == empresa_id,
        FacturaEmitida.estado == 'P',
    ).scalar() or 0

    # Extras de ingreso pendientes de cobro (se suman al "por cobrar" junto a las facturas emitidas)
    cobrar_extras = db.query(func.sum(ExApunte.importe)).join(
        Extra, and_(Extra.empresa_id == ExApunte.empresa_id, Extra.numero == ExApunte.extra)
    ).filter(
        ExApunte.empresa_id == empresa_id,
        Extra.tipo == 'I',
        Extra.estado == 'P',
        ExApunte.dh == 'H',
    ).scalar() or 0
    cobrar += cobrar_extras

    # Facturas recibidas pendientes de pago
    pagar = db.query(func.sum(FacturaRecibida.total)).filter(
        FacturaRecibida.empresa_id == empresa_id,
        FacturaRecibida.estado == 'P',
    ).scalar() or 0

    # Extras de gasto pendientes de pago (se suman al "por pagar" junto a las facturas recibidas)
    pagar_extras = db.query(func.sum(ExApunte.importe)).join(
        Extra, and_(Extra.empresa_id == ExApunte.empresa_id, Extra.numero == ExApunte.extra)
    ).filter(
        ExApunte.empresa_id == empresa_id,
        Extra.tipo == 'G',
        Extra.estado == 'P',
        ExApunte.dh == 'D',
    ).scalar() or 0
    pagar += pagar_extras

    # Ingresos / gastos del mes en curso y del mes anterior (facturas + extras +
    # pagas NNA + cuenta de cheques fundación) — misma lógica que Estadísticas,
    # ver app/services/estadisticas.py
    ingresos_mes = svc_estadisticas.ingresos_periodo(db, empresa_id, primer_dia_mes, ultimo_dia_mes)
    ingresos_mes_ant = svc_estadisticas.ingresos_periodo(db, empresa_id, primer_dia_mes_ant, ultimo_dia_mes_ant)
    gastos_mes = svc_estadisticas.gastos_periodo(db, empresa_id, primer_dia_mes, ultimo_dia_mes)
    gastos_mes_ant = svc_estadisticas.gastos_periodo(db, empresa_id, primer_dia_mes_ant, ultimo_dia_mes_ant)

    # Vencimientos próximos (7 días) con pendiente > 0
    limite_prox = hoy + datetime.timedelta(days=7)
    vtos_proximos = db.query(Vencimiento).filter(
        Vencimiento.empresa_id == empresa_id,
        Vencimiento.pendiente > 0,
        Vencimiento.fecha >= hoy,
        Vencimiento.fecha <= limite_prox,
    ).order_by(Vencimiento.fecha).all()

    vtos_vencidos = db.query(func.count(Vencimiento.id)).filter(
        Vencimiento.empresa_id == empresa_id,
        Vencimiento.pendiente > 0,
        Vencimiento.fecha < hoy,
    ).scalar() or 0

    return {
        "bancos": saldos_bancos,
        "total_bancos": round(sum(b["saldo"] for b in saldos_bancos), 2),
        "cobrar_pendiente": round(float(cobrar), 2),
        "pagar_pendiente": round(float(pagar), 2),
        "ingresos_mes": ingresos_mes,
        "ingresos_mes_anterior": ingresos_mes_ant,
        "gastos_mes": gastos_mes,
        "gastos_mes_anterior": gastos_mes_ant,
        "vencimientos_proximos": [
            {
                "numero": v.numero,
                "tipo": v.tipo,
                "fecha": str(v.fecha),
                "pendiente": round(float(v.pendiente or 0), 2),
                "importe": round(float(v.importe or 0), 2),
            }
            for v in vtos_proximos
        ],
        "vencimientos_vencidos": int(vtos_vencidos),
        "mes_nombre": f"{_MESES_ES[hoy.month - 1]} {hoy.year}",
    }
