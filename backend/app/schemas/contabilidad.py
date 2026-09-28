from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime
from decimal import Decimal


# ─── Plan de cuentas ─────────────────────────────────────────────────────────

class CuentaBase(BaseModel):
    cuenta: str
    texto: Optional[str] = None

class CuentaCreate(CuentaBase):
    empresa_id: int

class CuentaUpdate(BaseModel):
    texto: Optional[str] = None
    marca: Optional[str] = None

class CuentaRead(CuentaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    debe: Optional[Decimal] = 0
    haber: Optional[Decimal] = 0
    marca: Optional[str] = None


# ─── Líneas de asiento (Diario) ───────────────────────────────────────────────

class DiarioLineaCreate(BaseModel):
    cuenta: str
    importe: Decimal           # positivo = Debe, negativo = Haber
    clave: Optional[str] = None
    tipo: Optional[str] = None
    numero: Optional[int] = None
    multi: Optional[str] = None

class DiarioLineaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    asiento: int
    fecha: Optional[datetime.date] = None
    cuenta: Optional[str] = None
    importe: Optional[Decimal] = 0
    saldo: Optional[Decimal] = 0
    tpasiento: Optional[str] = None
    clave: Optional[str] = None
    tipo: Optional[str] = None
    numero: Optional[int] = None
    marca: Optional[str] = None


# ─── Asiento contable (cabecera + líneas) ────────────────────────────────────

class AsientoCreate(BaseModel):
    empresa_id: int
    fecha: datetime.date
    tpasiento: Optional[str] = None
    clave: Optional[str] = None
    tipo: Optional[str] = None
    numero: Optional[int] = None
    lineas: list[DiarioLineaCreate]

class AsientoRead(BaseModel):
    asiento: int
    empresa_id: int
    fecha: Optional[datetime.date] = None
    tpasiento: Optional[str] = None
    clave: Optional[str] = None
    tipo: Optional[str] = None
    numero: Optional[int] = None
    lineas: list[DiarioLineaRead] = []
    total_debe: Decimal = 0
    total_haber: Decimal = 0
    cuadrado: bool = False
