from fastapi import FastAPI
from api.crud_factory import make_crud_router
from api.schemas import *
from config.settings import settings

app = FastAPI(title="GLOBTRADE API CRUD", version="1.0.0")
app.include_router(make_crud_router("/dimensiones/regiones", "dim_region", "region_id", DimRegion, DimRegionCreate, DimRegionUpdate, "Región", int))
app.include_router(make_crud_router("/dimensiones/paises", "dim_pais", "country_id", DimPais, DimPaisCreate, DimPaisUpdate, "País", int))
app.include_router(make_crud_router("/dimensiones/categorias", "dim_categoria", "category_id", DimCategoria, DimCategoriaCreate, DimCategoriaUpdate, "Categoría", int))
app.include_router(make_crud_router("/dimensiones/canales", "dim_canal", "channel_id", DimCanal, DimCanalCreate, DimCanalUpdate, "Canal", int))
app.include_router(make_crud_router("/hechos/ventas", "fact_ventas", "venta_id", FactVenta, FactVentaCreate, FactVentaUpdate, "Hechos", int))

@app.get("/health")
def health():
    return {"status": "ok", "empresa": "GLOBTRADE", "motor": "MongoDB", "estudiante": "Pozo", "data": str(settings.data_parquet_dir)}
