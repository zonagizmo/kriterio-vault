from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.db.database import get_db
from app.schemas.bancos import (
    BancoRead, BancoCreate, BancoUpdate,
    MovimientoRead, MovimientoCreate, MovimientoUpdate,
    PagoRead,
    VencimientoRead, VencimientoCreate, VencimientoUpdate,
)
from app.services import bancos as svc

router = APIRouter(prefix="/api/bancos", tags=["bancos"])


def _enrich_movs(movs, db: Session) -> list[MovimientoRead]:
    """Serializa movimientos enriqueciendo cada pago con datos del documento y entidad.
    Hace las búsquedas en LOTE (una consulta por tipo de entidad para toda la página);
    la versión anterior lanzaba ~5 consultas por pago y el listado era O(n) consultas."""
    from app.models.contabilidad import Cuenta as CuentaModel, Extra
    from app.models.clientes_proveedores import Vencimiento, Proveedor, Cliente
    from app.models.facturacion import FacturaRecibida, FacturaEmitida
    from app.models.bancos import Banco as BancoModel
    from app.models.usuarios import PagaNNA, UsuarioNNA

    if not movs:
        return []
    empresa_id = movs[0].empresa_id
    todos_pagos = [p for m in movs for p in (m.pagos or [])]

    # ── Recolectar claves ──
    ctas_keys = {p.dirsubcta for p in todos_pagos if p.dirsubcta}
    vto_nums = {p.vto for p in todos_pagos if p.vto}
    bancot_nums = {p.bancot for p in todos_pagos if p.bancot}

    cuentas_map = {c.cuenta: c.texto for c in db.query(CuentaModel).filter(
        CuentaModel.empresa_id == empresa_id, CuentaModel.cuenta.in_(ctas_keys),
    ).all()} if ctas_keys else {}
    vtos_map = {v.numero: v for v in db.query(Vencimiento).filter(
        Vencimiento.empresa_id == empresa_id, Vencimiento.numero.in_(vto_nums),
    ).all()} if vto_nums else {}
    bancos_map = {b.numero: b.nombre for b in db.query(BancoModel).filter(
        BancoModel.empresa_id == empresa_id, BancoModel.numero.in_(bancot_nums),
    ).all()} if bancot_nums else {}

    # ── Documentos origen por tipo de vencimiento ──
    rec_nums = {v.tpnumero for v in vtos_map.values() if v.tipo == 'R' and v.tpnumero}
    emi_nums = {v.tpnumero for v in vtos_map.values() if v.tipo == 'F' and v.tpnumero}
    ext_nums = {v.tpnumero for v in vtos_map.values() if v.tipo == 'X' and v.tpnumero}
    paga_ids = {v.tpnumero for v in vtos_map.values() if v.tipo == 'N' and v.tpnumero}

    rec_map = {f.numero: f for f in db.query(FacturaRecibida).filter(
        FacturaRecibida.empresa_id == empresa_id, FacturaRecibida.numero.in_(rec_nums),
    ).all()} if rec_nums else {}
    emi_map = {f.numero: f for f in db.query(FacturaEmitida).filter(
        FacturaEmitida.empresa_id == empresa_id, FacturaEmitida.numero.in_(emi_nums),
    ).all()} if emi_nums else {}
    ext_map = {x.numero: x for x in db.query(Extra).filter(
        Extra.empresa_id == empresa_id, Extra.numero.in_(ext_nums),
    ).all()} if ext_nums else {}
    pagas_map = {pg.id: pg for pg in db.query(PagaNNA).filter(
        PagaNNA.empresa_id == empresa_id, PagaNNA.id.in_(paga_ids),
    ).all()} if paga_ids else {}

    prov_nums = {f.proveedor for f in rec_map.values() if f.proveedor}
    cli_nums = {f.cliente for f in emi_map.values() if f.cliente}
    nna_nums = {pg.usuario for pg in pagas_map.values()}
    prov_map = {p.numero: p.nombre for p in db.query(Proveedor).filter(
        Proveedor.empresa_id == empresa_id, Proveedor.numero.in_(prov_nums),
    ).all()} if prov_nums else {}
    cli_map = {c.numero: c.nombre for c in db.query(Cliente).filter(
        Cliente.empresa_id == empresa_id, Cliente.numero.in_(cli_nums),
    ).all()} if cli_nums else {}
    nna_map = {u.numero: u.nombre for u in db.query(UsuarioNNA).filter(
        UsuarioNNA.empresa_id == empresa_id, UsuarioNNA.numero.in_(nna_nums),
    ).all()} if nna_nums else {}

    # ── Construcción de la respuesta ──
    result = []
    for mov in movs:
        data = MovimientoRead.model_validate(mov)
        pagos_enriquecidos = []
        for p in (mov.pagos or []):
            pago = PagoRead.model_validate(p)
            if p.dirsubcta and p.dirsubcta in cuentas_map:
                pago.dirsubcta_nombre = cuentas_map[p.dirsubcta]
            if p.vto:
                vto = vtos_map.get(p.vto)
                pago.vto_existe = vto is not None
                if vto:
                    pago.vto_tipo = vto.tipo
                    pago.vto_tpnumero = vto.tpnumero
                    if vto.tipo == 'R' and vto.tpnumero in rec_map:
                        fac = rec_map[vto.tpnumero]
                        pago.doc_numero_externo = fac.prfactura
                        pago.doc_fecha = fac.fecha
                        if fac.proveedor in prov_map:
                            pago.doc_entidad_nombre = prov_map[fac.proveedor]
                    elif vto.tipo == 'F' and vto.tpnumero in emi_map:
                        fac = emi_map[vto.tpnumero]
                        pago.doc_numero_externo = fac.cnumalt
                        pago.doc_fecha = fac.fecha
                        if fac.cliente in cli_map:
                            pago.doc_entidad_nombre = cli_map[fac.cliente]
                    elif vto.tipo == 'X' and vto.tpnumero in ext_map:
                        extra = ext_map[vto.tpnumero]
                        pago.doc_entidad_nombre = extra.texto
                        pago.doc_fecha = extra.fecha
                    elif vto.tipo == 'N' and vto.tpnumero in pagas_map:
                        paga = pagas_map[vto.tpnumero]
                        pago.doc_fecha = paga.fecha
                        if paga.usuario in nna_map:
                            pago.doc_entidad_nombre = nna_map[paga.usuario]
            if p.bancot and p.bancot in bancos_map:
                pago.bancot_nombre = bancos_map[p.bancot]
            pagos_enriquecidos.append(pago)
        data.pagos = pagos_enriquecidos
        result.append(data)
    return result


