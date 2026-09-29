from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.empresas import Empresa
from app.models.contabilidad import Cuenta, Diario
from app.models.facturacion import FacturaEmitida, FacturaRecibida, AlbaranEmitido, AlbaranRecibido
from app.models.bancos import Banco, MovBanco
from app.models.usuarios import UsuarioNNA, PagaNNA
from app.models.clientes_proveedores import Cliente, Proveedor
from app.schemas.empresas import EmpresaRead, EmpresaCreate, EmpresaUpdate
from app.services.auth import get_current_user
from app.services.permissions import (require_configuration, empresa_query,
                                      exigir_empresa)
from app.services.plan_contable import crear_plan_cuentas

router = APIRouter(prefix="/api/empresas", tags=["empresas"])

TABLAS_CON_DATOS = [
    (Diario, "asientos contables"),
    (FacturaEmitida, "facturas emitidas"),
    (FacturaRecibida, "facturas recibidas"),
    (AlbaranEmitido, "albaranes emitidos"),
    (AlbaranRecibido, "albaranes recibidos"),
    (MovBanco, "movimientos bancarios"),
    (PagaNNA, "pagas NNA"),
    (Cliente, "clientes"),
    (Proveedor, "proveedores"),
]


def _empresa_tiene_datos(db: Session, empresa_id: int) -> list[str]:
    problemas = []
    for modelo, desc in TABLAS_CON_DATOS:
        count = db.query(modelo).filter(modelo.empresa_id == empresa_id).count()
        if count > 0:
            problemas.append(f"{desc} ({count})")
    return problemas


def _borrar_empresa(db: Session, empresa_id: int):
    for modelo, _ in TABLAS_CON_DATOS:
        db.query(modelo).filter(modelo.empresa_id == empresa_id).delete()
    db.query(Cuenta).filter(Cuenta.empresa_id == empresa_id).delete()
    db.query(Banco).filter(Banco.empresa_id == empresa_id).delete()
    db.query(UsuarioNNA).filter(UsuarioNNA.empresa_id == empresa_id).delete()
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if empresa:
        db.delete(empresa)
    db.commit()


@router.get("", response_model=list[EmpresaRead])
def listar_empresas(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(Empresa).filter(Empresa.activa == True)  # noqa: E712
    if getattr(current_user, "empresa_id", None) is not None:
        q = q.filter(Empresa.id == current_user.empresa_id)
    return q.order_by(Empresa.codigo).all()


@router.get("/{empresa_id}", response_model=EmpresaRead)
def obtener_empresa(empresa_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(current_user, empresa, campo="id")
    return empresa


@router.post("", response_model=EmpresaRead, status_code=201)
def crear_empresa(data: EmpresaCreate, db: Session = Depends(get_db), current_user=Depends(require_configuration)):
    # D-03 (v1.13.07): solo admins globales. Un admin con empresa asignada
    # crearía una empresa que no vería en su selector ni podría gestionar.
    if current_user.empresa_id is not None:
        raise HTTPException(403, "Solo un administrador global puede crear empresas")
    existing = db.query(Empresa).filter(Empresa.codigo == data.codigo).first()
    if existing:
        raise HTTPException(400, "Ya existe una empresa con ese código")
    empresa = Empresa(codigo=data.codigo, nombre=data.nombre, activa=True)
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    crear_plan_cuentas(db, empresa.id)
    return empresa


@router.put("/{empresa_id}", response_model=EmpresaRead)
def actualizar_empresa(empresa_id: int, data: EmpresaUpdate, db: Session = Depends(get_db), current_user=Depends(require_configuration)):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(current_user, empresa, campo="id")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(empresa, campo, valor)
    db.commit()
    db.refresh(empresa)
    return empresa


@router.delete("/{empresa_id}")
def eliminar_empresa(empresa_id: int, db: Session = Depends(get_db), current_user=Depends(require_configuration)):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(current_user, empresa, campo="id")
    problemas = _empresa_tiene_datos(db, empresa_id)
    if problemas:
        raise HTTPException(400, f"No se puede eliminar: tiene datos en: {', '.join(problemas)}")
    _borrar_empresa(db, empresa_id)
    return {"ok": True, "mensaje": "Empresa eliminada"}
