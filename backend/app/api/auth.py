from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.usuarios_sistema import UsuarioSistema
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest, UserRead, ChangePasswordRequest,
)
from app.services.auth import (
    verify_password, hash_password, create_access_token, create_refresh_token,
    decode_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UsuarioSistema).filter(
        UsuarioSistema.username == body.username,
        UsuarioSistema.activo == True,
    ).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )
    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserRead.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido",
        )
    user_id = payload.get("sub")
    user = db.query(UsuarioSistema).filter(
        UsuarioSistema.id == int(user_id),
        UsuarioSistema.activo == True,
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )
    access = create_access_token({"sub": str(user.id)})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def me(user: UsuarioSistema = Depends(get_current_user)):
    return UserRead.model_validate(user)


@router.put("/cambiar-password")
def cambiar_password(
    body: ChangePasswordRequest,
    user: UsuarioSistema = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.password_actual, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta",
        )
    if len(body.password_nuevo) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe tener al menos 4 caracteres",
        )
    user.hashed_password = hash_password(body.password_nuevo)
    db.commit()
    return {"ok": True, "mensaje": "Contraseña actualizada correctamente"}
