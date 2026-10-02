"""Auditoría de seguridad multiempresa + RBAC — Kriterio Vault (Fase dinámica).

Suite de la re-auditoría de `docs/auditoria_seguridad.md` (85 pruebas, 85/85
tras las correcciones de v1.13.04). Ahora vive en el repo: se ejecuta con el
resto de la suite desde cwd=backend:
    KRITERIO_NO_SHUTDOWN=1 ./venv/bin/python -m pytest -q
Autocontenida: usa solo su fixture `env` (SQLite en memoria propia por test,
`TestClient` con `get_db` sobrerrido) — no depende de `conftest.py`.
Cada test afirma la EXPECTATIVA DE SEGURIDAD: los fallos = hallazgos
regresados (ver también `test_auditoria_regresion.py`, 1 por hallazgo).
"""
import hashlib
import uuid as uuidlib
from datetime import timedelta

import pytest
from jose import jwt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.models.base import Base
from app.models import (  # noqa: F401 — registrar tablas
    empresas, usuarios, facturacion, contabilidad,
    clientes_proveedores, configuracion, bancos, sync,
)
from app.models.empresas import Empresa
from app.models.usuarios import UsuarioSistema
from app.models.sync import Instalacion
from app.models.clientes_proveedores import Cliente
from app.services.auth import hash_password, create_access_token, SECRET_KEY, ALGORITHM

# Hash único reutilizado (bcrypt cost 12): se calcula una sola vez por proceso.
_PW_HASH = hash_password("audit-only")

SYNC_KEY = "audit-key-01"
SYNC_KEY_HASH = hashlib.sha256(SYNC_KEY.encode()).hexdigest()


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def env():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _pragma(dbapi_conn, _):
        import sqlite3
        if isinstance(dbapi_conn, sqlite3.Connection):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    for eid in range(1, 5):
        db.add(Empresa(id=eid, codigo=f"EMP{eid}", nombre=f"Empresa {eid}"))
    db.commit()

    def mk(username, rol, empresa_id=None):
        u = UsuarioSistema(
            username=username, password_hash=_PW_HASH, nombre=username,
            rol=rol, activo=True, empresa_id=empresa_id,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    users = {
        "admin_global": mk("admin_global", "admin"),
        "admin_emp1": mk("admin_emp1", "admin", 1),
        "op_emp1": mk("op_emp1", "operador", 1),
        "op_emp2": mk("op_emp2", "operador", 2),
        "ro_emp1": mk("ro_emp1", "solo_lectura", 1),
        "op_global": mk("op_global", "operador"),
    }
    tokens = {k: create_access_token({"sub": u.id, "rol": u.rol})
              for k, u in users.items()}

    from app.main import app
    from app.db.database import get_db

    def _ov():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _ov
    try:
        with TestClient(app) as c:
            class E:
                pass
            e = E()
            e.client = c
            e.db = db
            e.users = users
            e.tokens = tokens
            e.ids = _seed(c, tokens["admin_global"])
            yield e
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)


def _seed(client, admin_token):
    """Crea recursos de empresa 1 y 2 con admin global (empresa NULL)."""
    H = auth(admin_token)
    ids = {}

    def post(url, payload, key):
        r = client.post(url, json=payload, headers=H)
        assert r.status_code == 201, f"seed {url} -> {r.status_code} {r.text[:300]}"
        body = r.json()
        ids[key] = body["id"] if isinstance(body, dict) and "id" in body else body
        return ids[key]

    for suf, emp in (("a", 1), ("b", 2)):
        ids[f"cli_{suf}"] = post("/api/clientes", {"nombre": f"Cliente {suf.upper()}", "empresa_id": emp}, f"cli_{suf}")
        ids[f"prov_{suf}"] = post("/api/proveedores", {"nombre": f"Proveedor {suf.upper()}", "empresa_id": emp}, f"prov_{suf}")
        ids[f"fam_{suf}"] = post("/api/familias", {"texto": f"Familia {suf.upper()}", "empresa_id": emp}, f"fam_{suf}")
        ids[f"art_{suf}"] = post("/api/articulos", {"nombre": f"Articulo {suf.upper()}", "empresa_id": emp}, f"art_{suf}")
        ids[f"banco_{suf}"] = post("/api/bancos", {"nombre": f"Banco {suf.upper()}", "empresa_id": emp}, f"banco_{suf}")
        ids[f"mov_{suf}"] = post(
            "/api/bancos/movimientos",
            {"banco": ids[f"banco_{suf}"], "fecha": "2026-01-10", "total": 123.45, "empresa_id": emp},
            f"mov_{suf}",
        )
        ids[f"vto_{suf}"] = post(
            "/api/bancos/vencimientos",
            {"empresa_id": emp, "tipo": "cliente", "fecha": "2026-03-15", "importe": 50},
            f"vto_{suf}",
        )
        ids[f"facemi_{suf}"] = post(
            "/api/facturas/emitidas",
            {"fecha": "2026-01-20", "cliente": ids[f"cli_{suf}"], "empresa_id": emp},
            f"facemi_{suf}",
        )
        ids[f"facrec_{suf}"] = post(
            "/api/facturas/recibidas",
            {"fecha": "2026-01-21", "proveedor": ids[f"prov_{suf}"], "empresa_id": emp},
            f"facrec_{suf}",
        )
        ids[f"albemi_{suf}"] = post(
            "/api/albaranes/emitidos",
            {"fecha": "2026-01-22", "cliente": ids[f"cli_{suf}"], "empresa_id": emp},
            f"albemi_{suf}",
        )
        ids[f"albrec_{suf}"] = post(
            "/api/albaranes/recibidos",
            {"fecha": "2026-01-23", "proveedor": ids[f"prov_{suf}"], "empresa_id": emp},
            f"albrec_{suf}",
        )
        ids[f"nna_{suf}"] = post("/api/usuarios", {"nombre": f"NNA {suf.upper()}", "empresa_id": emp}, f"nna_{suf}")
        ids[f"extra_{suf}"] = post(
            "/api/extras",
            {"fecha": "2026-02-01", "tipo": "cobro", "empresa_id": emp},
            f"extra_{suf}",
        )
    ids["cuenta_a"] = post("/api/contabilidad/cuentas", {"cuenta": "430000", "empresa_id": 1}, "cuenta_a")
    ids["cuenta_b"] = post("/api/contabilidad/cuentas", {"cuenta": "430001", "empresa_id": 2}, "cuenta_b")
    return ids


def _get(env, who, url, params=None):
    return env.client.get(url, params=params, headers=auth(env.tokens[who]))


def _post(env, who, url, payload):
    return env.client.post(url, json=payload, headers=auth(env.tokens[who]))


def _put(env, who, url, payload):
    return env.client.put(url, json=payload, headers=auth(env.tokens[who]))


