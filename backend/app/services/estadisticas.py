import datetime
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.models.facturacion import FacturaEmitida, FacturaRecibida
from app.models.contabilidad import Diario, Extra
from app.models.bancos import Banco, MovBanco
from app.models.clientes_proveedores import Cliente, Proveedor
from app.models.usuarios import PagaNNA, UsuarioNNA

CUENTA_GASTOS_GENERALES = '6780000'
CUENTA_PAGAS_NNA = '6780007'
CUENTA_SALIDAS_TERAPEUTICAS = '6780008'
CUENTAS_GASTO_EXTRAS = (CUENTA_GASTOS_GENERALES, CUENTA_PAGAS_NNA, CUENTA_SALIDAS_TERAPEUTICAS)

# Ingresos que no pasan por Facturas ni Extras (cheques de fundación ingresados
# directamente en banco)
CUENTAS_INGRESO_BANCO = ('7691000',)


def _suma_diario(db: Session, empresa_id: int, tipos, cuentas, desde, hasta,
                 prefijo: str = None) -> float:
    # Excluye regularización ('R'), cierre ('Z') y apertura ('A'), igual que el P&G
    # (get_pyg/get_sumas_saldos en contabilidad.py) para que ambos informes cuadren.
    query = db.query(func.sum(Diario.importe)).filter(
        Diario.empresa_id == empresa_id,
        Diario.tipo.in_(tipos),
        Diario.fecha >= desde,
        Diario.fecha <= hasta,
        or_(Diario.tpasiento.is_(None), ~Diario.tpasiento.in_(('R', 'Z', 'A'))),
    )
    if cuentas is not None:
        query = query.filter(Diario.cuenta.in_(cuentas))
    if prefijo:
        query = query.filter(Diario.cuenta.like(f'{prefijo}%'))
    return float(query.scalar() or 0)


def _filtro_estado_valido(modelo):
    """Excluye estados desconocidos (p. ej. una futura 'anulada'): solo cuentan
    facturas pendientes ('P'), cobradas/pagadas ('C') o sin estado (legacy)."""
    return or_(modelo.estado.is_(None), modelo.estado.in_(('P', 'C')))


def _abonos_proveedor(db: Session, empresa_id: int, desde, hasta) -> float:
    """Facturas de abono de proveedor (total negativo): dinero a nuestro favor,
    así que cuentan como ingreso en vez de restar del total de gastos. Devuelve
    el importe ya en positivo."""
    raw = db.query(func.sum(FacturaRecibida.total)).filter(
        FacturaRecibida.empresa_id == empresa_id,
        FacturaRecibida.fecha >= desde,
        FacturaRecibida.fecha <= hasta,
        FacturaRecibida.total < 0,
        _filtro_estado_valido(FacturaRecibida),
    ).scalar() or 0
    return round(-float(raw), 2)


def _abonos_cliente(db: Session, empresa_id: int, desde, hasta) -> float:
    """Facturas de abono a cliente (total negativo): dinero a favor del cliente,
    así que cuentan como gasto en vez de restar del total de ingresos. Devuelve
    el importe ya en positivo."""
    raw = db.query(func.sum(FacturaEmitida.total)).filter(
        FacturaEmitida.empresa_id == empresa_id,
        FacturaEmitida.fecha >= desde,
        FacturaEmitida.fecha <= hasta,
        FacturaEmitida.total < 0,
        _filtro_estado_valido(FacturaEmitida),
    ).scalar() or 0
    return round(-float(raw), 2)


def ingresos_periodo(db: Session, empresa_id: int, desde, hasta) -> float:
    facturas = db.query(func.sum(FacturaEmitida.total)).filter(
        FacturaEmitida.empresa_id == empresa_id,
        FacturaEmitida.fecha >= desde,
        FacturaEmitida.fecha <= hasta,
        FacturaEmitida.total >= 0,
        _filtro_estado_valido(FacturaEmitida),
    ).scalar() or 0
    # Las líneas de abono en el diario van en negativo (convención D+/H-)
    banco = -_suma_diario(db, empresa_id, ('B',), CUENTAS_INGRESO_BANCO, desde, hasta)
    abonos_proveedor = _abonos_proveedor(db, empresa_id, desde, hasta)
    return round(float(facturas) + banco + abonos_proveedor, 2)


