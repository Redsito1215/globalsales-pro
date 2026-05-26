from typing import Any, Callable
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from api.mongo import col

def make_crud_router(prefix, collection, pk_field, model, create_model, update_model, tag, id_type=lambda x: x):
    router = APIRouter(prefix=prefix, tags=[tag])
    @router.get("", response_model=list[model])
    def listar(limit: int = Query(100, le=500), offset: int = 0):
        return list(col(collection).find({}, {"_id": 0}).skip(offset).limit(limit))
    @router.get("/{item_id}", response_model=model)
    def obtener(item_id: str):
        doc = col(collection).find_one({pk_field: id_type(item_id)}, {"_id": 0})
        if not doc: raise HTTPException(404)
        return doc
    @router.post("", response_model=model, status_code=201)
    def crear(payload: create_model):
        data = payload.model_dump()
        if col(collection).find_one({pk_field: data[pk_field]}): raise HTTPException(409)
        col(collection).insert_one(data)
        return col(collection).find_one({pk_field: data[pk_field]}, {"_id": 0})
    @router.put("/{item_id}", response_model=model)
    def actualizar(item_id: str, payload: update_model):
        data = payload.model_dump(exclude_unset=True)
        if not col(collection).update_one({pk_field: id_type(item_id)}, {"$set": data}).matched_count:
            raise HTTPException(404)
        return col(collection).find_one({pk_field: id_type(item_id)}, {"_id": 0})
    @router.delete("/{item_id}", status_code=204)
    def eliminar(item_id: str):
        if not col(collection).delete_one({pk_field: id_type(item_id)}).deleted_count:
            raise HTTPException(404)
    return router
