from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger, Date, Boolean
from src.app.core.database import Base


class EndConsumer(Base):
    __tablename__ = "end_consumer"
    id = Column(Integer, primary_key=True, index=True)
    territory_id = Column(Integer, ForeignKey("territory.id"))
    name = Column(String(255))
    type = Column(String(50))
    mobile_number = Column(String(15))
    is_active = Column(Boolean, default=True)
    contact_person = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)


class TertiaryOrder(Base):
    __tablename__ = "tertiary_order"
    id = Column(BigInteger, primary_key=True, index=True)
    request_date = Column(Date)
    end_consumer_id = Column(Integer, ForeignKey("end_consumer.id"))
    assigned_so_id = Column(BigInteger, ForeignKey("users.id"))
    fulfilled_by_retailer_id = Column(Integer, ForeignKey("retailer.id"))
    batch_number = Column(String(50), nullable=False)
    product_id = Column(Integer, ForeignKey("product_master.id"))
    quantity = Column(Integer)
    status = Column(String(50))
    zone_id = Column(Integer, index=True, nullable=True)
    region_id = Column(Integer, index=True, nullable=True)
    state_id = Column(Integer, index=True, nullable=True)
    area_id = Column(Integer, index=True, nullable=True)
    territory_id = Column(Integer, index=True, nullable=True)


