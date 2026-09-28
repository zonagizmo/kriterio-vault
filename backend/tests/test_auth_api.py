"""Tests de la API de auth (login, me, cambiar-password, CRUD usuarios)."""
import pytest


# ─── Login ───────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_ok(self, client, admin_user):
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["usuario"]["username"] == "admin"
        assert data["usuario"]["rol"] == "admin"

    def test_login_password_incorrecta(self, client, admin_user):
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrongpass",
        })
        assert r.status_code == 401
        assert "incorrectos" in r.json()["detail"]

    def test_login_usuario_inexistente(self, client, admin_user):
        r = client.post("/api/auth/login", json={
            "username": "noexiste",
            "password": "abc",
        })
        assert r.status_code == 401

    def test_login_usuario_inactivo(self, client, db_session):
        from app.models.usuarios import UsuarioSistema
        from app.services.auth import hash_password
        user = UsuarioSistema(
            username="inactive", password_hash=hash_password("pw"),
            nombre="Inactivo", rol="operador", activo=False,
        )
        db_session.add(user)
        db_session.commit()
        r = client.post("/api/auth/login", json={
            "username": "inactive",
            "password": "pw",
        })
        # §16: usuario desactivado = 401 Unauthorized (nunca un 403 que
        # delataría que el usuario existe pero no tiene permisos)
        assert r.status_code == 401
        assert "desactivado" in r.json()["detail"]

    def test_login_operador(self, client, operador_user):
        r = client.post("/api/auth/login", json={
            "username": "operador",
            "password": "op123",
        })
        assert r.status_code == 200
        assert r.json()["usuario"]["rol"] == "operador"


# ─── GET /me ─────────────────────────────────────────────────────────────────

class TestMe:
    def test_me_ok(self, client, admin_token):
        r = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {admin_token}",
        })
        assert r.status_code == 200
        assert r.json()["username"] == "admin"
        assert r.json()["rol"] == "admin"

    def test_me_sin_token(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401  # get_current_user raises 401 when no token

    def test_me_token_invalido(self, client):
        r = client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalido",
        })
        assert r.status_code == 401


# ─── Cambiar password ────────────────────────────────────────────────────────

class TestCambiarPassword:
    def test_cambiar_password_ok(self, client, admin_token):
        r = client.post("/api/auth/cambiar-password", json={
            "password_actual": "admin123",
            "password_nuevo": "nueva456",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_cambiar_password_actual_mal(self, client, admin_token):
        r = client.post("/api/auth/cambiar-password", json={
            "password_actual": "mala",
            "password_nuevo": "nueva456",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 400


# ─── CRUD Usuarios (admin only) ─────────────────────────────────────────────

class TestUsuariosCRUD:
    def test_listar_usuarios(self, client, admin_token, admin_user):
        r = client.get("/api/auth/usuarios", headers={
            "Authorization": f"Bearer {admin_token}",
        })
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_listar_usuarios_no_admin(self, client, operador_token):
        r = client.get("/api/auth/usuarios", headers={
            "Authorization": f"Bearer {operador_token}",
        })
        assert r.status_code == 403

    def test_crear_usuario(self, client, admin_token):
        r = client.post("/api/auth/usuarios", json={
            "username": "nuevo",
            "password": "pass123",
            "nombre": "Nuevo Usuario",
            "rol": "operador",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 201
        assert r.json()["username"] == "nuevo"
        assert r.json()["rol"] == "operador"

    def test_crear_usuario_duplicado(self, client, admin_token, admin_user):
        r = client.post("/api/auth/usuarios", json={
            "username": "admin",
            "password": "pass123",
            "nombre": "Duplicado",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 400

    def test_crear_usuario_rol_invalido(self, client, admin_token):
        r = client.post("/api/auth/usuarios", json={
            "username": "test",
            "password": "pass123",
            "nombre": "Test",
            "rol": "rol_invalido",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 400

    def test_actualizar_usuario(self, client, admin_token, admin_user):
        r = client.put(f"/api/auth/usuarios/{admin_user.id}", json={
            "nombre": "Admin Actualizado",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_reset_password(self, client, admin_token, admin_user):
        r = client.post(f"/api/auth/usuarios/{admin_user.id}/reset-password", json={
            "password_nuevo": "nueva_pass",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_eliminar_usuario(self, client, admin_token, operador_user):
        r = client.delete(f"/api/auth/usuarios/{operador_user.id}", headers={
            "Authorization": f"Bearer {admin_token}",
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_no_autoeliminar(self, client, admin_token, admin_user):
        r = client.delete(f"/api/auth/usuarios/{admin_user.id}", headers={
            "Authorization": f"Bearer {admin_token}",
        })
        assert r.status_code == 400

    def test_no_desactivar_self(self, client, admin_token, admin_user):
        r = client.put(f"/api/auth/usuarios/{admin_user.id}", json={
            "activo": False,
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 400