def _del(env, who, url):
    return env.client.delete(url, headers=auth(env.tokens[who]))


# ── §10 MATEO: acceso directo cross-company (404) ───────────────────────────

def test_get_directo_recursos_ajenos_404(env):
    """op_emp1 (empresa 1) no puede leer ningún recurso individual de empresa 2."""
    i = env.ids
    ajenos = [
        f"/api/clientes/{i['cli_b']}",
        f"/api/proveedores/{i['prov_b']}",
        f"/api/articulos/{i['art_b']}",
        f"/api/familias/{i['fam_b']}",
        f"/api/bancos/{i['banco_b']}",
        f"/api/bancos/movimientos/{i['mov_b']}",
        f"/api/facturas/emitidas/{i['facemi_b']}",
        f"/api/facturas/recibidas/{i['facrec_b']}",
        f"/api/albaranes/emitidos/{i['albemi_b']}",
        f"/api/albaranes/recibidos/{i['albrec_b']}",
        f"/api/extras/{i['extra_b']}",
        f"/api/empresas/2",
    ]
    for url in ajenos:
        r = _get(env, "op_emp1", url)
        assert r.status_code == 404, f"esperaba 404 en {url}, obtuve {r.status_code}"


def test_get_directo_recursos_propios_200(env):
    i = env.ids
    propios = [
        f"/api/clientes/{i['cli_a']}",
        f"/api/proveedores/{i['prov_a']}",
        f"/api/articulos/{i['art_a']}",
        f"/api/familias/{i['fam_a']}",
        f"/api/bancos/{i['banco_a']}",
        f"/api/bancos/movimientos/{i['mov_a']}",
        f"/api/facturas/emitidas/{i['facemi_a']}",
        f"/api/extras/{i['extra_a']}",
        "/api/empresas/1",
    ]
    for url in propios:
        r = _get(env, "op_emp1", url)
        assert r.status_code == 200, f"esperaba 200 en {url}, obtuve {r.status_code}"


def test_404_id_inexistente_mismo_detalle_que_ajeno(env):
    """El 404 por empresa ajena no debe distinguirse del 404 por id inexistente."""
    r_ajeno = _get(env, "op_emp1", f"/api/clientes/{env.ids['cli_b']}")
    r_none = _get(env, "op_emp1", "/api/clientes/999999")
    assert r_ajeno.status_code == r_none.status_code == 404
    assert r_ajeno.json() == r_none.json(), (
        "el detalle del 404 revela si el recurso existe: "
        f"ajeno={r_ajeno.json()} inexistente={r_none.json()}"
    )


# ── §11 LISTADOS Y FILTROS ──────────────────────────────────────────────────

def test_listado_solo_recursos_de_su_empresa(env):
    r = _get(env, "op_emp1", "/api/clientes", {"empresa_id": 1})
    assert r.status_code == 200
    assert len(r.json()["items"]) >= 1
    assert all(c["empresa_id"] == 1 for c in r.json()["items"])

    r = _get(env, "op_emp1", "/api/facturas/emitidas", {"empresa_id": 1})
    assert r.status_code == 200
    assert all(f["empresa_id"] == 1 for f in r.json()["items"])

    r = _get(env, "op_emp1", "/api/bancos/vencimientos/lista", {"empresa_id": 1})
    assert r.status_code == 200
    assert all(v["empresa_id"] == 1 for v in r.json()["items"])

    r = _get(env, "op_emp1", "/api/contabilidad/cuentas", {"empresa_id": 1})
    assert r.status_code == 200
    assert all(c["empresa_id"] == 1 for c in r.json()["items"])


def test_filtro_empresa_ajena_404(env):
    """?empresa_id=2 con usuario de empresa 1 → 404 (empresa_query)."""
    for url in ["/api/clientes", "/api/dashboard", "/api/facturas/emitidas",
                "/api/bancos", "/api/usuarios", "/api/estadisticas/anios",
                "/api/contabilidad/cuentas", "/api/albaranes/emitidos"]:
        r = _get(env, "op_emp1", url, {"empresa_id": 2})
        assert r.status_code == 404, f"{url}?empresa_id=2 → {r.status_code} (esperado 404)"


def test_filtro_empresa_inexistente_404_para_usuario_de_empresa(env):
    r = _get(env, "op_emp1", "/api/clientes", {"empresa_id": 999})
    assert r.status_code == 404


def test_usuario_global_ve_las_dos_empresas(env):
    r1 = _get(env, "op_global", "/api/clientes", {"empresa_id": 1})
    r2 = _get(env, "op_global", "/api/clientes", {"empresa_id": 2})
    assert r1.status_code == 200 and r2.status_code == 200
    assert len(r1.json()) >= 1 and len(r2.json()) >= 1


def test_listado_requiere_empresa_id(env):
    """Los endpoints con empresa_query exigen ?empresa_id (422 si falta)."""
    r = _get(env, "op_emp1", "/api/clientes")
    assert r.status_code == 422


# ── §12/§13 ACTUALIZAR/BORRAR CROSS-COMPANY + EL BUG PUT PROPIO ────────────

def test_put_recurso_ajeno_404(env):
    r = _put(env, "op_emp1", f"/api/clientes/{env.ids['cli_b']}", {"nombre": "TOMADO"})
    assert r.status_code == 404
    # y el recurso no cambió
    r2 = _get(env, "op_global", f"/api/clientes/{env.ids['cli_b']}")
    assert r2.json()["nombre"] == "Cliente B"


def test_put_recurso_propio_deberia_200(env):
    """FUNC: un usuario con empresa asignada debe poder editar sus recursos.

    Falla aquí = el doble exigir_empresa(user, previo/data) en los PUT rechaza
    también el recurso propio (schema Update sin empresa_id → fail-closed).
    """
    r = _post(env, "op_emp1", "/api/clientes",
              {"nombre": "Cliente propio edit", "empresa_id": 1})
    assert r.status_code == 201
    cid = r.json()["id"]
    r2 = _put(env, "op_emp1", f"/api/clientes/{cid}", {"nombre": "Renombrado"})
    assert r2.status_code == 200, (
        f"PUT propio con empresa asignada devolvió {r2.status_code}: {r2.text[:200]}"
    )


def test_put_recursos_propios_varios_deberian_200(env):
    """Mismo bug en extras, movimientos, artículos, facturas, usuarios NNA..."""
    i = env.ids
    casos = [
        (f"/api/extras/{i['extra_a']}", {"fecha": "2026-02-01", "tipo": "pago"}),
        (f"/api/bancos/movimientos/{i['mov_a']}", {"banco": i["banco_a"], "fecha": "2026-01-11", "total": 99.99}),
        (f"/api/articulos/{i['art_a']}", {"nombre": "Articulo A v2"}),
        (f"/api/familias/{i['fam_a']}", {"texto": "Familia A v2"}),
        (f"/api/proveedores/{i['prov_a']}", {"nombre": "Proveedor A v2"}),
        (f"/api/facturas/emitidas/{i['facemi_a']}", {"fecha": "2026-01-20", "cliente": i["cli_a"]}),
        (f"/api/albaranes/emitidos/{i['albemi_a']}", {"fecha": "2026-01-22", "cliente": i["cli_a"]}),
    ]
    fallos = []
    for url, payload in casos:
        r = _put(env, "op_emp1", url, payload)
        if r.status_code != 200:
            fallos.append(f"{url} → {r.status_code}")
    assert not fallos, "PUT propio falló (bug fail-closed): " + "; ".join(fallos)


