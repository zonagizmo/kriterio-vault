from sqlalchemy import String, Integer, Numeric, Boolean, Text, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from app.models.sync_mixin import SyncMixin
import datetime


class Cuenta(SyncMixin, Base):
    __tablename__ = "cuentas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    texto: Mapped[str] = mapped_column(String(100), nullable=True)
    debe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    haber: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    pentidad: Mapped[int] = mapped_column(Integer, nullable=True)
    pdirecto: Mapped[int] = mapped_column(Integer, nullable=True)
    ptipo: Mapped[int] = mapped_column(Integer, nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)


class Diario(Base):
    __tablename__ = "diario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    asiento: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    tpasiento: Mapped[str] = mapped_column(String(6), nullable=True)
    clave: Mapped[str] = mapped_column(String(15), nullable=True)
    clave_ori: Mapped[str] = mapped_column(String(15), nullable=True)
    tipo: Mapped[str] = mapped_column(String(2), nullable=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=True, index=True)
    saldo: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    multi: Mapped[str] = mapped_column(String(2), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)


class DiarioTxt(Base):
    __tablename__ = "diario_txt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(2), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    texto: Mapped[str] = mapped_column(String(100), nullable=True)
    docu: Mapped[str] = mapped_column(String(20), nullable=True)
    multi: Mapped[str] = mapped_column(String(2), nullable=True)
    negativo: Mapped[str] = mapped_column(String(1), nullable=True)
    acumular: Mapped[str] = mapped_column(String(1), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class Analitica(Base):
    __tablename__ = "analitica"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(2), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    actividad: Mapped[int] = mapped_column(Integer, nullable=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)


class Ajuste(Base):
    __tablename__ = "ajustes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(2), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    contra: Mapped[str] = mapped_column(String(15), nullable=True)
    cambioas: Mapped[str] = mapped_column(String(1), nullable=True)
    afectaiva: Mapped[str] = mapped_column(String(1), nullable=True)
    declterc: Mapped[str] = mapped_column(String(1), nullable=True)


class Extra(SyncMixin, Base):
    __tablename__ = "extras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cnumero: Mapped[int] = mapped_column(Integer, nullable=True)
    tiponum: Mapped[str] = mapped_column(String(2), nullable=True)
    cnumalt: Mapped[str] = mapped_column(String(20), nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=True)
    clave: Mapped[str] = mapped_column(String(15), nullable=True)
    texto: Mapped[str] = mapped_column(String(100), nullable=True)
    grupo: Mapped[str] = mapped_column(String(10), nullable=True)
    estado: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class ExApunte(Base):
    __tablename__ = "ex_apuntes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    extra: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    ayuda: Mapped[str] = mapped_column(String(100), nullable=True)
    dh: Mapped[str] = mapped_column(String(1), nullable=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    declterc: Mapped[str] = mapped_column(String(1), nullable=True)


class RefApunte(Base):
    __tablename__ = "ref_apuntes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(2), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    tpnumero: Mapped[int] = mapped_column(Integer, nullable=True)


class Lbi(Base):
    """Libro de Bienes de Inversión."""
    __tablename__ = "lbi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    cuenbien: Mapped[str] = mapped_column(String(15), nullable=True)
    cuendota: Mapped[str] = mapped_column(String(15), nullable=True)
    cuenamort: Mapped[str] = mapped_column(String(15), nullable=True)
    coste: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    residual: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    fbaja: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    cbaja: Mapped[str] = mapped_column(String(15), nullable=True)
    coefi: Mapped[float] = mapped_column(Numeric(5, 2, asdecimal=False), nullable=True)
    periodo: Mapped[int] = mapped_column(Integer, nullable=True)
    meses: Mapped[int] = mapped_column(Integer, nullable=True)
    iva: Mapped[int] = mapped_column(Integer, nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    recibida: Mapped[int] = mapped_column(Integer, nullable=True)
    proveedor: Mapped[int] = mapped_column(Integer, nullable=True)
    regfecha: Mapped[datetime.date] = mapped_column(Date, nullable=True)
    registro: Mapped[int] = mapped_column(Integer, nullable=True)
    cuadro: Mapped[int] = mapped_column(Integer, nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)
