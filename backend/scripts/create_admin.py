#!/usr/bin/env python3
"""Script para crear el primer usuario administrador del sistema.

La contraseña NUNCA está embebida en el código: se toma de la variable de
entorno ADMIN_PASSWORD (uso no interactivo/automatizado) o se pide por
teclado con getpass (no aparece en pantalla ni en el historial).

Uso:
    python scripts/create_admin.py                        # admin / pide contraseña
    ADMIN_PASSWORD='...' python scripts/create_admin.py    # no interactivo
    python scripts/create_admin.py --username ana --rol operador --empresa-id 1
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal, engine
from app.models.base import Base

# Importar todos los modelos para que SQLAlchemy los registre
import app.models.empresas
import app.models.usuarios
import app.models.clientes_proveedores
import app.models.facturacion
import app.models.bancos
import app.models.contabilidad
import app.models.configuracion
import app.models.sync

from app.models.usuarios import UsuarioSistema
from app.services.auth import hash_password
from app.services.permissions import ROLES_VALIDOS


def _pedir_password() -> str:
    """Contraseña desde ADMIN_PASSWORD o por teclado. Sin valor por defecto."""
    password = os.getenv("ADMIN_PASSWORD", "")
    if password:
        if len(password) < 8:
            print("ERROR: ADMIN_PASSWORD debe tener al menos 8 caracteres.")
            sys.exit(1)
        return password

    if not sys.stdin.isatty():
        print(
            "ERROR: modo no interactivo sin ADMIN_PASSWORD.\n"
            "  ADMIN_PASSWORD='...' python scripts/create_admin.py"
        )
        sys.exit(1)

    pw1 = getpass.getpass("Contraseña para el nuevo usuario (mín. 8, obligatoria): ")
    pw2 = getpass.getpass("Repite la contraseña: ")
    if len(pw1) < 8:
        print("ERROR: la contraseña debe tener al menos 8 caracteres.")
        sys.exit(1)
    if pw1 != pw2:
        print("ERROR: las contraseñas no coinciden.")
        sys.exit(1)
    return pw1


def create_admin(username: str, rol: str, empresa_id):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing = db.query(UsuarioSistema).filter(UsuarioSistema.username == username).first()
        if existing:
            print(f"Ya existe un usuario '{username}'. Usuari existent.")
            return

        password = _pedir_password()

        user = UsuarioSistema(
            username=username,
            password_hash=hash_password(password),
            nombre="Administrador" if rol == "admin" else username,
            email=f"{username}@local",
            rol=rol,
            activo=True,
            empresa_id=empresa_id,
        )
        db.add(user)
        db.commit()
        print(f"Usuari '{username}' creat correctament (rol: {rol}).")
        print("  IMPORTANT: Canvia la contrasenya després del primer inici de sessió.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crea un usuario del sistema")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--rol", default="admin", choices=ROLES_VALIDOS)
    parser.add_argument("--empresa-id", type=int, default=None,
                        help="Restringe el usuario a una empresa (sin argumento: todas)")
    args = parser.parse_args()
    create_admin(args.username, args.rol, args.empresa_id)
