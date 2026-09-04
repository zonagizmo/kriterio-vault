from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import datetime
from app.db.database import get_db
from app.models.contabilidad import Cuenta
from app.schemas.contabilidad import (
    CuentaRead, CuentaCreate, CuentaUpdate,
    DiarioLineaRead, AsientoCreate, AsientoRead,
)
from app.services import contabilidad as svc

router = APIRouter(prefix="/api/contabilidad", tags=["contabilidad"])


# ─── Plan de cuentas ─────────────────────────────────────────────────────────

@router.get("/cuentas", response_model=dict)
def listar_cuentas(
    empresa_id: int,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    solo_con_saldo: bool = False,
    db: Session = Depends(get_db),
):
    items, total = svc.get_cuentas(db, empresa_id, q, skip, limit, solo_con_saldo)
    # items can be dicts (from raw SQL) or ORM objects — model_validate handles both
    return {"total": total, "items": [
        CuentaRead.model_validate(i, from_attributes=isinstance(i, Cuenta)) for i in items
    ]}


@router.post("/cuentas", response_model=CuentaRead, status_code=201)
def crear_cuenta(data: CuentaCreate, db: Session = Depends(get_db)):
    return svc.create_cuenta(db, data)


@router.put("/cuentas/{cuenta_id}", response_model=CuentaRead)
def actualizar_cuenta(cuenta_id: int, data: CuentaUpdate, db: Session = Depends(get_db)):
    c = svc.update_cuenta(db, cuenta_id, data)
    if not c:
        raise HTTPException(404, "Cuenta no encontrada")
    return c


@router.delete("/cuentas/{cuenta_id}", status_code=204)
def eliminar_cuenta(cuenta_id: int, db: Session = Depends(get_db)):
    try:
        if not svc.delete_cuenta(db, cuenta_id):
            raise HTTPException(404, "Cuenta no encontrada")
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))


# ─── Asientos del diario ──────────────────────────────────────────────────────

@router.get("/asientos", response_model=dict)
def listar_asientos(
    empresa_id: int,
    fecha_desde: Optional[datetime.date] = None,
    fecha_hasta: Optional[datetime.date] = None,
    cuenta: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    orden: str = "fecha",
    db: Session = Depends(get_db),
):
    items, total = svc.get_asientos(db, empresa_id, fecha_desde, fecha_hasta, cuenta, skip, limit, orden)
    return {"total": total, "items": [AsientoRead.model_validate(i) for i in items]}


@router.get("/asientos/{asiento_num}", response_model=AsientoRead)
def obtener_asiento(asiento_num: int, empresa_id: int, db: Session = Depends(get_db)):
    a = svc.get_asiento(db, empresa_id, asiento_num)
    if not a:
        raise HTTPException(404, "Asiento no encontrado")
    return a


def _validar_cuadre(data: AsientoCreate):
    """El cuadre debe validarse también en el servidor: un asiento descuadrado
    rompe el balance de toda la contabilidad."""
    if not data.lineas:
        raise HTTPException(400, "El asiento debe tener al menos una línea")
    descuadre = round(sum(float(l.importe or 0) for l in data.lineas), 2)
    if abs(descuadre) >= 0.01:
        raise HTTPException(400, f"El asiento no está cuadrado (diferencia {descuadre:+.2f})")


@router.post("/asientos", response_model=AsientoRead, status_code=201)
def crear_asiento(data: AsientoCreate, db: Session = Depends(get_db)):
    _validar_cuadre(data)
    return svc.create_asiento(db, data)


@router.put("/asientos/{asiento_num}", response_model=AsientoRead)
def actualizar_asiento(asiento_num: int, data: AsientoCreate, db: Session = Depends(get_db)):
    _validar_cuadre(data)
    a = svc.update_asiento(db, data.empresa_id, asiento_num, data)
    if not a:
        raise HTTPException(404, "Asiento no encontrado")
    return a


@router.delete("/asientos/{asiento_num}", status_code=204)
def eliminar_asiento(asiento_num: int, empresa_id: int, force: bool = False, db: Session = Depends(get_db)):
    try:
        if not svc.delete_asiento(db, empresa_id, asiento_num, force=force):
            raise HTTPException(404, "Asiento no encontrado")
    except ValueError as e:
        raise HTTPException(409, str(e))


# ─── Libro mayor ─────────────────────────────────────────────────────────────

@router.get("/diagnostico", response_model=dict)
def diagnostico_contable(empresa_id: int, db: Session = Depends(get_db)):
    return svc.get_diagnostico(db, empresa_id)


@router.post("/generar-pendientes", response_model=dict)
def generar_pendientes(empresa_id: int, db: Session = Depends(get_db)):
    return svc.generar_asientos_pendientes(db, empresa_id)


