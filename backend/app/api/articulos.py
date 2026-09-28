from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.auth import get_current_user
from app.services.permissions import require_method_permission, empresa_query, exigir_empresa, puede_ver_empresa
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.facturacion import ArticuloRead, ArticuloCreate, ArticuloUpdate
from app.services import articulos as svc
from typing import Optional
router = APIRouter(prefix="/api/articulos", tags=["articulos"], dependencies=[Depends(require_method_permission)])


@router.get("", response_model=dict)
def listar(
    empresa_id: int = Depends(empresa_query),
    q: str = Query(""),
    familia: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    items, total = svc.get_articulos(db, empresa_id, q, familia, skip, limit)
    return {"total": total, "items": [ArticuloRead.model_validate(i) for i in items]}


@router.get("/{articulo_id}", response_model=ArticuloRead)
def obtener(articulo_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    a = svc.get_articulo(db, articulo_id)
    if not a:
        raise HTTPException(404, "Artículo no encontrado")
    exigir_empresa(user, a)
    return a


@router.post("", response_model=ArticuloRead, status_code=201)
def crear(data: ArticuloCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    exigir_empresa(user, data)
    return svc.create_articulo(db, data)


@router.put("/{articulo_id}", response_model=ArticuloRead)
def actualizar(articulo_id: int, data: ArticuloUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    previo = svc.get_articulo(db, articulo_id)
    if not previo:
        raise HTTPException(404, "Artículo no encontrado")
    exigir_empresa(user, previo)
    exigir_empresa(user, data)
    a = svc.update_articulo(db, articulo_id, data)
    if not a:
        raise HTTPException(404, "Artículo no encontrado")
    return a


@router.delete("/{articulo_id}", status_code=204)
def eliminar(articulo_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    actual = svc.get_articulo(db, articulo_id)
    if not actual:
        raise HTTPException(status_code=404, detail="Articulo no encontrado")
    exigir_empresa(user, actual)
    if not svc.delete_articulo(db, articulo_id):
        raise HTTPException(404, "Artículo no encontrado")