def test_put_recurso_propio_global_200_control(env):
    r = _put(env, "op_global", f"/api/clientes/{env.ids['cli_a']}", {"nombre": "Cliente A OK"})
    assert r.status_code == 200


def test_delete_recurso_ajeno_404(env):
    r = _del(env, "op_emp1", f"/api/clientes/{env.ids['cli_b']}")
    assert r.status_code == 404
    assert _get(env, "op_global", f"/api/clientes/{env.ids['cli_b']}").status_code == 200


def test_delete_recurso_propio_204(env):
    r = _del(env, "op_emp1", f"/api/clientes/{env.ids['cli_a']}")
    assert r.status_code == 204, f"DELETE propio → {r.status_code} {r.text[:200]}"


def test_delete_cross_company_mas_recursos_404(env):
    """IDOR de borrado sobre cuentas, extras, NNA, bancos, facturas."""
    i = env.ids
    ajenos = [
        f"/api/contabilidad/cuentas/{i['cuenta_b']}",
        f"/api/extras/{i['extra_b']}",
        f"/api/usuarios/{i['nna_b']}",
        f"/api/bancos/{i['banco_b']}",
        f"/api/facturas/emitidas/{i['facemi_b']}",
        f"/api/facturas/recibidas/{i['facrec_b']}",
    ]
    for url in ajenos:
        r = _del(env, "op_emp1", url)
        assert r.status_code == 404, f"DELETE ajeno {url} → {r.status_code} (esperado 404)"
    # nada se borró
    assert _get(env, "op_global", f"/api/extras/{i['extra_b']}").status_code == 200


# ── §14 CREAR CON EMPRESA_ID AJENO ──────────────────────────────────────────

def test_create_empresa_ajena_404(env):
    r = _post(env, "op_emp1", "/api/clientes", {"nombre": "Intruso", "empresa_id": 2})
    assert r.status_code == 404


def test_create_empresa_propia_201_y_asignacion_correcta(env):
    r = _post(env, "op_emp1", "/api/clientes", {"nombre": "Nuevo propio", "empresa_id": 1})
    assert r.status_code == 201
    assert r.json()["empresa_id"] == 1


def test_create_global_puede_crear_en_cualquier_empresa(env):
    r = _post(env, "op_global", "/api/clientes", {"nombre": "En e2", "empresa_id": 2})
    assert r.status_code == 201
    assert r.json()["empresa_id"] == 2


def test_create_relacion_cross_company_bloqueada(env):
    """Una factura/movimiento de empresa 1 no debe poder referenciar recursos de empresa 2."""
    i = env.ids
    r1 = _post(env, "op_emp1", "/api/facturas/emitidas",
               {"fecha": "2026-02-01", "cliente": i["cli_b"], "empresa_id": 1})
    r2 = _post(env, "op_emp1", "/api/bancos/movimientos",
               {"banco": i["banco_b"], "fecha": "2026-02-01", "total": 10, "empresa_id": 1})
    problemas = []
    if r1.status_code == 201:
        problemas.append("factura empresa 1 creada con cliente de empresa 2 (201)")
    if r2.status_code == 201:
        problemas.append("movimiento empresa 1 creado con banco de empresa 2 (201)")
    assert not problemas, "; ".join(problemas)


# ── §15 MASS ASSIGNMENT ─────────────────────────────────────────────────────

def test_put_no_permite_cambiar_empresa_id(env):
    """PUT con empresa_id en el body no debe mover el recurso de empresa."""
    cid = env.ids["cli_a"]
    r = _put(env, "op_global", f"/api/clientes/{cid}",
             {"nombre": "IntentoMA", "empresa_id": 2})
    assert r.status_code == 200
    row = env.db.query(Cliente).filter(Cliente.id == cid).first()
    env.db.refresh(row)
    assert row.empresa_id == 1, f"mass assignment: empresa_id cambió a {row.empresa_id}"
    assert row.nombre == "IntentoMA"  # el resto del payload sí se aplica


def test_create_por_api_valida_empresa_antes_de_escribir(env):
    """(cobertura cruzada con test_create_empresa_ajena_404) no escribe nada."""
    r = _post(env, "op_emp1", "/api/clientes", {"nombre": "X", "empresa_id": 3})
    assert r.status_code == 404
    assert env.db.query(Cliente).filter(Cliente.nombre == "X").count() == 0


# ── §16 IDOR / AUTH SWEEP ───────────────────────────────────────────────────

def test_sin_token_401_en_get(env):
    r = env.client.get("/api/clientes", params={"empresa_id": 1})
    assert r.status_code == 401


def test_todos_los_get_protegidos_sin_token_401(env):
    """Barrido: toda petición GET de la API exige Bearer (salvo /api/version)."""
    from app.main import app
    Publicos = {"/api/version"}
    fallos = []
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None)
        if not path.startswith("/api") or not methods or "GET" not in methods:
            continue
        if path in Publicos:
            continue
        url = path
        for ph in ("{cliente_id}", "{proveedor_id}", "{articulo_id}", "{familia_id}",
                   "{banco_id}", "{mov_id}", "{vto_id}", "{factura_id}", "{albaran_id}",
                   "{extra_id}", "{empresa_id}", "{user_id}", "{cuenta_id}",
                   "{asiento_num}", "{usuario_id}", "{paga_id}"):
            url = url.replace(ph, "999999")
        url = url.replace("{nombre}", "x.db")
        r = env.client.get(url, params={"empresa_id": 1})
        if r.status_code != 401:
            fallos.append(f"GET {url} → {r.status_code}")
    assert not fallos, "GETs sin autenticación: " + "; ".join(fallos)


def test_get_version_publico(env):
    r = env.client.get("/api/version")
    assert r.status_code == 200


# ── §17 JWT ─────────────────────────────────────────────────────────────────

def test_token_secreto_incorrecto_401(env):
    bad = jwt.encode({"sub": str(env.users["op_emp1"].id), "exp": "2099-01-01"},
                     "secreto-falso", algorithm=ALGORITHM)
    r = env.client.get("/api/auth/me", headers=auth(bad))
    assert r.status_code == 401


