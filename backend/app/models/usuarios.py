from sqlalchemy import String, Integer, Numeric, Boolean, Text, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from app.models.sync_mixin import SyncMixin
import datetime
from decimal import Decimal


class UsuarioSistema(Base):
    """Usuarios del sistema con acceso al ERP."""
    __tablename__ = "usuarios_sistema"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=True)
    rol: Mapped[str] = mapped_column(String(20), default="operador")  # admin, operador, solo_lectura
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=True)


class UsuarioNNA(SyncMixin, Base):
    __tablename__ = "usuarios_nna"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=True)
    fecha_nacimiento: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    fecha_ingreso: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    fecha_salida: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    paga_mensual: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class PagaNNA(SyncMixin, Base):
    __tablename__ = "pagas_nna"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    usuario: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # UsuarioNNA.numero
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    importe: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notas: Mapped[str] = mapped_column(String(200), nullable=True)
