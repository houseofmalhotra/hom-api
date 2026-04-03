from sqlalchemy import Column, Integer, String, Numeric, Boolean, Text
from src.app.core.database import Base


class ProductMaster(Base):
    __tablename__ = "product_master"

    id = Column(Integer, primary_key=True, index=True)
    sku_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    description = Column(Text)

    standard_cost = Column(Numeric(12, 4), default=0.0000)

    item_type = Column(String(50), default="FG")
    uom = Column(String(50), default="BOXES")

    mrp = Column(Numeric(10, 2), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)
    gst_percent = Column(Integer, default=18)

    is_active = Column(Boolean, default=True)