@router.post("/regenerar-asiento-banco", response_model=dict)
def regenerar_asiento_banco(
    empresa_id: int,
    banco: int,
    numero: int,
    db: Session = Depends(get_db),
):
    try:
        return svc.regenerar_asiento_movimiento(db, empresa_id, banco, numero)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ─── Balance de sumas y saldos ────────────────────────────────────────────────

@router.get("/conciliacion-bancos", response_model=list)
def conciliacion_bancos(empresa_id: int, db: Session = Depends(get_db)):
    return svc.get_conciliacion_bancos(db, empresa_id)


@router.get("/sumas-saldos", response_model=dict)
def sumas_saldos(
    empresa_id: int,
    fecha_desde: Optional[datetime.date] = None,
    fecha_hasta: Optional[datetime.date] = None,
    nivel: Optional[int] = None,
    db: Session = Depends(get_db),
):
    filas, td, th, tsd, tsa = svc.get_sumas_saldos(db, empresa_id, fecha_desde, fecha_hasta, nivel)
    return {
        'filas': filas,
        'total_debe': td,
        'total_haber': th,
        'total_saldo_deudor': tsd,
        'total_saldo_acreedor': tsa,
    }


@router.get("/pyg", response_model=dict)
def pyg(
    empresa_id: int,
    fecha_desde: Optional[datetime.date] = None,
    fecha_hasta: Optional[datetime.date] = None,
    db: Session = Depends(get_db),
):
    return svc.get_pyg(db, empresa_id, fecha_desde, fecha_hasta)