def gastos_periodo(db: Session, empresa_id: int, desde, hasta) -> float:
    facturas = db.query(func.sum(FacturaRecibida.total)).filter(
        FacturaRecibida.empresa_id == empresa_id,
        FacturaRecibida.fecha >= desde,
        FacturaRecibida.fecha <= hasta,
        FacturaRecibida.total >= 0,
        _filtro_estado_valido(FacturaRecibida),
    ).scalar() or 0
    # Extras (tipo 'X') y pagas NNA (tipo 'P'): cualquier cuenta de gasto 6xxx,
    # no solo las 3 habituales — así un extra contabilizado contra otra cuenta 6
    # también cuenta (igual que en el P&G).
    extras_y_pagas = _suma_diario(db, empresa_id, ('X', 'P'), None, desde, hasta, prefijo='6')
    abonos_cliente = _abonos_cliente(db, empresa_id, desde, hasta)
    return round(float(facturas) + extras_y_pagas + abonos_cliente, 2)


def ingresos_por_categoria(db: Session, empresa_id: int, desde, hasta) -> list:
    facturas = db.query(func.sum(FacturaEmitida.total)).filter(
        FacturaEmitida.empresa_id == empresa_id,
        FacturaEmitida.fecha >= desde,
        FacturaEmitida.fecha <= hasta,
        FacturaEmitida.total >= 0,
        _filtro_estado_valido(FacturaEmitida),
    ).scalar() or 0
    # Las líneas de abono en el diario van en negativo (convención D+/H-)
    banco = -_suma_diario(db, empresa_id, ('B',), CUENTAS_INGRESO_BANCO, desde, hasta)
    abonos_proveedor = _abonos_proveedor(db, empresa_id, desde, hasta)

    categorias = [
        {"categoria": "Facturas emitidas", "importe": round(float(facturas), 2)},
        {"categoria": "Cheques fundación", "importe": round(banco, 2)},
    ]
    if abs(abonos_proveedor) >= 0.01:
        categorias.append({"categoria": "Abonos de proveedores", "importe": abonos_proveedor})
    return categorias


def gastos_por_categoria(db: Session, empresa_id: int, desde, hasta) -> list:
    facturas = db.query(func.sum(FacturaRecibida.total)).filter(
        FacturaRecibida.empresa_id == empresa_id,
        FacturaRecibida.fecha >= desde,
        FacturaRecibida.fecha <= hasta,
        FacturaRecibida.total >= 0,
        _filtro_estado_valido(FacturaRecibida),
    ).scalar() or 0
    generales = _suma_diario(db, empresa_id, ('X',), (CUENTA_GASTOS_GENERALES,), desde, hasta)
    pagas_nna = _suma_diario(db, empresa_id, ('X', 'P'), (CUENTA_PAGAS_NNA,), desde, hasta)
    terapeuticas = _suma_diario(db, empresa_id, ('X',), (CUENTA_SALIDAS_TERAPEUTICAS,), desde, hasta)
    # Extras contra cualquier otra cuenta de gasto 6xxx no listada arriba
    total_6 = _suma_diario(db, empresa_id, ('X', 'P'), None, desde, hasta, prefijo='6')
    otros = round(total_6 - generales - pagas_nna - terapeuticas, 2)
    abonos_cliente = _abonos_cliente(db, empresa_id, desde, hasta)

    categorias = [
        {"categoria": "Facturas recibidas", "importe": round(float(facturas), 2)},
        {"categoria": "Gastos generales", "importe": round(generales, 2)},
        {"categoria": "Pagas NNA", "importe": round(pagas_nna, 2)},
        {"categoria": "Salidas terapéuticas", "importe": round(terapeuticas, 2)},
    ]
    if abs(otros) >= 0.01:
        categorias.append({"categoria": "Otros gastos", "importe": otros})
    if abs(abonos_cliente) >= 0.01:
        categorias.append({"categoria": "Abonos a clientes", "importe": abonos_cliente})
    return categorias


