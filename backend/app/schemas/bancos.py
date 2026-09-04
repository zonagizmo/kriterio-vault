from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime


# ─── Bancos ──────────────────────────────────────────────────────────────────

class BancoBase(BaseModel):
    nombre: Optional[str] = None
    sucursal: Optional[str] = None
    numcta: Optional[str] = None
    cuenta: Optional[str] = None
    notas: Optional[str] = None

class BancoCreate(BancoBase):
    nombre: str
    empresa_id: int
    saldoini: Optional[float] = 0

class BancoUpdate(BancoBase):
    numero: Optional[int] = None
    saldoini: Optional[float] = None

class BancoRead(BancoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int
    saldoini: Optional[float] = 0
    saldoact: Optional[float] = 0


# ─── Pagos (líneas de un movimiento) ─────────────────────────────────────────

class PagoCreate(BaseModel):
    importe: float
    vto: Optional[int] = None
    dirsubcta: Optional[str] = None
    declterc: Optional[str] = None
    bancot: Optional[int] = None     # transferencia a otro banco

class PagoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    banco: int
    numero: int
    importe: Optional[float] = 0
    vto: Optional[int] = None
    dirsubcta: Optional[str] = None
    dirsubcta_nombre: Optional[str] = None
    declterc: Optional[str] = None
    bancot: Optional[int] = None
    numerot: Optional[int] = None
    # Campos enriquecidos para la UI (no están en la BD, se calculan en _enrich_mov)
    vto_tipo: Optional[str] = None
    vto_tpnumero: Optional[int] = None
    vto_existe: Optional[bool] = None
    doc_numero_externo: Optional[str] = None
    doc_entidad_nombre: Optional[str] = None
    doc_fecha: Optional[datetime.date] = None
    bancot_nombre: Optional[str] = None


# ─── Movimientos bancarios ────────────────────────────────────────────────────

class MovimientoBase(BaseModel):
    banco: Optional[int] = None
    texto: Optional[str] = None
    fecha: Optional[datetime.date] = None
    total: Optional[float] = 0
    clave: Optional[str] = None
    notas: Optional[str] = None
    estado: Optional[str] = None
    conciliado: Optional[bool] = False

class MovimientoCreate(MovimientoBase):
    banco: int
    fecha: datetime.date
    total: float
    empresa_id: int
    pagos: list[PagoCreate] = []

class MovimientoUpdate(MovimientoBase):
    total: Optional[float] = None   # override para distinguir "no enviado" de 0
    conciliado: Optional[bool] = None  # override: None = no tocar (el default False de la base reseteaba la conciliación en cada edición)
    pagos: Optional[list[PagoCreate]] = None

class MovimientoRead(MovimientoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int
    cnumero: Optional[int] = None
    tiponum: Optional[str] = None
    cnumalt: Optional[str] = None
    autotext: Optional[bool] = False
    saldonue: Optional[float] = 0
    marca: Optional[str] = None
    pagos: list[PagoRead] = []


# ─── Vencimientos ─────────────────────────────────────────────────────────────

class VencimientoCreate(BaseModel):
    empresa_id: int
    tipo: str
    tpnumero: Optional[int] = None
    fecha: datetime.date
    importe: float
    cuenta: Optional[str] = None
    cuentadef: Optional[str] = None

class VencimientoUpdate(BaseModel):
    fecha: Optional[datetime.date] = None
    pendiente: Optional[float] = None

class VencimientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int
    tipo: str
    tpnumero: Optional[int] = None
    fecha: Optional[datetime.date] = None
    importe: Optional[float] = 0
    pendiente: Optional[float] = 0
    cuenta: Optional[str] = None
    cuentadef: Optional[str] = None
    pentidad: Optional[int] = None
    ptipo: Optional[int] = None
    extra_tipo: Optional[str] = None  # 'G' o 'I' cuando tipo='X'
