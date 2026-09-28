"""Tests del servicio de facturas (total_previsto, renumerar, get_factura)."""
import datetime
import pytest
from unittest.mock import MagicMock
from app.services.facturas import (
    _total_previsto,
    _renumerar,
    get_factura_emi,
)
from app.services.documentos import calcular_importe_linea
from app.models.facturacion import FacturaEmitida, Apunte


# ─── _total_previsto (pure function) ───────────────────────────────────────

class TestTotalPrevisto:
    def test_vacio(self):
        assert _total_previsto([]) == 0.0

    def test_una_linea(self):
        line = MagicMock(cantidad=2, precio=50, dcto1=0, dcto2=0, dcto3=0)
        assert _total_previsto([line]) == 100.0

    def test_varias_lineas(self):
        l1 = MagicMock(cantidad=1, precio=100, dcto1=10, dcto2=0, dcto3=0)
        l2 = MagicMock(cantidad=3, precio=20, dcto1=0, dcto2=5, dcto3=0)
        # l1: 1*100*0.9 = 90, l2: 3*20*0.95 = 57
        assert _total_previsto([l1, l2]) == 147.0

    def test_none_fields(self):
        line = MagicMock(cantidad=None, precio=None, dcto1=None, dcto2=None, dcto3=None)
        # cantidad=1 default, precio=0, no descuentos -> 0
        assert _total_previsto([line]) == 0.0


# ─── _renumerar (DB) ───────────────────────────────────────────────────────

class TestRenumerar:
    def test_renumerar_todas(self, db_session):
        f1 = FacturaEmitida(empresa_id=1, numero=1, fecha=datetime.date(2026, 1, 10))
        f2 = FacturaEmitida(empresa_id=1, numero=2, fecha=datetime.date(2026, 1, 5))
        f3 = FacturaEmitida(empresa_id=1, numero=3, fecha=datetime.date(2026, 2, 1))
        db_session.add_all([f1, f2, f3])
        db_session.commit()

        from app.services.facturas import _renumerar
        count = _renumerar(db_session, FacturaEmitida, empresa_id=1)
        assert count == 3

        db_session.expire_all()
        all_f = db_session.query(FacturaEmitida).order_by(FacturaEmitida.id).all()
        # Ordered by fecha asc, id asc: f2 (Jan 5) -> 1, f1 (Jan 10) -> 2, f3 (Feb 1) -> 3
        by_id = {f.id: f.cnumero for f in all_f}
        # f2 has lower fecha so it's cnumero=1 regardless of id
        for f in all_f:
            if f.fecha == datetime.date(2026, 1, 5):
                assert f.cnumero == 1
            elif f.fecha == datetime.date(2026, 1, 10):
                assert f.cnumero == 2
            elif f.fecha == datetime.date(2026, 2, 1):
                assert f.cnumero == 3

    def test_renumerar_desde_id(self, db_session):
        f1 = FacturaEmitida(empresa_id=1, numero=1, fecha=datetime.date(2026, 1, 1))
        f2 = FacturaEmitida(empresa_id=1, numero=2, fecha=datetime.date(2026, 2, 1))
        f3 = FacturaEmitida(empresa_id=1, numero=3, fecha=datetime.date(2026, 3, 1))
        db_session.add_all([f1, f2, f3])
        db_session.commit()

        db_session.refresh(f2)
        from app.services.facturas import _renumerar
        count = _renumerar(db_session, FacturaEmitida, empresa_id=1, desde_id=f2.id)
        assert count == 2  # f2 + f3 renumbered

        db_session.expire_all()
        all_f = db_session.query(FacturaEmitida).order_by(FacturaEmitida.fecha).all()
        by_fecha = {f.fecha: f.cnumero for f in all_f}
        # f2 (Feb) starts at 1, f3 (Mar) gets 2
        # start=1 (f1 before idx), so f2 gets cnumero=2, f3 gets cnumero=3
        assert by_fecha[datetime.date(2026, 2, 1)] == 2
        assert by_fecha[datetime.date(2026, 3, 1)] == 3

    def test_renumerar_empresas_independientes(self, db_session):
        f1 = FacturaEmitida(empresa_id=1, numero=1, fecha=datetime.date(2026, 1, 1))
        f2 = FacturaEmitida(empresa_id=2, numero=1, fecha=datetime.date(2026, 1, 1))
        db_session.add_all([f1, f2])
        db_session.commit()

        from app.services.facturas import _renumerar
        _renumerar(db_session, FacturaEmitida, empresa_id=1)

        db_session.expire_all()
        f2_r = db_session.get(FacturaEmitida, f2.id)
        assert f2_r.cnumero is None  # untouched (empresa_id=2)

    def test_renumerar_id_inexistente(self, db_session):
        from app.services.facturas import _renumerar
        count = _renumerar(db_session, FacturaEmitida, empresa_id=1, desde_id=99999)
        assert count == 0


# ─── get_factura_emi (DB) ──────────────────────────────────────────────────

class TestGetFacturaEmi:
    def test_existe(self, db_session):
        f = FacturaEmitida(empresa_id=1, numero=1, fecha=datetime.date(2026, 1, 1))
        db_session.add(f)
        db_session.commit()
        db_session.refresh(f)
        result = get_factura_emi(db_session, f.id)
        assert result is not None
        assert result.numero == 1

    def test_no_existe(self, db_session):
        result = get_factura_emi(db_session, 99999)
        assert result is None
