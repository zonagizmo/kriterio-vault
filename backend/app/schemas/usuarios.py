from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime


# ─── Usuario NNA ─────────────────────────────────────────────────────────────

class UsuarioBase(BaseModel):
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    fecha_nacimiento: Optional[datetime.date] = None
    fecha_ingreso: Optional[datetime.date] = None
    fecha_salida: Optional[datetime.date] = None
    paga_mensual: Optional[float] = 0
    activo: Optional[bool] = True
    notas: Optional[str] = None

class UsuarioCreate(UsuarioBase):
    nombre: str
    empresa_id: int

class UsuarioUpdate(UsuarioBase):
    pass

class UsuarioRead(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int


# ─── Paga NNA ────────────────────────────────────────────────────────────────

class PagaCreate(BaseModel):
    empresa_id: int
    usuario: int        # UsuarioNNA.numero
    fecha: datetime.date
    importe: float
    notas: Optional[str] = None

class PagaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    usuario: int
    fecha: datetime.date
    importe: float
    notas: Optional[str] = None


# ─── Registro mensual (entrada) ───────────────────────────────────────────────

class RegistroMensualItem(BaseModel):
    usuario: int
    importe: float
    notas: Optional[str] = None

class RegistroMensualCreate(BaseModel):
    empresa_id: int
    fecha: datetime.date
    items: list[RegistroMensualItem]