def _listado_ingresos_banco(db: Session, empresa_id: int, desde, hasta) -> list:
    """Ingresos en cuenta 7691000 (cheques fundación) que entran directo por banco.
    Diario no guarda el nº de banco en una columna propia: se codifica en
    tpasiento='B{numero_banco}' (ver services/contabilidad.py), así que hay que
    decodificarlo para poder recuperar el texto del movimiento bancario."""
    filas = db.query(Diario.numero, Diario.tpasiento, Diario.fecha, Diario.importe).filter(
        Diario.empresa_id == empresa_id,
        Diario.tipo == 'B',
        Diario.cuenta.in_(CUENTAS_INGRESO_BANCO),
        Diario.fecha >= desde,
        Diario.fecha <= hasta,
        or_(Diario.tpasiento.is_(None), ~Diario.tpasiento.in_(('R', 'Z', 'A'))),
    ).all()
    resultado = []
    for numero, tpasiento, fecha, importe in filas:
        texto = None
        if tpasiento and tpasiento.startswith('B') and tpasiento[1:].isdigit():
            banco_num = int(tpasiento[1:])
            mov = db.query(MovBanco).filter(
                MovBanco.empresa_id == empresa_id,
                MovBanco.banco == banco_num,
                MovBanco.numero == numero,
            ).first()
            if mov:
                texto = mov.texto
        resultado.append({
            "fecha": fecha,
            "origen": "Cheques fundación",
            "concepto": texto or "Ingreso banco",
            "importe": round(-float(importe or 0), 2),
        })
    return resultado


def listado_ingresos(db: Session, empresa_id: int, desde, hasta) -> list:
    filas = []
    facturas = db.query(FacturaEmitida).filter(
        FacturaEmitida.empresa_id == empresa_id,
        FacturaEmitida.fecha >= desde,
        FacturaEmitida.fecha <= hasta,
        FacturaEmitida.total >= 0,
        _filtro_estado_valido(FacturaEmitida),
    ).all()
    cli_nums = {f.cliente for f in facturas if f.cliente}
    cli_map = {c.numero: c.nombre for c in db.query(Cliente).filter(
        Cliente.empresa_id == empresa_id, Cliente.numero.in_(cli_nums),
    ).all()} if cli_nums else {}
    for f in facturas:
        concepto = f"Fra. nº{f.cnumero or f.numero}"
        if cli_map.get(f.cliente):
            concepto += f" — {cli_map[f.cliente]}"
        filas.append({
            "fecha": f.fecha,
            "origen": "Factura emitida",
            "concepto": concepto,
            "importe": round(float(f.total or 0), 2),
        })

    # Facturas de abono de proveedor (total negativo): dinero a nuestro favor,
    # se muestran como ingreso en vez de como gasto negativo.
    abonos = db.query(FacturaRecibida).filter(
        FacturaRecibida.empresa_id == empresa_id,
        FacturaRecibida.fecha >= desde,
        FacturaRecibida.fecha <= hasta,
        FacturaRecibida.total < 0,
        _filtro_estado_valido(FacturaRecibida),
    ).all()
    prov_nums = {f.proveedor for f in abonos if f.proveedor}
    prov_map = {p.numero: p.nombre for p in db.query(Proveedor).filter(
        Proveedor.empresa_id == empresa_id, Proveedor.numero.in_(prov_nums),
    ).all()} if prov_nums else {}
    for f in abonos:
        concepto = f"Abono nº{f.cnumero or f.numero}"
        if prov_map.get(f.proveedor):
            concepto += f" — {prov_map[f.proveedor]}"
        filas.append({
            "fecha": f.fecha,
            "origen": "Abono proveedor",
            "concepto": concepto,
            "importe": round(-float(f.total or 0), 2),
        })

    filas += _listado_ingresos_banco(db, empresa_id, desde, hasta)
    filas.sort(key=lambda r: r["fecha"] or datetime.date.min)
    return filas


