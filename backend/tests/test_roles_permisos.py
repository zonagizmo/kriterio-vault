"""Autorización por roles (RBAC): 401, 403 por rol y aislamiento por empresa.

Demuestra que solo_lectura ≠ operador ≠ admin y que ningún permiso se puede
conseguir manipulando las peticiones HTTP directamente (TestClient = curl):
la decisión de autorización ocurre siempre en el backend.
"""
from datetime import timedelta

import pytest

from app.models.usuarios import UsuarioSistema
from app.services.auth import create_access_token, hash_password


def h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─── Autenticación: 401 ──────────────────────────────────────────────────────

class TestAutenticacion401:
    def test_sin_token(self, client):
        r = client.get("/api/clientes", params={"empresa_id": 1})
        assert r.status_code == 401

    def test_token_invalido(self, client):
        r = client.get("/api/clientes", params={"empresa_id": 1},
                       headers=h("esto-no-es-un-jwt"))
        assert r.status_code == 401

    def test_token_firmado_con_otra_clave(self, client):
        from jose import jwt as jose_jwt
        from app.services.auth import SECRET_KEY
        token = jose_jwt.encode({"sub": "1", "rol": "admin", "exp": 9999999999},
                                "clave-erronea", algorithm="HS256")
        r = client.get("/api/clientes", params={"empresa_id": 1}, headers=h(token))
        assert r.status_code == 401
        assert SECRET_KEY  # se usa la clave configurada, no una por defecto conocida

    def test_token_expirado(self, client, admin_user):
        token = create_access_token({"sub": admin_user.id, "rol": "admin"},
                                    expires_delta=timedelta(seconds=-10))
        r = client.get("/api/clientes", params={"empresa_id": 1}, headers=h(token))
        assert r.status_code == 401

    def test_usuario_desactivado(self, client, db_session):
        user = UsuarioSistema(
            username="baja", password_hash=hash_password("pw123456"),
            nombre="Baja", rol="admin", activo=False,
        )
        db_session.add(user)
        db_session.commit()
        token = create_access_token({"sub": user.id, "rol": "admin"})
        r = client.get("/api/clientes", params={"empresa_id": 1}, headers=h(token))
        assert r.status_code == 401

    def test_admin_cambiado_a_solo_lectura_pierde_permisos(self, client, db_session, admin_user):
        """Los permisos salen de la BD en cada petición, no del token."""
        admin_user.rol = "solo_lectura"
        db_session.commit()
        token = create_access_token({"sub": admin_user.id, "rol": "admin"})
        r = client.post("/api/clientes", json={"nombre": "X", "empresa_id": 1},
                        headers=h(token))
        assert r.status_code == 403  # el rol "admin" del JWT no sirve de nada


# ─── Solo lectura: GET sí, escrituras 403 ────────────────────────────────────

class TestSoloLectura:
    def test_get_ok(self, client, solo_lectura_token):
        r = client.get("/api/clientes", params={"empresa_id": 1}, headers=h(solo_lectura_token))
        assert r.status_code == 200

    @pytest.mark.parametrize("method,path,payload", [
        ("post", "/api/clientes", {"nombre": "Nuevo", "empresa_id": 1}),
        ("put", "/api/clientes/1", {"nombre": "Editado"}),
        ("delete", "/api/clientes/1", None),
        ("post", "/api/proveedores", {"nombre": "Prov", "empresa_id": 1}),
        ("post", "/api/facturas/emitidas/renumerar", {"empresa_id": 1, "desde_id": 1}),
        ("post", "/api/articulos", {"nombre": "Art", "empresa_id": 1}),
        ("delete", "/api/empresas/1", None),
    ])
    def test_escrituras_403(self, client, solo_lectura_token, method, path, payload):
        r = client.request(method, path, json=payload, headers=h(solo_lectura_token))
        assert r.status_code == 403, f"{method.upper()} {path} -> {r.status_code}"

    @pytest.mark.parametrize("method,path,payload", [
        ("get", "/api/ajustes/backups", None),
        ("post", "/api/ajustes/backup", None),
        ("post", "/api/ajustes/restaurar", None),
        ("post", "/api/ajustes/restaurar-backup/gestionmgd_x.db", None),
        ("put", "/api/ajustes/config", {"hora": "03:00", "dias": [1]}),
        ("delete", "/api/ajustes/backup/gestionmgd_x.db", None),
        ("get", "/api/auth/usuarios", None),
        ("post", "/api/auth/usuarios",
         {"username": "x", "password": "12345678", "nombre": "X"}),
        ("post", "/api/shutdown", None),
        ("post", "/api/sync/ejecutar", None),
        ("post", "/api/empresas", {"codigo": "Z1", "nombre": "Z"}),
    ])
    def test_admin_403(self, client, solo_lectura_token, method, path, payload):
        r = client.request(method, path, json=payload, headers=h(solo_lectura_token))
        assert r.status_code == 403, f"{method.upper()} {path} -> {r.status_code}"

    def test_no_puede_crear_usuario(self, client, solo_lectura_token):
        r = client.post("/api/auth/usuarios", json={
            "username": "hack", "password": "12345678", "nombre": "Hack",
            "rol": "admin",
        }, headers=h(solo_lectura_token))
        assert r.status_code == 403


