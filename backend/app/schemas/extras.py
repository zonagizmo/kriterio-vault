from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime


class ExApunteCreate(BaseModel):
    cuenta: Optional[str] = None
    ayuda: Optional[str] = None
    dh: Optional[str] = None      # 'D' = Debe, 'H' = Haber
    importe: float = 0
    declterc: Optional[str] = None


class ExApunteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    numero: int
    extra: int
    cuenta: Optional[str] = None
    ayuda: Optional[str] = None
    dh: Optional[str] = None
    importe: Optional[float] = 0
    declterc: Optional[str] = None


class ExtraBase(BaseModel):
    fecha: Optional[datetime.date] = None
    tipo: Optional[str] = None       # 'G' = Gasto, 'I' = Ingreso
    texto: Optional[str] = None
    grupo: Optional[str] = None
    clave: Optional[str] = None
    estado: Optional[str] = None
    notas: Optional[str] = None


class ExtraCreate(ExtraBase):
    empresa_id: int
    fecha: datetime.date
    tipo: str
    apuntes: list[ExApunteCreate] = []
    generar_vto: bool = False
    vto_importe: Optional[float] = None
    vto_cuenta: Optional[str] = None
    vto_fecha: Optional[datetime.date] = None


class ExtraUpdate(ExtraBase):
    apuntes: Optional[list[ExApunteCreate]] = None
    generar_vto: Optional[bool] = None
    vto_importe: Optional[float] = None
    vto_cuenta: Optional[str] = None
    vto_fecha: Optional[datetime.date] = None


class ExtraPagoInfo(BaseModel):
    banco_nombre: str
    fecha: Optional[datetime.date] = None
    importe: float


class ExtraRead(ExtraBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    numero: int
    cnumero: Optional[int] = None
    tiponum: Optional[str] = None
    apuntes: list[ExApunteRead] = []
    pago_info: Optional[ExtraPagoInfo] = None
    fecha_vto: Optional[datetime.date] = None
    tiene_vencimiento: bool = False
