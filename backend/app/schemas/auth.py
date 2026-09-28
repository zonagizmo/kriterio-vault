from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: dict


class UsuarioToken(BaseModel):
    id: int
    username: str
    nombre: str
    rol: str
    activo: bool = True
    empresa_id: Optional[int] = None


class CambioPassword(BaseModel):
    password_actual: str
    password_nuevo: str


class UsuarioSistemaCreate(BaseModel):
    username: str
    password: str
    nombre: str
    email: Optional[str] = None
    rol: str = "operador"
    empresa_id: Optional[int] = None


class UsuarioSistemaUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None
    empresa_id: Optional[int] = None


class CambioPasswordAdmin(BaseModel):
    password_nuevo: str
