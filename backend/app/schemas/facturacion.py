from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
import datetime
from decimal import Decimal


class FacturaPagoInfo(BaseModel):
    banco_nombre: str
    fecha: Optional[datetime.date] = None
    importe: Decimal


# ─── Familias ────────────────────────────────────────────────────────────────

class FamiliaBase(BaseModel):
    padre: Optional[int] = None
    texto: Optional[str] = None
    dcto: Optional[Decimal] = 0
    tdcto: Optional[str] = None

class FamiliaCreate(FamiliaBase):
    texto: str
    empresa_id: int

class FamiliaUpdate(FamiliaBase):
    pass

class FamiliaRead(FamiliaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int


# ─── Artículos ───────────────────────────────────────────────────────────────

class ArticuloBase(BaseModel):
    codigo: Optional[str] = None
    ean13: Optional[str] = None
    ubicacion: Optional[str] = None
    proveedor: Optional[int] = None
    familia: Optional[int] = None
    nombre: Optional[str] = None
    pventa: Optional[Decimal] = 0
    dcto: Optional[Decimal] = 0
    tdcto: Optional[str] = None
    dcto2: Optional[Decimal] = 0
    dcto3: Optional[Decimal] = 0
    pcompra: Optional[Decimal] = 0
    pcdcto: Optional[Decimal] = 0
    tipoivac: Optional[int] = None
    tipoivav: Optional[int] = None
    operacionv: Optional[int] = None
    operacionc: Optional[int] = None
    minimo: Optional[Decimal] = 0
    tipo: Optional[str] = None
    notas: Optional[str] = None

class ArticuloCreate(ArticuloBase):
    nombre: str
    empresa_id: int

class ArticuloUpdate(ArticuloBase):
    pass

class ArticuloRead(ArticuloBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int
    qinvent: Optional[Decimal] = 0
    qcompras: Optional[Decimal] = 0
    qventas: Optional[Decimal] = 0
    marca: Optional[str] = None


# ─── Apuntes (líneas de documentos) ──────────────────────────────────────────

class ApunteBase(BaseModel):
    tipo: Optional[str] = None
    articulo: Optional[int] = None
    texto: Optional[str] = None
    texto2: Optional[str] = None
    cantidad: Optional[Decimal] = 1
    precio: Optional[Decimal] = 0
    dcto1: Optional[Decimal] = 0
    dcto2: Optional[Decimal] = 0
    dcto3: Optional[Decimal] = 0
    tiva: Optional[int] = None
    tipoop: Optional[int] = None
    cuenta: Optional[str] = None
    grupo: Optional[str] = None
    almacen: Optional[str] = None

class ApunteCreate(ApunteBase):
    pass

class ApunteRead(ApunteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    albaran: int
    talbaran: Optional[str] = None
    fecha: Optional[datetime.date] = None
    importe: Optional[Decimal] = 0


# ─── Albaranes emitidos ───────────────────────────────────────────────────────

class AlbaranEmiBase(BaseModel):
    fecha: Optional[datetime.date] = None
    cliente: Optional[int] = None
    cnumalt: Optional[str] = None
    cpi: Optional[str] = None
    notas: Optional[str] = None
    estado: Optional[str] = 'P'

class AlbaranEmiCreate(AlbaranEmiBase):
    fecha: datetime.date
    cliente: int
    empresa_id: int
    lineas: list[ApunteCreate] = []

class AlbaranEmiUpdate(AlbaranEmiBase):
    lineas: Optional[list[ApunteCreate]] = None

class AlbaranEmiRead(AlbaranEmiBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int
    cnumero: Optional[int] = None
    tiponum: Optional[str] = None
    factura: Optional[int] = None
    importe: Optional[Decimal] = 0
    marca: Optional[str] = None
    lineas: list[ApunteRead] = []


# ─── Albaranes recibidos ──────────────────────────────────────────────────────

class AlbaranRecBase(BaseModel):
    fecha: Optional[datetime.date] = None
    proveedor: Optional[int] = None
    pralbaran: Optional[str] = None
    prfecha: Optional[datetime.date] = None
    cnumalt: Optional[str] = None
    notas: Optional[str] = None
    estado: Optional[str] = 'P'

class AlbaranRecCreate(AlbaranRecBase):
    fecha: datetime.date
    proveedor: int
    empresa_id: int
    lineas: list[ApunteCreate] = []

class AlbaranRecUpdate(AlbaranRecBase):
    lineas: Optional[list[ApunteCreate]] = None

class AlbaranRecRead(AlbaranRecBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int
    cnumero: Optional[int] = None
    tiponum: Optional[str] = None
    factura: Optional[int] = None
    importe: Optional[Decimal] = 0
    marca: Optional[str] = None
    lineas: list[ApunteRead] = []


# ─── Facturas emitidas ────────────────────────────────────────────────────────

class FacturaEmiBase(BaseModel):
    fecha: Optional[datetime.date] = None
    cliente: Optional[int] = None
    clcuenta: Optional[str] = None
    tipoop: Optional[int] = None
    cnumalt: Optional[str] = None
    declterc: Optional[str] = None
    ccaja: Optional[str] = None
    notas: Optional[str] = None
    estado: Optional[str] = 'P'

class FacturaEmiCreate(FacturaEmiBase):
    fecha: datetime.date
    cliente: int
    empresa_id: int
    lineas: list[ApunteCreate] = []

class FacturaEmiUpdate(FacturaEmiBase):
    lineas: Optional[list[ApunteCreate]] = None

class FacturaEmiRead(FacturaEmiBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int
    cnumero: Optional[int] = None
    tiponum: Optional[str] = None
    total: Optional[Decimal] = 0
    totaldecl: Optional[Decimal] = 0
    marca: Optional[str] = None
    lineas: list[ApunteRead] = []
    pago_info: Optional[FacturaPagoInfo] = None
    fecha_vto: Optional[datetime.date] = None


# ─── Facturas recibidas ───────────────────────────────────────────────────────

class FacturaRecBase(BaseModel):
    fecha: Optional[datetime.date] = None
    proveedor: Optional[int] = None
    prcuenta: Optional[str] = None
    prfactura: Optional[str] = None
    prfecha: Optional[datetime.date] = None
    tipoop: Optional[int] = None
    cnumalt: Optional[str] = None
    declterc: Optional[str] = None
    ccaja: Optional[str] = None
    notas: Optional[str] = None
    estado: Optional[str] = 'P'

class FacturaRecCreate(FacturaRecBase):
    fecha: datetime.date
    proveedor: int
    empresa_id: int
    lineas: list[ApunteCreate] = []
    forzar: Optional[bool] = False

class FacturaRecUpdate(FacturaRecBase):
    lineas: Optional[list[ApunteCreate]] = None
    forzar: Optional[bool] = False

class FacturaRecRead(FacturaRecBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int
    cnumero: Optional[int] = None
    tiponum: Optional[str] = None
    total: Optional[Decimal] = 0
    totaldecl: Optional[Decimal] = 0
    marca: Optional[str] = None
    lineas: list[ApunteRead] = []
    pago_info: Optional[FacturaPagoInfo] = None
    fecha_vto: Optional[datetime.date] = None


# ─── Presupuestos ─────────────────────────────────────────────────────────────

class PresupuestoBase(BaseModel):
    fecha: Optional[datetime.date] = None
    cliente: Optional[int] = None
    cnumalt: Optional[str] = None
    notas: Optional[str] = None
    estado: Optional[str] = 'P'

class PresupuestoCreate(PresupuestoBase):
    fecha: datetime.date
    cliente: int
    empresa_id: int
    lineas: list[ApunteCreate] = []

class PresupuestoUpdate(PresupuestoBase):
    lineas: Optional[list[ApunteCreate]] = None

class PresupuestoRead(PresupuestoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int
    cnumero: Optional[int] = None
    tiponum: Optional[str] = None
    importe: Optional[Decimal] = 0
    marca: Optional[str] = None
    lineas: list[ApunteRead] = []
