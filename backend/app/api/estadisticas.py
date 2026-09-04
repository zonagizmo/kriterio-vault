import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services import estadisticas as svc
from app.api.contabilidad import _csv_response, _xlsx_response

router = APIRouter(prefix="/api/estadisticas", tags=["estadisticas"])


@router.get("/anios")
def anios(empresa_id: int, db: Session = Depends(get_db)):
    return {"anios": svc.anios_disponibles(db, empresa_id)}


@router.get("")
def resumen(empresa_id: int, anio: int, db: Session = Depends(get_db)):
    desde_anio = datetime.date(anio, 1, 1)
    hasta_anio = datetime.date(anio, 12, 31)
    meses = svc.evolucion_mensual(db, empresa_id, anio)
    return {
        "anio": anio,
        "meses": meses,
        "categorias_gasto": svc.gastos_por_categoria(db, empresa_id, desde_anio, hasta_anio),
        "saldos_bancos": svc.saldos_bancos_mensual(db, empresa_id, anio),
        # Totales del año calculados de forma independiente (no sumando "meses",
        # que arrastra el resultado del mes anterior mes a mes y da un total inflado).
        "ingresos_total": svc.ingresos_periodo(db, empresa_id, desde_anio, hasta_anio),
        "gastos_total": svc.gastos_periodo(db, empresa_id, desde_anio, hasta_anio),
    }


@router.get("/periodo")
def periodo(empresa_id: int, fecha_desde: datetime.date, fecha_hasta: datetime.date, db: Session = Depends(get_db)):
    ingresos = svc.ingresos_periodo(db, empresa_id, fecha_desde, fecha_hasta)
    gastos = svc.gastos_periodo(db, empresa_id, fecha_desde, fecha_hasta)
    return {
        "fecha_desde": str(fecha_desde),
        "fecha_hasta": str(fecha_hasta),
        "ingresos_total": ingresos,
        "gastos_total": gastos,
        "resultado": round(ingresos - gastos, 2),
        "categorias_ingreso": svc.ingresos_por_categoria(db, empresa_id, fecha_desde, fecha_hasta),
        "categorias_gasto": svc.gastos_por_categoria(db, empresa_id, fecha_desde, fecha_hasta),
    }


@router.get("/periodo/ingresos")
def periodo_listado_ingresos(empresa_id: int, fecha_desde: datetime.date, fecha_hasta: datetime.date, db: Session = Depends(get_db)):
    return {"items": svc.listado_ingresos(db, empresa_id, fecha_desde, fecha_hasta)}


@router.get("/periodo/gastos")
def periodo_listado_gastos(empresa_id: int, fecha_desde: datetime.date, fecha_hasta: datetime.date, db: Session = Depends(get_db)):
    return {"items": svc.listado_gastos(db, empresa_id, fecha_desde, fecha_hasta)}


def _fmt_fecha(f) -> str:
    return f.strftime('%d/%m/%Y') if f else ''


def _rows_ingresos(items: list) -> list[list]:
    rows = [['Fecha', 'Origen', 'Concepto', 'Importe']]
    for it in items:
        rows.append([_fmt_fecha(it['fecha']), it['origen'], it['concepto'], it['importe']])
    total = round(sum(it['importe'] or 0 for it in items), 2)
    rows.append(['', '', 'Total', total])
    return rows


def _rows_gastos(items: list) -> list[list]:
    rows = [['Fecha', 'Origen', 'Proveedor', 'Nº Factura', 'Importe']]
    for it in items:
        rows.append([_fmt_fecha(it['fecha']), it['origen'], it['proveedor'], it['nfactura'], it['importe']])
    total = round(sum(it['importe'] or 0 for it in items), 2)
    rows.append(['', '', '', 'Total', total])
    return rows


@router.get("/periodo/ingresos/export")
def export_listado_ingresos(
    empresa_id: int, fecha_desde: datetime.date, fecha_hasta: datetime.date,
    format: str = 'xlsx', db: Session = Depends(get_db),
):
    rows = _rows_ingresos(svc.listado_ingresos(db, empresa_id, fecha_desde, fecha_hasta))
    nombre = f"ingresos_{fecha_desde}_{fecha_hasta}.{format}"
    return _xlsx_response(rows, nombre) if format == 'xlsx' else _csv_response(rows, nombre)


@router.get("/periodo/gastos/export")
def export_listado_gastos(
    empresa_id: int, fecha_desde: datetime.date, fecha_hasta: datetime.date,
    format: str = 'xlsx', db: Session = Depends(get_db),
):
    rows = _rows_gastos(svc.listado_gastos(db, empresa_id, fecha_desde, fecha_hasta))
    nombre = f"gastos_{fecha_desde}_{fecha_hasta}.{format}"
    return _xlsx_response(rows, nombre) if format == 'xlsx' else _csv_response(rows, nombre)
