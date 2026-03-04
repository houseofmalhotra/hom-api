from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, ForeignKey, Date
from src.app.core.database import Base


class TradeScheme(Base):
    __tablename__ = "trade_schemes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    scheme_name = Column(String(100), nullable=False)


    min_qty = Column(Integer, nullable=False)
    discount_percent = Column(DECIMAL(5, 2), default=0.00)
    free_qty = Column(Integer, default=0)


    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)