from typing import Optional
from pydantic import BaseModel, ConfigDict


class EmpresaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    activa: bool
    nif: Optional[str] = None
    domicilio: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    cod_postal: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None


class EmpresaUpdate(BaseModel):
    nombre: Optional[str] = None
    nif: Optional[str] = None
    domicilio: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    cod_postal: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
