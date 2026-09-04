from sqlalchemy import String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    nif: Mapped[str] = mapped_column(String(20), nullable=True)
    domicilio: Mapped[str] = mapped_column(String(100), nullable=True)
    localidad: Mapped[str] = mapped_column(String(50), nullable=True)
    provincia: Mapped[str] = mapped_column(String(50), nullable=True)
    cod_postal: Mapped[str] = mapped_column(String(10), nullable=True)
    telefono: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=True)
