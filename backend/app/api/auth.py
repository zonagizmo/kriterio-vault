from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.middleware.rate_limit import limiter
from app.models.usuarios import UsuarioSistema
from app.schemas.auth import (
    LoginRequest, LoginResponse, UsuarioToken,
    CambioPassword, UsuarioSistemaCreate, UsuarioSistemaUpdate, CambioPasswordAdmin,
)
from app.services.auth import verify_password, hash_password, create_access_token, get_current_user
from app.services.permissions import ROLES_VALIDOS, exigir_empresa, require_user_management

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UsuarioSistema).filter(
        UsuarioSistema.username == data.username
    ).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario desactivado",
        )

    access_token = create_access_token(data={"sub": user.id, "rol": user.rol})

    return LoginResponse(
        access_token=access_token,
        usuario={
            "id": user.id,
            "username": user.username,
            "nombre": user.nombre,
            "email": user.email,
            "rol": user.rol,
            "activo": user.activo,
            "empresa_id": user.empresa_id,
        },
    )


@router.get("/me", response_model=UsuarioToken)
def get_me(current_user: UsuarioSistema = Depends(get_current_user)):
    return UsuarioToken(
        id=current_user.id,
        username=current_user.username,
        nombre=current_user.nombre,
        rol=current_user.rol,
        activo=current_user.activo,
        empresa_id=current_user.empresa_id,
    )


@router.post("/cambiar-password")
def cambiar_password(data: CambioPassword, db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(get_current_user)):
    if not verify_password(data.password_actual, current_user.password_hash):
        raise HTTPException(400, "La contraseña actual es incorrecta")
    current_user.password_hash = hash_password(data.password_nuevo)
    db.commit()
    return {"ok": True, "mensaje": "Contraseña cambiada correctamente"}


# --- Gestion de usuarios (user_management: solo admin) ---


@router.get("/usuarios", response_model=dict)
def listar_usuarios(db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(require_user_management)):
    q = db.query(UsuarioSistema)
    if getattr(current_user, "empresa_id", None) is not None:
        # RPT-001: el admin de una empresa solo ve los de su empresa
        # (más los usuarios globales, empresa_id NULL, que no pertenecen a nadie).
        q = q.filter(or_(
            UsuarioSistema.empresa_id == current_user.empresa_id,
            UsuarioSistema.empresa_id.is_(None),
        ))
    users = q.order_by(UsuarioSistema.username).all()
    return {
        "total": len(users),
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "nombre": u.nombre,
                "email": u.email,
                "rol": u.rol,
                "activo": u.activo,
                "empresa_id": u.empresa_id,
            }
            for u in users
        ],
    }


@router.post("/usuarios", status_code=201)
def crear_usuario_sistema(data: UsuarioSistemaCreate, db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(require_user_management)):
    existing = db.query(UsuarioSistema).filter(UsuarioSistema.username == data.username).first()
    if existing:
        raise HTTPException(400, "Ya existe un usuario con ese nombre")
    if data.rol not in ROLES_VALIDOS:
        raise HTTPException(400, "Rol no valido. Use: admin, operador, solo_lectura")
    # RPT-002: un admin con empresa asignada solo da de alta en su propia empresa
    # (ni en otra empresa ni usuarios globales, que tendrían acceso a todas).
    empresa_asignada = data.empresa_id
    if getattr(current_user, "empresa_id", None) is not None:
        if empresa_asignada is not None and empresa_asignada != current_user.empresa_id:
            raise HTTPException(404, "Recurso no encontrado")
        empresa_asignada = current_user.empresa_id
    user = UsuarioSistema(
        username=data.username,
        password_hash=hash_password(data.password),
        nombre=data.nombre,
        email=data.email,
        rol=data.rol,
        activo=True,
        empresa_id=empresa_asignada,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "nombre": user.nombre, "email": user.email, "rol": user.rol, "activo": user.activo, "empresa_id": user.empresa_id}


@router.put("/usuarios/{user_id}")
def actualizar_usuario_sistema(user_id: int, data: UsuarioSistemaUpdate, db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(require_user_management)):
    user = db.query(UsuarioSistema).filter(UsuarioSistema.id == user_id).first()
    if not user:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(current_user, user)
    campos = data.model_dump(exclude_unset=True)
    if (getattr(current_user, "empresa_id", None) is not None
            and "empresa_id" in campos
            and campos["empresa_id"] != current_user.empresa_id):
        raise HTTPException(404, "Recurso no encontrado")
    if user.id == current_user.id and data.activo is False:
        raise HTTPException(400, "No puedes desactivar tu propio usuario")
    for campo, valor in campos.items():
        if campo == "rol" and valor not in ROLES_VALIDOS:
            raise HTTPException(400, "Rol no valido")
        setattr(user, campo, valor)
    db.commit()
    return {"ok": True}


@router.post("/usuarios/{user_id}/reset-password")
def reset_password_admin(user_id: int, data: CambioPasswordAdmin, db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(require_user_management)):
    user = db.query(UsuarioSistema).filter(UsuarioSistema.id == user_id).first()
    if not user:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(current_user, user)
    user.password_hash = hash_password(data.password_nuevo)
    db.commit()
    return {"ok": True, "mensaje": f"Contrasena de {user.username} reseteada"}


@router.delete("/usuarios/{user_id}")
def eliminar_usuario_sistema(user_id: int, db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(require_user_management)):
    user = db.query(UsuarioSistema).filter(UsuarioSistema.id == user_id).first()
    if not user:
        raise HTTPException(404, "Recurso no encontrado")
    exigir_empresa(current_user, user)
    if user.id == current_user.id:
        raise HTTPException(400, "No puedes eliminar tu propio usuario")
    db.delete(user)
    db.commit()
    return {"ok": True}
