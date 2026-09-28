#!/usr/bin/env python3
"""Script para crear el primer usuario administrador del sistema."""
import sys
import os

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

def create_admin():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing = db.query(UsuarioSistema).filter(UsuarioSistema.username == "admin").first()
        if existing:
            print("Ya existe un usuario 'admin'. Usuari existent.")
            return

        admin = UsuarioSistema(
            username="admin",
            password_hash=hash_password("admin123"),
            nombre="Administrador",
            email="admin@kriterio.local",
            rol="admin",
            activo=True,
        )
        db.add(admin)
        db.commit()
        print("Usuario 'admin' creat correctament.")
        print("  Usuario: admin")
        print("  Contraseña: admin123")
        print("  IMPORTANT: Canvia la contrasenya després del primer inici de sessió.")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
