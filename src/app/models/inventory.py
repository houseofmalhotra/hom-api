from sqlalchemy import Column, Integer, String, DECIMAL, ForeignKey, BigInteger, DateTime, Date, func
from src.app.core.database import Base

class StockLedger(Base):
    """The History of Truth - Every movement is recorded here"""
    __tablename__ = "stock_ledger"
    id = Column(BigInteger, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    entity_type = Column(String(255))
    entity_id = Column(Integer)
    product_id = Column(Integer, ForeignKey("product_master.id"))
    batch_number = Column(String(50), nullable=False)
    transaction_type = Column(String(255))
    reference_document = Column(String(255))
    quantity_change = Column(Integer)
    closing_balance = Column(Integer)


class FactoryInventory(Base):
    __tablename__ = "factory_inventory"
    id = Column(Integer, primary_key=True)
    factory_id = Column(Integer, ForeignKey("factory_master.id"))
    product_id = Column(Integer, ForeignKey("product_master.id"))
    batch_number = Column(String(50), nullable=False)
    current_stock_qty = Column(Integer, default=0)


class SSInventory(Base):
    __tablename__ = "ss_inventory"
    id = Column(Integer, primary_key=True)
    # PLURAL MAPPING
    ss_id = Column(Integer, ForeignKey("super_stockist.id"))
    product_id = Column(Integer, ForeignKey("product_master.id"))
    batch_number = Column(String(50), nullable=False)
    current_stock_qty = Column(Integer, default=0)


class DistributorInventory(Base):
    __tablename__ = "distributor_inventory"
    id = Column(Integer, primary_key=True)
    # PLURAL MAPPING
    distributor_id = Column(Integer, ForeignKey("distributor.id"))
    product_id = Column(Integer, ForeignKey("product_master.id"))
    batch_number = Column(String(50), nullable=False)
    current_stock_qty = Column(Integer, default=0)


class RetailerInventory(Base):
    __tablename__ = "retailer_inventory"
    id = Column(Integer, primary_key=True)
    # PLURAL MAPPING
    retailer_id = Column(Integer, ForeignKey("retailer.id"))
    product_id = Column(Integer, ForeignKey("product_master.id"))
    batch_number = Column(String(50), nullable=False)
    current_stock_qty = Column(Integer, default=0)


class FactoryMaster(Base):
    __tablename__ = "factory_master"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(100))
    batch_number = Column(String(50), nullable=False)


class InTransitInventory(Base):
    """Holds stock that has left the factory but hasn't reached the destination"""
    __tablename__ = "in_transit_inventory"
    id = Column(Integer, primary_key=True)
    order_id = Column(BigInteger, index=True)
    product_id = Column(Integer, ForeignKey("product_master.id"))
    batch_number = Column(String(50), nullable=False)
    current_stock_qty = Column(Integer, default=0)


class DailyProductionLog(Base):
    __tablename__ = "daily_production_log"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    factory_id = Column(Integer, ForeignKey("factory_master.id"), nullable=False)
    batch_number = Column(String(50), nullable=False)
    quantity_produced = Column(Integer, nullable=False)
    production_date = Column(Date, nullable=False)