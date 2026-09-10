"""Columnas comunes para las tablas que se sincronizarán con el servidor central.

`uuid` es la identidad estable de la fila entre instalaciones (el `numero` de
negocio no sirve para esto: se calcula como MAX(numero)+1 por empresa y puede
colisionar entre dos instalaciones que crean documentos sin conexión).
`version` se usa para detectar conflictos de sincronización (edición concurrente
del mismo documento desde dos instalaciones) sin necesidad de comparar filas
completas.
"""
import datetime
import uuid as uuid_lib
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class SyncMixin:
    """`version` se incrementa a mano en los servicios de edición (no vía
    evento ORM antes de update): una fila puede recibir más de un UPDATE SQL
    dentro de una misma operación de alta (p. ej. fijar el total tras guardar
    las líneas), y un incremento automático por cada UPDATE confundiría eso
    con una edición real de cara a la detección de conflictos."""
    uuid: Mapped[str] = mapped_column(
        String(36), default=lambda: str(uuid_lib.uuid4()), unique=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
