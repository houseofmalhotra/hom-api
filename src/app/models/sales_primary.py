from sqlalchemy import Column, Integer, String, DECIMAL, ForeignKey, BigInteger, Date
from sqlalchemy.orm import relationship
from src.app.core.database import Base


class PrimaryOrder(Base):
    __tablename__ = "primary_order"

    id = Column(BigInteger, primary_key=True, index=True)
    order_number = Column(String(100), unique=True)
    type = Column(String(50))
    from_entity_id = Column(Integer)
    to_entity_id = Column(Integer)
    status = Column(String(50), default="Pending")

    items = relationship("PrimaryOrderItems", back_populates="order")
    invoice = relationship("PrimaryInvoice", back_populates="order", uselist=False)
    shipment = relationship("Shipment", back_populates="order", uselist=False)

    zone_id = Column(Integer, index=True, nullable=True)
    region_id = Column(Integer, index=True, nullable=True)
    state_id = Column(Integer, index=True, nullable=True)
    area_id = Column(Integer, index=True, nullable=True)
    territory_id = Column(Integer, index=True, nullable=True)


class PrimaryOrderItems(Base):
    __tablename__ = "primary_order_items"
    id = Column(BigInteger, primary_key=True, index=True)
    primary_order_id = Column(BigInteger, ForeignKey("primary_order.id"))
    product_id = Column(Integer, ForeignKey("product_master.id"))
    batch_number = Column(String(50), nullable=False)


    quantity_cases = Column(Integer, nullable=False)
    dispatched_cases = Column(Integer, default=0)
    backordered_cases = Column(Integer, default=0)
    free_cases = Column(Integer, default=0)


    final_price_per_case = Column(DECIMAL(10, 2))
    order = relationship("PrimaryOrder", back_populates="items")


class PrimaryInvoice(Base):
    __tablename__ = "primary_invoice"

    id = Column(BigInteger, primary_key=True, index=True)
    primary_order_id = Column(BigInteger, ForeignKey("primary_order.id"))
    invoice_number = Column(String(100), unique=True)
    final_amount = Column(DECIMAL(12, 2))
    invoice_date = Column(Date)

    order = relationship("PrimaryOrder", back_populates="invoice")