# ─── Operador: CRUD operativo sí, administración 403 ─────────────────────────

class TestOperador:
    def test_get_ok(self, client, operador_token):
        r = client.get("/api/clientes", params={"empresa_id": 1}, headers=h(operador_token))
        assert r.status_code == 200

    def test_crud_completo(self, client, operador_token):
        r = client.post("/api/clientes", json={"nombre": "Op cliente", "empresa_id": 1},
                        headers=h(operador_token))
        assert r.status_code == 201
        cliente_id = r.json()["id"]

        r = client.put(f"/api/clientes/{cliente_id}", json={"nombre": "Op editado"},
                       headers=h(operador_token))
        assert r.status_code == 200

        r = client.delete(f"/api/clientes/{cliente_id}", headers=h(operador_token))
        assert r.status_code == 204

    @pytest.mark.parametrize("method,path,payload", [
        ("get", "/api/auth/usuarios", None),
        ("post", "/api/auth/usuarios",
         {"username": "nuevo", "password": "12345678", "nombre": "N", "rol": "admin"}),
        ("put", "/api/auth/usuarios/1", {"rol": "admin"}),
        ("post", "/api/auth/usuarios/1/reset-password", {"password_nuevo": "12345678"}),
        ("delete", "/api/auth/usuarios/1", None),
        ("post", "/api/ajustes/backup", None),
        ("post", "/api/ajustes/restaurar", None),
        ("put", "/api/ajustes/config", {"hora": "03:00", "dias": [1]}),
        ("post", "/api/shutdown", None),
        ("post", "/api/sync/ejecutar", None),
        ("post", "/api/empresas", {"codigo": "Z2", "nombre": "Z"}),
        ("delete", "/api/empresas/1", None),
    ])
    def test_admin_403(self, client, operador_token, method, path, payload):
        r = client.request(method, path, json=payload, headers=h(operador_token))
        assert r.status_code == 403, f"{method.upper()} {path} -> {r.status_code}"

    def test_no_puede_subirse_a_admin(self, client, operador_token, operador_user, db_session):
        r = client.put(f"/api/auth/usuarios/{operador_user.id}", json={"rol": "admin"},
                       headers=h(operador_token))
        assert r.status_code == 403
        db_session.refresh(operador_user)
        assert operador_user.rol == "operador"


# ─── Contabilidad: diagnóstico y cierre (decisión v1.13.01) ───────────────────
# El diagnóstico pasa de solo-admin a lectura (GET) y los botones de
# reparación/generación/cierre siguen exigiendo create: el operador puede
# diagnosticar, reparar y cerrar ejercicio; solo_lectura solo mira.

class TestContabilidadDiagnosticoYCierre:
    def test_operador_diagnostica(self, client, operador_token):
        r = client.get("/api/contabilidad/diagnostico",
                       params={"empresa_id": 1}, headers=h(operador_token))
        assert r.status_code == 200

    def test_solo_lectura_diagnostica(self, client, solo_lectura_token):
        """GET = read: también el rol de consulta puede ver el diagnóstico."""
        r = client.get("/api/contabilidad/diagnostico",
                       params={"empresa_id": 1}, headers=h(solo_lectura_token))
        assert r.status_code == 200

    def test_solo_lectura_no_repara(self, client, solo_lectura_token):
        r = client.post("/api/contabilidad/generar-pendientes",
                        params={"empresa_id": 1}, headers=h(solo_lectura_token))
        assert r.status_code == 403

    @pytest.mark.parametrize("path, params", [
        ("/api/contabilidad/generar-pendientes", {"empresa_id": 1}),
        ("/api/contabilidad/regenerar-asiento-banco",
         {"empresa_id": 1, "banco": 1, "numero": 999}),
        ("/api/contabilidad/cierre", {"empresa_id": 1, "anio": 2023}),
    ])
    def test_operador_puede_reparar_y_cerrar(self, client, operador_token, path, params):
        """create = operador: nunca 401/403 (el 400/404/200 depende de los datos)."""
        r = client.post(path, params=params, headers=h(operador_token))
        assert r.status_code not in (401, 403), f"{path} -> {r.status_code}"

    @pytest.mark.parametrize("path, params", [
        ("/api/contabilidad/generar-pendientes", {"empresa_id": 1}),
        ("/api/contabilidad/cierre", {"empresa_id": 1, "anio": 2023}),
    ])
    def test_solo_lectura_no_cierra(self, client, solo_lectura_token, path, params):
        r = client.post(path, params=params, headers=h(solo_lectura_token))
        assert r.status_code == 403, f"{path} -> {r.status_code}"


