"""Lado servidor de la sincronización: aplica en destino las operaciones que
empuja una instalación, reproduciéndolas con la misma lógica de servicio que
las generó (no se copian filas sueltas — ver sync_log en app/models/sync.py).

Idempotencia: cada operación puede reintentarse sin duplicar efectos.
- 'C': si ya existe una fila con ese uuid, no se repite el alta.
- 'U'/'D': si no existe la fila, se considera aplicada (alta aún no llegada,
  o baja ya aplicada antes) en vez de fallar.
El `uuid` es la identidad estable entre instalaciones — no `numero`/`id`
(ver docs/sincronizacion.md) —, así que tras un alta hay que corregirlo: la
función `crear_*` genera uno propio (vía SyncMixin) que no coincide con el
`entidad_uuid` original de la instalación de origen.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.facturacion import FacturaEmitida, FacturaRecibida, AlbaranEmitido, AlbaranRecibido, Familia, Articulo
from app.models.clientes_proveedores import Cliente, Proveedor, Vencimiento
from app.models.bancos import Banco, MovBanco
from app.models.contabilidad import Cuenta, Extra
from app.models.usuarios import UsuarioNNA, PagaNNA

from app.schemas.facturacion import (
    FacturaEmiCreate, FacturaEmiUpdate, FacturaRecCreate, FacturaRecUpdate,
    AlbaranEmiCreate, AlbaranEmiUpdate, AlbaranRecCreate, AlbaranRecUpdate,
    FamiliaCreate, FamiliaUpdate, ArticuloCreate, ArticuloUpdate,
)
from app.schemas.clientes_proveedores import ClienteCreate, ClienteUpdate, ProveedorCreate, ProveedorUpdate
from app.schemas.bancos import BancoCreate, BancoUpdate, MovimientoCreate, MovimientoUpdate, VencimientoCreate, VencimientoUpdate
from app.schemas.contabilidad import CuentaCreate, CuentaUpdate
from app.schemas.extras import ExtraCreate, ExtraUpdate
from app.schemas.usuarios import UsuarioCreate, UsuarioUpdate, PagaCreate

from app.services import facturas as facturas_svc
from app.services import albaranes as albaranes_svc
from app.services import familias as familias_svc
from app.services import articulos as articulos_svc
from app.services import clientes as clientes_svc
from app.services import proveedores as proveedores_svc
from app.services import bancos as bancos_svc
from app.services import contabilidad as contabilidad_svc
from app.services import extras as extras_svc
from app.services import usuarios as usuarios_svc


class ReplayError(Exception):
    pass


# tabla -> (modelo, esquema_crear, esquema_editar, fn_crear, fn_editar, fn_borrar)
# fn_editar/fn_borrar pueden ser None si esa tabla nunca genera esa operación.
SYNC_REGISTRO = {
    "facturas_emitidas": (FacturaEmitida, FacturaEmiCreate, FacturaEmiUpdate,
                          facturas_svc.create_factura_emi, facturas_svc.update_factura_emi, facturas_svc.delete_factura_emi),
    "facturas_recibidas": (FacturaRecibida, FacturaRecCreate, FacturaRecUpdate,
                           facturas_svc.create_factura_rec, facturas_svc.update_factura_rec, facturas_svc.delete_factura_rec),
    "albaranes_emitidos": (AlbaranEmitido, AlbaranEmiCreate, AlbaranEmiUpdate,
                           albaranes_svc.create_albaran_emi, albaranes_svc.update_albaran_emi, albaranes_svc.delete_albaran_emi),
    "albaranes_recibidos": (AlbaranRecibido, AlbaranRecCreate, AlbaranRecUpdate,
                            albaranes_svc.create_albaran_rec, albaranes_svc.update_albaran_rec, albaranes_svc.delete_albaran_rec),
    "familias": (Familia, FamiliaCreate, FamiliaUpdate,
                familias_svc.create_familia, familias_svc.update_familia, familias_svc.delete_familia),
    "articulos": (Articulo, ArticuloCreate, ArticuloUpdate,
                 articulos_svc.create_articulo, articulos_svc.update_articulo, articulos_svc.delete_articulo),
    "clientes": (Cliente, ClienteCreate, ClienteUpdate,
                clientes_svc.create_cliente, clientes_svc.update_cliente, clientes_svc.delete_cliente),
    "proveedores": (Proveedor, ProveedorCreate, ProveedorUpdate,
                    proveedores_svc.create_proveedor, proveedores_svc.update_proveedor, proveedores_svc.delete_proveedor),
    "vencimientos": (Vencimiento, VencimientoCreate, VencimientoUpdate,
                     bancos_svc.create_vencimiento, bancos_svc.update_vencimiento, None),
    "bancos": (Banco, BancoCreate, BancoUpdate,
              bancos_svc.create_banco, bancos_svc.update_banco, bancos_svc.delete_banco),
    "mov_bancos": (MovBanco, MovimientoCreate, MovimientoUpdate,
                  bancos_svc.create_movimiento, bancos_svc.update_movimiento, bancos_svc.delete_movimiento),
    "cuentas": (Cuenta, CuentaCreate, CuentaUpdate,
               contabilidad_svc.create_cuenta, contabilidad_svc.update_cuenta, contabilidad_svc.delete_cuenta),
    "extras": (Extra, ExtraCreate, ExtraUpdate,
              extras_svc.create_extra, extras_svc.update_extra, extras_svc.delete_extra),
    "usuarios_nna": (UsuarioNNA, UsuarioCreate, UsuarioUpdate,
                     usuarios_svc.create_usuario, usuarios_svc.update_usuario, usuarios_svc.delete_usuario),
    "pagas_nna": (PagaNNA, PagaCreate, None,
                 usuarios_svc.create_paga, None, usuarios_svc.delete_paga),
}


def _corregir_uuid(db: Session, tabla: str, id_creado: int, entidad_uuid: str):
    """Las funciones crear_* generan su propio uuid (vía SyncMixin); hay que
    forzarlo al uuid original de la instalación de origen para que la fila
    tenga la misma identidad en todas las instalaciones."""
    actual = db.execute(
        text(f"SELECT uuid FROM {tabla} WHERE id = :id"), {"id": id_creado}
    ).scalar()
    if actual != entidad_uuid:
        db.execute(
            text(f"UPDATE {tabla} SET uuid = :u WHERE id = :id"),
            {"u": entidad_uuid, "id": id_creado},
        )
        db.commit()


def replay_operacion(db: Session, tabla: str, entidad_uuid: str, operacion: str,
                     empresa_id: int, payload: dict | None):
    registro = SYNC_REGISTRO.get(tabla)
    if not registro:
        raise ReplayError(f"Tabla no sincronizable: {tabla}")
    modelo, esquema_crear, esquema_editar, fn_crear, fn_editar, fn_borrar = registro

    existente = db.query(modelo).filter(modelo.uuid == entidad_uuid).first()

    if operacion == 'C':
        if existente:
            return  # ya aplicada (reintento)
        datos = dict(payload or {})
        if 'forzar' in esquema_crear.model_fields:
            datos['forzar'] = True  # ya se validó/confirmó en la instalación de origen
        obj = fn_crear(db, esquema_crear(**datos))
        id_creado = obj['id'] if isinstance(obj, dict) else obj.id
        _corregir_uuid(db, tabla, id_creado, entidad_uuid)

    elif operacion == 'U':
        if not fn_editar or not esquema_editar:
            raise ReplayError(f"{tabla} no admite edición")
        if not existente:
            raise ReplayError("No existe la entidad a editar (¿aún no llegó su alta?)")
        datos = dict(payload or {})
        if 'forzar' in esquema_editar.model_fields:
            datos['forzar'] = True
        fn_editar(db, existente.id, esquema_editar(**datos))

    elif operacion == 'D':
        if not fn_borrar:
            raise ReplayError(f"{tabla} no admite baja")
        if not existente:
            return  # ya borrada o nunca llegó a existir
        fn_borrar(db, existente.id)

    else:
        raise ReplayError(f"Operación desconocida: {operacion}")
