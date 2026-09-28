"""Tests del servicio de documentos (numeracion, lineas, importes)."""
import datetime
import pytest
from decimal import Decimal
from app.services.documentos import (
    calcular_importe_linea,
    siguiente_numero,
    siguiente_cnumero,
    total_lineas,
)
from app.models.facturacion import FacturaEmitida, FacturaRecibida, Apunte


# ─── calcular_importe_linea ──────────────────────────────────────────────────

class TestCalcularImporteLinea:
    def test_simple(self):
        assert calcular_importe_linea(2, 10) == Decimal('20.00')

    def test_con_dcto1(self):
        # 10 * 100 = 1000, con 10% dcto = 900
        assert calcular_importe_linea(10, 100, dcto1=10) == Decimal('900.00')

    def test_con_dcto2(self):
        # 10 * 100 = 1000, con 10% dcto1 = 900, con 5% dcto2 = 855
        result = calcular_importe_linea(10, 100, dcto1=10, dcto2=5)
        assert result == Decimal('855.00')

    def test_con_tres_descuentos(self):
        # 1 * 100 = 100, 10% -> 90, 5% -> 85.5, 2% -> 83.79
        result = calcular_importe_linea(1, 100, dcto1=10, dcto2=5, dcto3=2)
        assert result == Decimal('83.79')

    def test_cantidad_zero(self):
        assert calcular_importe_linea(0, 100) == Decimal('0.00')

    def test_precio_zero(self):
        assert calcular_importe_linea(10, 0) == Decimal('0.00')

    def test_sin_descuentos(self):
        assert calcular_importe_linea(3, 25.50) == Decimal('76.50')


# ─── siguiente_numero ────────────────────────────────────────────────────────

class TestSiguienteNumero:
    def test_primera_factura(self, db_session):
        numero = siguiente_numero(db_session, FacturaEmitida, empresa_id=1)
        assert numero == 1

    def test_despues_de_existente(self, db_session):
        f = FacturaEmitida(empresa_id=1, numero=5, fecha=datetime.date(2026, 1, 1))
        db_session.add(f)
        db_session.commit()
        numero = siguiente_numero(db_session, FacturaEmitida, empresa_id=1)
        assert numero == 6

    def test_empresas_independientes(self, db_session):
        f1 = FacturaEmitida(empresa_id=1, numero=10, fecha=datetime.date(2026, 1, 1))
        f2 = FacturaEmitida(empresa_id=2, numero=3, fecha=datetime.date(2026, 1, 1))
        db_session.add_all([f1, f2])
        db_session.commit()
        assert siguiente_numero(db_session, FacturaEmitida, empresa_id=1) == 11
        assert siguiente_numero(db_session, FacturaEmitida, empresa_id=2) == 4

    def test_modelos_independientes(self, db_session):
        f = FacturaEmitida(empresa_id=1, numero=7, fecha=datetime.date(2026, 1, 1))
        db_session.add(f)
        db_session.commit()
        numero = siguiente_numero(db_session, FacturaRecibida, empresa_id=1)
        assert numero == 1


# ─── siguiente_cnumero ───────────────────────────────────────────────────────

class TestSiguienteCnumero:
    def test_primero_del_anio(self, db_session):
        import datetime
        tiponum, num = siguiente_cnumero(
            db_session, FacturaEmitida, empresa_id=1,
            fecha=datetime.date(2026, 1, 15), tiponum="N",
        )
        assert tiponum == "N"
        assert num == 1

    def test_despues_de_existente(self, db_session):
        import datetime
        f = FacturaEmitida(
            empresa_id=1, numero=1, cnumero=5, tiponum="N",
            fecha=datetime.date(2026, 3, 1),
        )
        db_session.add(f)
        db_session.commit()
        tiponum, num = siguiente_cnumero(
            db_session, FacturaEmitida, empresa_id=1,
            fecha=datetime.date(2026, 6, 15), tiponum="N",
        )
        assert num == 6

    def test_anios_independientes(self, db_session):
        import datetime
        f = FacturaEmitida(
            empresa_id=1, numero=1, cnumero=10, tiponum="N",
            fecha=datetime.date(2025, 12, 31),
        )
        db_session.add(f)
        db_session.commit()
        _, num = siguiente_cnumero(
            db_session, FacturaEmitida, empresa_id=1,
            fecha=datetime.date(2026, 1, 1), tiponum="N",
        )
        assert num == 1


# ─── total_lineas ────────────────────────────────────────────────────────────

class TestTotalLineas:
    def test_vacio(self):
        assert total_lineas([]) == 0

    def test_una_linea(self):
        ap = Apunte(importe=25.50)
        assert total_lineas([ap]) == Decimal('25.50')

    def test_varias_lineas(self):
        ap1 = Apunte(importe=10.0)
        ap2 = Apunte(importe=20.0)
        ap3 = Apunte(importe=30.0)
        assert total_lineas([ap1, ap2, ap3]) == Decimal('60.00')

    def test_con_none(self):
        ap1 = Apunte(importe=10.0)
        ap2 = Apunte(importe=None)
        assert total_lineas([ap1, ap2]) == Decimal('10.00')
