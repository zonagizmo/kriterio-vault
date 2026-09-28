from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.middleware.rate_limit import limiter
from app.models.usuarios import UsuarioSistema
from app.schemas.auth import (
    LoginRequest, LoginResponse, UsuarioToken,
    CambioPassword, UsuarioSistemaCreate, UsuarioSistemaUpdate, CambioPasswordAdmin,
)
from app.services.auth import verify_password, hash_password, create_access_token, get_current_user

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
            status_code=status.HTTP_403_FORBIDDEN,
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
        },
    )


@router.get("/me", response_model=UsuarioToken)
def get_me(current_user: UsuarioSistema = Depends(get_current_user)):
    return UsuarioToken(
        id=current_user.id,
        username=current_user.username,
        nombre=current_user.nombre,
        rol=current_user.rol,
    )


@router.post("/cambiar-password")
def cambiar_password(data: CambioPassword, db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(get_current_user)):
    if not verify_password(data.password_actual, current_user.password_hash):
        raise HTTPException(400, "La contraseña actual es incorrecta")
    current_user.password_hash = hash_password(data.password_nuevo)
    db.commit()
    return {"ok": True, "mensaje": "Contraseña cambiada correctamente"}


# --- Gestion de usuarios (solo admin) ---

def _require_admin(current_user: UsuarioSistema):
    if current_user.rol != "admin":
        raise HTTPException(403, "Solo los administradores pueden gestionar usuarios")


@router.get("/usuarios", response_model=dict)
def listar_usuarios(db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(get_current_user)):
    _require_admin(current_user)
    users = db.query(UsuarioSistema).order_by(UsuarioSistema.username).all()
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
            }
            for u in users
        ],
    }


@router.post("/usuarios", status_code=201)
def crear_usuario_sistema(data: UsuarioSistemaCreate, db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(get_current_user)):
    _require_admin(current_user)
    existing = db.query(UsuarioSistema).filter(UsuarioSistema.username == data.username).first()
    if existing:
        raise HTTPException(400, "Ya existe un usuario con ese nombre")
    if data.rol not in ("admin", "operador", "solo_lectura"):
        raise HTTPException(400, "Rol no valido. Use: admin, operador, solo_lectura")
    user = UsuarioSistema(
        username=data.username,
        password_hash=hash_password(data.password),
        nombre=data.nombre,
        email=data.email,
        rol=data.rol,
        activo=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "nombre": user.nombre, "email": user.email, "rol": user.rol, "activo": user.activo}


@router.put("/usuarios/{user_id}")
def actualizar_usuario_sistema(user_id: int, data: UsuarioSistemaUpdate, db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(get_current_user)):
    _require_admin(current_user)
    user = db.query(UsuarioSistema).filter(UsuarioSistema.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if user.id == current_user.id and data.activo is False:
        raise HTTPException(400, "No puedes desactivar tu propio usuario")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        if campo == "rol" and valor not in ("admin", "operador", "solo_lectura"):
            raise HTTPException(400, "Rol no valido")
        setattr(user, campo, valor)
    db.commit()
    return {"ok": True}


@router.post("/usuarios/{user_id}/reset-password")
def reset_password_admin(user_id: int, data: CambioPasswordAdmin, db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(get_current_user)):
    _require_admin(current_user)
    user = db.query(UsuarioSistema).filter(UsuarioSistema.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    user.password_hash = hash_password(data.password_nuevo)
    db.commit()
    return {"ok": True, "mensaje": f"Contrasena de {user.username} reseteada"}


@router.delete("/usuarios/{user_id}")
def eliminar_usuario_sistema(user_id: int, db: Session = Depends(get_db), current_user: UsuarioSistema = Depends(get_current_user)):
    _require_admin(current_user)
    user = db.query(UsuarioSistema).filter(UsuarioSistema.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(400, "No puedes eliminar tu propio usuario")
    db.delete(user)
    db.commit()
    return {"ok": True}
