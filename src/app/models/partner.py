from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DECIMAL, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.app.core.database import Base


class SuperStockist(Base):
    __tablename__ = "super_stockist"

    id = Column(Integer, primary_key=True, index=True)
    firm_name = Column(String(100), nullable=False)
    contact_person = Column(String(100))
    contact_number = Column(String(20))
    gstin = Column(String(15), unique=True)
    is_active = Column(Boolean, default=True)

    zone_id = Column(Integer, ForeignKey("zone.id"))
    user_id = Column(BigInteger, ForeignKey("users.id"), unique=True, nullable=True)

    outstanding_balance = Column(DECIMAL(12, 2), default=0.00)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    zone = relationship("Zone")
    user = relationship("User")
    distributor = relationship("Distributor", back_populates="parent_ss")


class Distributor(Base):
    __tablename__ = "distributor"

    id = Column(Integer, primary_key=True, index=True)
    firm_name = Column(String(100), nullable=False)
    contact_person = Column(String(100))
    contact_number = Column(String(20))
    gstin = Column(String(15), unique=True)
    is_active = Column(Boolean, default=True)

    zone_id = Column(Integer, ForeignKey("zone.id"), nullable=True)
    state_id = Column(Integer, ForeignKey("state.id"))

    parent_ss_id = Column(Integer, ForeignKey("super_stockist.id"), nullable=True)
    is_direct_party = Column(Boolean, default=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), unique=True, nullable=True)

    outstanding_balance = Column(DECIMAL(12, 2), default=0.00)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    state = relationship("State")
    zone = relationship("Zone")
    parent_ss = relationship("SuperStockist", back_populates="distributor")
    user = relationship("User")
    retailer = relationship("Retailer", back_populates="linked_distributor")


class Retailer(Base):
    __tablename__ = "retailer"

    id = Column(Integer, primary_key=True, index=True)
    shop_name = Column(String(100), nullable=False)
    contact_person = Column(String(100))
    contact_number = Column(String(20))
    gstin = Column(String(15), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)

    zone_id = Column(Integer, ForeignKey("zone.id"), nullable=True)
    state_id = Column(Integer, ForeignKey("state.id"), nullable=True)
    region_id = Column(Integer, ForeignKey("region.id"), nullable=True)
    area_id = Column(Integer, ForeignKey("area.id"), nullable=True)
    territory_id = Column(Integer, ForeignKey("territory.id"))

    linked_distributor_id = Column(Integer, ForeignKey("distributor.id"), nullable=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), unique=True, nullable=True)

    outstanding_balance = Column(DECIMAL(12, 2), default=0.00)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    territory = relationship("Territory")
    area = relationship("Area")
    region = relationship("Region")
    state = relationship("State")
    zone = relationship("Zone")
    linked_distributor = relationship("Distributor", back_populates="retailer")
    user = relationship("User")