# ─── Admin: acceso completo ──────────────────────────────────────────────────

class TestAdmin:
    def test_crud_clientes(self, client, admin_token):
        r = client.post("/api/clientes", json={"nombre": "Adm cliente", "empresa_id": 1},
                        headers=h(admin_token))
        assert r.status_code == 201
        cliente_id = r.json()["id"]
        assert client.put(f"/api/clientes/{cliente_id}", json={"nombre": "Adm edit"},
                          headers=h(admin_token)).status_code == 200
        assert client.delete(f"/api/clientes/{cliente_id}",
                             headers=h(admin_token)).status_code == 204

    def test_gestion_usuarios(self, client, admin_token, db_session):
        r = client.get("/api/auth/usuarios", headers=h(admin_token))
        assert r.status_code == 200

        r = client.post("/api/auth/usuarios", json={
            "username": "creado", "password": "12345678", "nombre": "Creado",
            "rol": "solo_lectura",
        }, headers=h(admin_token))
        assert r.status_code == 201
        user_id = r.json()["id"]

        assert client.put(f"/api/auth/usuarios/{user_id}", json={"rol": "operador"},
                          headers=h(admin_token)).status_code == 200
        assert client.delete(f"/api/auth/usuarios/{user_id}",
                             headers=h(admin_token)).status_code == 200

    def test_rol_invalido_rechazado(self, client, admin_token):
        r = client.post("/api/auth/usuarios", json={
            "username": "malrol", "password": "12345678", "nombre": "M",
            "rol": "superuser",
        }, headers=h(admin_token))
        assert r.status_code == 400

    def test_listar_backups(self, client, admin_token):
        r = client.get("/api/ajustes/backups", headers=h(admin_token))
        assert r.status_code == 200

    def test_backup_manual(self, client, admin_token, tmp_path, monkeypatch):
        from app.api import ajustes
        import sqlite3
        db_falso = tmp_path / "test.db"
        sqlite3.connect(str(db_falso)).close()
        monkeypatch.setattr(ajustes, "DB_PATH", db_falso)
        monkeypatch.setattr(ajustes, "BACKUP_DIR", tmp_path / "backups")
        r = client.post("/api/ajustes/backup", headers=h(admin_token))
        assert r.status_code == 200

    def test_configuracion(self, client, admin_token, tmp_path, monkeypatch):
        from app.api import ajustes
        monkeypatch.setattr(ajustes, "CONFIG_PATH", tmp_path / "cfg.json")
        r = client.put("/api/ajustes/config", json={"hora": "03:30", "dias": [1, 2]},
                       headers=h(admin_token))
        assert r.status_code == 200

    def test_shutdown_admin(self, client, admin_token, monkeypatch):
        monkeypatch.setenv("KRITERIO_NO_SHUTDOWN", "1")
        r = client.post("/api/shutdown", headers=h(admin_token))
        assert r.status_code == 200

    def test_diagnostico(self, client, admin_token):
        r = client.get("/api/contabilidad/diagnostico", params={"empresa_id": 1},
                       headers=h(admin_token))
        assert r.status_code == 200

    def test_sync_no_403(self, client, admin_token):
        """El permiso sync es exclusivo de admin (la ejecución real depende
        de la configuración de sincronización del entorno)."""
        r = client.post("/api/sync/ejecutar", headers=h(admin_token))
        assert r.status_code != 403


# ─── Multiempresa: usuario + empresa + permiso ───────────────────────────────

