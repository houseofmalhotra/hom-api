from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.app.core.database import Base


class Zone(Base):
    __tablename__ = 'zone'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    states = relationship("State", back_populates="zone")


class State(Base):
    __tablename__ = 'state'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    zone_id = Column(Integer, ForeignKey("zone.id"))

    zone = relationship("Zone", back_populates="states")
    regions = relationship("Region", back_populates="state")


class Region(Base):
    __tablename__ = 'region'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    state_id = Column(Integer, ForeignKey("state.id"))

    state = relationship("State", back_populates="regions")
    areas = relationship("Area", back_populates="region")


class Area(Base):
    __tablename__ = 'area'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    region_id = Column(Integer, ForeignKey("region.id"))

    region = relationship("Region", back_populates="areas")
    territories = relationship("Territory", back_populates="area")


class Territory(Base):
    __tablename__ = 'territory'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    area_id = Column(Integer, ForeignKey("area.id"))
    area = relationship("Area", back_populates="territories")