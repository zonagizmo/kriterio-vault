"""Lado cliente de la sincronización: empuja el log de operaciones pendiente
(app/models/sync.py:SyncLog) al servidor central configurado. No requiere
conexión permanente — si falla, se reintenta en el siguiente ciclo con las
mismas entradas (nada se marca `sincronizado` hasta confirmar el envío)."""
import json
import os

import requests
from sqlalchemy.orm import Session

from app.models.sync import SyncLog

LOTE_MAXIMO = 200
TIMEOUT_SEGUNDOS = 30


def _config_servidor():
    url = os.getenv("SYNC_SERVER_URL")
    api_key = os.getenv("SYNC_API_KEY")
    return url, api_key


def sincronizar_con_servidor(db: Session) -> dict:
    url, api_key = _config_servidor()
    if not url or not api_key:
        return {"estado": "sin_configurar"}

    pendientes = (db.query(SyncLog)
                  .filter(SyncLog.sincronizado == False)  # noqa: E712
                  .order_by(SyncLog.id)
                  .limit(LOTE_MAXIMO)
                  .all())
    if not pendientes:
        return {"estado": "sin_pendientes", "enviados": 0}

    items = [{
        "tabla": p.tabla,
        "entidad_uuid": p.entidad_uuid,
        "operacion": p.operacion,
        "empresa_id": p.empresa_id,
        "payload": json.loads(p.payload) if p.payload else None,
    } for p in pendientes]

    try:
        resp = requests.post(
            f"{url.rstrip('/')}/api/sync/push",
            json=items,
            headers={"X-Sync-Key": api_key},
            timeout=TIMEOUT_SEGUNDOS,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"estado": "error_conexion", "detalle": str(e)}

    resultados = resp.json()["resultados"]
    aplicados = 0
    errores = []
    for p, r in zip(pendientes, resultados):
        if r["ok"]:
            p.sincronizado = True
            aplicados += 1
        else:
            errores.append({"tabla": p.tabla, "entidad_uuid": p.entidad_uuid, "error": r.get("error")})
    db.commit()

    return {"estado": "ok", "enviados": len(pendientes), "aplicados": aplicados, "errores": errores}