def _enrich_mov(mov, db: Session) -> MovimientoRead:
    """Versión para un solo movimiento (endpoints de detalle/creación/edición)."""
    return _enrich_movs([mov], db)[0]


# ─── Cuentas bancarias ────────────────────────────────────────────────────────

@router.get("", response_model=list[BancoRead])
def listar(empresa_id: int, db: Session = Depends(get_db)):
    return svc.get_bancos(db, empresa_id)


@router.get("/{banco_id}", response_model=BancoRead)
def obtener(banco_id: int, db: Session = Depends(get_db)):
    b = svc.get_banco(db, banco_id)
    if not b:
        raise HTTPException(404, "Banco no encontrado")
    return b


@router.post("", response_model=BancoRead, status_code=201)
def crear(data: BancoCreate, db: Session = Depends(get_db)):
    return svc.create_banco(db, data)


@router.put("/{banco_id}", response_model=BancoRead)
def actualizar(banco_id: int, data: BancoUpdate, db: Session = Depends(get_db)):
    try:
        b = svc.update_banco(db, banco_id, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not b:
        raise HTTPException(404, "Banco no encontrado")
    return b


@router.delete("/{banco_id}", status_code=204)
def eliminar(banco_id: int, db: Session = Depends(get_db)):
    try:
        if not svc.delete_banco(db, banco_id):
            raise HTTPException(404, "Banco no encontrado")
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.post("/{banco_id}/reparar_saldos", response_model=BancoRead)
def reparar_saldos(banco_id: int, db: Session = Depends(get_db)):
    banco = svc.reparar_saldos_banco(db, banco_id)
    if not banco:
        raise HTTPException(404, "Banco no encontrado")
    return banco


# ─── Movimientos ──────────────────────────────────────────────────────────────

@router.get("/movimientos/lista", response_model=dict)
def listar_movimientos(
    empresa_id: int,
    banco: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    solo_no_conciliados: bool = False,
    db: Session = Depends(get_db),
):
    items, total = svc.get_movimientos(db, empresa_id, banco, skip, limit, solo_no_conciliados)
    return {"total": total, "items": _enrich_movs(items, db)}


@router.get("/movimientos/{mov_id}", response_model=MovimientoRead)
def obtener_movimiento(mov_id: int, db: Session = Depends(get_db)):
    mov = svc.get_movimiento(db, mov_id)
    if not mov:
        raise HTTPException(404, "Movimiento no encontrado")
    return _enrich_mov(mov, db)


@router.post("/movimientos", response_model=MovimientoRead, status_code=201)
def crear_movimiento(data: MovimientoCreate, db: Session = Depends(get_db)):
    return _enrich_mov(svc.create_movimiento(db, data), db)


@router.put("/movimientos/{mov_id}", response_model=MovimientoRead)
def actualizar_movimiento(mov_id: int, data: MovimientoUpdate, db: Session = Depends(get_db)):
    mov = svc.update_movimiento(db, mov_id, data)
    if not mov:
        raise HTTPException(404, "Movimiento no encontrado")
    return _enrich_mov(mov, db)


@router.delete("/movimientos/{mov_id}", status_code=204)
def eliminar_movimiento(mov_id: int, db: Session = Depends(get_db)):
    if not svc.delete_movimiento(db, mov_id):
        raise HTTPException(404, "Movimiento no encontrado")


class ReordenarBody(BaseModel):
    direccion: str  # 'arriba' | 'abajo'


@router.post("/movimientos/{mov_id}/reordenar", response_model=MovimientoRead)
def reordenar_movimiento(mov_id: int, body: ReordenarBody, db: Session = Depends(get_db)):
    mov = svc.reordenar_movimiento(db, mov_id, body.direccion)
    if not mov:
        raise HTTPException(404, "Movimiento no encontrado")
    return mov


# ─── Vencimientos ─────────────────────────────────────────────────────────────

@router.get("/vencimientos/lista", response_model=dict)
def listar_vencimientos(
    empresa_id: int,
    tipo: Optional[str] = None,
    solo_pendientes: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    from app.models.contabilidad import Extra
    items, total = svc.get_vencimientos(db, empresa_id, tipo, solo_pendientes, skip, limit)
    result = []
    for i in items:
        vto = VencimientoRead.model_validate(i)
        if i.tipo == 'X' and i.tpnumero:
            extra = db.query(Extra).filter(
                Extra.empresa_id == i.empresa_id,
                Extra.numero == i.tpnumero,
            ).first()
            if extra:
                vto.extra_tipo = extra.tipo
        result.append(vto)
    return {"total": total, "items": result}


@router.post("/vencimientos", response_model=VencimientoRead, status_code=201)
def crear_vencimiento(data: VencimientoCreate, db: Session = Depends(get_db)):
    return svc.create_vencimiento(db, data)


@router.put("/vencimientos/{vto_id}", response_model=VencimientoRead)
def actualizar_vencimiento(vto_id: int, data: VencimientoUpdate, db: Session = Depends(get_db)):
    vto = svc.update_vencimiento(db, vto_id, data)
    if not vto:
        raise HTTPException(404, "Vencimiento no encontrado")
    return vto
