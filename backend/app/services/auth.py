import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.usuarios import UsuarioSistema

def _cargar_secret_key() -> str:
    """Clave JWT desde JWT_SECRET_KEY (única variable).

    No existe secreto por defecto: si la variable no está definida se genera
    una clave aleatoria efímera para ese proceso (los tokens no sobreviven a
    un reinicio) y se avisa con claridad. En producción JWT_SECRET_KEY es
    obligatoria: deploy/aprovisionar_servidor.sh la genera con openssl.
    """
    key = os.getenv("JWT_SECRET_KEY", "").strip()
    if key:
        return key
    import secrets as _secrets
    import warnings as _warnings
    _warnings.warn(
        "JWT_SECRET_KEY no está definida: se genera una clave efímera. "
        "Los tokens caducarán al reiniciar el servidor. Define JWT_SECRET_KEY "
        "en .env (ver .env.example).",
        RuntimeWarning,
        stacklevel=2,
    )
    return _secrets.token_hex(32)


SECRET_KEY = _cargar_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 horas por defecto

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> UsuarioSistema:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )
    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    user = db.query(UsuarioSistema).filter(UsuarioSistema.id == user_id).first()
    if user is None or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[UsuarioSistema]:
    """Version opcional - no lanza error si no hay token."""
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None
