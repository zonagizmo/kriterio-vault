"""
Fixtures compartidos para todos los tests.
BD en memoria que se crea/destruye por test.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base

from app.models import (  # noqa: F401 — ensure all tables registered
    empresas, usuarios, facturacion, contabilidad,
    clientes_proveedores, configuracion, bancos, sync,
)

from app.models.usuarios import UsuarioSistema
from app.services.auth import hash_password, create_access_token


@pytest.fixture(scope="function")
def db_session():
    """Crea una BD SQLite en memoria nueva por cada test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        import sqlite3
        if isinstance(dbapi_conn, sqlite3.Connection):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    from app.models.empresas import Empresa
    for eid in range(1, 5):
        session.add(Empresa(id=eid, codigo=f"EMP{eid}", nombre=f"Empresa {eid}"))
    session.commit()
    session.expire_all()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient con la BD en memoria."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.database import get_db

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(db_session):
    """Crea un usuario admin en la BD de test."""
    user = UsuarioSistema(
        username="admin",
        password_hash=hash_password("admin123"),
        nombre="Administrador Test",
        email="admin@test.local",
        rol="admin",
        activo=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def operador_user(db_session):
    """Crea un usuario operador en la BD de test."""
    user = UsuarioSistema(
        username="operador",
        password_hash=hash_password("op123"),
        nombre="Operador Test",
        email="op@test.local",
        rol="operador",
        activo=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def solo_lectura_user(db_session):
    """Crea un usuario solo_lectura en la BD de test."""
    user = UsuarioSistema(
        username="readonly",
        password_hash=hash_password("ro123"),
        nombre="Solo Lectura Test",
        email="ro@test.local",
        rol="solo_lectura",
        activo=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_token(admin_user):
    """Genera un JWT valido para el admin."""
    return create_access_token(data={"sub": admin_user.id, "rol": admin_user.rol})


@pytest.fixture(scope="function")
def operador_token(operador_user):
    """Genera un JWT valido para el operador."""
    return create_access_token(data={"sub": operador_user.id, "rol": operador_user.rol})


@pytest.fixture(scope="function")
def solo_lectura_token(solo_lectura_user):
    """Genera un JWT valido para el usuario de solo lectura."""
    return create_access_token(data={"sub": solo_lectura_user.id, "rol": solo_lectura_user.rol})


def bearer(token: str) -> dict:
    """Cabecera Authorization para las peticiones de test."""
    return {"Authorization": f"Bearer {token}"}
