from sqlalchemy import String, Integer, Numeric, Text, ForeignKey, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
import datetime


class Banco(Base):
    __tablename__ = "bancos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=True)
    sucursal: Mapped[str] = mapped_column(String(100), nullable=True)
    numcta: Mapped[str] = mapped_column(String(30), nullable=True)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    saldoini: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    saldoact: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class MovBanco(Base):
    __tablename__ = "mov_bancos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    banco: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cnumero: Mapped[int] = mapped_column(Integer, nullable=True)
    tiponum: Mapped[str] = mapped_column(String(2), nullable=True)
    cnumalt: Mapped[str] = mapped_column(String(20), nullable=True)
    texto: Mapped[str] = mapped_column(String(100), nullable=True)
    autotext: Mapped[bool] = mapped_column(Boolean, default=False)
    clave: Mapped[str] = mapped_column(String(15), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    total: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    saldonue: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    estado: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    conciliado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class Pago(Base):
    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    banco: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    vto: Mapped[int] = mapped_column(Integer, nullable=True)
    dirsubcta: Mapped[str] = mapped_column(String(15), nullable=True)
    numerot: Mapped[int] = mapped_column(Integer, nullable=True)
    bancot: Mapped[int] = mapped_column(Integer, nullable=True)
    declterc: Mapped[str] = mapped_column(String(1), nullable=True)
