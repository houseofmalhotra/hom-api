from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.app.core.database import get_db
from src.app.schemas.production import RawMaterialIntake, ProductionRunCreate
from src.app.services.production_service import (
    intake_raw_material,
    execute_production_run,
    reverse_production_run
)
from src.app.models.production_core import BOMMaster, BOMItem
from src.app.models.production_core import WIPInventory, FactoryLedger, ProductionStage, ScrapReason
from src.app.core.security import check_permissions
from src.app.models.user import User
from src.app.models.production_core import WIPInventory, FactoryLedger
from src.app.models.product import ProductMaster
from src.app.models.inventory import ScrapInventory
from pydantic import BaseModel
from typing import List

router = APIRouter()


@router.post("/intake-raw-material")
def receive_raw_material(payload: RawMaterialIntake, db: Session = Depends(get_db),current_user: User = Depends(check_permissions("manage_production"))):
    """Receives raw steel coils from vendors and creates the initial WIP entry for Stage 1."""
    return intake_raw_material(db, payload)


@router.post("/execute-run")
def run_production_stage(payload: ProductionRunCreate, db: Session = Depends(get_db),current_user: User = Depends(check_permissions("manage_production"))):
    """Executes a single manufacturing stage, consumes WIP, and generates the next stage's WIP."""
    return execute_production_run(db, payload)


@router.get("/wip/available/{stage_id}")
def get_available_wip_for_stage(stage_id: int, db: Session = Depends(get_db),current_user: User = Depends(check_permissions("view_production"))):
    """Fetches all available Work-in-Progress inventory queued for a specific stage."""

    wip_records = db.query(WIPInventory, ProductMaster).join(
        ProductMaster, WIPInventory.product_id == ProductMaster.id
    ).filter(
        WIPInventory.current_stage_id == stage_id,
        WIPInventory.status == "AVAILABLE",
        WIPInventory.current_qty > 0
    ).order_by(WIPInventory.created_at.asc()).all()

    return [
        {
            "id": wip.id,
            "product_id": wip.product_id,
            "product_name": product.name,
            "batch_number": wip.batch_number,
            "vendor_lot_number": wip.vendor_lot_number,
            "current_qty": float(wip.current_qty),
            "uom": wip.uom,
            "blades_per_tuck": product.blades_per_tuck or 5,
            "tucks_per_box": product.tucks_per_box or 2000,
            "status": wip.status
        }
        for wip, product in wip_records
    ]


@router.get("/ledger/{factory_id}")
def get_factory_ledger(factory_id: int, db: Session = Depends(get_db),current_user: User = Depends(check_permissions("view_production"))):
    """Fetches the internal WIP movement history with actual Product Names."""

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
            "sku": product.sku_code,
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
def api_reverse_production_run(run_id: int, operator_id: int = 1, db: Session = Depends(get_db),current_user: User = Depends(check_permissions("manage_production"))):
    """
    Cancels a production run.
    Restores the consumed WIP, removes the produced WIP/FG, and logs the reversal in the ledger.
    """
    return reverse_production_run(db=db, run_id=run_id, operator_id=operator_id)


@router.get("/wip/factory/{factory_id}")
def get_factory_wip_stock(factory_id: int, db: Session = Depends(get_db),current_user: User = Depends(check_permissions("view_production"))):
    """Fetches all active WIP sitting on the factory floor."""
    records = db.query(WIPInventory, ProductMaster).join(
        ProductMaster, WIPInventory.product_id == ProductMaster.id
    ).filter(
        WIPInventory.factory_id == factory_id,
        WIPInventory.current_qty > 0
    ).all()

    return [
        {
            "id": w.id,
            "product_id": w.product_id,
            "product_name": p.name,
            "sku_code": p.sku_code,
            "batch_number": w.batch_number,
            "current_qty": float(w.current_qty),
            "uom": w.uom
        }
        for w, p in records
    ]


@router.get("/scrap/factory/{factory_id}")
def get_factory_scrap_stock(factory_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_permissions("view_production"))
):
    """Fetches all accumulated scrap waste for a factory."""
    records = db.query(ScrapInventory, ProductMaster).join(
        ProductMaster, ScrapInventory.product_id == ProductMaster.id
    ).filter(
        ScrapInventory.factory_id == factory_id,
        ScrapInventory.current_qty > 0
    ).all()

    return [
        {
            "id": s.id,
            "product_id": s.product_id,
            "product_name": p.name,
            "sku_code": p.sku_code,
            "current_qty": float(s.current_qty),
            "uom": s.uom
        }
        for s, p in records
    ]

@router.get("/stages")
def get_production_stages(db: Session = Depends(get_db), current_user: User = Depends(check_permissions("view_production"))):
    """Fetches all 16 manufacturing stages directly from the database."""
    return db.query(ProductionStage).order_by(ProductionStage.sequence_number.asc()).all()

@router.get("/scrap-reasons")
def get_scrap_reasons(db: Session = Depends(get_db), current_user: User = Depends(check_permissions("view_production"))):
    """Fetches all valid reasons for logging scrap and defects from the database."""
    return db.query(ScrapReason).all()


class BOMItemCreate(BaseModel):
    input_product_id: int
    expected_qty: float


class BOMMasterCreate(BaseModel):
    output_product_id: int
    stage_id: int
    base_qty: float
    items: List[BOMItemCreate]


@router.get("/boms")
def get_conversion_rules(db: Session = Depends(get_db)):
    """Fetches all conversion rules (Bill of Materials)"""
    from src.app.models.production_core import BOMMaster, BOMItem

    boms = db.query(BOMMaster).all()
    result = []

    for bom in boms:
        items = db.query(BOMItem).filter(BOMItem.bom_master_id == bom.id).all()
        result.append({
            "id": bom.id,
            "output_product_id": bom.output_product_id,
            "stage_id": bom.stage_id,
            "base_qty": float(bom.base_qty),
            "items": [
                {
                    "id": i.id,
                    "input_product_id": i.input_product_id,
                    "expected_qty": float(i.expected_qty)
                } for i in items
            ]
        })
    return result


@router.post("/boms")
def create_conversion_rule(payload: BOMMasterCreate, db: Session = Depends(get_db)):
    """Creates a new Bill of Materials / Conversion recipe"""

    new_bom = BOMMaster(
        output_product_id=payload.output_product_id,
        stage_id=payload.stage_id,
        base_qty=payload.base_qty
    )
    db.add(new_bom)
    db.flush()

    for item in payload.items:
        new_item = BOMItem(
            bom_master_id=new_bom.id,
            input_product_id=item.input_product_id,
            expected_qty=item.expected_qty
        )
        db.add(new_item)

    db.commit()
    return {"message": "Conversion rule successfully created"}