@router.get("/mayor", response_model=dict)
def libro_mayor(
    empresa_id: int,
    cuenta: str,
    fecha_desde: Optional[datetime.date] = None,
    fecha_hasta: Optional[datetime.date] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    items, total, saldo_anterior = svc.get_mayor(db, empresa_id, cuenta, fecha_desde, fecha_hasta, skip, limit)
    return {"total": total, "saldo_anterior": saldo_anterior, "items": [DiarioLineaRead.model_validate(i) for i in items]}

# ─── Balance de situación ─────────────────────────────────────────────────────

@router.get("/balance")
def balance_situacion(
    empresa_id: int,
    fecha_desde: Optional[datetime.date] = None,
    fecha_hasta: Optional[datetime.date] = None,
    db: Session = Depends(get_db),
):
    return svc.get_balance_situacion(db, empresa_id, fecha_desde, fecha_hasta)


# ─── Cierre de ejercicio ──────────────────────────────────────────────────────

@router.post("/cierre")
def cierre_ejercicio(
    empresa_id: int,
    anio: int,
    crear_apertura: bool = True,
    db: Session = Depends(get_db),
):
    try:
        return svc.realizar_cierre_ejercicio(db, empresa_id, anio, crear_apertura)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ─── Exportar a CSV / XLSX ────────────────────────────────────────────────────

import csv, io
from fastapi.responses import StreamingResponse


def _csv_response(rows: list[list], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    for row in rows:
        w.writerow(row)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type='text/csv; charset=utf-8-sig',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


def _xlsx_response(rows: list[list], filename: str) -> StreamingResponse:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Mayor"
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF")
    for ci, val in enumerate(rows[0], 1):
        cell = ws.cell(row=1, column=ci, value=val)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    for ri, row in enumerate(rows[1:], 2):
        for ci, val in enumerate(row, 1):
            ws.cell(row=ri, column=ci, value=val)
    for col in ws.columns:
        max_len = max((len(str(c.value or '')) for c in col), default=8)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.get("/export/diario")
def export_diario(
    empresa_id: int,
    fecha_desde: Optional[datetime.date] = None,
    fecha_hasta: Optional[datetime.date] = None,
    db: Session = Depends(get_db),
):
    from app.models.contabilidad import Diario
    query = db.query(Diario).filter(Diario.empresa_id == empresa_id)
    if fecha_desde:
        query = query.filter(Diario.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Diario.fecha <= fecha_hasta)
    lineas = query.order_by(Diario.fecha, Diario.asiento).all()

    rows = [['Asiento', 'Fecha', 'Tipo', 'Referencia', 'Cuenta', 'Importe']]
    for l in lineas:
        rows.append([l.asiento, str(l.fecha), l.tpasiento or '', l.clave or '',
                     l.cuenta or '', str(l.importe or 0).replace('.', ',')])
    nombre = f"diario_{empresa_id}_{fecha_desde or 'inicio'}_{fecha_hasta or 'hoy'}.csv"
    return _csv_response(rows, nombre)


_COLS_MAYOR_ORDEN = [
    'fecha', 'asiento', 'tipo', 'tipo_doc', 'numero_doc',
    'referencia', 'desc_cuenta', 'concepto', 'notas',
    'cuenta_contra', 'desc_contra',
    'debe', 'haber', 'saldo',
]
_COLS_MAYOR_CAB = {
    'fecha':          'Fecha',
    'asiento':        'N.º Asiento',
    'tipo':           'Tipo asiento',
    'tipo_doc':       'Tipo doc.',
    'numero_doc':     'N.º documento',
    'referencia':     'Referencia',
    'desc_cuenta':    'Descripción cuenta',
    'concepto':       'Concepto tercero',
    'notas':          'Notas',
    'cuenta_contra':  'Cuenta contrapartida',
    'desc_contra':    'Descripción contrapartida',
    'debe':           'Debe',
    'haber':          'Haber',
    'saldo':          'Saldo',
}
_COLS_MAYOR_DEFAULT = ['fecha', 'asiento', 'tipo', 'referencia', 'debe', 'haber', 'saldo']


@router.get("/export/mayor")
def export_mayor(
    empresa_id: int,
    cuenta: str,
    fecha_desde: Optional[datetime.date] = None,
    fecha_hasta: Optional[datetime.date] = None,
    columnas: Optional[str] = None,
    formato: Optional[str] = 'csv',
    cabeceras_custom: Optional[str] = None,
    nombre: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from app.models.contabilidad import Diario as DiarioModel, DiarioTxt, Cuenta as CuentaModel
    from collections import defaultdict
    items, _, _ = svc.get_mayor(db, empresa_id, cuenta, fecha_desde, fecha_hasta, skip=0, limit=99999)
    cols = ([c.strip() for c in columnas.split(',') if c.strip() in _COLS_MAYOR_ORDEN]
            if columnas else _COLS_MAYOR_DEFAULT)

    necesita_desc    = 'desc_cuenta' in cols or 'desc_contra' in cols
    necesita_diatxt  = 'concepto' in cols or 'notas' in cols
    necesita_contra  = 'cuenta_contra' in cols or 'desc_contra' in cols
    cuenta_map   = {}
    concepto_map = {}
    notas_map    = {}
    contra_map   = defaultdict(list)

    if necesita_desc:
        for c in db.query(CuentaModel).filter(CuentaModel.empresa_id == empresa_id).all():
            cuenta_map[c.cuenta] = c.texto or ''
    if necesita_diatxt:
        for d in db.query(DiarioTxt).filter(DiarioTxt.empresa_id == empresa_id).all():
            key = (d.tipo, d.numero)
            concepto_map[key] = d.texto or ''
            notas_map[key]    = d.notas or ''
    if necesita_contra:
        asiento_nums = list({l.asiento for l in items})
        otras = db.query(DiarioModel).filter(
            DiarioModel.empresa_id == empresa_id,
            DiarioModel.asiento.in_(asiento_nums),
            DiarioModel.cuenta.isnot(None),
            DiarioModel.cuenta != cuenta,
        ).all()
        vistas = defaultdict(set)
        for o in otras:
            if o.cuenta not in vistas[o.asiento]:
                vistas[o.asiento].add(o.cuenta)
                contra_map[o.asiento].append(o.cuenta)

    es_xlsx = (formato == 'xlsx')

    def _fmt_num(v):
        return v if es_xlsx else str(v).replace('.', ',')

    if cabeceras_custom:
        cab_lista = cabeceras_custom.split('|')
        header = cab_lista if len(cab_lista) == len(cols) else [_COLS_MAYOR_CAB[c] for c in cols]
    else:
        header = [_COLS_MAYOR_CAB[c] for c in cols]
    rows = [header]
    saldo = 0.0
    for l in items:
        imp = float(l.importe or 0)
        saldo = round(saldo + imp, 2)
        debe  = round(imp, 2) if imp > 0 else 0
        haber = round(-imp, 2) if imp < 0 else 0
        contras = contra_map.get(l.asiento, [])
        fecha_str = l.fecha.strftime('%d/%m/%Y') if l.fecha else ''
        fila = []
        for c in cols:
            if   c == 'fecha':          fila.append(fecha_str)
            elif c == 'asiento':        fila.append(l.asiento)
            elif c == 'tipo':           fila.append(l.tpasiento or '')
            elif c == 'tipo_doc':       fila.append(l.tipo or '')
            elif c == 'numero_doc':     fila.append(l.numero if l.numero else '')
            elif c == 'referencia':     fila.append(l.clave or '')
            elif c == 'desc_cuenta':    fila.append(cuenta_map.get(l.cuenta, ''))
            elif c == 'concepto':       fila.append(concepto_map.get((l.tipo, l.numero), ''))
            elif c == 'notas':          fila.append(notas_map.get((l.tipo, l.numero), ''))
            elif c == 'cuenta_contra':  fila.append(' / '.join(contras))
            elif c == 'desc_contra':    fila.append(' / '.join(cuenta_map.get(ct, ct) for ct in contras))
            elif c == 'debe':           fila.append(_fmt_num(debe))
            elif c == 'haber':          fila.append(_fmt_num(haber))
            elif c == 'saldo':          fila.append(_fmt_num(saldo))
        rows.append(fila)

    import re
    base = re.sub(r'[^\w\- ]', '_', nombre).strip() if nombre else f"mayor_{cuenta}_{empresa_id}"
    if es_xlsx:
        return _xlsx_response(rows, f"{base}.xlsx")
    return _csv_response(rows, f"{base}.csv")


@router.get("/export/sumas-saldos")
def export_sumas_saldos(
    empresa_id: int,
    fecha_desde: Optional[datetime.date] = None,
    fecha_hasta: Optional[datetime.date] = None,
    db: Session = Depends(get_db),
):
    filas, td, th, tsd, tsa = svc.get_sumas_saldos(db, empresa_id, fecha_desde, fecha_hasta)
    rows = [['Cuenta', 'Descripción', 'Debe', 'Haber', 'Saldo Deudor', 'Saldo Acreedor']]
    for f in filas:
        rows.append([f['cuenta'], f['texto'],
                     str(f['debe']).replace('.', ','), str(f['haber']).replace('.', ','),
                     str(f['saldo_deudor']).replace('.', ','), str(f['saldo_acreedor']).replace('.', ',')])
    rows.append(['TOTALES', '', str(td).replace('.', ','), str(th).replace('.', ','),
                 str(tsd).replace('.', ','), str(tsa).replace('.', ',')])
    return _csv_response(rows, f"sumas_saldos_{empresa_id}.csv")


@router.get("/export/pyg")
def export_pyg(
    empresa_id: int,
    fecha_desde: Optional[datetime.date] = None,
    fecha_hasta: Optional[datetime.date] = None,
    db: Session = Depends(get_db),
):
    # Mismos datos que la pantalla PyG (svc.get_pyg): importes netos por cuenta,
    # exclusión de apertura y saldo inicial de bancos incluidos
    d = svc.get_pyg(db, empresa_id, fecha_desde, fecha_hasta)
    rows = [['Tipo', 'Cuenta', 'Descripción', 'Importe']]
    for f in d['ingresos']:
        rows.append(['Ingreso', f['cuenta'], f['texto'],
                     str(f['importe']).replace('.', ',')])
    for f in d['gastos']:
        rows.append(['Gasto', f['cuenta'], f['texto'],
                     str(f['importe']).replace('.', ',')])
    rows.append(['', '', 'TOTAL INGRESOS', str(d['total_ingresos']).replace('.', ',')])
    rows.append(['', '', 'TOTAL GASTOS',   str(d['total_gastos']).replace('.', ',')])
    rows.append(['', '', 'RESULTADO',      str(d['resultado']).replace('.', ',')])
    rows.append(['', '', 'SALDO INICIAL BANCOS', str(d['saldo_inicial_bancos']).replace('.', ',')])
    rows.append(['', '', 'RESULTADO CON SALDO INICIAL', str(d['resultado_con_saldo_inicial']).replace('.', ',')])
    return _csv_response(rows, f"pyg_{empresa_id}.csv")


@router.get("/export/balance")
def export_balance(
    empresa_id: int,
    fecha_desde: Optional[datetime.date] = None,
    fecha_hasta: Optional[datetime.date] = None,
    db: Session = Depends(get_db),
):
    d = svc.get_balance_situacion(db, empresa_id, fecha_desde, fecha_hasta)
    rows = [['Sección', 'Cuenta', 'Descripción', 'Importe']]
    labels = {
        'activo_no_corriente': 'Activo No Corriente',
        'activo_corriente':    'Activo Corriente',
        'patrimonio_neto':     'Patrimonio Neto',
        'pasivo_no_corriente': 'Pasivo No Corriente',
        'pasivo_corriente':    'Pasivo Corriente',
    }
    for key, label in labels.items():
        for item in d[key]:
            rows.append([label, item['cuenta'], item['texto'],
                         str(item['importe']).replace('.', ',')])
        if key == 'patrimonio_neto':
            rows.append(['Patrimonio Neto', '1290000', 'Resultado del ejercicio',
                         str(d['resultado_ejercicio']).replace('.', ',')])
    rows.append(['', '', 'TOTAL ACTIVO',      str(d['total_activo']).replace('.', ',')])
    rows.append(['', '', 'TOTAL PASIVO + PN', str(d['total_pasivo_pn']).replace('.', ',')])
    return _csv_response(rows, f"balance_{empresa_id}.csv")
