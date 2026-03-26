from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from datetime import date
import uuid

# Import your models
from src.app.models.production_core import ProductionStage, WIPInventory, ProductionRun, RunConsumption, FactoryLedger, ProductRouting
from src.app.models.inventory import StockLedger, DailyProductionLog, FactoryInventory
from src.app.schemas.production import ProductionRunCreate, RawMaterialIntake


def execute_production_run(db: Session, run_data: ProductionRunCreate):
    try:
        # 1. IDEMPOTENCY CHECK: Block duplicate runs from double-clicks/latency
        existing_run = db.query(ProductionRun).filter(ProductionRun.idempotency_key == run_data.idempotency_key).first()
        if existing_run:
            return {"status": "success", "run_id": existing_run.id, "message": "Run already processed."}

        # 2. Fetch the current stage
        current_stage = db.query(ProductionStage).filter(ProductionStage.id == run_data.stage_id).first()
        if not current_stage:
            raise HTTPException(status_code=404, detail="Production stage not found.")

        total_input_qty = 0
        vendor_lot_to_carry_forward = None
        unified_batch_number = None

        # 3. Process Consumptions
        for consumed in run_data.consumed_wips:
            wip_record = db.query(WIPInventory).filter(WIPInventory.id == consumed.wip_id).with_for_update().first()

            if not wip_record:
                raise HTTPException(status_code=404, detail=f"WIP Batch {consumed.wip_id} not found.")
            if wip_record.current_qty < consumed.qty_to_consume:
                raise HTTPException(status_code=400, detail=f"Insufficient quantity in WIP {wip_record.batch_number}")

            # UNIFIED BATCH FIX: Inherit the batch number from the primary consumed WIP
            if not unified_batch_number:
                unified_batch_number = wip_record.batch_number
                vendor_lot_to_carry_forward = wip_record.vendor_lot_number

            # Deduct the quantity
            wip_record.current_qty -= consumed.qty_to_consume
            if wip_record.current_qty <= 0:
                wip_record.status = "CONSUMED"

            total_input_qty += consumed.qty_to_consume

            # WRITE TO NEW FACTORY LEDGER (Not StockLedger)
            ledger_consume = FactoryLedger(
                factory_id=run_data.factory_id,
                product_id=wip_record.product_id,
                batch_number=wip_record.batch_number,
                stage_id=current_stage.id,
                transaction_type="WIP_CONSUMED",
                reference_document="RUN-PENDING",
                quantity_change=-consumed.qty_to_consume,
                closing_balance=wip_record.current_qty
            )
            db.add(ledger_consume)

        # Fallback just in case no WIP was provided (though your schema requires it)
        if not unified_batch_number:
            unified_batch_number = f"BATCH-{uuid.uuid4().hex[:8].upper()}"

        # 4. Create the Production Run Ledger Entry
        new_run = ProductionRun(
            idempotency_key=run_data.idempotency_key,
            stage_id=current_stage.id,
            factory_id=run_data.factory_id,
            operator_id=run_data.operator_id,
            output_batch_number=unified_batch_number, # Unified ID
            product_id=run_data.product_id,
            input_qty=total_input_qty,
            good_output_qty=run_data.good_output_qty,
            scrap_qty=run_data.scrap_qty
        )
        db.add(new_run)
        db.flush()

        # Update reference document for ledger entries now that we have run.id
        db.query(FactoryLedger).filter(
            FactoryLedger.reference_document == "RUN-PENDING",
            FactoryLedger.factory_id == run_data.factory_id
        ).update({"reference_document": f"RUN-{new_run.id}"})

        # 5. Mapping Records
        for consumed in run_data.consumed_wips:
            run_mapping = RunConsumption(
                run_id=new_run.id,
                consumed_wip_id=consumed.wip_id,
                qty_consumed=consumed.qty_to_consume
            )
            db.add(run_mapping)

        # 6. SEQUENCE GAP FIX: Dynamically find the *next* available stage
            # 6. PRODUCT ROUTING: Find the next step for THIS specific product
            current_route = db.query(ProductRouting).filter(
                ProductRouting.product_id == run_data.product_id,
                ProductRouting.stage_id == current_stage.id
            ).first()

            if not current_route:
                raise HTTPException(status_code=400, detail="This stage is not valid for this product's routing.")

            # Find the next step number
            next_route = db.query(ProductRouting).filter(
                ProductRouting.product_id == run_data.product_id,
                ProductRouting.step_number > current_route.step_number
            ).order_by(ProductRouting.step_number.asc()).first()

            if next_route and not current_route.is_final_step:
                # NOT THE FINAL STAGE: Fetch the actual stage info and Queue it up
                next_stage = db.query(ProductionStage).filter(ProductionStage.id == next_route.stage_id).first()

                new_wip = WIPInventory(
                    factory_id=run_data.factory_id,
                    product_id=run_data.product_id,
                    current_stage_id=next_stage.id,  # Points to the dynamically found next stage
                    batch_number=unified_batch_number,
                    vendor_lot_number=vendor_lot_to_carry_forward,
                    current_qty=run_data.good_output_qty,
                    uom=next_stage.input_uom,
                    status="AVAILABLE"
                )
                db.add(new_wip)
                # ... (keep your FactoryLedger code for WIP_PRODUCED here) ...
        if next_stage:
            # NOT THE FINAL STAGE: Queue it up
            new_wip = WIPInventory(
                factory_id=run_data.factory_id,
                product_id=run_data.product_id,
                current_stage_id=next_stage.id,
                batch_number=unified_batch_number, # Unified ID
                vendor_lot_number=vendor_lot_to_carry_forward,
                current_qty=run_data.good_output_qty,
                uom=next_stage.input_uom,
                status="AVAILABLE"
            )
            db.add(new_wip)

            # WRITE TO FACTORY LEDGER
            ledger_produce = FactoryLedger(
                factory_id=run_data.factory_id,
                product_id=run_data.product_id,
                batch_number=unified_batch_number,
                stage_id=next_stage.id,
                transaction_type="WIP_PRODUCED",
                reference_document=f"RUN-{new_run.id}",
                quantity_change=run_data.good_output_qty,
                closing_balance=run_data.good_output_qty
            )
            db.add(ledger_produce)

        else:
            # THE FINAL STAGE: Push to Finished Goods (StockLedger)
            factory_stock = db.query(FactoryInventory).filter(
                FactoryInventory.factory_id == run_data.factory_id,
                FactoryInventory.product_id == run_data.product_id,
                FactoryInventory.batch_number == unified_batch_number
            ).with_for_update().first()

            new_closing_balance = run_data.good_output_qty

            if factory_stock:
                factory_stock.current_stock_qty += run_data.good_output_qty
                new_closing_balance = factory_stock.current_stock_qty
            else:
                factory_stock = FactoryInventory(
                    factory_id=run_data.factory_id,
                    product_id=run_data.product_id,
                    batch_number=unified_batch_number,
                    current_stock_qty=run_data.good_output_qty
                )
                db.add(factory_stock)

            # Log to DailyProductionLog
            daily_log = DailyProductionLog(
                product_id=run_data.product_id,
                factory_id=run_data.factory_id,
                batch_number=unified_batch_number,
                quantity_produced=run_data.good_output_qty,
                production_date=date.today()
            )
            db.add(daily_log)

            # FINISHED GOODS go to the main StockLedger
            ledger_fg = StockLedger(
                entity_type="FACTORY",
                entity_id=run_data.factory_id,
                product_id=run_data.product_id,
                batch_number=unified_batch_number,
                transaction_type="FG_PRODUCED",
                reference_document=f"RUN-{new_run.id}",
                quantity_change=run_data.good_output_qty,
                closing_balance=new_closing_balance
            )
            db.add(ledger_fg)

        db.commit()
        return {"status": "success", "run_id": new_run.id, "batch_number": unified_batch_number}

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database integrity error. Check foreign keys or idempotency.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def intake_raw_material(db: Session, data: RawMaterialIntake):
    # Dynamically find the lowest sequence stage (usually 1)
    stage_1 = db.query(ProductionStage).order_by(ProductionStage.sequence_number.asc()).first()
    if not stage_1:
        raise HTTPException(status_code=500, detail="Master data missing. No production stages found.")

    internal_batch_number = getattr(data, "custom_batch_number", None) or data.vendor_lot_number
    new_rm_stock = WIPInventory(
        factory_id=data.factory_id,
        product_id=data.product_id,
        current_stage_id=stage_1.id,
        batch_number=internal_batch_number,
        vendor_lot_number=data.vendor_lot_number,
        current_qty=data.invoice_qty,
        uom=data.uom,
        status="AVAILABLE"
    )
    db.add(new_rm_stock)

    # Main Stock Ledger (Receiving RM into the building)
    ledger_entry = StockLedger(
        entity_type="FACTORY_WIP",
        entity_id=data.factory_id,
        product_id=data.product_id,
        batch_number=internal_batch_number,
        transaction_type="RM_INTAKE",
        reference_document=data.vendor_lot_number,
        quantity_change=data.invoice_qty,
        closing_balance=data.invoice_qty
    )
    db.add(ledger_entry)

    # Also log to FactoryLedger so WIP trace starts clean
    factory_ledger_entry = FactoryLedger(
        factory_id=data.factory_id,
        product_id=data.product_id,
        batch_number=internal_batch_number,
        stage_id=stage_1.id,
        transaction_type="RM_TO_WIP",
        reference_document=data.vendor_lot_number,
        quantity_change=data.invoice_qty,
        closing_balance=data.invoice_qty
    )
    db.add(factory_ledger_entry)

    try:
        db.commit()
        db.refresh(new_rm_stock)
        return {
            "status": "success",
            "wip_id": new_rm_stock.id,
            "batch_number": internal_batch_number
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to intake material: {str(e)}")