"""Tests del servicio de bancos (numeracion vencimientos, pagos)."""
import datetime
import pytest
from app.services.bancos import (
    siguiente_numero_vencimiento,
    _aplicar_pago_pendiente,
    _restaurar_pendiente,
)
from app.models.bancos import Banco, MovBanco, Pago
from app.models.clientes_proveedores import Vencimiento


# ─── siguiente_numero_vencimiento ────────────────────────────────────────────

class TestSiguienteVencimiento:
    def test_primero(self, db_session):
        num = siguiente_numero_vencimiento(db_session, empresa_id=1)
        assert num == 1

    def test_despues_de_existente(self, db_session):
        v = Vencimiento(empresa_id=1, numero=5, fecha=datetime.date(2026, 1, 1),
                        tipo="F", tpnumero=1, importe=100, pendiente=100)
        db_session.add(v)
        db_session.commit()
        num = siguiente_numero_vencimiento(db_session, empresa_id=1)
        assert num == 6

    def test_considera_pagos_huerfanos(self, db_session):
        """Si hay pagos referenciando vencimientos borrados, usa el max de pagos."""
        p = Pago(empresa_id=1, vto=10, banco=1, numero=1, importe=50)
        db_session.add(p)
        db_session.commit()
        num = siguiente_numero_vencimiento(db_session, empresa_id=1)
        assert num == 11  # max(0, 10) + 1

    def test_empresas_independientes(self, db_session):
        v1 = Vencimiento(empresa_id=1, numero=3, fecha=datetime.date(2026, 1, 1),
                         tipo="F", tpnumero=1, importe=100, pendiente=100)
        v2 = Vencimiento(empresa_id=2, numero=7, fecha=datetime.date(2026, 1, 1),
                         tipo="F", tpnumero=1, importe=100, pendiente=100)
        db_session.add_all([v1, v2])
        db_session.commit()
        assert siguiente_numero_vencimiento(db_session, empresa_id=1) == 4
        assert siguiente_numero_vencimiento(db_session, empresa_id=2) == 8


# ─── _aplicar_pago_pendiente ────────────────────────────────────────────────

class TestAplicarPago:
    def test_pago_total(self):
        class FakeVto:
            pendiente = 100.0
            importe = 100.0
        vto = FakeVto()
        _aplicar_pago_pendiente(vto, 100)
        assert vto.pendiente == 0.0

    def test_pago_parcial(self):
        class FakeVto:
            pendiente = 100.0
            importe = 100.0
        vto = FakeVto()
        _aplicar_pago_pendiente(vto, 30)
        assert vto.pendiente == 70.0

    def test_pago_superior(self):
        class FakeVto:
            pendiente = 50.0
            importe = 100.0
        vto = FakeVto()
        _aplicar_pago_pendiente(vto, 200)
        assert vto.pendiente == 0.0  # no puede ser negativo

    def test_abono(self):
        class FakeVto:
            pendiente = -100.0
            importe = -100.0
        vto = FakeVto()
        _aplicar_pago_pendiente(vto, -50)
        assert vto.pendiente == -50.0


# ─── _restaurar_pendiente ───────────────────────────────────────────────────

class TestRestaurarPendiente:
    def test_restaurar_parcial(self):
        class FakeVto:
            pendiente = 70.0
            importe = 100.0
        vto = FakeVto()
        _restaurar_pendiente(vto, 30)
        assert vto.pendiente == 100.0

    def test_restaurar_no_supera_importe(self):
        class FakeVto:
            pendiente = 90.0
            importe = 100.0
        vto = FakeVto()
        _restaurar_pendiente(vto, 50)
        assert vto.pendiente == 100.0  # tope en importe
