from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class DimRegionBase(BaseModel):
    name: str
    description: Optional[str] = None
class DimRegionCreate(DimRegionBase):
    region_id: int
class DimRegionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
class DimRegion(DimRegionBase):
    model_config = ConfigDict(from_attributes=True)
    region_id: int

class DimPaisBase(BaseModel):
    name: str
    region_id: int
class DimPaisCreate(DimPaisBase):
    country_id: int
class DimPaisUpdate(BaseModel):
    name: Optional[str] = None
    region_id: Optional[int] = None
class DimPais(DimPaisBase):
    model_config = ConfigDict(from_attributes=True)
    country_id: int

class DimCategoriaBase(BaseModel):
    name: str
    description: Optional[str] = None
class DimCategoriaCreate(DimCategoriaBase):
    category_id: int
class DimCategoriaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
class DimCategoria(DimCategoriaBase):
    model_config = ConfigDict(from_attributes=True)
    category_id: int

class DimCanalBase(BaseModel):
    name: str
    description: Optional[str] = None
class DimCanalCreate(DimCanalBase):
    channel_id: int
class DimCanalUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
class DimCanal(DimCanalBase):
    model_config = ConfigDict(from_attributes=True)
    channel_id: int

class FactVentaBase(BaseModel):
    order_id: str
    fecha_id: Optional[str] = None
    units_sold: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    unit_cost: float = Field(ge=0)
    total_revenue: float = 0
    total_cost: float = 0
    total_profit: float = 0
class FactVentaCreate(FactVentaBase):
    venta_id: int
class FactVentaUpdate(BaseModel):
    order_id: Optional[str] = None
    units_sold: Optional[int] = Field(default=None, ge=1)
    unit_price: Optional[float] = None
    total_profit: Optional[float] = None
class FactVenta(FactVentaBase):
    model_config = ConfigDict(from_attributes=True)
    venta_id: int
