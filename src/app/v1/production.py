from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.app.core.database import get_db
from src.app.schemas.production import RawMaterialIntake, ProductionRunCreate
from src.app.services.production_service import intake_raw_material, execute_production_run
from src.app.models.production_core import WIPInventory
from src.app.models.production_core import FactoryLedger
from sqlalchemy import desc
from src.app.models.product import ProductMaster
from src.app.services.production_service import reverse_production_run

router = APIRouter()


@router.post("/intake-raw-material")
def receive_raw_material(payload: RawMaterialIntake, db: Session = Depends(get_db)):
    """Receives raw steel coils from vendors and creates the initial WIP entry for Stage 1."""
    return intake_raw_material(db, payload)


@router.post("/execute-run")
def run_production_stage(payload: ProductionRunCreate, db: Session = Depends(get_db)):
    """Executes a single manufacturing stage, consumes WIP, and generates the next stage's WIP."""
    return execute_production_run(db, payload)


@router.get("/wip/available/{stage_id}")
def get_available_wip_for_stage(stage_id: int, db: Session = Depends(get_db)):
    """Fetches all available Work-in-Progress inventory queued for a specific stage."""

    wip_records = db.query(WIPInventory).filter(
        WIPInventory.current_stage_id == stage_id,
        WIPInventory.status == "AVAILABLE",
        WIPInventory.current_qty > 0
    ).order_by(WIPInventory.created_at.asc()).all()

    return [
        {
            "id": wip.id,
            "batch_number": wip.batch_number,
            "vendor_lot_number": wip.vendor_lot_number,
            "current_qty": float(wip.current_qty),
            "uom": wip.uom,
            "status": wip.status
        }
        for wip in wip_records
    ]


@router.get("/ledger/{factory_id}")
def get_factory_ledger(factory_id: int, db: Session = Depends(get_db)):
    """Fetches the internal WIP movement history with actual Product Names."""

    # Perform a JOIN between FactoryLedger and ProductMaster
    records = db.query(FactoryLedger, ProductMaster).join(
        ProductMaster, FactoryLedger.product_id == ProductMaster.id
    ).filter(
        FactoryLedger.factory_id == factory_id
    ).order_by(desc(FactoryLedger.created_at)).limit(200).all()

    return [
        {
            "id": ledger.id,
            "date": ledger.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "product_name": product.name,
            "sku": product.sku_code,  # 🚨 FIXED: Changed from .sku to .sku_code
            "batch_number": ledger.batch_number,
            "stage_id": ledger.stage_id,
            "transaction_type": ledger.transaction_type,
            "reference_document": ledger.reference_document,
            "quantity_change": float(ledger.quantity_change),
            "closing_balance": float(ledger.closing_balance)
        }
        for ledger, product in records
    ]

@router.post("/reverse-run/{run_id}")
def api_reverse_production_run(run_id: int, operator_id: int = 1, db: Session = Depends(get_db)):
    """
    Cancels a production run.
    Restores the consumed WIP, removes the produced WIP/FG, and logs the reversal in the ledger.
    """
    return reverse_production_run(db=db, run_id=run_id, operator_id=operator_id)