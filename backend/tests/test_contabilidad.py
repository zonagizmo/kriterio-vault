"""Tests del servicio de contabilidad (clasificación balance, build asiento, CRUD cuentas)."""
import datetime
import pytest
from unittest.mock import MagicMock, patch
from app.services.contabilidad import (
    _clasificar_balance,
    _build_asiento,
    get_cuenta,
    delete_cuenta,
)
from app.models.contabilidad import Cuenta, Diario


# ─── _clasificar_balance (pure function) ────────────────────────────────────

class TestClasificarBalance:
    def test_cuenta_none(self):
        assert _clasificar_balance(None, 100) is None

    def test_cuenta_vacia(self):
        assert _clasificar_balance("", 100) is None

    def test_grupo_2_anc(self):
        assert _clasificar_balance("2000000", 100) == "ANC"
        assert _clasificar_balance("2900000", -50) == "ANC"

    def test_grupo_3_ac(self):
        assert _clasificar_balance("3000000", 100) == "AC"

    def test_grupo_1_pn(self):
        for p2 in ("10", "11", "12", "13"):
            assert _clasificar_balance(f"{p2}00000", 100) == "PN"

    def test_grupo_1_pnc(self):
        assert _clasificar_balance("1400000", 100) == "PNC"
        assert _clasificar_balance("1900000", -50) == "PNC"

    def test_grupo_4_acordeon_deudor(self):
        assert _clasificar_balance("4000000", 100) == "AC"

    def test_grupo_4_acordeon_acreedor(self):
        assert _clasificar_balance("4000000", -100) == "PC"

    def test_grupo_4_cero_es_ac(self):
        assert _clasificar_balance("4000000", 0) == "AC"

    def test_grupo_5_acordeon_deudor(self):
        assert _clasificar_balance("5000000", 50) == "AC"

    def test_grupo_5_acordeon_acreedor(self):
        assert _clasificar_balance("5000000", -50) == "PC"

    def test_grupo_6_none(self):
        assert _clasificar_balance("6000000", 100) is None

    def test_grupo_7_none(self):
        assert _clasificar_balance("7000000", 100) is None

    def test_grupo_8_none(self):
        assert _clasificar_balance("8000000", 100) is None

    def test_grupo_9_none(self):
        assert _clasificar_balance("9000000", 100) is None


# ─── _build_asiento (pure function) ────────────────────────────────────────

class TestBuildAsiento:
    def test_empty_lines(self):
        assert _build_asiento([]) is None

    def test_single_line_debe(self):
        line = MagicMock(
            asiento=1, empresa_id=1, fecha=datetime.date(2026, 1, 1),
            tpasiento="N", clave=None, tipo=None, numero=None,
            importe=100.0,
        )
        result = _build_asiento([line])
        assert result["total_debe"] == 100.0
        assert result["total_haber"] == 0.0
        assert result["cuadrado"] is False  # unbalanced: no haber

    def test_single_line_haber(self):
        line = MagicMock(
            asiento=1, empresa_id=1, fecha=datetime.date(2026, 1, 1),
            tpasiento="N", clave=None, tipo=None, numero=None,
            importe=-100.0,
        )
        result = _build_asiento([line])
        assert result["total_debe"] == 0.0
        assert result["total_haber"] == 100.0
        assert result["cuadrado"] is False  # unbalanced: no debe

    def test_balanced_asiento(self):
        l1 = MagicMock(asiento=1, empresa_id=1, fecha=datetime.date(2026, 1, 1),
                       tpasiento="N", clave=None, tipo=None, numero=None,
                       importe=200.0)
        l2 = MagicMock(asiento=1, empresa_id=1, fecha=datetime.date(2026, 1, 1),
                       tpasiento="N", clave=None, tipo=None, numero=None,
                       importe=-200.0)
        result = _build_asiento([l1, l2])
        assert result["total_debe"] == 200.0
        assert result["total_haber"] == 200.0
        assert result["cuadrado"] is True

    def test_unbalanced_asiento(self):
        l1 = MagicMock(asiento=1, empresa_id=1, fecha=datetime.date(2026, 1, 1),
                       tpasiento="N", clave=None, tipo=None, numero=None,
                       importe=200.0)
        l2 = MagicMock(asiento=1, empresa_id=1, fecha=datetime.date(2026, 1, 1),
                       tpasiento="N", clave=None, tipo=None, numero=None,
                       importe=-100.0)
        result = _build_asiento([l1, l2])
        assert result["total_debe"] == 200.0
        assert result["total_haber"] == 100.0
        assert result["cuadrado"] is False

    def test_none_importe_treated_as_zero(self):
        line = MagicMock(
            asiento=1, empresa_id=1, fecha=datetime.date(2026, 1, 1),
            tpasiento="N", clave=None, tipo=None, numero=None,
            importe=None,
        )
        result = _build_asiento([line])
        assert result["total_debe"] == 0.0
        assert result["total_haber"] == 0.0
        assert result["cuadrado"] is True

    def test_metadata_fields_copied(self):
        line = MagicMock(
            asiento=5, empresa_id=2, fecha=datetime.date(2026, 6, 15),
            tpasiento="A", clave="K", tipo="F", numero=42,
            importe=50.0,
        )
        result = _build_asiento([line])
        assert result["asiento"] == 5
        assert result["empresa_id"] == 2
        assert result["fecha"] == datetime.date(2026, 6, 15)
        assert result["tpasiento"] == "A"
        assert result["clave"] == "K"
        assert result["tipo"] == "F"
        assert result["numero"] == 42


