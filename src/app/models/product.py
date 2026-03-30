from sqlalchemy import Column, Integer, String, Numeric, Boolean, Text
from src.app.core.database import Base


class ProductMaster(Base):
    __tablename__ = "product_master"

    id = Column(Integer, primary_key=True, index=True)
    sku_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    description = Column(Text)

    item_type = Column(String(50), default="FG")  # 'FG', 'RM', 'WIP'
    uom = Column(String(50), default="BOXES")  # FG Defaults to BOXES

    mrp = Column(Numeric(10, 2), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)
    gst_percent = Column(Integer, default=18)

    # Legacy generic column (kept so we don't break old order code)
    units_per_case = Column(Integer, default=1)

    blades_per_tuck = Column(Integer, default=5)  # Allowed: 5, 6, 10, 12
    tucks_per_box = Column(Integer, default=2000)  # Auto-calculated by backend
    blades_per_box = Column(Integer, default=10000)  # Allowed: 10000, 12000
    box_type = Column(String(50), default="Standard")  # "Standard Pack", "Saloon Pack"

    is_active = Column(Boolean, default=True)