from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.facturacion import ArticuloRead, ArticuloCreate, ArticuloUpdate
from app.services import articulos as svc
from typing import Optional

router = APIRouter(prefix="/api/articulos", tags=["articulos"])


@router.get("", response_model=dict)
def listar(
    empresa_id: int,
    q: str = Query(""),
    familia: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    items, total = svc.get_articulos(db, empresa_id, q, familia, skip, limit)
    return {"total": total, "items": [ArticuloRead.model_validate(i) for i in items]}


@router.get("/{articulo_id}", response_model=ArticuloRead)
def obtener(articulo_id: int, db: Session = Depends(get_db)):
    a = svc.get_articulo(db, articulo_id)
    if not a:
        raise HTTPException(404, "Artículo no encontrado")
    return a


@router.post("", response_model=ArticuloRead, status_code=201)
def crear(data: ArticuloCreate, db: Session = Depends(get_db)):
    return svc.create_articulo(db, data)


@router.put("/{articulo_id}", response_model=ArticuloRead)
def actualizar(articulo_id: int, data: ArticuloUpdate, db: Session = Depends(get_db)):
    a = svc.update_articulo(db, articulo_id, data)
    if not a:
        raise HTTPException(404, "Artículo no encontrado")
    return a


@router.delete("/{articulo_id}", status_code=204)
def eliminar(articulo_id: int, db: Session = Depends(get_db)):
    if not svc.delete_articulo(db, articulo_id):
        raise HTTPException(404, "Artículo no encontrado")
