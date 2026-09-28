"""Política centralizada de autorización (RBAC) de Kriterio Vault.

Cadena de decisión:

    Autenticación (JWT) → Rol → Permisos → Empresa → Recurso

El backend es la única fuente de verdad: el frontend únicamente refleja esta
política ocultando controles, pero la validación real ocurre aquí.

- 401: no autenticado (token ausente, inválido, expirado o usuario inactivo).
- 403: autenticado pero sin permiso suficiente.
- 404: el recurso no existe o pertenece a otra empresa (para no revelar su
  existencia).
"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from app.models.usuarios import UsuarioSistema
from app.services.auth import get_current_user

# ── Catálogo de permisos ────────────────────────────────────────────────────

PERMISOS = (
    "read",
    "create",
    "update",
    "delete",
    "write",  # alias lógico: create o update
    "admin",
    "backup",
    "restore",
    "user_management",
    "configuration",
    "sync",
)

# ── Matriz Rol × Permiso (única fuente de verdad) ───────────────────────────

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "read",
        "create",
        "update",
        "delete",
        "admin",
        "backup",
        "restore",
        "user_management",
        "configuration",
        "sync",
    },
    "operador": {
        "read",
        "create",
        "update",
        "delete",
    },
    "solo_lectura": {
        "read",
    },
}

ROLES_VALIDOS = tuple(ROLE_PERMISSIONS.keys())

# Decisión documentada (SECURITY.md §DELETE): el operador conserva el borrado
# de registros operativos tal y como funcionaba hasta ahora; el borrado de
# zonas administrativas (backups, usuarios, empresas) requiere admin.


def permisos_de_rol(rol: Optional[str]) -> set[str]:
    """Devuelve los permisos de un rol. Rol desconocido → sin permisos (fail-safe)."""
    return set(ROLE_PERMISSIONS.get(rol or "", set()))


def tiene_permiso(user: UsuarioSistema, perm: str) -> bool:
    perms = permisos_de_rol(getattr(user, "rol", None))
    if perm == "write":
        return "create" in perms or "update" in perms
    if perm == "admin":
        return "admin" in perms
    return perm in perms


def requiere_permiso(user: UsuarioSistema, perm: str) -> None:
    """Lanza 403 si el usuario no tiene `perm`. Nunca filtra qué permisos existen."""
    if not tiene_permiso(user, perm):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes para esta operación",
        )


def require_permiso(perm: str):
    """Dependencia FastAPI: `user=Depends(require_permiso("delete"))`."""

    def _dependency(user: UsuarioSistema = Depends(get_current_user)) -> UsuarioSistema:
        requiere_permiso(user, perm)
        return user

    return _dependency


# Dependencias reutilizables (§6 del enunciado)
require_read = require_permiso("read")
require_create = require_permiso("create")
require_update = require_permiso("update")
require_delete = require_permiso("delete")
require_write = require_permiso("write")
require_admin = require_permiso("admin")
require_backup = require_permiso("backup")
require_restore = require_permiso("restore")
require_user_management = require_permiso("user_management")
require_configuration = require_permiso("configuration")
require_sync = require_permiso("sync")
require_authenticated = get_current_user  # solo exige sesión válida (401)

# ── Autorización derivada del método HTTP (política por defecto) ────────────

METHOD_PERMISSION = {
    "GET": "read",
    "HEAD": "read",
    "OPTIONS": "read",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}


def require_method_permission(
    request: Request,
    user: UsuarioSistema = Depends(get_current_user),
) -> UsuarioSistema:
    """Política por defecto de los routers CRUD: el permiso sale del método.

    GET/HEAD/OPTIONS → read · POST → create · PUT/PATCH → update · DELETE → delete.
    Los endpoints administrativos sobrescriben esto con require_* explícitos.
    """
    perm = METHOD_PERMISSION.get(request.method, "read")
    requiere_permiso(user, perm)
    return user


# ── Aislamiento por empresa ─────────────────────────────────────────────────
# El rol NO sustituye al aislamiento por empresa: usuario + empresa + permiso.

def puede_ver_empresa(user: UsuarioSistema, empresa_id: Optional[int]) -> bool:
    """None en el usuario = acceso a todas las empresas (compatibilidad)."""
    if getattr(user, "empresa_id", None) is None:
        return True
    return empresa_id is not None and int(empresa_id) == int(user.empresa_id)


def empresa_query(empresa_id: int, user: UsuarioSistema = Depends(get_current_user)) -> int:
    """Dependencia para endpoints con query param `empresa_id`: 404 si no le pertenece."""
    if not puede_ver_empresa(user, empresa_id):
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return empresa_id


def exigir_empresa(user: UsuarioSistema, obj, campo: str = "empresa_id") -> None:
    """Comprueba el aislamiento de un recurso ya cargado; 404 si es de otra empresa.

    `campo` indica el atributo que lleva el identificador de empresa
    (por defecto empresa_id; para el modelo Empresa, id).
    """
    if obj is None:
        return
    if not puede_ver_empresa(user, getattr(obj, campo, None)):
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
