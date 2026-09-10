from sqlalchemy import String, Integer, Numeric, Boolean, Text, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from app.models.sync_mixin import SyncMixin
import datetime


class Familia(SyncMixin, Base):
    __tablename__ = "familias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    padre: Mapped[int] = mapped_column(Integer, nullable=True)
    texto: Mapped[str] = mapped_column(String(100), nullable=True)
    dcto: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False), default=0)
    tdcto: Mapped[str] = mapped_column(String(1), nullable=True)


class FamiliaC(Base):
    __tablename__ = "familias_c"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    familia: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    carnum: Mapped[int] = mapped_column(Integer, nullable=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=True)
    texto: Mapped[str] = mapped_column(String(100), nullable=True)


class Articulo(SyncMixin, Base):
    __tablename__ = "articulos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(30), nullable=True, index=True)
    ean13: Mapped[str] = mapped_column(String(13), nullable=True, index=True)
    ubicacion: Mapped[str] = mapped_column(String(30), nullable=True)
    proveedor: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    familia: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    pventa: Mapped[float] = mapped_column(Numeric(15, 4, asdecimal=False), default=0)
    dcto: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False), default=0)
    tdcto: Mapped[str] = mapped_column(String(1), nullable=True)
    dcto2: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False), default=0)
    dcto3: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False), default=0)
    pcompra: Mapped[float] = mapped_column(Numeric(15, 4, asdecimal=False), default=0)
    pcdcto: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False), default=0)
    pcdcto2: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False), default=0)
    pcdcto3: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False), default=0)
    tipoivac: Mapped[int] = mapped_column(Integer, nullable=True)
    tipoivav: Mapped[int] = mapped_column(Integer, nullable=True)
    operacionc: Mapped[int] = mapped_column(Integer, nullable=True)
    operacionv: Mapped[int] = mapped_column(Integer, nullable=True)
    albinvent: Mapped[int] = mapped_column(Integer, nullable=True)
    finvent: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    qinvent: Mapped[float] = mapped_column(Numeric(15, 4, asdecimal=False), default=0)
    qcompras: Mapped[float] = mapped_column(Numeric(15, 4, asdecimal=False), default=0)
    qventas: Mapped[float] = mapped_column(Numeric(15, 4, asdecimal=False), default=0)
    minimo: Mapped[float] = mapped_column(Numeric(15, 4, asdecimal=False), default=0)
    tipo: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    asociado: Mapped[int] = mapped_column(Integer, nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class ArticuloC(Base):
    __tablename__ = "articulos_c"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    articulo: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    carnum: Mapped[int] = mapped_column(Integer, nullable=True)
    dato: Mapped[str] = mapped_column(String(100), nullable=True)


class FacturaEmitida(SyncMixin, Base):
    __tablename__ = "facturas_emitidas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cnumero: Mapped[int] = mapped_column(Integer, nullable=True)
    tiponum: Mapped[str] = mapped_column(String(2), nullable=True)
    cnumalt: Mapped[str] = mapped_column(String(20), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    fregistro: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    cliente: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    clcuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    tipoop: Mapped[int] = mapped_column(Integer, nullable=True)
    tocuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    total: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    totaldecl: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    declterc: Mapped[str] = mapped_column(String(1), nullable=True)
    ccaja: Mapped[str] = mapped_column(String(1), nullable=True)
    estado: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    registro: Mapped[int] = mapped_column(Integer, nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class FacturaRecibida(SyncMixin, Base):
    __tablename__ = "facturas_recibidas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cnumero: Mapped[int] = mapped_column(Integer, nullable=True)
    tiponum: Mapped[str] = mapped_column(String(2), nullable=True)
    cnumalt: Mapped[str] = mapped_column(String(20), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    regfecha: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    proveedor: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    prcuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    prfactura: Mapped[str] = mapped_column(String(20), nullable=True)
    prfecha: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    tipoop: Mapped[int] = mapped_column(Integer, nullable=True)
    tocuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    total: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    totaldecl: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    declterc: Mapped[str] = mapped_column(String(1), nullable=True)
    ccaja: Mapped[str] = mapped_column(String(1), nullable=True)
    estado: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    registro: Mapped[int] = mapped_column(Integer, nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class AlbaranEmitido(SyncMixin, Base):
    __tablename__ = "albaranes_emitidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cnumero: Mapped[int] = mapped_column(Integer, nullable=True)
    tiponum: Mapped[str] = mapped_column(String(2), nullable=True)
    cnumalt: Mapped[str] = mapped_column(String(20), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    cliente: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    factura: Mapped[int] = mapped_column(Integer, nullable=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    apuntes: Mapped[int] = mapped_column(Integer, nullable=True)
    cpi: Mapped[str] = mapped_column(String(1), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=True)
    estadorep: Mapped[str] = mapped_column(String(1), nullable=True)
    estado: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class AlbaranRecibido(SyncMixin, Base):
    __tablename__ = "albaranes_recibidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cnumero: Mapped[int] = mapped_column(Integer, nullable=True)
    tiponum: Mapped[str] = mapped_column(String(2), nullable=True)
    cnumalt: Mapped[str] = mapped_column(String(20), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    proveedor: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    factura: Mapped[int] = mapped_column(Integer, nullable=True)
    pralbaran: Mapped[str] = mapped_column(String(20), nullable=True)
    prfecha: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    apuntes: Mapped[int] = mapped_column(Integer, nullable=True)
    cpi: Mapped[str] = mapped_column(String(1), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=True)
    estadorep: Mapped[str] = mapped_column(String(1), nullable=True)
    pedido: Mapped[int] = mapped_column(Integer, nullable=True)
    estado: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class Presupuesto(Base):
    __tablename__ = "presupuestos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cnumero: Mapped[int] = mapped_column(Integer, nullable=True)
    tiponum: Mapped[str] = mapped_column(String(2), nullable=True)
    cnumalt: Mapped[str] = mapped_column(String(20), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    cliente: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    apuntes: Mapped[int] = mapped_column(Integer, nullable=True)
    estado: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class PedidoProveedor(Base):
    __tablename__ = "pedidos_proveedor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cnumero: Mapped[int] = mapped_column(Integer, nullable=True)
    tiponum: Mapped[str] = mapped_column(String(2), nullable=True)
    cnumalt: Mapped[str] = mapped_column(String(20), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    proveedor: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    apuntes: Mapped[int] = mapped_column(Integer, nullable=True)
    estado: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class PedidoCliente(Base):
    __tablename__ = "pedidos_cliente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cnumero: Mapped[int] = mapped_column(Integer, nullable=True)
    tiponum: Mapped[str] = mapped_column(String(2), nullable=True)
    cnumalt: Mapped[str] = mapped_column(String(20), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    cliente: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    apuntes: Mapped[int] = mapped_column(Integer, nullable=True)
    estado: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class AlbaranInventario(Base):
    __tablename__ = "albaranes_inventario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=True)
    cnumero: Mapped[int] = mapped_column(Integer, nullable=True)
    tiponum: Mapped[str] = mapped_column(String(2), nullable=True)
    cnumalt: Mapped[str] = mapped_column(String(20), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    apuntes: Mapped[int] = mapped_column(Integer, nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class AlbaranReparto(Base):
    __tablename__ = "albaranes_reparto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=False)
    albaran: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    factura: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    apuntes: Mapped[int] = mapped_column(Integer, nullable=True)
    cpi: Mapped[str] = mapped_column(String(1), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=True)
    reparto: Mapped[str] = mapped_column(String(1), nullable=True)


class Apunte(Base):
    """Líneas de albaranes, facturas, presupuestos y pedidos."""
    __tablename__ = "apuntes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    albaran: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    talbaran: Mapped[str] = mapped_column(String(2), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=True)
    articulo: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    texto: Mapped[str] = mapped_column(String(100), nullable=True)
    texto2: Mapped[str] = mapped_column(String(100), nullable=True)
    dcto1: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False), default=0)
    dcto2: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False), default=0)
    dcto3: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False), default=0)
    cantidad: Mapped[float] = mapped_column(Numeric(15, 4, asdecimal=False), default=0)
    precio: Mapped[float] = mapped_column(Numeric(15, 4, asdecimal=False), default=0)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    tiva: Mapped[int] = mapped_column(Integer, nullable=True)
    tipoop: Mapped[int] = mapped_column(Integer, nullable=True)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    reparto: Mapped[str] = mapped_column(String(1), nullable=True)
    grupo: Mapped[str] = mapped_column(String(10), nullable=True)
    almacen: Mapped[str] = mapped_column(String(10), nullable=True)


class Eriva(Base):
    """Registro de IVA por factura."""
    __tablename__ = "eriva"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=False, index=True)
    factura: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=True)
    iva: Mapped[float] = mapped_column(Numeric(5, 2, asdecimal=False), default=0)
    iva_cta: Mapped[str] = mapped_column(String(15), nullable=True)
    iva_total: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    re: Mapped[float] = mapped_column(Numeric(5, 2, asdecimal=False), default=0)
    re_cta: Mapped[str] = mapped_column(String(15), nullable=True)
    re_total: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    base: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    nodedu: Mapped[str] = mapped_column(String(1), nullable=True)
    binversion: Mapped[str] = mapped_column(String(1), nullable=True)


class Foto(Base):
    __tablename__ = "fotos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=True)
    mostrar: Mapped[bool] = mapped_column(Boolean, default=True)
    izq: Mapped[int] = mapped_column(Integer, nullable=True)
    arr: Mapped[int] = mapped_column(Integer, nullable=True)
    ancho: Mapped[int] = mapped_column(Integer, nullable=True)
    alto: Mapped[int] = mapped_column(Integer, nullable=True)
