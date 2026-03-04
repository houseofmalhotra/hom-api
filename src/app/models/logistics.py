from sqlalchemy import Column, Integer, String, Date, ForeignKey, BigInteger, DateTime, func
from sqlalchemy.orm import relationship
from src.app.core.database import Base


class Shipment(Base):
    __tablename__ = "shipment"

    id = Column(BigInteger, primary_key=True, index=True)
    primary_order_id = Column(BigInteger, ForeignKey("primary_order.id"), nullable=False)


    transporter_name = Column(String(150), nullable=False)
    vehicle_number = Column(String(50), nullable=False)
    lr_number = Column(String(100), nullable=True)
    driver_phone = Column(String(20), nullable=True)


    dispatch_date = Column(DateTime, server_default=func.now())
    estimated_arrival_date = Column(Date, nullable=True)
    actual_arrival_date = Column(Date, nullable=True)

    status = Column(String(50), default="In Transit")

    order = relationship("PrimaryOrder", back_populates="shipment")