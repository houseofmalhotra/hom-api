from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from pydantic import ConfigDict

class ProductUpdate(BaseModel):
    sku_code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    mrp: Optional[Decimal] = None
    base_price: Optional[Decimal] = None
    gst_percent: Optional[int] = None
    units_per_case: Optional[int] = None
    is_active: Optional[bool] = None

class ProductBase(BaseModel):
    sku_code: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    mrp: Decimal
    base_price: Decimal
    gst_percent: int = 18
    units_per_case: int = 1
    is_active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)