def test_token_alg_none_401(env):
    import base64, json
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    token = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': str(env.users['op_emp1'].id)})}."
    r = env.client.get("/api/auth/me", headers=auth(token))
    assert r.status_code == 401


def test_token_expirado_401(env):
    tok = create_access_token({"sub": env.users["op_emp1"].id},
                               expires_delta=timedelta(minutes=-5))
    r = env.client.get("/api/auth/me", headers=auth(tok))
    assert r.status_code == 401


def test_token_sub_no_numerico_401(env):
    tok = create_access_token({"sub": "no-numerico"})
    r = env.client.get("/api/auth/me", headers=auth(tok))
    assert r.status_code == 401


def test_token_sub_inexistente_401(env):
    tok = create_access_token({"sub": 999999})
    r = env.client.get("/api/auth/me", headers=auth(tok))
    assert r.status_code == 401


def test_token_usuario_inactivo_401(env):
    u = env.users["op_emp2"]
    u.activo = False
    env.db.commit()
    r = env.client.get("/api/auth/me", headers=auth(env.tokens["op_emp2"]))
    assert r.status_code == 401


def test_claim_rol_manipulado_ignorado(env):
    """El rol del token no manda: la BD manda (claim rol=admin inútil)."""
    fake = create_access_token({"sub": env.users["op_emp1"].id, "rol": "admin"})
    r = env.client.get("/api/ajustes/backups", headers=auth(fake))
    assert r.status_code == 403, "claim rol=admin en token de operador concedió acceso admin"
    r2 = env.client.get("/api/auth/me", headers=auth(fake))
    assert r2.status_code == 200
    assert r2.json()["rol"] == "operador"


def test_token_sin_claim_rol_funciona_por_bd(env):
    tok = create_access_token({"sub": env.users["op_emp1"].id})
    r = env.client.get("/api/auth/me", headers=auth(tok))
    assert r.status_code == 200
    assert r.json()["rol"] == "operador"


# ── §18 ESCALADA DE PRIVILEGIOS ─────────────────────────────────────────────

def test_operador_no_gestiona_usuarios(env):
    admin_id = env.users["admin_global"].id
    assert _post(env, "op_emp1", "/api/auth/usuarios",
                 {"username": "hacker", "password": "x1234", "nombre": "H", "rol": "admin"}).status_code == 403
    assert _put(env, "op_emp1", f"/api/auth/usuarios/{admin_id}",
                {"rol": "admin"}).status_code == 403
    assert _del(env, "op_emp1", f"/api/auth/usuarios/{admin_id}").status_code == 403
    assert _post(env, "op_emp1", f"/api/auth/usuarios/{admin_id}/reset-password",
                 {"password_nuevo": "nuevo"}).status_code == 403


def test_solo_lectura_solo_get(env):
    i = env.ids
    assert _get(env, "ro_emp1", "/api/clientes", {"empresa_id": 1}).status_code == 200
    assert _post(env, "ro_emp1", "/api/clientes", {"nombre": "X", "empresa_id": 1}).status_code == 403
    assert _put(env, "ro_emp1", f"/api/clientes/{i['cli_a']}", {"nombre": "X"}).status_code == 403
    assert _del(env, "ro_emp1", f"/api/clientes/{i['cli_a']}").status_code == 403


def test_zona_admin_restringida_por_rol(env):
    for who in ("op_emp1", "ro_emp1", "op_global", "op_emp2"):
        assert _get(env, who, "/api/ajustes/backups").status_code == 403, who
        assert _put(env, who, "/api/ajustes/config",
                    {"hora": "03:00", "dias": [1, 2]}).status_code == 403, who
        assert _post(env, who, "/api/ajustes/backup", {}).status_code == 403, who
        assert _post(env, who, f"/api/ajustes/backup/download/x.db", {}).status_code in (403, 405), who
        assert _post(env, who, "/api/ajustes/restaurar", {}).status_code == 403, who
        assert _post(env, who, "/api/shutdown", {}).status_code == 403, who
        assert _post(env, who, "/api/sync/ejecutar", {}).status_code == 403, who


def test_admin_global_accede_zona_admin(env):
    assert _get(env, "admin_global", "/api/ajustes/backups").status_code == 200
    assert _get(env, "admin_global", "/api/auth/usuarios").status_code == 200


def test_operador_no_edita_empresas(env):
    assert _put(env, "op_emp1", "/api/empresas/1", {"nombre": "X"}).status_code == 403
    assert _post(env, "op_emp1", "/api/empresas", {"codigo": "Z", "nombre": "Z"}).status_code == 403
    assert _del(env, "op_emp1", "/api/empresas/4").status_code == 403
    assert _put(env, "ro_emp1", "/api/empresas/1", {"nombre": "X"}).status_code == 403


# ── §19 ADMIN CON EMPRESA ASIGNADA (límites laterales) ─────────────────────

def test_admin_emp1_listado_empresas_filtrado(env):
    r = _get(env, "admin_emp1", "/api/empresas")
    assert r.status_code == 200
    assert [e["id"] for e in r.json()] == [1], f"ve más empresas: {[e['id'] for e in r.json()]}"


def test_admin_emp1_get_empresa_ajena_404(env):
    assert _get(env, "admin_emp1", "/api/empresas/2").status_code == 404
    assert _get(env, "admin_emp1", "/api/empresas/1").status_code == 200


def test_admin_emp1_put_empresa_ajena_bloqueado(env):
    """VULN: PUT /api/empresas/{id} no llama exigir_empresa → ¿edita empresa 2?"""
    r = _put(env, "admin_emp1", "/api/empresas/2", {"nombre": "EMPRESA COMPROMETIDA"})
    assert r.status_code == 404, (
        f"admin de empresa 1 editó la empresa 2 (PUT devolvió {r.status_code})"
    )
    row = env.db.query(Empresa).filter(Empresa.id == 2).first()
    assert row.nombre == "Empresa 2", f"nombre de empresa 2 alterado a {row.nombre!r}"


def test_admin_emp1_delete_empresa_ajena_bloqueado(env):
    """VULN: DELETE /api/empresas/{id} sin exigir_empresa → ¿borra empresa 4 (vacía)?"""
    r = _del(env, "admin_emp1", "/api/empresas/4")
    assert r.status_code == 404, f"admin de empresa 1 borró la empresa 4 (DELETE {r.status_code})"
    assert env.db.query(Empresa).filter(Empresa.id == 4).first() is not None


def test_admin_emp1_usuarios_sin_recororte_empresa(env):
    """DEB: ¿el admin de empresa 1 ve/gestiona usuarios de otras empresas?"""
    r = _get(env, "admin_emp1", "/api/auth/usuarios")
    assert r.status_code == 200
    otros = [u for u in r.json()["items"] if u.get("empresa_id") not in (1, None)]
    assert not otros, f"admin empresa 1 ve usuarios de otras empresas: {otros}"


