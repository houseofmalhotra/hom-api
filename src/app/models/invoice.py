from sqlalchemy import Column, BigInteger, String, Float, DateTime
from datetime import datetime
from src.app.core.database import Base

class Invoice(Base):
    __tablename__ = "invoices"
    id  = Column(BigInteger, primary_key=True, index=True)
    order_id = Column(BigInteger, index=True)
    invoice_number = Column(String(100), index=True, unique=True)
    total_amount = Column(Float, index=True)
    issued_at = Column(DateTime, index=True, default=datetime.utcnow)