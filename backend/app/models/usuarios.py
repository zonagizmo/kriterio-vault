from sqlalchemy import String, Integer, Numeric, Boolean, Text, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from app.models.sync_mixin import SyncMixin
import datetime


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
    paga_mensual: Mapped[float] = mapped_column(Numeric(10, 2, asdecimal=False), default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class PagaNNA(SyncMixin, Base):
    __tablename__ = "pagas_nna"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    usuario: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # UsuarioNNA.numero
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    importe: Mapped[float] = mapped_column(Numeric(10, 2, asdecimal=False), nullable=False)
    notas: Mapped[str] = mapped_column(String(200), nullable=True)