def test_admin_emp1_crear_usuario_en_otra_empresa_bloqueado(env):
    """DEB: ¿puede crear un usuario asignado a empresa 2?"""
    r = _post(env, "admin_emp1", "/api/auth/usuarios",
              {"username": "invitado_e2", "password": "x1234", "nombre": "E2",
               "rol": "operador", "empresa_id": 2})
    assert r.status_code in (400, 403, 404), (
        f"admin empresa 1 creó usuario en empresa 2 (HTTP {r.status_code})"
    )


def test_admin_emp1_usuarios_nna_ajenos_404(env):
    i = env.ids
    assert _put(env, "admin_emp1", f"/api/usuarios/{i['nna_b']}", {"nombre": "X"}).status_code == 404
    assert _del(env, "admin_emp1", f"/api/usuarios/{i['nna_b']}").status_code == 404


# ── §20 SYNC (X-SYNC-KEY) ───────────────────────────────────────────────────

def _seed_instalacion(db, empresas_csv, key_hash=SYNC_KEY_HASH):
    inst = Instalacion(
        uuid=str(uuidlib.uuid4()), nombre="audit", api_key_hash=key_hash,
        empresas=empresas_csv, activo=True,
    )
    db.add(inst)
    db.commit()
    return inst


def test_sync_sin_key_401(env):
    r = env.client.post("/api/sync/push", json=[])
    assert r.status_code in (401, 422), f"push sin X-SYNC-KEY → {r.status_code}"


def test_sync_key_invalida_401(env):
    r = env.client.post("/api/sync/push", json=[], headers={"X-SYNC-KEY": "mala"})
    assert r.status_code == 401


def test_sync_empresa_no_autorizada_para_instalacion(env):
    _seed_instalacion(env.db, "1")
    item = {"tabla": "clientes", "entidad_uuid": str(uuidlib.uuid4()),
            "operacion": "C", "empresa_id": 2,
            "payload": {"nombre": "NoDebe", "empresa_id": 2}}
    r = env.client.post("/api/sync/push", json=[item], headers={"X-SYNC-KEY": SYNC_KEY})
    assert r.status_code == 200
    assert r.json()["resultados"][0]["ok"] is False
    assert env.db.query(Cliente).filter(Cliente.nombre == "NoDebe").count() == 0


def test_sync_create_en_empresa_permitida_ok(env):
    _seed_instalacion(env.db, "1")
    item = {"tabla": "clientes", "entidad_uuid": str(uuidlib.uuid4()),
            "operacion": "C", "empresa_id": 1,
            "payload": {"nombre": "Sync OK", "empresa_id": 1}}
    r = env.client.post("/api/sync/push", json=[item], headers={"X-SYNC-KEY": SYNC_KEY})
    assert r.status_code == 200
    assert r.json()["resultados"][0]["ok"] is True
    assert env.db.query(Cliente).filter(Cliente.nombre == "Sync OK").one().empresa_id == 1


def test_sync_create_payload_empresa_ajena_bloqueado(env):
    """VULN: item.empresa_id=1 (permitido) pero payload.empresa_id=2 → ¿escribe en empresa 2?"""
    _seed_instalacion(env.db, "1")
    item = {"tabla": "clientes", "entidad_uuid": str(uuidlib.uuid4()),
            "operacion": "C", "empresa_id": 1,
            "payload": {"nombre": "SYNC-HACK", "empresa_id": 2}}
    r = env.client.post("/api/sync/push", json=[item], headers={"X-SYNC-KEY": SYNC_KEY})
    assert r.status_code == 200
    ok = r.json()["resultados"][0].get("ok")
    fila = env.db.query(Cliente).filter(Cliente.nombre == "SYNC-HACK").first()
    assert (not ok) and fila is None, (
        f"push creó cliente en empresa 2 con key limitada a empresa 1 (ok={ok}, "
        f"fila={getattr(fila, 'empresa_id', None)})"
    )


def test_sync_update_recurso_ajeno_bloqueado(env):
    """VULN: 'U' sobre uuid de empresa 2 con key limitada a empresa 1."""
    _seed_instalacion(env.db, "1")
    cli_b = env.db.query(Cliente).filter(Cliente.id == env.ids["cli_b"]).first()
    item = {"tabla": "clientes", "entidad_uuid": cli_b.uuid, "operacion": "U",
            "empresa_id": 1, "payload": {"nombre": "SYNC-HACK-U"}}
    r = env.client.post("/api/sync/push", json=[item], headers={"X-SYNC-KEY": SYNC_KEY})
    assert r.status_code == 200
    ok = r.json()["resultados"][0].get("ok")
    env.db.refresh(cli_b)
    assert (not ok) and cli_b.nombre == "Cliente B", (
        f"push modificó un cliente de empresa 2 con key de empresa 1 (ok={ok}, nombre={cli_b.nombre!r})"
    )


def test_sync_delete_recurso_ajeno_bloqueado(env):
    """VULN: 'D' sobre uuid de empresa 2 con key limitada a empresa 1."""
    _seed_instalacion(env.db, "1")
    cli_b = env.db.query(Cliente).filter(Cliente.id == env.ids["cli_b"]).first()
    item = {"tabla": "clientes", "entidad_uuid": cli_b.uuid, "operacion": "D",
            "empresa_id": 1, "payload": None}
    r = env.client.post("/api/sync/push", json=[item], headers={"X-SYNC-KEY": SYNC_KEY})
    assert r.status_code == 200
    ok = r.json()["resultados"][0].get("ok")
    vivo = env.db.query(Cliente).filter(Cliente.id == env.ids["cli_b"]).first()
    assert (not ok) and vivo is not None, (
        f"push borró un cliente de empresa 2 con key de empresa 1 (ok={ok})"
    )


# ── §21 MATRIZ RBAC (rol × método) ──────────────────────────────────────────

@pytest.mark.parametrize("who,method,esperado", [
    # GET /api/clientes (con ?empresa_id de su empresa o sin él para global)
    ("admin_global", "GET", 200), ("op_global", "GET", 200), ("ro_emp1", "GET", 200),
    # POST /api/clientes
    ("admin_global", "POST", 201), ("op_global", "POST", 201), ("ro_emp1", "POST", 403),
    # DELETE /api/clientes sobre recurso propio (creado por el propio test)
    ("admin_global", "DELETE", 204), ("op_global", "DELETE", 204), ("ro_emp1", "DELETE", 403),
])
def test_matriz_rbac_clientes(env, who, method, esperado):
    if method == "GET":
        params = {"empresa_id": 1}
        r = _get(env, who, "/api/clientes", params)
    else:
        r0 = _post(env, "admin_global", "/api/clientes",
                   {"nombre": f"matriz {who} {method}", "empresa_id": 1})
        assert r0.status_code == 201
        cid = r0.json()["id"]
        if method == "POST":
            r = _post(env, who, "/api/clientes", {"nombre": "otro", "empresa_id": 1})
        else:
            r = _del(env, who, f"/api/clientes/{cid}")
    assert r.status_code == esperado, (
        f"{who} {method} /api/clientes → {r.status_code} (esperado {esperado})"
    )


