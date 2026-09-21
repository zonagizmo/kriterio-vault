from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserRead"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserRead(BaseModel):
    id: int
    username: str
    activo: bool

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    password_actual: str
    password_nuevo: str
