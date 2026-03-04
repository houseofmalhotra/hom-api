from sqlalchemy import Column, Integer, String, Numeric, Boolean, Text
from src.app.core.database import Base


class ProductMaster(Base):
    __tablename__ = "product_master"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)

    sku_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(String(100))
    description = Column(Text, nullable=True)

    mrp = Column(Numeric(10, 2), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)
    gst_percent = Column(Integer, default=18)

    units_per_case = Column(Integer, default=1, nullable=False)

    is_active = Column(Boolean, default=True)