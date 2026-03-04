from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    batch_number: str


class PrimaryOrderCreate(BaseModel):
    order_number: str
    type: str
    from_entity_id: int
    to_entity_id: int
    items: List[OrderItemBase]

class SecondaryOrderCreate(BaseModel):
    retailer_id: int
    distributor_id: int
    items: List[OrderItemBase]

class TertiaryOrderCreate(BaseModel):
    end_consumer_id: int
    fulfilled_by_retailer_id: int
    product_id: int
    quantity: int
    batch_number : str
    assigned_so_id: int

class DispatchPayload(BaseModel):
    transporter_name: str
    vehicle_number: str
    lr_number: str
    driver_phone: Optional[str] = None
    estimated_arrival_date: date

class OrderItemRead(BaseModel):
    product_id: int
    quantity_cases: int
    batch_number: Optional[str] = None

    class Config:
        from_attributes = True


class ShipmentRead(BaseModel):
    transporter_name: str
    vehicle_number: str
    lr_number: str
    estimated_arrival_date: date
    driver_phone: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class PrimaryOrderRead(BaseModel):
    id: int
    order_number: str
    status: str
    ss_id: Optional[int] = None
    to_entity_id: Optional[int] = None
    items: List[OrderItemRead] = []
    shipment: Optional[ShipmentRead] = None

    class Config:
        from_attributes = True

class PrimaryOrderRead(BaseModel):
    id: int
    order_number: str
    status: str
    type: str
    from_entity_id: int
    ss_id: Optional[int] = None
    to_entity_id: Optional[int] = None
    items: List[OrderItemRead] = []
    shipment: Optional[ShipmentRead] = None

class SecondaryOrderRead(BaseModel):
    id: int
    distributor_id: int
    retailer_id: int
    status: str
    items: List[OrderItemRead] = []

    class Config:
        from_attributes = True


class SecondaryDispatchCreate(BaseModel):
    transport_name : str
    vehicle_number : str
    lr_number : str
    estimated_arrival_date: date
    driver_phone: str | None = None

