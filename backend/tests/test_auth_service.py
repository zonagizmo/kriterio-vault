"""Tests del servicio de auth (hash, token, verify)."""
import pytest
from app.services.auth import (
    hash_password, verify_password,
    create_access_token, decode_token,
    SECRET_KEY, ALGORITHM,
)
from jose import jwt
import datetime


# ─── hash_password / verify_password ─────────────────────────────────────────

class TestHashVerify:
    def test_hash_genera_bcrypt(self):
        h = hash_password("test123")
        assert h.startswith("$2b$")

    def test_hash_cambia_cada_vez(self):
        h1 = hash_password("test123")
        h2 = hash_password("test123")
        assert h1 != h2  # salts diferentes

    def test_verify_correcto(self):
        h = hash_password("mypass")
        assert verify_password("mypass", h) is True

    def test_verify_incorrecto(self):
        h = hash_password("mypass")
        assert verify_password("wrongpass", h) is False

    def test_verify_password_vacia(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("a", h) is False

    def test_verify_password_largo(self):
        pw = "a" * 1000
        h = hash_password(pw)
        assert verify_password(pw, h) is True


# ─── create_access_token / decode_token ──────────────────────────────────────

class TestTokens:
    def test_create_y_decode_token(self):
        token = create_access_token({"sub": 1, "rol": "admin"})
        payload = decode_token(token)
        assert payload["sub"] == "1"  # se convierte a string
        assert payload["rol"] == "admin"
        assert "exp" in payload

    def test_token_expiry_corta(self):
        token = create_access_token(
            {"sub": 1},
            expires_delta=datetime.timedelta(seconds=-1),
        )
        with pytest.raises(Exception):
            decode_token(token)

    def test_token_invalido(self):
        with pytest.raises(Exception):
            decode_token("token_falso")

    def test_token_firmado_con_clave_correcta(self):
        token = create_access_token({"sub": 42})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "42"

    def test_token_sub_como_int(self):
        token = create_access_token({"sub": 99})
        payload = decode_token(token)
        assert payload["sub"] == "99"
        # get_current_user hace int(sub)
        assert int(payload["sub"]) == 99
