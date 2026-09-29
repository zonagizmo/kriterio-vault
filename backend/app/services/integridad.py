"""Integridad referencial multiempresa (REL-001).

Un recurso solo puede referenciar entidades (cliente / proveedor / banco) de su
misma empresa. La validación vive en la capa de servicio para que cubra tanto la
API como el replay de sincronización (`sync_replay`), que llama a estas mismas
funciones sin pasar por HTTP.

El valor aceptado es `id` o `numero`: el frontend envía el `numero` de la entidad
dentro de su empresa (AutocompleteEntidad) y los datos antiguos guardaron el `id`.
El mensaje es único para id inexistente y para recurso de otra empresa: no se
revela qué existe (coherente con el 404 uniforme de `exigir_empresa`).
"""
from sqlalchemy import or_
from sqlalchemy.orm import Session


class ReferenciaInvalida(ValueError):
    """FK inexistente o de otra empresa. `sync_replay` la captura como ValueError."""


def exigir_fk_empresa(db: Session, modelo, valor, empresa_id, etiqueta: str) -> None:
    """404 (vía ReferenciaInvalida) si `valor` no designa una entidad de `empresa_id`."""
    if valor is None:
        return
    coincide = db.query(modelo.id).filter(
        modelo.empresa_id == empresa_id,
        or_(modelo.id == valor, modelo.numero == valor),
    ).first()
    if coincide is None:
        raise ReferenciaInvalida(f"{etiqueta} no encontrado")
