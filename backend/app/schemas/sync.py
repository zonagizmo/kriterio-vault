from pydantic import BaseModel
from typing import Optional


class SyncPushItem(BaseModel):
    tabla: str
    entidad_uuid: str
    operacion: str  # C / U / D
    empresa_id: int
    payload: Optional[dict] = None


class SyncPushResult(BaseModel):
    ok: bool
    error: Optional[str] = None


class SyncPushResponse(BaseModel):
    resultados: list[SyncPushResult]