def listado_gastos(db: Session, empresa_id: int, desde, hasta) -> list:
    filas = []
    facturas = db.query(FacturaRecibida).filter(
        FacturaRecibida.empresa_id == empresa_id,
        FacturaRecibida.fecha >= desde,
        FacturaRecibida.fecha <= hasta,
        FacturaRecibida.total >= 0,
        _filtro_estado_valido(FacturaRecibida),
    ).all()
    prov_nums = {f.proveedor for f in facturas if f.proveedor}
    prov_map = {p.numero: p.nombre for p in db.query(Proveedor).filter(
        Proveedor.empresa_id == empresa_id, Proveedor.numero.in_(prov_nums),
    ).all()} if prov_nums else {}
    for f in facturas:
        proveedor = prov_map.get(f.proveedor) or (f"Proveedor nº{f.proveedor}" if f.proveedor else "")
        filas.append({
            "fecha": f.fecha,
            "origen": "Factura recibida",
            "proveedor": proveedor,
            "nfactura": f.prfactura or "",
            "importe": round(float(f.total or 0), 2),
        })

    # Facturas de abono a cliente (total negativo): dinero a favor del cliente,
    # se muestran como gasto en vez de como ingreso negativo.
    abonos_cli = db.query(FacturaEmitida).filter(
        FacturaEmitida.empresa_id == empresa_id,
        FacturaEmitida.fecha >= desde,
        FacturaEmitida.fecha <= hasta,
        FacturaEmitida.total < 0,
        _filtro_estado_valido(FacturaEmitida),
    ).all()
    cli_nums = {f.cliente for f in abonos_cli if f.cliente}
    cli_map = {c.numero: c.nombre for c in db.query(Cliente).filter(
        Cliente.empresa_id == empresa_id, Cliente.numero.in_(cli_nums),
    ).all()} if cli_nums else {}
    for f in abonos_cli:
        cliente = cli_map.get(f.cliente) or (f"Cliente nº{f.cliente}" if f.cliente else "")
        filas.append({
            "fecha": f.fecha,
            "origen": "Abono cliente",
            "proveedor": cliente,
            "nfactura": "",
            "importe": round(-float(f.total or 0), 2),
        })

    # Extras (gastos generales, salidas terapéuticas y pagas NNA legacy tipo M)
    origen_cuenta = {
        CUENTA_GASTOS_GENERALES: "Gastos generales",
        CUENTA_SALIDAS_TERAPEUTICAS: "Salidas terapéuticas",
        CUENTA_PAGAS_NNA: "Pagas NNA",
    }
    extras_rows = db.query(Diario.fecha, Diario.numero, Diario.cuenta, Diario.importe).filter(
        Diario.empresa_id == empresa_id,
        Diario.tipo == 'X',
        Diario.cuenta.like('6%'),
        Diario.fecha >= desde,
        Diario.fecha <= hasta,
        or_(Diario.tpasiento.is_(None), ~Diario.tpasiento.in_(('R', 'Z', 'A'))),
    ).all()
    ext_nums = {r.numero for r in extras_rows}
    ext_map = {e.numero: e.texto for e in db.query(Extra).filter(
        Extra.empresa_id == empresa_id, Extra.numero.in_(ext_nums),
    ).all()} if ext_nums else {}
    for fecha, numero, cuenta, importe in extras_rows:
        filas.append({
            "fecha": fecha,
            "origen": origen_cuenta.get(cuenta, "Extra"),
            "proveedor": ext_map.get(numero) or f"Extra nº{numero}",
            "nfactura": "",
            "importe": round(float(importe or 0), 2),
        })

    # Pagas NNA del módulo dedicado (activo desde 2026-06-30)
    pagas_rows = db.query(PagaNNA).filter(
        PagaNNA.empresa_id == empresa_id,
        PagaNNA.fecha >= desde,
        PagaNNA.fecha <= hasta,
    ).all()
    usr_nums = {p.usuario for p in pagas_rows}
    usr_map = {u.numero: u.nombre for u in db.query(UsuarioNNA).filter(
        UsuarioNNA.empresa_id == empresa_id, UsuarioNNA.numero.in_(usr_nums),
    ).all()} if usr_nums else {}
    for p in pagas_rows:
        concepto = "Paga mensual"
        if usr_map.get(p.usuario):
            concepto += f" — {usr_map[p.usuario]}"
        filas.append({
            "fecha": p.fecha,
            "origen": "Pagas NNA",
            "proveedor": concepto,
            "nfactura": "",
            "importe": round(float(p.importe or 0), 2),
        })

    filas.sort(key=lambda r: r["fecha"] or datetime.date.min)
    return filas


def _limites_mes(anio: int, mes: int):
    desde = datetime.date(anio, mes, 1)
    if mes == 12:
        hasta = datetime.date(anio, 12, 31)
    else:
        hasta = datetime.date(anio, mes + 1, 1) - datetime.timedelta(days=1)
    return desde, hasta


