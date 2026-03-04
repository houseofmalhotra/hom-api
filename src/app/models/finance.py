from sqlalchemy import Column, Integer, String, DECIMAL, BigInteger, DateTime, func
from src.app.core.database import Base


class FinancialLedger(Base):
    __tablename__ = "financial_ledger"

    id = Column(BigInteger, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now())

    party_type = Column(String(50), nullable=False)
    party_id = Column(Integer, nullable=False)

    transaction_type = Column(String(50), nullable=False)
    reference_document = Column(String(100))

    credit_amount = Column(DECIMAL(10,2), nullable=False)
    debit_amount = Column(DECIMAL(12, 2), default=0.00)
    closing_balance = Column(DECIMAL(12, 2), nullable=False)
    remarks = Column(String(255), nullable=True)

    zone_id = Column(Integer, index=True, nullable=True)
    region_id = Column(Integer, index=True, nullable=True)
    state_id = Column(Integer, index=True, nullable=True)
    area_id = Column(Integer, index=True, nullable=True)
    territory_id = Column(Integer, index=True, nullable=True)