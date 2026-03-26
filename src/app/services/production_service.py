from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from datetime import date
import uuid
from src.app.models.inventory import ScrapInventory
from src.app.models.production_core import ProductionStage, WIPInventory, ProductionRun, RunConsumption, FactoryLedger, ProductRouting
from src.app.models.inventory import StockLedger, DailyProductionLog, FactoryInventory
from src.app.schemas.production import ProductionRunCreate, RawMaterialIntake

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from datetime import date
import uuid

from src.app.models.production_core import WIPInventory, ProductionRun, RunConsumption, FactoryLedger
from src.app.models.inventory import FactoryInventory, DailyProductionLog, ScrapInventory, StockLedger
# Import Core Production Models
from src.app.models.production_core import (
    ProductionStage, WIPInventory, ProductionRun,
    RunConsumption, FactoryLedger, ProductRouting
)
# Import Inventory Models
from src.app.models.inventory import (
    StockLedger, DailyProductionLog, FactoryInventory, ScrapInventory
)
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

        # --- TRACKING FOR FRANKENSTEIN BATCHES ---
        consumed_batches = set()
        consumed_vendor_lots = set()

        # 3. Process Consumptions
        for consumed in run_data.consumed_wips:
            wip_record = db.query(WIPInventory).filter(WIPInventory.id == consumed.wip_id).with_for_update().first()

            if not wip_record:
                raise HTTPException(status_code=404, detail=f"WIP Batch {consumed.wip_id} not found.")
            if wip_record.current_qty < consumed.qty_to_consume:
                raise HTTPException(status_code=400, detail=f"Insufficient quantity in WIP {wip_record.batch_number}")

            # Capture batches for Mix detection
            consumed_batches.add(wip_record.batch_number)
            if wip_record.vendor_lot_number:
                consumed_vendor_lots.add(wip_record.vendor_lot_number)

            # Deduct the quantity
            wip_record.current_qty -= consumed.qty_to_consume
            if wip_record.current_qty <= 0:
                wip_record.status = "CONSUMED"

            total_input_qty += consumed.qty_to_consume

            # WRITE TO FACTORY LEDGER
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

        # =================================================================
        # 🚨 THE FRANKENSTEIN BATCH LOGIC 🚨
        # =================================================================
        if len(consumed_batches) == 1:
            # Pure Batch: Only 1 unique batch was consumed. Inherit it directly!
            unified_batch_number = consumed_batches.pop()
            vendor_lot_to_carry_forward = consumed_vendor_lots.pop() if consumed_vendor_lots else None

        elif len(consumed_batches) > 1:
            # Mixed Batch: Multiple different batches were blended. Generate a MIX ID.
            unified_batch_number = f"MIX-S{current_stage.sequence_number}-{uuid.uuid4().hex[:6].upper()}"
            vendor_lot_to_carry_forward = "MIXED"

        else:
            # Fallback (Should theoretically never hit)
            unified_batch_number = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
            vendor_lot_to_carry_forward = None
        # =================================================================

        # 4. Create the Production Run Ledger Entry
        new_run = ProductionRun(
            idempotency_key=run_data.idempotency_key,
            stage_id=current_stage.id,
            factory_id=run_data.factory_id,
            operator_id=run_data.operator_id,
            output_batch_number=unified_batch_number,  # Unified or MIX ID
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

        # 6. PRODUCT ROUTING & LIGHTWEIGHT MUTATION
        current_route = db.query(ProductRouting).filter(
            ProductRouting.product_id == run_data.product_id,
            ProductRouting.stage_id == current_stage.id
        ).first()

        if not current_route:
            raise HTTPException(status_code=400, detail="This stage is not valid for this product's routing.")

        # --- MUTATION CHECK ---
        # If the routing dictates a new product comes out, we use it. Otherwise, keep the input ID.
        target_output_product_id = current_route.output_product_id or run_data.product_id

        # Find the next step number
        next_route = db.query(ProductRouting).filter(
            ProductRouting.product_id == run_data.product_id,
            ProductRouting.step_number > current_route.step_number
        ).order_by(ProductRouting.step_number.asc()).first()

        if next_route and not current_route.is_final_step:
            # NOT THE FINAL STAGE: Queue it up for the next machine
            next_stage = db.query(ProductionStage).filter(ProductionStage.id == next_route.stage_id).first()

            new_wip = WIPInventory(
                factory_id=run_data.factory_id,
                product_id=target_output_product_id,  # 🚨 MUTATED PRODUCT ID
                current_stage_id=next_stage.id,
                batch_number=unified_batch_number,
                vendor_lot_number=vendor_lot_to_carry_forward,
                current_qty=run_data.good_output_qty,
                uom=next_stage.input_uom,
                status="AVAILABLE"
            )
            db.add(new_wip)

            # WRITE TO FACTORY LEDGER
            ledger_produce = FactoryLedger(
                factory_id=run_data.factory_id,
                product_id=target_output_product_id,  # 🚨 MUTATED PRODUCT ID
                batch_number=unified_batch_number,
                stage_id=next_stage.id,
                transaction_type="WIP_PRODUCED",
                reference_document=f"RUN-{new_run.id}",
                quantity_change=run_data.good_output_qty,
                closing_balance=run_data.good_output_qty
            )
            db.add(ledger_produce)

        else:
            # THE FINAL STAGE: Push to Finished Goods
            factory_stock = db.query(FactoryInventory).filter(
                FactoryInventory.factory_id == run_data.factory_id,
                FactoryInventory.product_id == target_output_product_id,  # 🚨 MUTATED PRODUCT ID
                FactoryInventory.batch_number == unified_batch_number
            ).with_for_update().first()

            new_closing_balance = run_data.good_output_qty

            if factory_stock:
                factory_stock.current_stock_qty += run_data.good_output_qty
                new_closing_balance = factory_stock.current_stock_qty
            else:
                factory_stock = FactoryInventory(
                    factory_id=run_data.factory_id,
                    product_id=target_output_product_id,  # 🚨 MUTATED PRODUCT ID
                    batch_number=unified_batch_number,
                    current_stock_qty=run_data.good_output_qty
                )
                db.add(factory_stock)

            # Log to DailyProductionLog
            daily_log = DailyProductionLog(
                product_id=target_output_product_id,  # 🚨 MUTATED PRODUCT ID
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
                product_id=target_output_product_id,  # 🚨 MUTATED PRODUCT ID
                batch_number=unified_batch_number,
                transaction_type="FG_PRODUCED",
                reference_document=f"RUN-{new_run.id}",
                quantity_change=run_data.good_output_qty,
                closing_balance=new_closing_balance
            )
            db.add(ledger_fg)

        # =================================================================
        # 7. CAPTURE THE SCRAP / WASTE
        # =================================================================
        if run_data.scrap_qty > 0:
            # We track scrap using the ORIGINAL INPUT product ID (e.g. Steel)
            scrap_record = db.query(ScrapInventory).filter(
                ScrapInventory.factory_id == run_data.factory_id,
                ScrapInventory.product_id == run_data.product_id
            ).with_for_update().first()

            new_scrap_balance = run_data.scrap_qty

            if scrap_record:
                scrap_record.current_qty += run_data.scrap_qty
                new_scrap_balance = scrap_record.current_qty
            else:
                scrap_record = ScrapInventory(
                    factory_id=run_data.factory_id,
                    product_id=run_data.product_id,
                    current_qty=run_data.scrap_qty,
                    uom=current_stage.input_uom
                )
                db.add(scrap_record)

            ledger_scrap = FactoryLedger(
                factory_id=run_data.factory_id,
                product_id=run_data.product_id,
                batch_number=unified_batch_number,
                stage_id=current_stage.id,
                transaction_type="SCRAP_PRODUCED",
                reference_document=f"RUN-{new_run.id}",
                quantity_change=run_data.scrap_qty,
                closing_balance=new_scrap_balance
            )
            db.add(ledger_scrap)
        # =================================================================

        # 8. Commit the entire transaction safely
        db.commit()
        return {"status": "success", "run_id": new_run.id, "batch_number": unified_batch_number}

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database integrity error. Check foreign keys or idempotency.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def intake_raw_material(db: Session, data: RawMaterialIntake):
    # Find the starting stage based on the Product's Routing!
    first_route = db.query(ProductRouting).filter(
        ProductRouting.product_id == data.product_id,
        ProductRouting.step_number == 1
    ).first()

    if not first_route:
        # Fallback to sequence 1 if no routing exists yet
        stage_1 = db.query(ProductionStage).order_by(ProductionStage.sequence_number.asc()).first()
    else:
        stage_1 = db.query(ProductionStage).filter(ProductionStage.id == first_route.stage_id).first()

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


def reverse_production_run(db: Session, run_id: int, operator_id: int):
    try:
        # 1. Fetch and Lock the Run
        run = db.query(ProductionRun).filter(ProductionRun.id == run_id).with_for_update().first()
        if not run:
            raise HTTPException(status_code=404, detail="Production run not found.")
        if run.is_reversed:
            raise HTTPException(status_code=400, detail="This run has already been reversed.")

        # ==========================================================
        # 2. VALIDATE & REVERT OUTPUT (WIP or FG)
        # ==========================================================
        # Check if the output is sitting in WIP
        output_wip = db.query(WIPInventory).filter(
            WIPInventory.batch_number == run.output_batch_number,
            WIPInventory.status == "AVAILABLE"
        ).first()

        if output_wip:
            # Check if anyone consumed part of it already
            if output_wip.current_qty < run.good_output_qty:
                raise HTTPException(status_code=400,
                                    detail="Cannot reverse: This batch has already been partially consumed by the next stage.")

            # Revert WIP
            output_wip.current_qty -= run.good_output_qty
            if output_wip.current_qty <= 0:
                output_wip.status = "REVERSED"

            # Ledger Reversal
            ledger_wip_rev = FactoryLedger(
                factory_id=run.factory_id, product_id=output_wip.product_id,
                batch_number=run.output_batch_number, stage_id=run.stage_id,
                transaction_type="WIP_PRODUCED_REVERSAL", reference_document=f"REV-RUN-{run.id}",
                quantity_change=-run.good_output_qty, closing_balance=output_wip.current_qty
            )
            db.add(ledger_wip_rev)

        else:
            # Check if it was Final Stage and went to Factory Inventory (FG)
            output_fg = db.query(FactoryInventory).filter(
                FactoryInventory.batch_number == run.output_batch_number
            ).first()

            if not output_fg or output_fg.current_stock_qty < run.good_output_qty:
                raise HTTPException(status_code=400,
                                    detail="Cannot reverse: Finished Goods have already been shipped or moved.")

            # Revert FG
            output_fg.current_stock_qty -= run.good_output_qty

            # Remove from Daily Log
            db.query(DailyProductionLog).filter(DailyProductionLog.batch_number == run.output_batch_number).delete()

            # Ledger Reversals
            ledger_fg_rev = StockLedger(
                entity_type="FACTORY", entity_id=run.factory_id, product_id=output_fg.product_id,
                batch_number=run.output_batch_number, transaction_type="FG_PRODUCED_REVERSAL",
                reference_document=f"REV-RUN-{run.id}", quantity_change=-run.good_output_qty,
                closing_balance=output_fg.current_stock_qty
            )
            db.add(ledger_fg_rev)

        # ==========================================================
        # 3. RESTORE CONSUMED INPUTS
        # ==========================================================
        consumptions = db.query(RunConsumption).filter(RunConsumption.run_id == run.id).all()
        for consumption in consumptions:
            input_wip = db.query(WIPInventory).filter(WIPInventory.id == consumption.consumed_wip_id).first()
            if input_wip:
                input_wip.current_qty += consumption.qty_consumed
                input_wip.status = "AVAILABLE"  # Bring it back to life

                ledger_consume_rev = FactoryLedger(
                    factory_id=run.factory_id, product_id=input_wip.product_id,
                    batch_number=input_wip.batch_number, stage_id=run.stage_id,
                    transaction_type="WIP_CONSUMED_REVERSAL", reference_document=f"REV-RUN-{run.id}",
                    quantity_change=consumption.qty_consumed, closing_balance=input_wip.current_qty
                )
                db.add(ledger_consume_rev)

        # ==========================================================
        # 4. RESTORE SCRAP
        # ==========================================================
        if run.scrap_qty > 0:
            scrap_record = db.query(ScrapInventory).filter(
                ScrapInventory.factory_id == run.factory_id,
                ScrapInventory.product_id == run.product_id
            ).first()

            if scrap_record:
                scrap_record.current_qty -= run.scrap_qty

                ledger_scrap_rev = FactoryLedger(
                    factory_id=run.factory_id, product_id=run.product_id,
                    batch_number=run.output_batch_number, stage_id=run.stage_id,
                    transaction_type="SCRAP_PRODUCED_REVERSAL", reference_document=f"REV-RUN-{run.id}",
                    quantity_change=-run.scrap_qty, closing_balance=scrap_record.current_qty
                )
                db.add(ledger_scrap_rev)

        # Mark Run as Reversed and Commit
        run.is_reversed = True
        db.commit()

        return {"status": "success", "message": f"Run {run.id} successfully reversed."}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reverse run: {str(e)}")