from sqlalchemy import Column, Integer, String, DECIMAL, ForeignKey, BigInteger, Date
from sqlalchemy.orm import relationship
from src.app.core.database import Base


class SecondaryOrder(Base):
    __tablename__ = "secondary_order"

    id = Column(BigInteger, primary_key=True, index=True)
    order_date = Column(Date)
    retailer_id = Column(Integer, ForeignKey("retailer.id"))
    distributor_id = Column(Integer, ForeignKey("distributor.id"))
    so_user_id = Column(BigInteger, ForeignKey("users.id"))
    total_amount = Column(DECIMAL(12, 2))
    status = Column(String(50))

    items = relationship("SecondaryOrderItems", back_populates="order")

    zone_id = Column(Integer, index=True, nullable=True)
    region_id = Column(Integer, index=True, nullable=True)
    state_id = Column(Integer, index=True, nullable=True)
    area_id = Column(Integer, index=True, nullable=True)
    territory_id = Column(Integer, index=True, nullable=True)

class SecondaryOrderItems(Base):
    __tablename__ = "secondary_order_items"

    id = Column(BigInteger, primary_key=True, index=True)
    secondary_order_id = Column(BigInteger, ForeignKey("secondary_order.id"))
    product_id = Column(Integer, ForeignKey("product_master.id"))
    quantity_units = Column(Integer)
    batch_number = Column(String(50), nullable=False)
    order = relationship("SecondaryOrder", back_populates="items")