# ─── get_cuenta / delete_cuenta (DB) ───────────────────────────────────────

class TestGetCuenta:
    def test_existe(self, db_session):
        c = Cuenta(empresa_id=1, cuenta="6000000", texto="Compras")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        result = get_cuenta(db_session, c.id)
        assert result is not None
        assert result.cuenta == "6000000"

    def test_no_existe(self, db_session):
        result = get_cuenta(db_session, 99999)
        assert result is None


class TestDeleteCuenta:
    @patch("app.services.contabilidad.registrar_operacion")
    def test_eliminar_sin_apuntes(self, mock_sync, db_session):
        c = Cuenta(empresa_id=1, cuenta="6000000", texto="Compras")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        result = delete_cuenta(db_session, c.id)
        assert result is True
        assert get_cuenta(db_session, c.id) is None

    def test_no_existe(self, db_session):
        result = delete_cuenta(db_session, 99999)
        assert result is False

    @patch("app.services.contabilidad.registrar_operacion")
    def test_no_eliminar_con_apuntes(self, mock_sync, db_session):
        c = Cuenta(empresa_id=1, cuenta="6000000", texto="Compras")
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        d = Diario(empresa_id=1, asiento=1, fecha=datetime.date(2026, 1, 1),
                   cuenta="6000000", importe=100.0)
        db_session.add(d)
        db_session.commit()
        with pytest.raises(ValueError, match="tiene 1 apuntes"):
            delete_cuenta(db_session, c.id)


def h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─── Regresión v1.13.08: PyG con saldo inicial de bancos ─────────────────────
# func.sum() sobre la columna Numeric devuelve Decimal y ti/tg son float:
# get_pyg hacía float + Decimal → TypeError → 500 en la pestaña P&G de las
# empresas con asientos de apertura en cuentas 57xxxx (saldo inicial > 0).

class TestPyGConSaldoInicial:
    def test_pyg_y_export_200_con_apertura(self, client, admin_token, db_session):
        db_session.add(Diario(empresa_id=1, asiento=1, fecha=datetime.date(2025, 12, 31),
                              cuenta="5720000", tpasiento="A", importe=1000))
        db_session.add(Diario(empresa_id=1, asiento=2, fecha=datetime.date(2026, 1, 15),
                              cuenta="6000000", importe=250))
        db_session.commit()

        r = client.get("/api/contabilidad/pyg", params={"empresa_id": 1}, headers=h(admin_token))
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["saldo_inicial_bancos"] == 1000
        assert j["resultado_con_saldo_inicial"] == j["resultado"] + 1000

        r2 = client.get("/api/contabilidad/export/pyg", params={"empresa_id": 1}, headers=h(admin_token))
        assert r2.status_code == 200, r2.text
