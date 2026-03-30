from typing import List
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional

class WIPConsumption(BaseModel):
    wip_id: int
    qty_to_consume: Decimal

class ProductionRunCreate(BaseModel):
    idempotency_key: str
    stage_id: int
    factory_id: int
    operator_id: int
    product_id: int
    consumed_wips: List[WIPConsumption]
    good_output_qty: Decimal
    scrap_qty: Decimal

class RawMaterialIntake(BaseModel):
    factory_id: int
    product_id: int
    vendor_lot_number: str
    invoice_qty: Decimal
    uom: str = "KG"
    operator_id: Optional[int] = None
    custom_batch_number: Optional[str] = None