def _ultimo_mes_con_datos(anio: int) -> int:
    """Mes actual si se consulta el año en curso (no tiene sentido mostrar meses
    futuros, todavía sin datos); 12 si es un año ya cerrado."""
    hoy = datetime.date.today()
    return hoy.month if anio == hoy.year else 12


# Ajuste manual del resultado del ejercicio anterior, solo para el mes de enero
# de la tabla mensual de Estadísticas. No afecta al Diario, al P&G ni al módulo
# "Ingresos y Gastos".
def _resultado_ejercicio_anterior(db: Session, empresa_id: int, anio: int) -> float:
    """Suma de los saldos iniciales de todos los bancos/cajas de la empresa."""
    raw = db.query(func.sum(Banco.saldoini)).filter(
        Banco.empresa_id == empresa_id,
    ).scalar() or 0
    return round(float(raw), 2)


def evolucion_mensual(db: Session, empresa_id: int, anio: int) -> list:
    meses = []
    resultado_anterior = None
    for mes in range(1, _ultimo_mes_con_datos(anio) + 1):
        desde, hasta = _limites_mes(anio, mes)
        ingresos = ingresos_periodo(db, empresa_id, desde, hasta)
        gastos = gastos_periodo(db, empresa_id, desde, hasta)
        if mes == 1:
            # En enero, el resultado del ejercicio anterior (beneficio/pérdida
            # trasladado por la apertura) también cuenta como ingreso del mes.
            ingresos = round(ingresos + _resultado_ejercicio_anterior(db, empresa_id, anio), 2)
        else:
            # En los demás meses, el resultado (ingresos - gastos) del mes
            # anterior también cuenta como ingreso, arrastrando el saldo mes a mes.
            ingresos = round(ingresos + resultado_anterior, 2)
        resultado_anterior = round(ingresos - gastos, 2)
        meses.append({"mes": mes, "ingresos": ingresos, "gastos": gastos})
    return meses


def saldos_bancos_mensual(db: Session, empresa_id: int, anio: int) -> list:
    """Saldo total de todos los bancos/cajas al final de cada mes del año,
    hasta el mes en curso si el año consultado es el actual."""
    bancos = db.query(Banco).filter(Banco.empresa_id == empresa_id).order_by(Banco.numero).all()
    saldo_inicial_total = sum(float(b.saldoini or 0) for b in bancos)

    ultimo_mes = _ultimo_mes_con_datos(anio)

    # Movimientos del año agrupados por mes (suma de 'total', que ya viene con signo)
    movs = db.query(
        func.strftime('%m', MovBanco.fecha).label('mes'),
        func.sum(MovBanco.total).label('delta'),
    ).filter(
        MovBanco.empresa_id == empresa_id,
        MovBanco.fecha < datetime.date(anio + 1, 1, 1),
    ).group_by('mes').all()
    deltas_por_mes = {int(m): float(d or 0) for m, d in movs if m is not None}

    # Saldo acumulado justo antes del 1 de enero del año consultado
    saldo_previo = db.query(func.sum(MovBanco.total)).filter(
        MovBanco.empresa_id == empresa_id,
        MovBanco.fecha < datetime.date(anio, 1, 1),
    ).scalar() or 0
    acumulado = saldo_inicial_total + float(saldo_previo)

    resultado = []
    for mes in range(1, ultimo_mes + 1):
        acumulado = round(acumulado + deltas_por_mes.get(mes, 0.0), 2)
        resultado.append({"mes": mes, "saldo": acumulado})
    return resultado


def anios_disponibles(db: Session, empresa_id: int) -> list:
    anios = set()
    for modelo in (FacturaEmitida, FacturaRecibida):
        for (anio,) in db.query(func.strftime('%Y', modelo.fecha)).filter(
            modelo.empresa_id == empresa_id, modelo.fecha.isnot(None)
        ).distinct():
            if anio:
                anios.add(int(anio))
    for (anio,) in db.query(func.strftime('%Y', Diario.fecha)).filter(
        Diario.empresa_id == empresa_id
    ).distinct():
        if anio:
            anios.add(int(anio))
    if not anios:
        anios.add(datetime.date.today().year)
    return sorted(anios, reverse=True)
