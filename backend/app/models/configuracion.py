from sqlalchemy import String, Integer, Numeric, Boolean, Text, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Parametro(Base):
    __tablename__ = "parametros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    etiqueta: Mapped[str] = mapped_column(String(30), nullable=False)
    texto: Mapped[str] = mapped_column(String(200), nullable=True)
    mas: Mapped[str] = mapped_column(Text, nullable=True)


class Actividad(Base):
    __tablename__ = "actividades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre: Mapped[str] = mapped_column(String(50), nullable=True)
    etiqueta: Mapped[str] = mapped_column(String(20), nullable=True)
    activa: Mapped[str] = mapped_column(String(1), nullable=True)


class TipoIva(Base):
    __tablename__ = "tipo_iva"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    texto: Mapped[str] = mapped_column(String(50), nullable=True)
    iva: Mapped[float] = mapped_column(Numeric(5, 2, asdecimal=False), nullable=True)
    cta_iva: Mapped[str] = mapped_column(String(15), nullable=True)
    iva_re: Mapped[float] = mapped_column(Numeric(5, 2, asdecimal=False), nullable=True)
    cta_iva_re: Mapped[str] = mapped_column(String(15), nullable=True)
    pordefecto: Mapped[bool] = mapped_column(Boolean, default=False)
    inactivo: Mapped[bool] = mapped_column(Boolean, default=False)
    abrevia: Mapped[str] = mapped_column(String(10), nullable=True)


class Operacion(Base):
    __tablename__ = "operaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    texto: Mapped[str] = mapped_column(String(50), nullable=True)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    pordefecto: Mapped[bool] = mapped_column(Boolean, default=False)
    iva: Mapped[int] = mapped_column(Integer, nullable=True)


class Referencia(Base):
    __tablename__ = "referencias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    texto: Mapped[str] = mapped_column(String(50), nullable=True)


class TipoVto(Base):
    __tablename__ = "tipo_vtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    texto: Mapped[str] = mapped_column(String(50), nullable=True)
    clidef: Mapped[str] = mapped_column(String(1), nullable=True)
    provdef: Mapped[str] = mapped_column(String(1), nullable=True)
    estado: Mapped[str] = mapped_column(String(1), nullable=True)


class Directo(Base):
    __tablename__ = "directos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=False)
    texto: Mapped[str] = mapped_column(String(100), nullable=True)


class ExPlantilla(Base):
    __tablename__ = "ex_plantillas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    texto: Mapped[str] = mapped_column(String(100), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=True)
