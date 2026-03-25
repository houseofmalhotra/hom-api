from pydantic import BaseModel
from datetime import datetime

class InvoiceBase(BaseModel):
    order_id: int
    invoice_number: str
    total_amount: float

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceResponse(InvoiceBase):
    id: int
    issued_at: datetime

    class Config:
        from_attributes = True