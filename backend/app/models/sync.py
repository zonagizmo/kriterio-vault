from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
import datetime


class SyncLog(Base):
    """Registro de operaciones de negocio (alta/edición/baja) pendientes de
    enviar al servidor central. No se sincroniza fila a fila: cada entrada
    describe una operación completa (los mismos datos que recibió el
    endpoint), para poder reproducirla en destino con la misma lógica de
    servicio que ya genera los efectos derivados (asientos, vencimientos...)."""
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tabla: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entidad_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    operacion: Mapped[str] = mapped_column(String(1), nullable=False)  # C=alta, U=edición, D=baja
    payload: Mapped[str] = mapped_column(Text, nullable=True)
    origen_instalacion: Mapped[str] = mapped_column(String(36), nullable=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, index=True)
    sincronizado: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Instalacion(Base):
    """Instalación registrada para sincronizar con el servidor central. Solo
    tiene sentido en el servidor (Postgres); en una instalación local normal
    esta tabla existe pero se queda vacía. El emparejamiento se hace a mano
    con `scripts/crear_instalacion.py` en el propio servidor, no por HTTP:
    no hay ningún usuario "admin" autenticado que pueda dar de alta otras
    instalaciones, así que ese primer paso tiene que hacerse fuera de la API."""
    __tablename__ = "instalaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    empresas: Mapped[str] = mapped_column(String(200), nullable=True)  # CSV de empresa_id permitidos; NULL = todas
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    ultima_sincronizacion: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
