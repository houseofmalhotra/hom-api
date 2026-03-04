from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from typing import Optional


class FactoryCreate(BaseModel):
    name: str
    
class StockUpdate(BaseModel):
    product_id: int
    quantity_change: int
    transaction_type: str
    reference_document: str
    batch_number : str

class StockLedgerRead(BaseModel):
    id: int
    created_at: datetime
    entity_type: str
    entity_id: int
    product_id: int
    quantity_change: int
    batch_number: str
    transaction_type: str
    reference_document: str
    closing_balance: int
    model_config = ConfigDict(from_attributes=True)

class ProductionLogCreate(BaseModel):
    product_id: int
    factory_id: int
    quantity_produced: int
    batch_number: str
    production_date: date