from sqlalchemy import String, Integer, Numeric, Boolean, Text, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
import datetime


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    comercial: Mapped[str] = mapped_column(String(100), nullable=True)
    domicilio: Mapped[str] = mapped_column(String(100), nullable=True)
    localidad: Mapped[str] = mapped_column(String(50), nullable=True)
    provincia: Mapped[str] = mapped_column(String(50), nullable=True)
    cod_postal: Mapped[str] = mapped_column(String(10), nullable=True)
    ap_correos: Mapped[str] = mapped_column(String(20), nullable=True)
    nif: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=True, index=True)
    operacion: Mapped[int] = mapped_column(Integer, nullable=True)
    bruto: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    neto: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    pendiente: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    banco_nom: Mapped[str] = mapped_column(String(4), nullable=True)
    banco_suc: Mapped[str] = mapped_column(String(4), nullable=True)
    banco_dig: Mapped[str] = mapped_column(String(2), nullable=True)
    iva: Mapped[int] = mapped_column(Integer, nullable=True)
    banco_tit: Mapped[str] = mapped_column(String(100), nullable=True)
    anticipo: Mapped[str] = mapped_column(String(1), nullable=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=True)
    declterc: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    telefono: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=True)
    contactos: Mapped[str] = mapped_column(Text, nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class Proveedor(Base):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    comercial: Mapped[str] = mapped_column(String(100), nullable=True)
    domicilio: Mapped[str] = mapped_column(String(100), nullable=True)
    localidad: Mapped[str] = mapped_column(String(50), nullable=True)
    provincia: Mapped[str] = mapped_column(String(50), nullable=True)
    cod_postal: Mapped[str] = mapped_column(String(10), nullable=True)
    ap_correos: Mapped[str] = mapped_column(String(20), nullable=True)
    nif: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=True, index=True)
    operacion: Mapped[int] = mapped_column(Integer, nullable=True)
    bruto: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    pendiente: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    neto: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    iva: Mapped[int] = mapped_column(Integer, nullable=True)
    ctairpf: Mapped[str] = mapped_column(String(15), nullable=True)
    anticipo: Mapped[str] = mapped_column(String(1), nullable=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=True)
    ccaja: Mapped[str] = mapped_column(String(1), nullable=True)
    declterc: Mapped[str] = mapped_column(String(1), nullable=True)
    marca: Mapped[str] = mapped_column(String(1), nullable=True)
    telefono: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=True)
    contactos: Mapped[str] = mapped_column(Text, nullable=True)
    notas: Mapped[str] = mapped_column(Text, nullable=True)


class Vencimiento(Base):
    __tablename__ = "vencimientos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=False, index=True)
    tpnumero: Mapped[int] = mapped_column(Integer, nullable=True)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=True, index=True)
    importe: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    pendiente: Mapped[float] = mapped_column(Numeric(15, 2, asdecimal=False), default=0)
    cuenta: Mapped[str] = mapped_column(String(15), nullable=True)
    cuentadef: Mapped[str] = mapped_column(String(15), nullable=True)
    pentidad: Mapped[int] = mapped_column(Integer, nullable=True)
    ptipo: Mapped[int] = mapped_column(Integer, nullable=True)


class Recibo(Base):
    __tablename__ = "recibos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(1), nullable=False)
    agente: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    tipoap: Mapped[str] = mapped_column(String(2), nullable=True)
    dia: Mapped[int] = mapped_column(Integer, nullable=True)
    mes: Mapped[int] = mapped_column(Integer, nullable=True)
    ejercicio: Mapped[int] = mapped_column(Integer, nullable=True)
    importe: Mapped[str] = mapped_column(String(20), nullable=True)
    concepto: Mapped[str] = mapped_column(String(100), nullable=True)
    rseparado: Mapped[int] = mapped_column(Integer, nullable=True)
    vto: Mapped[str] = mapped_column(String(20), nullable=True)


class EtiCod(Base):
    __tablename__ = "eticod"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(2), nullable=False)
    clave: Mapped[str] = mapped_column(String(20), nullable=False)
    forma: Mapped[str] = mapped_column(String(20), nullable=True)
    codigo: Mapped[str] = mapped_column(String(30), nullable=True)


class EtiDat(Base):
    __tablename__ = "etidat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(2), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    clave: Mapped[str] = mapped_column(String(20), nullable=False)
    texto: Mapped[str] = mapped_column(String(100), nullable=True)