def test_matriz_rbac_zona_admin_y_gestion(env):
    """GET /api/ajustes/backups y GET /api/auth/usuarios: solo admin."""
    esperado_backups = {"admin_global": 200, "op_global": 403,
                        "op_emp1": 403, "op_emp2": 403, "ro_emp1": 403}
    esperado_usuarios = {"admin_global": 200, "op_global": 403,
                         "op_emp1": 403, "op_emp2": 403, "ro_emp1": 403}
    fallos = []
    for who, exp in esperado_backups.items():
        got = _get(env, who, "/api/ajustes/backups").status_code
        if got != exp:
            fallos.append(f"backups {who} → {got} (esperado {exp})")
    for who, exp in esperado_usuarios.items():
        got = _get(env, who, "/api/auth/usuarios").status_code
        if got != exp:
            fallos.append(f"usuarios {who} → {got} (esperado {exp})")
    assert not fallos, "; ".join(fallos)


def test_operador_no_shutdown(env):
    assert _post(env, "op_global", "/api/shutdown", {}).status_code == 403


# ── NUE-001 (v1.13.09) SHUTDOWN SOLO ADMIN GLOBAL ────────────────────────────

def test_nue001_admin_con_empresa_no_apaga(env, monkeypatch):
    """NUE-001: el admin de empresa 1 no debe poder apagar el servidor (403)."""
    monkeypatch.setenv("KRITERIO_NO_SHUTDOWN", "1")
    r = _post(env, "admin_emp1", "/api/shutdown", {})
    assert r.status_code == 403, (
        f"admin con empresa apagó el servidor (HTTP {r.status_code}) — NUE-001 regresada"
    )
    assert "global" in r.json()["detail"].lower()


def test_nue001_admin_global_si_apaga(env, monkeypatch):
    """NUE-001: el admin global (empresa NULL) sigue pudiendo apagar (200)."""
    monkeypatch.setenv("KRITERIO_NO_SHUTDOWN", "1")
    r = _post(env, "admin_global", "/api/shutdown", {})
    assert r.status_code == 200, f"admin global no pudo apagar: {r.status_code}"
    assert r.json()["ok"] is True


def test_solo_lectura_y_operador_no_restauran_backup(env):
    for who in ("ro_emp1", "op_global"):
        assert _post(env, who, "/api/ajustes/restaurar", {}).status_code == 403
        assert _post(env, who, "/api/ajustes/restaurar-backup/x.db", {}).status_code == 403


# ── §22/§23 DASHBOARD, ESTADÍSTICAS, EXPORT ─────────────────────────────────

def test_dashboard_estadisticas_respetan_empresa(env):
    assert _get(env, "op_emp1", "/api/dashboard", {"empresa_id": 1}).status_code == 200
    assert _get(env, "op_emp1", "/api/dashboard", {"empresa_id": 2}).status_code == 404
    assert _get(env, "op_emp1", "/api/estadisticas/anios", {"empresa_id": 2}).status_code == 404
    assert _get(env, "op_emp1", "/api/estadisticas",
                {"empresa_id": 2, "anio": 2026}).status_code == 404
    assert _get(env, "op_global", "/api/dashboard", {"empresa_id": 2}).status_code == 200


def test_export_requiere_autenticacion(env):
    """Los exports (window.open en frontend) no envían Bearer → 401 en navegador."""
    url = "/api/estadisticas/periodo/ingresos/export"
    params = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31", "empresa_id": 1}
    sin_auth = env.client.get(url, params=params)
    assert sin_auth.status_code == 401, (
        f"export accesible sin Bearer → {sin_auth.status_code} "
        "(window.open lo estaría sirviendo a cualquiera)"
    )
    con_auth = env.client.get(url, params=params, headers=auth(env.tokens["op_emp1"]))
    assert con_auth.status_code == 200
    # el export de otra empresa debe rechazarse
    params2 = dict(params, empresa_id=2)
    r2 = env.client.get(url, params=params2, headers=auth(env.tokens["op_emp1"]))
    assert r2.status_code == 404


