from pydantic import BaseModel, ConfigDict
from typing import Optional
from decimal import Decimal


class ProductBase(BaseModel):
    sku_code: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None

    item_type: Optional[str] = "FG"
    uom: Optional[str] = "BOXES"

    mrp: Decimal
    base_price: Decimal
    gst_percent: int = 18
    units_per_case: int = 1

    # ==========================================
    # 📦 STRICT PACKAGING LOGIC FIELDS
    # ==========================================
    blades_per_tuck: Optional[int] = 5
    tucks_per_box: Optional[int] = 2000
    blades_per_box: Optional[int] = 10000
    box_type: Optional[str] = "Standard Pack"

    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku_code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None

    item_type: Optional[str] = None
    uom: Optional[str] = None

    mrp: Optional[Decimal] = None
    base_price: Optional[Decimal] = None
    gst_percent: Optional[int] = None
    units_per_case: Optional[int] = None

    # ==========================================
    # 📦 STRICT PACKAGING LOGIC FIELDS
    # ==========================================
    blades_per_tuck: Optional[int] = None
    tucks_per_box: Optional[int] = None
    blades_per_box: Optional[int] = None
    box_type: Optional[str] = None

    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)