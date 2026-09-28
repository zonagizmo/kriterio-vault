"""
Lógica compartida para albaranes, facturas y presupuestos.
Todos comparten el mismo modelo de cabecera + líneas (apuntes).
"""
import time
import logging
import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.facturacion import Apunte

logger = logging.getLogger(__name__)

MAX_INTENTOS_NUMERACION = 5
ESPERA_REINTENTO = 0.05  # segundos, base entre reintentos


# ─── Tipos de documento ───────────────────────────────────────────────────────
# talbaran: 'E'=albarán emitido, 'R'=albarán recibido, 'P'=presupuesto,
#           'K'=pedido proveedor, 'D'=pedido cliente, 'I'=inventario,
#           'F'=factura emitida, 'C'=factura recibida


def calcular_importe_linea(cantidad, precio,
                            dcto1=0, dcto2=0, dcto3=0):
    cantidad = Decimal(str(cantidad or 0))
    precio = Decimal(str(precio or 0))
    dcto1 = Decimal(str(dcto1 or 0))
    dcto2 = Decimal(str(dcto2 or 0))
    dcto3 = Decimal(str(dcto3 or 0))
    neto = (cantidad * precio).quantize(Decimal('0.0001'))
    if dcto1:
        neto = (neto * (1 - dcto1 / 100)).quantize(Decimal('0.0001'))
    if dcto2:
        neto = (neto * (1 - dcto2 / 100)).quantize(Decimal('0.0001'))
    if dcto3:
        neto = (neto * (1 - dcto3 / 100)).quantize(Decimal('0.0001'))
    return neto.quantize(Decimal('0.01'))


def siguiente_numero(db: Session, modelo, empresa_id: int) -> int:
    """Calcula el siguiente número secuencial para un modelo, con protección
    contra race conditions mediante reintento automático ante IntegrityError."""
    from sqlalchemy.exc import IntegrityError
    for intento in range(MAX_INTENTOS_NUMERACION):
        try:
            numero = (db.query(func.max(modelo.numero)).filter(
                modelo.empresa_id == empresa_id
            ).scalar() or 0) + 1
            return numero
        except IntegrityError:
            db.rollback()
            if intento < MAX_INTENTOS_NUMERACION - 1:
                time.sleep(ESPERA_REINTENTO * (2 ** intento))
                continue
            raise


def siguiente_cnumero(db: Session, modelo, empresa_id: int, fecha: datetime.date,
                      tiponum: str = 'N') -> tuple[str, int]:
    """Calcula el siguiente cnumero (nº por año/tipo), con protección contra
    race conditions mediante reintento automático ante IntegrityError."""
    from sqlalchemy.exc import IntegrityError
    for intento in range(MAX_INTENTOS_NUMERACION):
        try:
            anio = fecha.year
            ultimo = db.query(func.max(modelo.cnumero)).filter(
                modelo.empresa_id == empresa_id,
                func.extract('year', modelo.fecha) == anio,
                modelo.tiponum == tiponum,
            ).scalar() or 0
            return tiponum, ultimo + 1
        except IntegrityError:
            db.rollback()
            if intento < MAX_INTENTOS_NUMERACION - 1:
                time.sleep(ESPERA_REINTENTO * (2 ** intento))
                continue
            raise


def guardar_lineas(db: Session, empresa_id: int, albaran: int,
                   talbaran: str, fecha: datetime.date, lineas_data: list) -> list[Apunte]:
    # Borrar líneas anteriores
    db.query(Apunte).filter(
        Apunte.empresa_id == empresa_id,
        Apunte.albaran == albaran,
        Apunte.talbaran == talbaran,
    ).delete()

    nuevas = []
    for ld in lineas_data:
        importe = calcular_importe_linea(
            ld.cantidad or 1, ld.precio or 0,
            ld.dcto1 or 0, ld.dcto2 or 0, ld.dcto3 or 0,
        )
        ap = Apunte(
            empresa_id=empresa_id,
            albaran=albaran,
            talbaran=talbaran,
            fecha=fecha,
            tipo=ld.tipo,
            articulo=ld.articulo,
            texto=ld.texto,
            texto2=ld.texto2,
            cantidad=ld.cantidad or 1,
            precio=ld.precio or 0,
            dcto1=ld.dcto1 or 0,
            dcto2=ld.dcto2 or 0,
            dcto3=ld.dcto3 or 0,
            importe=importe,
            tiva=ld.tiva,
            tipoop=ld.tipoop,
            cuenta=ld.cuenta,
            grupo=ld.grupo,
            almacen=ld.almacen,
        )
        db.add(ap)
        nuevas.append(ap)
    db.flush()
    return nuevas


def get_lineas(db: Session, empresa_id: int, albaran: int, talbaran: str) -> list[Apunte]:
    return db.query(Apunte).filter(
        Apunte.empresa_id == empresa_id,
        Apunte.albaran == albaran,
        Apunte.talbaran == talbaran,
    ).all()


def total_lineas(lineas: list[Apunte]):
    return sum(l.importe or 0 for l in lineas)
