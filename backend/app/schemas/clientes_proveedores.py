from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime


# ─── Clientes ────────────────────────────────────────────────────────────────

class ClienteBase(BaseModel):
    nombre: Optional[str] = None
    comercial: Optional[str] = None
    domicilio: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    cod_postal: Optional[str] = None
    ap_correos: Optional[str] = None
    nif: Optional[str] = None
    cuenta: Optional[str] = None
    operacion: Optional[int] = None
    iva: Optional[int] = None
    banco_nom: Optional[str] = None
    banco_suc: Optional[str] = None
    banco_dig: Optional[str] = None
    banco_tit: Optional[str] = None
    anticipo: Optional[str] = None
    tipo: Optional[str] = None
    declterc: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    contactos: Optional[str] = None
    notas: Optional[str] = None


class ClienteCreate(ClienteBase):
    nombre: str
    empresa_id: int


class ClienteUpdate(ClienteBase):
    pass


class ClienteRead(ClienteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    numero: int
    bruto: Optional[float] = 0
    neto: Optional[float] = 0
    pendiente: Optional[float] = 0
    marca: Optional[str] = None


# ─── Proveedores ──────────────────────────────────────────────────────────────

class ProveedorBase(BaseModel):
    nombre: Optional[str] = None
    comercial: Optional[str] = None
    domicilio: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    cod_postal: Optional[str] = None
    ap_correos: Optional[str] = None
    nif: Optional[str] = None
    cuenta: Optional[str] = None
    operacion: Optional[int] = None
    iva: Optional[int] = None
    ctairpf: Optional[str] = None
    anticipo: Optional[str] = None
    tipo: Optional[str] = None
    ccaja: Optional[str] = None
    declterc: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    contactos: Optional[str] = None
    notas: Optional[str] = None


class ProveedorCreate(ProveedorBase):
    nombre: str
    empresa_id: int


class ProveedorUpdate(ProveedorBase):
    pass


class ProveedorRead(ProveedorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    numero: int
    bruto: Optional[float] = 0
    pendiente: Optional[float] = 0
    neto: Optional[float] = 0
    marca: Optional[str] = None


# ─── Vencimientos ─────────────────────────────────────────────────────────────

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