@pytest.fixture
def usuario_empresa(db_session):
    """Fábrica de usuarios restringidos a una empresa concreta."""
    def _crear(username: str, empresa_id: int) -> UsuarioSistema:
        user = UsuarioSistema(
            username=username, password_hash=hash_password("pw123456"),
            nombre=username.title(), rol="operador", activo=True,
            empresa_id=empresa_id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _crear


@pytest.fixture
def cliente_a(client, admin_token):
    r = client.post("/api/clientes", json={"nombre": "Cliente A", "empresa_id": 1},
                    headers=h(admin_token))
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def cliente_b(client, admin_token):
    r = client.post("/api/clientes", json={"nombre": "Cliente B", "empresa_id": 2},
                    headers=h(admin_token))
    assert r.status_code == 201
    return r.json()


class TestMultiempresa:
    def test_get_por_id_ajeno_404(self, client, usuario_empresa, cliente_a, cliente_b):
        user_a = usuario_empresa("user_a", 1)
        user_b = usuario_empresa("user_b", 2)
        tok_a = create_access_token({"sub": user_a.id, "rol": "operador"})
        tok_b = create_access_token({"sub": user_b.id, "rol": "operador"})

        assert client.get(f"/api/clientes/{cliente_a['id']}",
                          headers=h(tok_a)).status_code == 200
        assert client.get(f"/api/clientes/{cliente_b['id']}",
                          headers=h(tok_a)).status_code == 404
        assert client.get(f"/api/clientes/{cliente_b['id']}",
                          headers=h(tok_b)).status_code == 200
        assert client.get(f"/api/clientes/{cliente_a['id']}",
                          headers=h(tok_b)).status_code == 404

    def test_update_y_delete_ajenos_404(self, client, usuario_empresa, cliente_a,
                                        cliente_b, admin_token):
        user_a = usuario_empresa("u_upd_a", 1)
        tok_a = create_access_token({"sub": user_a.id, "rol": "operador"})

        assert client.put(f"/api/clientes/{cliente_b['id']}",
                          json={"nombre": "Hackeado"}, headers=h(tok_a)).status_code == 404
        assert client.delete(f"/api/clientes/{cliente_b['id']}",
                             headers=h(tok_a)).status_code == 404
        # el registro sigue intacto: un admin lo ve con su nombre original
        admin_view = client.get(f"/api/clientes/{cliente_b['id']}",
                                headers=h(admin_token)).json()
        assert admin_view["nombre"] == "Cliente B"

    def test_lista_empresa_ajena_404(self, client, usuario_empresa):
        user_a = usuario_empresa("u_lista_a", 1)
        tok_a = create_access_token({"sub": user_a.id, "rol": "operador"})
        assert client.get("/api/clientes", params={"empresa_id": 1},
                          headers=h(tok_a)).status_code == 200
        assert client.get("/api/clientes", params={"empresa_id": 2},
                          headers=h(tok_a)).status_code == 404

    def test_crear_en_empresa_ajena_404(self, client, usuario_empresa):
        user_a = usuario_empresa("u_crea_a", 1)
        tok_a = create_access_token({"sub": user_a.id, "rol": "operador"})
        r = client.post("/api/clientes", json={"nombre": "Intruso", "empresa_id": 2},
                        headers=h(tok_a))
        assert r.status_code == 404

    def test_facturas_emitidas_aisladas(self, client, usuario_empresa, admin_token,
                                        cliente_a):
        r = client.post("/api/facturas/emitidas", json={
            "empresa_id": 1,
            "cliente": cliente_a["numero"],
            "fecha": "2026-01-15",
        }, headers=h(admin_token))
        assert r.status_code == 201, r.text
        factura = r.json()
        user_a = usuario_empresa("u_fac_a", 1)
        user_b = usuario_empresa("u_fac_b", 2)
        tok_a = create_access_token({"sub": user_a.id, "rol": "operador"})
        tok_b = create_access_token({"sub": user_b.id, "rol": "operador"})
        assert client.get(f"/api/facturas/emitidas/{factura['id']}",
                          headers=h(tok_a)).status_code == 200
        assert client.get(f"/api/facturas/emitidas/{factura['id']}",
                          headers=h(tok_b)).status_code == 404

    def test_empresas_aisladas(self, client, usuario_empresa):
        user_a = usuario_empresa("u_emp_a", 1)
        tok_a = create_access_token({"sub": user_a.id, "rol": "operador"})
        empresas = client.get("/api/empresas", headers=h(tok_a)).json()
        assert [e["id"] for e in empresas] == [1]
        assert client.get("/api/empresas/2", headers=h(tok_a)).status_code == 404
        assert client.get("/api/empresas/1", headers=h(tok_a)).status_code == 200

    def test_usuarios_sin_empresa_ven_todo(self, client, operador_token):
        """Compatibilidad: empresa_id NULL = todas las empresas."""
        empresas = client.get("/api/empresas", headers=h(operador_token)).json()
        assert len(empresas) >= 4
