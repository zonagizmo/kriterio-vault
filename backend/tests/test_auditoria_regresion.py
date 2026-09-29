"""Regresiones de la auditoría de seguridad multiempresa + RBAC (v1.13.04).

Un test por hallazgo corregido de `docs/auditoria_seguridad.md` §F:
FN-001 (PUT propio con empresa), SYNC-001/002/003 (push cross-company),
EMP-001/002 (PUT/DELETE de empresas ajenas), RPT-001/002 (usuarios del
sistema por empresa), REL-001 (FK entre empresas) e IDOR-001 (404 uniforme).
Si alguno vuelve a fallar, la vulnerabilidad correspondiente ha regresado.
"""
import hashlib
import uuid as uuidlib

import pytest

from app.models.clientes_proveedores import Cliente
from app.models.empresas import Empresa
from app.models.sync import Instalacion
from app.models.usuarios import UsuarioSistema
from app.services.auth import create_access_token, hash_password


def h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _tok(user) -> str:
    return create_access_token({"sub": user.id, "rol": user.rol})


@pytest.fixture
def usuario_empresa(db_session):
    """Fábrica de usuarios restringidos a una empresa concreta."""
    def _crear(username: str, empresa_id: int, rol: str = "operador") -> UsuarioSistema:
        user = UsuarioSistema(
            username=username, password_hash=hash_password("pw123456"),
            nombre=username.title(), rol=rol, activo=True,
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


# ─── FN-001: el PUT con usuario con empresa no puede devolver 404 en lo propio ─

class TestFN001PutPropioConEmpresa:
    def test_put_cliente_propio_200(self, client, usuario_empresa, cliente_a):
        user_a = usuario_empresa("fn_op_a", 1)
        r = client.put(f"/api/clientes/{cliente_a['id']}",
                       json={"nombre": "Renombrado"}, headers=h(_tok(user_a)))
        assert r.status_code == 200, (
            f"PUT propio con empresa asignada devolvió {r.status_code}: {r.text[:200]}"
        )
        assert r.json()["nombre"] == "Renombrado"

    def test_put_factura_propia_200_y_ajena_404(self, client, usuario_empresa,
                                                cliente_a, cliente_b, admin_token):
        fac = client.post("/api/facturas/emitidas", json={
            "empresa_id": 1, "cliente": cliente_a["numero"], "fecha": "2026-03-01",
        }, headers=h(admin_token))
        assert fac.status_code == 201, fac.text
        fac_b = client.post("/api/facturas/emitidas", json={
            "empresa_id": 2, "cliente": cliente_b["numero"], "fecha": "2026-03-02",
        }, headers=h(admin_token))
        assert fac_b.status_code == 201, fac_b.text

        tok = h(_tok(usuario_empresa("fn_op_fac", 1)))
        r = client.put(f"/api/facturas/emitidas/{fac.json()['id']}",
                       json={"fecha": "2026-03-05", "cliente": cliente_a["numero"]},
                       headers=tok)
        assert r.status_code == 200, f"PUT propio falló: {r.status_code} {r.text[:200]}"
        r_ajena = client.put(f"/api/facturas/emitidas/{fac_b.json()['id']}",
                             json={"fecha": "2026-03-06", "cliente": cliente_b["numero"]},
                             headers=tok)
        assert r_ajena.status_code == 404

    def test_put_movimiento_propio_200(self, client, usuario_empresa, admin_token):
        banco = client.post("/api/bancos", json={"nombre": "Banco 1", "empresa_id": 1},
                            headers=h(admin_token))
        assert banco.status_code == 201, banco.text
        mov = client.post("/api/bancos/movimientos", json={
            "empresa_id": 1, "banco": banco.json()["numero"],
            "fecha": "2026-03-03", "total": 50,
        }, headers=h(admin_token))
        assert mov.status_code == 201, mov.text
        user_a = usuario_empresa("fn_op_mov", 1)
        r = client.put(f"/api/bancos/movimientos/{mov.json()['id']}",
                       json={"fecha": "2026-03-04", "total": 60},
                       headers=h(_tok(user_a)))
        assert r.status_code == 200, f"PUT propio falló: {r.status_code} {r.text[:200]}"


# ─── SYNC-001/002/003: el push no alcanza a otras empresas ──────────────────

@pytest.fixture
def sync_key(db_session):
    """Instalación autorizada SOLO para la empresa 1."""
    clave = "regresion-key-01"
    inst = Instalacion(
        uuid=str(uuidlib.uuid4()), nombre="regresion",
        api_key_hash=hashlib.sha256(clave.encode()).hexdigest(),
        empresas="1", activo=True,
    )
    db_session.add(inst)
    db_session.commit()
    return clave


def _push(client, clave, item):
    return client.post("/api/sync/push", json=[item],
                       headers={"X-SYNC-KEY": clave})


class TestSyncCrossCompany:
    def test_create_payload_empresa_ajena_bloqueado(self, client, db_session, sync_key):
        item = {"tabla": "clientes", "entidad_uuid": str(uuidlib.uuid4()),
                "operacion": "C", "empresa_id": 1,
                "payload": {"nombre": "SYNC-HACK", "empresa_id": 2}}
        r = _push(client, sync_key, item)
        assert r.status_code == 200
        assert r.json()["resultados"][0]["ok"] is False, (
            "push aceptó payload con empresa_id ajeno"
        )
        assert db_session.query(Cliente).filter(Cliente.nombre == "SYNC-HACK").count() == 0

    def test_update_recurso_ajeno_bloqueado(self, client, db_session, sync_key,
                                            cliente_b):
        uuid_b = db_session.query(Cliente).filter(
            Cliente.id == cliente_b["id"]).one().uuid
        item = {"tabla": "clientes", "entidad_uuid": uuid_b, "operacion": "U",
                "empresa_id": 1, "payload": {"nombre": "SYNC-HACK-U"}}
        r = _push(client, sync_key, item)
        assert r.status_code == 200
        assert r.json()["resultados"][0]["ok"] is False
        vivo = db_session.query(Cliente).filter(Cliente.id == cliente_b["id"]).one()
        assert vivo.nombre == "Cliente B", "push modificó un cliente de otra empresa"

    def test_delete_recurso_ajeno_bloqueado(self, client, db_session, sync_key,
                                            cliente_b):
        uuid_b = db_session.query(Cliente).filter(
            Cliente.id == cliente_b["id"]).one().uuid
        item = {"tabla": "clientes", "entidad_uuid": uuid_b, "operacion": "D",
                "empresa_id": 1, "payload": None}
        r = _push(client, sync_key, item)
        assert r.status_code == 200
        assert r.json()["resultados"][0]["ok"] is False
        assert db_session.query(Cliente).filter(
            Cliente.id == cliente_b["id"]).count() == 1, (
            "push borró un cliente de otra empresa"
        )

    def test_create_en_empresa_permitida_ok(self, client, db_session, sync_key):
        item = {"tabla": "clientes", "entidad_uuid": str(uuidlib.uuid4()),
                "operacion": "C", "empresa_id": 1,
                "payload": {"nombre": "Sync OK", "empresa_id": 1}}
        r = _push(client, sync_key, item)
        assert r.status_code == 200
        assert r.json()["resultados"][0]["ok"] is True
        fila = db_session.query(Cliente).filter(Cliente.nombre == "Sync OK").one()
        assert fila.empresa_id == 1


# ─── EMP-001/002: la zona de empresas exige pertenencia ─────────────────────

class TestEmpresasCrossCompany:
    def test_put_empresa_ajena_404(self, client, usuario_empresa, db_session):
        admin1 = usuario_empresa("adm_e1", 1, rol="admin")
        r = client.put("/api/empresas/2", json={"nombre": "COMPROMETIDA"},
                       headers=h(_tok(admin1)))
        assert r.status_code == 404, (
            f"admin de empresa 1 editó la empresa 2 ({r.status_code})"
        )
        assert db_session.query(Empresa).filter(Empresa.id == 2).one().nombre == "Empresa 2"

    def test_delete_empresa_ajena_404(self, client, usuario_empresa, db_session):
        admin1 = usuario_empresa("adm_e1_del", 1, rol="admin")
        r = client.delete("/api/empresas/4", headers=h(_tok(admin1)))
        assert r.status_code == 404, (
            f"admin de empresa 1 borró la empresa 4 ({r.status_code})"
        )
        assert db_session.query(Empresa).filter(Empresa.id == 4).first() is not None

    def test_admin_global_edita_empresa_control(self, client, admin_token):
        r = client.put("/api/empresas/2", json={"nombre": "Empresa 2 Edit"},
                       headers=h(admin_token))
        assert r.status_code == 200


# ─── RPT-001/002: usuarios del sistema filtrados por empresa ────────────────

class TestUsuariosSistemaPorEmpresa:
    def test_listado_sin_usuarios_de_otra_empresa(self, client, usuario_empresa):
        usuario_empresa("op_e2", 2)
        admin1 = usuario_empresa("adm_e1_rpt", 1, rol="admin")
        r = client.get("/api/auth/usuarios", headers=h(_tok(admin1)))
        assert r.status_code == 200
        ajenos = [u for u in r.json()["items"]
                  if u.get("empresa_id") not in (1, None)]
        assert not ajenos, f"admin empresa 1 ve usuarios de otras empresas: {ajenos}"

    def test_alta_en_otra_empresa_rechazada(self, client, usuario_empresa):
        admin1 = usuario_empresa("adm_e1_alta", 1, rol="admin")
        r = client.post("/api/auth/usuarios", headers=h(_tok(admin1)), json={
            "username": "invitado_e2", "password": "x1234", "nombre": "E2",
            "rol": "operador", "empresa_id": 2,
        })
        assert r.status_code in (400, 403, 404), (
            f"admin empresa 1 creó usuario en empresa 2 (HTTP {r.status_code})"
        )

    def test_alta_sin_empresa_se_asigna_a_la_suya(self, client, usuario_empresa,
                                                 db_session):
        admin1 = usuario_empresa("adm_e1_alta2", 1, rol="admin")
        r = client.post("/api/auth/usuarios", headers=h(_tok(admin1)), json={
            "username": "operador_e1", "password": "x1234", "nombre": "Op E1",
            "rol": "operador",
        })
        assert r.status_code == 201, r.text
        creado = db_session.query(UsuarioSistema).filter(
            UsuarioSistema.username == "operador_e1").one()
        assert creado.empresa_id == 1, "el alta no se forzó a la empresa del admin"

    def test_mutaciones_usuario_de_otra_empresa_404(self, client, usuario_empresa):
        objetivo = usuario_empresa("op_e2_tgt", 2)
        admin1 = usuario_empresa("adm_e1_put", 1, rol="admin")
        tok = h(_tok(admin1))
        r = client.put(f"/api/auth/usuarios/{objetivo.id}",
                       json={"nombre": "X"}, headers=tok)
        assert r.status_code == 404
        r_reset = client.post(f"/api/auth/usuarios/{objetivo.id}/reset-password",
                              json={"password_nuevo": "nueva"}, headers=tok)
        assert r_reset.status_code == 404
        r_del = client.delete(f"/api/auth/usuarios/{objetivo.id}", headers=tok)
        assert r_del.status_code == 404


# ─── REL-001: documentos sin entidades de otra empresa ──────────────────────

class TestRelacionesCrossCompany:
    def test_factura_con_cliente_ajeno_rechazada(self, client, cliente_a, cliente_b,
                                                 admin_token):
        r = client.post("/api/facturas/emitidas", headers=h(admin_token), json={
            "empresa_id": 1, "cliente": cliente_b["id"], "fecha": "2026-04-01",
        })
        assert r.status_code != 201, "factura empresa 1 creada con cliente de empresa 2"
        ok = client.post("/api/facturas/emitidas", headers=h(admin_token), json={
            "empresa_id": 1, "cliente": cliente_a["numero"], "fecha": "2026-04-02",
        })
        assert ok.status_code == 201, ok.text

    def test_albaran_con_cliente_ajeno_rechazado(self, client, cliente_b, admin_token):
        r = client.post("/api/albaranes/emitidos", headers=h(admin_token), json={
            "empresa_id": 1, "cliente": cliente_b["id"], "fecha": "2026-04-03",
        })
        assert r.status_code != 201, "albarán empresa 1 creado con cliente de empresa 2"

    def test_movimiento_con_banco_ajeno_rechazado(self, client, admin_token):
        b2 = client.post("/api/bancos", json={"nombre": "Banco E2", "empresa_id": 2},
                         headers=h(admin_token))
        assert b2.status_code == 201, b2.text
        r = client.post("/api/bancos/movimientos", headers=h(admin_token), json={
            "empresa_id": 1, "banco": b2.json()["id"], "fecha": "2026-04-04", "total": 10,
        })
        assert r.status_code != 201, "movimiento empresa 1 creado con banco de empresa 2"
        b1 = client.post("/api/bancos", json={"nombre": "Banco E1", "empresa_id": 1},
                         headers=h(admin_token))
        assert b1.status_code == 201, b1.text
        ok_mov = client.post("/api/bancos/movimientos", headers=h(admin_token), json={
            "empresa_id": 1, "banco": b1.json()["numero"], "fecha": "2026-04-05",
            "total": 10,
        })
        assert ok_mov.status_code == 201, ok_mov.text

    def test_factura_recibida_con_proveedor_ajeno_rechazada(self, client, admin_token):
        p = client.post("/api/proveedores", json={"nombre": "Prov E2", "empresa_id": 2},
                        headers=h(admin_token))
        assert p.status_code == 201, p.text
        r = client.post("/api/facturas/recibidas", headers=h(admin_token), json={
            "empresa_id": 1, "proveedor": p.json()["id"], "fecha": "2026-04-06",
        })
        assert r.status_code != 201, (
            "factura recibida empresa 1 con proveedor de empresa 2"
        )


# ─── IDOR-001: el 404 no distingue inexistente de ajeno ─────────────────────

class Test404Uniforme:
    @pytest.mark.parametrize("recurso", ["clientes", "proveedores", "facturas/emitidas"])
    def test_detalle_idéntico(self, client, usuario_empresa, cliente_a, admin_token,
                              recurso):
        # recursos de empresa 1 pedidos por un usuario de empresa 2 (ajenos)
        if recurso == "clientes":
            ajeno = cliente_a["id"]
        elif recurso == "proveedores":
            p = client.post("/api/proveedores",
                            json={"nombre": "Prov A", "empresa_id": 1},
                            headers=h(admin_token))
            assert p.status_code == 201
            ajeno = p.json()["id"]
        else:
            f = client.post("/api/facturas/emitidas", headers=h(admin_token), json={
                "empresa_id": 1, "cliente": cliente_a["numero"], "fecha": "2026-04-07",
            })
            assert f.status_code == 201, f.text
            ajeno = f.json()["id"]

        user_b = usuario_empresa("idor_op_b", 2)
        tok = h(_tok(user_b))
        r_ajeno = client.get(f"/api/{recurso}/{ajeno}", headers=tok)
        r_none = client.get(f"/api/{recurso}/999999", headers=tok)
        assert r_ajeno.status_code == r_none.status_code == 404
        assert r_ajeno.json() == r_none.json(), (
            "el detalle del 404 revela si el recurso existe: "
            f"ajeno={r_ajeno.json()} inexistente={r_none.json()}"
        )