def test_export_ajeno_404_para_usuario_de_empresa(env):
    for url, params in [
        ("/api/usuarios/pagas/export", {"empresa_id": 2}),
        ("/api/estadisticas/periodo/gastos/export",
         {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31", "empresa_id": 2}),
        ("/api/contabilidad/export/balance", {"empresa_id": 2}),
    ]:
        r = env.client.get(url, params=params, headers=auth(env.tokens["op_emp1"]))
        assert r.status_code == 404, f"{url} empresa 2 → {r.status_code} (esperado 404)"


# ── §24 CONTABILIDAD / BALANCE / DIAGNÓSTICO ────────────────────────────────

def test_contabilidad_endpoints_ajenos_404(env):
    for url in ["/api/contabilidad/balance", "/api/contabilidad/mayor",
                "/api/contabilidad/sumas-saldos", "/api/contabilidad/pyg",
                "/api/contabilidad/diagnostico", "/api/contabilidad/asientos",
                "/api/contabilidad/conciliacion-bancos"]:
        r = _get(env, "op_emp1", url, {"empresa_id": 2})
        assert r.status_code == 404, f"{url}?empresa_id=2 → {r.status_code}"
    # su propia empresa: 200
    r = _get(env, "op_emp1", "/api/contabilidad/balance", {"empresa_id": 1})
    assert r.status_code == 200


def test_cierre_y_generar_pendientes_solo_escritura(env):
    assert _post(env, "ro_emp1", "/api/contabilidad/generar-pendientes",
                 {}).status_code in (403, 405, 422)
    # solo_lectura no debe poder cerrar (POST /cierre)
    r = _post(env, "ro_emp1", "/api/contabilidad/cierre", {"empresa_id": 1, "anio": 2025})
    assert r.status_code in (403, 405, 422), f"cierre solo_lectura → {r.status_code}"


# ── §25 USUARIOS NNA / PAGAS ────────────────────────────────────────────────

def test_usuarios_nna_listado_y_mutaciones(env):
    i = env.ids
    # listado filtrado
    r = _get(env, "op_emp1", "/api/usuarios", {"empresa_id": 1})
    assert r.status_code == 200
    assert all(u["empresa_id"] == 1 for u in r.json()["items"])
    # crear en su empresa: 201 (operador tiene create)
    r = _post(env, "op_emp1", "/api/usuarios", {"nombre": "NNA propio", "empresa_id": 1})
    assert r.status_code == 201
    # crear en ajena: 404
    r = _post(env, "op_emp1", "/api/usuarios", {"nombre": "NNA ajeno", "empresa_id": 2})
    assert r.status_code == 404
    # borrar ajeno: 404
    assert _del(env, "op_emp1", f"/api/usuarios/{i['nna_b']}").status_code == 404
    # solo_lectura no borra el propio
    assert _del(env, "ro_emp1", f"/api/usuarios/{i['nna_a']}").status_code == 403


# ── §26 BACKUPS / RESTAURAR (solo autorización, sin ejecutar acciones) ─────

def test_backup_download_sin_auth_401(env):
    r = env.client.get("/api/ajustes/backup/download/no_existe.db")
    assert r.status_code == 401


def test_backup_download_rol_solo_lectura_403(env):
    r = _get(env, "ro_emp1", "/api/ajustes/backup/download/no_existe.db")
    assert r.status_code == 403


def test_restaurar_sin_auth_401(env):
    r = env.client.post("/api/ajustes/restaurar", json={})
    assert r.status_code == 401


# ── §27 CÓDIGOS HTTP ────────────────────────────────────────────────────────

def test_metodo_no_permitido_405(env):
    r = env.client.post(f"/api/clientes/{env.ids['cli_a']}", json={},
                        headers=auth(env.tokens["admin_global"]))
    assert r.status_code == 405


def test_403_vs_404_consistente(env):
    """Sin permiso → 403; empresa ajena/inexistente → 404 (nunca 500)."""
    assert _get(env, "ro_emp1", "/api/ajustes/backups").status_code == 403
    assert _get(env, "op_emp1", "/api/clientes/999999").status_code == 404
    assert _get(env, "op_emp1", "/api/clientes", {"empresa_id": 2}).status_code == 404
    assert _get(env, "admin_emp1", "/api/empresas/999").status_code == 404


# ── §10b MUTANTES AVANZADOS (reparar/renumerar/reordenar/asientos) ──────────

def test_put_recursos_ajenos_varios_404(env):
    i = env.ids
    casos = [
        (f"/api/bancos/{i['banco_b']}", {"nombre": "TOMA"}),
        (f"/api/bancos/movimientos/{i['mov_b']}",
         {"banco": i["banco_b"], "fecha": "2026-01-10", "total": 1}),
        (f"/api/bancos/vencimientos/{i['vto_b']}",
         {"empresa_id": 2, "tipo": "cliente", "fecha": "2026-03-15", "importe": 55}),
        (f"/api/contabilidad/cuentas/{i['cuenta_b']}", {"cuenta": "430001"}),
        (f"/api/usuarios/{i['nna_b']}", {"nombre": "TOMA"}),
        (f"/api/facturas/recibidas/{i['facrec_b']}",
         {"fecha": "2026-01-21", "proveedor": i["prov_b"]}),
        (f"/api/albaranes/recibidos/{i['albrec_b']}",
         {"fecha": "2026-01-23", "proveedor": i["prov_b"]}),
        (f"/api/articulos/{i['art_b']}", {"nombre": "TOMA"}),
        (f"/api/familias/{i['fam_b']}", {"texto": "TOMA"}),
    ]
    fallos = []
    for url, payload in casos:
        r = _put(env, "op_emp1", url, payload)
        if r.status_code != 404:
            fallos.append(f"{url} → {r.status_code}")
    assert not fallos, "PUT ajeno no devolvió 404: " + "; ".join(fallos)


def test_put_recursos_propios_avanzados_deberian_200(env):
    """FUNC: mismo bug fail-closed en bancos, vencimientos, cuentas y NNA."""
    i = env.ids
    fallos = []
    casos = [
        (f"/api/bancos/{i['banco_a']}", {"nombre": "Banco A v2"}),
        (f"/api/bancos/vencimientos/{i['vto_a']}",
         {"empresa_id": 1, "tipo": "cliente", "fecha": "2026-03-15", "importe": 66}),
        (f"/api/contabilidad/cuentas/{i['cuenta_a']}", {"cuenta": "430000"}),
        (f"/api/usuarios/{i['nna_a']}", {"nombre": "NNA A v2"}),
        (f"/api/facturas/recibidas/{i['facrec_a']}",
         {"fecha": "2026-01-21", "proveedor": i["prov_a"]}),
        (f"/api/albaranes/recibidos/{i['albrec_a']}",
         {"fecha": "2026-01-23", "proveedor": i["prov_a"]}),
    ]
    for url, payload in casos:
        r = _put(env, "op_emp1", url, payload)
        if r.status_code != 200:
            fallos.append(f"{url} → {r.status_code}")
    assert not fallos, "PUT propio falló (fail-closed): " + "; ".join(fallos)


def _crear_asiento(env, who, empresa):
    body = {"empresa_id": empresa, "fecha": "2026-03-01",
            "lineas": [{"cuenta": "430000" if empresa == 1 else "430001",
                        "importe": 100},
                       {"cuenta": "430000" if empresa == 1 else "430001",
                        "importe": -100}]}
    r = _post(env, who, "/api/contabilidad/asientos", body)
    assert r.status_code == 201, f"crear asiento e{empresa}: {r.status_code} {r.text[:300]}"
    return r.json()["asiento"], body


def test_put_asiento_propio_funciona_y_ajeno_404(env):
    """Contraste: los asientos (PUT con AsientoCreate, que SÍ lleva empresa_id) no tienen el bug."""
    num1, body1 = _crear_asiento(env, "op_emp1", 1)      # e1 → nº1
    _crear_asiento(env, "admin_global", 2)                # e2 → nº1 (misma cifra)
    num2, body2 = _crear_asiento(env, "admin_global", 2)  # e2 → nº2 (e1 no tiene nº2)

    r = _put(env, "op_emp1", f"/api/contabilidad/asientos/{num1}", body1)
    assert r.status_code == 200, f"PUT asiento propio → {r.status_code}"

    # con empresa_id propio pero número de asiento que solo existe en e2 → sin match → 404
    r = _put(env, "op_emp1", f"/api/contabilidad/asientos/{num2}", body1)
    assert r.status_code == 404, (
        f"PUT asientos/{num2} con body e1 → {r.status_code} "
        "(el servicio tocó un asiento de otra empresa)"
    )

    # con empresa_id ajeno → exigir_empresa → 404
    r = _put(env, "op_emp1", f"/api/contabilidad/asientos/{num2}", body2)
    assert r.status_code == 404, f"PUT asiento ajeno (body e2) → {r.status_code}"


def test_delete_asiento_cross_404_y_propio_204(env):
    num1, _ = _crear_asiento(env, "op_emp1", 1)      # e1 → nº1
    _crear_asiento(env, "admin_global", 2)            # e2 → nº1
    num2, _ = _crear_asiento(env, "admin_global", 2)  # e2 → nº2 (no existe en e1)
    assert _del(env, "op_emp1", f"/api/contabilidad/asientos/{num2}?empresa_id=2").status_code == 404
    assert _del(env, "op_emp1", f"/api/contabilidad/asientos/{num2}?empresa_id=1").status_code == 404, (
        "DELETE con empresa propia sobre asiento inexistente en e1 no devolvió 404"
    )
    assert _del(env, "op_emp1", f"/api/contabilidad/asientos/{num1}?empresa_id=1").status_code == 204


def test_renumerar_cross_404_y_propio_200(env):
    fallos = []
    for url in ["/api/extras/renumerar", "/api/facturas/emitidas/renumerar",
                "/api/facturas/recibidas/renumerar"]:
        r = _post(env, "op_emp1", url, {"empresa_id": 2})
        if r.status_code != 404:
            fallos.append(f"{url} e2 → {r.status_code}")
        r = _post(env, "op_emp1", url, {"empresa_id": 1})
        if r.status_code != 200:
            fallos.append(f"{url} e1 → {r.status_code}")
    assert not fallos, "; ".join(fallos)


def test_reparar_saldos_cross_404_y_propio_200(env):
    i = env.ids
    assert _post(env, "op_emp1", f"/api/bancos/{i['banco_b']}/reparar_saldos", {}).status_code == 404
    assert _post(env, "op_emp1", f"/api/bancos/{i['banco_a']}/reparar_saldos", {}).status_code == 200


def test_reordenar_cross_404_y_propio_200(env):
    i = env.ids
    body = {"direccion": "abajo"}
    assert _post(env, "op_emp1", f"/api/bancos/movimientos/{i['mov_b']}/reordenar", body).status_code == 404
    assert _post(env, "op_emp1", f"/api/bancos/movimientos/{i['mov_a']}/reordenar", body).status_code == 200


def test_mutantes_solo_lectura_403(env):
    i = env.ids
    casos = [
        ("POST", "/api/extras/renumerar", {"empresa_id": 1}),
        ("POST", f"/api/bancos/{i['banco_a']}/reparar_saldos", {}),
        ("POST", f"/api/bancos/movimientos/{i['mov_a']}/reordenar", {"direccion": "abajo"}),
        ("POST", "/api/contabilidad/asientos",
         {"empresa_id": 1, "fecha": "2026-03-01",
          "lineas": [{"cuenta": "430000", "importe": 1}, {"cuenta": "430000", "importe": -1}]}),
        ("PUT", f"/api/contabilidad/cuentas/{i['cuenta_a']}", {"cuenta": "430000"}),
        ("PUT", f"/api/usuarios/{i['nna_a']}", {"nombre": "X"}),
    ]
    fallos = []
    for method, url, payload in casos:
        if method == "POST":
            r = _post(env, "ro_emp1", url, payload)
        else:
            r = _put(env, "ro_emp1", url, payload)
        if r.status_code != 403:
            fallos.append(f"{method} {url} → {r.status_code}")
    assert not fallos, "; ".join(fallos)


def test_admin_emp1_zona_admin_sin_recororte_empresa(env):
    """DEB: los permisos admin (backups, sync…) no se recortan por empresa del admin.

    Un admin con empresa asignada accede a la zona global (backups = BD completa).
    """
    assert _get(env, "admin_emp1", "/api/ajustes/backups").status_code == 200
    assert _get(env, "admin_emp1", "/api/auth/usuarios").status_code == 200


def test_empresas_put_delete_admin_global_ok_control(env):
    """Control: el admin sin empresa sí administra empresas (por diseño)."""
    r = _put(env, "admin_global", "/api/empresas/4", {"nombre": "Empresa 4 OK"})
    assert r.status_code == 200
    assert env.db.query(Empresa).filter(Empresa.id == 4).one().nombre == "Empresa 4 OK"
    # empresa con datos no se puede borrar (guardia interna)
    r = _del(env, "admin_global", "/api/empresas/1")
    assert r.status_code == 400


def test_pagas_cross_404_y_propio_201(env):
    i = env.ids
    r = _post(env, "admin_global", "/api/usuarios/pagas",
              {"empresa_id": 2, "usuario": i["nna_b"], "fecha": "2026-01-05", "importe": 10})
    assert r.status_code == 201, r.text[:200]
    paga_b = r.json()["id"]
    fallos = []
    r = _post(env, "op_emp1", "/api/usuarios/pagas",
              {"empresa_id": 2, "usuario": i["nna_b"], "fecha": "2026-01-06", "importe": 10})
    if r.status_code != 404:
        fallos.append(f"POST pagas e2 → {r.status_code}")
    r = _post(env, "op_emp1", "/api/usuarios/pagas",
              {"empresa_id": 1, "usuario": i["nna_a"], "fecha": "2026-01-06", "importe": 10})
    if r.status_code != 201:
        fallos.append(f"POST pagas e1 → {r.status_code}")
    r = _del(env, "op_emp1", f"/api/usuarios/pagas/{paga_b}")
    if r.status_code != 404:
        fallos.append(f"DELETE pagas e2 → {r.status_code}")
    r = _post(env, "op_emp1", "/api/usuarios/pagas/mes",
              {"empresa_id": 2, "fecha": "2026-01-31",
               "items": [{"usuario": i["nna_b"], "importe": 5}]})
    if r.status_code != 404:
        fallos.append(f"POST pagas/mes e2 → {r.status_code}")
    r = _post(env, "op_emp1", "/api/usuarios/pagas/mes",
              {"empresa_id": 1, "fecha": "2026-01-31",
               "items": [{"usuario": i["nna_a"], "importe": 5}]})
    if r.status_code not in (200, 201):
        fallos.append(f"POST pagas/mes e1 → {r.status_code}")
    r = env.client.get("/api/usuarios/pagas/export", params={"empresa_id": 2},
                       headers=auth(env.tokens["op_emp1"]))
    if r.status_code != 404:
        fallos.append(f"GET pagas/export e2 → {r.status_code}")
    assert not fallos, "; ".join(fallos)


# ── D-03 (v1.13.07) ALTA DE EMPRESAS SOLO ADMIN GLOBAL ─────────────────────

def test_d03_admin_con_empresa_no_crea_empresas(env):
    """D-03: un admin con empresa asignada no debe poder crear empresas (403)."""
    r = _post(env, "admin_emp1", "/api/empresas", {"codigo": "NUE1", "nombre": "Nueva"})
    assert r.status_code == 403, (
        f"admin con empresa creó una empresa (HTTP {r.status_code}) — D-03 regresada"
    )


def test_d03_admin_global_si_crea_empresas(env):
    """D-03: el admin global (empresa NULL) sigue pudiendo crear empresas."""
    r = _post(env, "admin_global", "/api/empresas", {"codigo": "NUE1", "nombre": "Nueva"})
    assert r.status_code == 201, f"admin global no pudo crear empresa: {r.status_code}"
    assert r.json()["codigo"] == "NUE1"
