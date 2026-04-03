from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, BigInteger, DateTime, func
from sqlalchemy.orm import relationship
from src.app.core.database import Base
from sqlalchemy import Boolean
from sqlalchemy import Boolean
from sqlalchemy import Boolean


class ProductPackaging(Base):
    __tablename__ = "product_packaging"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    packaging_type = Column(String(50))
    contains_qty = Column(Integer)
    contains_uom = Column(String(50))
    inner_product_id = Column(Integer, ForeignKey("product_master.id"), nullable=True)

class BOMMaster(Base):
    __tablename__ = "bom_master"
    id = Column(Integer, primary_key=True, index=True)
    output_product_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    stage_id = Column(Integer, ForeignKey("production_stage.id"), nullable=False)
    base_qty = Column(Integer, default=1)

class BOMItem(Base):
    __tablename__ = "bom_item"
    id = Column(Integer, primary_key=True, index=True)
    bom_master_id = Column(Integer, ForeignKey("bom_master.id"), nullable=False)
    input_product_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    expected_qty = Column(Numeric(12, 3), nullable=False)

class ScrapReason(Base):
    __tablename__ = "scrap_reason"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True)
    description = Column(String(255))
    is_recoverable = Column(Boolean, default=False)

class ProductionRunScrap(Base):
    __tablename__ = "production_run_scrap"
    id = Column(BigInteger, primary_key=True, index=True)
    run_id = Column(BigInteger, ForeignKey("production_run.id"), nullable=False)
    reason_id = Column(Integer, ForeignKey("scrap_reason.id"), nullable=False)
    qty = Column(Numeric(12, 3), nullable=False)


class ProductionStage(Base):
    """Defines the 15 manufacturing steps (Master Data)"""
    __tablename__ = "production_stage"

    id = Column(Integer, primary_key=True, index=True)
    sequence_number = Column(Integer, nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    input_uom = Column(String(20), nullable=False)
    output_uom = Column(String(20), nullable=False)

class WIPInventory(Base):
    """The Asynchronous Buffer: Holds materials waiting for the next stage"""
    __tablename__ = "wip_inventory"

    id = Column(BigInteger, primary_key=True, index=True)
    factory_id = Column(Integer, ForeignKey("factory_master.id"))
    product_id = Column(Integer, ForeignKey("product_master.id"))
    current_stage_id = Column(Integer, ForeignKey("production_stage.id"))

    batch_number = Column(String(50), index=True, nullable=False)
    vendor_lot_number = Column(String(100), nullable=True)

    current_qty = Column(Numeric(12, 3), default=0)
    uom = Column(String(20), nullable=False)
    status = Column(String(20), default="AVAILABLE")

    created_at = Column(DateTime, server_default=func.now())


class ProductionRun(Base):
    """The Transaction Ledger: Replaces DailyProductionLog for internal routing"""
    __tablename__ = "production_run"

    id = Column(BigInteger, primary_key=True, index=True)

    # ADD THIS: Prevents double-clicks/latency duplicates
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)

    stage_id = Column(Integer, ForeignKey("production_stage.id"), nullable=False)
    factory_id = Column(Integer, ForeignKey("factory_master.id"), nullable=False)
    operator_id = Column(Integer, nullable=True)

    output_batch_number = Column(String(50), nullable=False)
    product_id = Column(Integer, ForeignKey("product_master.id"))

    input_qty = Column(Numeric(12, 3), nullable=False)
    good_output_qty = Column(Numeric(12, 3), nullable=False)

    total_material_cost = Column(Numeric(12, 2), default=0.00)
    cost_per_unit_produced = Column(Numeric(12, 4), default=0.0000)


    created_at = Column(DateTime, server_default=func.now())
    scrap_qty = Column(Numeric(12, 3), default=0)
    is_reversed = Column(Boolean, default=False, nullable=False)


class FactoryLedger(Base):
    """Dedicated ledger for internal factory/WIP movements"""
    __tablename__ = "factory_ledger"

    id = Column(BigInteger, primary_key=True, index=True)
    factory_id = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, nullable=False)
    batch_number = Column(String(50), nullable=False, index=True)

    stage_id = Column(Integer, nullable=True)
    transaction_type = Column(String(50), nullable=False)
    reference_document = Column(String(100), nullable=True)

    quantity_change = Column(Numeric(12, 3), nullable=False)
    closing_balance = Column(Numeric(12, 3), nullable=False)

    created_at = Column(DateTime, server_default=func.now())


class RunConsumption(Base):
    """Mapping table for Merging (consuming 3 WIP coils into 1 run)"""
    __tablename__ = "run_consumption"

    id = Column(BigInteger, primary_key=True, index=True)
    run_id = Column(BigInteger, ForeignKey("production_run.id"))
    consumed_wip_id = Column(BigInteger, ForeignKey("wip_inventory.id"))
    qty_consumed = Column(Numeric(12, 3), nullable=False)

class ProductRouting(Base):
    """Maps a specific product to its unique sequence of manufacturing stages"""
    __tablename__ = "product_routing"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    stage_id = Column(Integer, ForeignKey("production_stage.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    is_final_step = Column(Boolean, default=False)
    output_product_id = Column(Integer, ForeignKey("product_master.id"), nullable=True)