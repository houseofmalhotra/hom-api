from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from datetime import date
import uuid
from decimal import Decimal

# Models
from src.app.models.production_core import (
    ProductionStage, WIPInventory, ProductionRun,
    RunConsumption, FactoryLedger, ProductRouting,
    ScrapReason, ProductionRunScrap  # NEW
)
from src.app.models.inventory import (
    StockLedger, DailyProductionLog, FactoryInventory, ScrapInventory
)
from src.app.models.product import ProductMaster  # NEW
from src.app.schemas.production import ProductionRunCreate
from src.app.services.stock_service import StockService  # NEW


def execute_production_run(db: Session, run_data: ProductionRunCreate):
    try:
        # 1. IDEMPOTENCY CHECK: Block duplicate runs from double-clicks/latency
        existing_run = db.query(ProductionRun).filter(
            ProductionRun.idempotency_key == run_data.idempotency_key
        ).first()

        if existing_run:
            return {"status": "success", "run_id": existing_run.id, "message": "Run already processed."}

        # 2. Fetch the current stage
        current_stage = db.query(ProductionStage).filter(ProductionStage.id == run_data.stage_id).first()
        if not current_stage:
            raise HTTPException(status_code=404, detail="Production stage not found.")

        total_input_qty = Decimal("0.00")
        total_material_cost_incurred = Decimal("0.00")  # NEW: Costing tracker

        consumed_batches = set()
        consumed_vendor_lots = set()
        pending_ledgers = []

        # =================================================================
        # 3A. PROCESS WIP CONSUMPTIONS (Blades / Intermediate Goods)
        # =================================================================
        for consumed in run_data.consumed_wips:
            wip_record = db.query(WIPInventory).filter(
                WIPInventory.id == consumed.wip_id
            ).with_for_update().first()

            if not wip_record:
                raise HTTPException(status_code=404, detail=f"WIP Batch {consumed.wip_id} not found.")
            if wip_record.current_qty < consumed.qty_to_consume:
                raise HTTPException(status_code=400, detail=f"Insufficient quantity in WIP {wip_record.batch_number}")

            consumed_batches.add(wip_record.batch_number)
            if wip_record.vendor_lot_number:
                consumed_vendor_lots.add(wip_record.vendor_lot_number)

            # Deduct the quantity
            wip_record.current_qty -= consumed.qty_to_consume
            if wip_record.current_qty <= 0:
                wip_record.status = "CONSUMED"

            total_input_qty += Decimal(str(consumed.qty_to_consume))

            # NEW: Calculate Cost for this WIP
            wip_product = db.query(ProductMaster).filter(ProductMaster.id == wip_record.product_id).first()
            if wip_product and wip_product.standard_cost:
                cost_of_wip = Decimal(str(consumed.qty_to_consume)) * Decimal(str(wip_product.standard_cost))
                total_material_cost_incurred += cost_of_wip

            # WRITE TO FACTORY LEDGER
            ledger_consume = FactoryLedger(
                factory_id=run_data.factory_id,
                product_id=wip_record.product_id,
                batch_number=wip_record.batch_number,
                stage_id=current_stage.id,
                transaction_type="WIP_CONSUMED",
                reference_document="PENDING",
                quantity_change=-consumed.qty_to_consume,
                closing_balance=wip_record.current_qty
            )
            db.add(ledger_consume)
            pending_ledgers.append(ledger_consume)

        # =================================================================
        # 3B. PROCESS RAW MATERIAL CONSUMPTIONS (Packaging, Glue, Cellophane)
        # =================================================================
        if hasattr(run_data, 'consumed_materials'):
            for rm in run_data.consumed_materials:
                rm_product = db.query(ProductMaster).filter(ProductMaster.id == rm.product_id).first()
                if not rm_product:
                    raise HTTPException(status_code=404, detail=f"Raw Material Product ID {rm.product_id} not found.")

                # NEW: Calculate Cost for this Raw Material
                if rm_product.standard_cost:
                    cost_of_rm = Decimal(str(rm.qty_to_consume)) * Decimal(str(rm_product.standard_cost))
                    total_material_cost_incurred += cost_of_rm

                # Deduct immediately from Factory Inventory using StockService
                StockService.update_stock(
                    db=db,
                    entity_type="Factory",
                    entity_id=run_data.factory_id,
                    product_id=rm.product_id,
                    batch_number=rm.batch_number,
                    qty_change=-rm.qty_to_consume,
                    ref_doc="RUN-PENDING",
                    trans_type="RM_CONSUMED"
                )

        # =================================================================
        # 4. THE FRANKENSTEIN BATCH LOGIC
        # =================================================================
        if len(consumed_batches) == 1:
            unified_batch_number = next(iter(consumed_batches))
            vendor_lot_to_carry_forward = next(iter(consumed_vendor_lots)) if consumed_vendor_lots else None
        elif len(consumed_batches) > 1:
            unified_batch_number = f"MIX-S{current_stage.sequence_number}-{uuid.uuid4().hex[:6].upper()}"
            vendor_lot_to_carry_forward = "MIXED"
        else:
            unified_batch_number = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
            vendor_lot_to_carry_forward = None

        # =================================================================
        # 5. CREATE PRODUCTION RUN & COSTING METRICS
        # =================================================================
        good_qty = Decimal(str(run_data.good_output_qty))
        unit_cost_of_output = Decimal("0.00")

        if good_qty > 0:
            unit_cost_of_output = total_material_cost_incurred / good_qty

        new_run = ProductionRun(
            idempotency_key=run_data.idempotency_key,
            stage_id=current_stage.id,
            factory_id=run_data.factory_id,
            operator_id=run_data.operator_id,
            output_batch_number=unified_batch_number,
            product_id=run_data.product_id,
            input_qty=total_input_qty,
            good_output_qty=good_qty,
            total_material_cost=total_material_cost_incurred,  # NEW
            cost_per_unit_produced=unit_cost_of_output  # NEW
        )
        db.add(new_run)
        db.flush()

        run_reference = f"RUN-{new_run.id}"
        for ledger in pending_ledgers:
            ledger.reference_document = run_reference

        for consumed in run_data.consumed_wips:
            run_mapping = RunConsumption(
                run_id=new_run.id,
                consumed_wip_id=consumed.wip_id,
                qty_consumed=consumed.qty_to_consume
            )
            db.add(run_mapping)

        # =================================================================
        # 6. PRODUCT ROUTING & QUEUEING
        # =================================================================
        current_route = db.query(ProductRouting).filter(
            ProductRouting.product_id == run_data.product_id,
            ProductRouting.stage_id == current_stage.id
        ).first()

        next_stage = None
        is_final_step = False

        if current_route:
            target_output_product_id = current_route.output_product_id or run_data.product_id
            is_final_step = current_route.is_final_step

            next_route = db.query(ProductRouting).filter(
                ProductRouting.product_id == run_data.product_id,
                ProductRouting.step_number > current_route.step_number
            ).order_by(ProductRouting.step_number.asc()).first()

            if next_route and not is_final_step:
                next_stage = db.query(ProductionStage).filter(ProductionStage.id == next_route.stage_id).first()
        else:
            target_output_product_id = run_data.product_id
            next_stage = db.query(ProductionStage).filter(
                ProductionStage.sequence_number > current_stage.sequence_number
            ).order_by(ProductionStage.sequence_number.asc()).first()

            if not next_stage:
                is_final_step = True

        # Update the standard cost of the newly produced item in the Product Master
        output_product = db.query(ProductMaster).filter(ProductMaster.id == target_output_product_id).first()
        if output_product:
            output_product.standard_cost = unit_cost_of_output

        if not is_final_step and next_stage:
            new_wip = WIPInventory(
                factory_id=run_data.factory_id,
                product_id=target_output_product_id,
                current_stage_id=next_stage.id,
                batch_number=unified_batch_number,
                vendor_lot_number=vendor_lot_to_carry_forward,
                current_qty=good_qty,
                uom=next_stage.input_uom,
                status="AVAILABLE"
            )
            db.add(new_wip)

            ledger_produce = FactoryLedger(
                factory_id=run_data.factory_id,
                product_id=target_output_product_id,
                batch_number=unified_batch_number,
                stage_id=next_stage.id,
                transaction_type="WIP_PRODUCED",
                reference_document=run_reference,
                quantity_change=good_qty,
                closing_balance=good_qty
            )
            db.add(ledger_produce)
        else:
            factory_stock = db.query(FactoryInventory).filter(
                FactoryInventory.factory_id == run_data.factory_id,
                FactoryInventory.product_id == target_output_product_id,
                FactoryInventory.batch_number == unified_batch_number
            ).with_for_update().first()

            new_closing_balance = good_qty
            if factory_stock:
                factory_stock.current_stock_qty += good_qty
                new_closing_balance = factory_stock.current_stock_qty
            else:
                factory_stock = FactoryInventory(
                    factory_id=run_data.factory_id,
                    product_id=target_output_product_id,
                    batch_number=unified_batch_number,
                    current_stock_qty=good_qty
                )
                db.add(factory_stock)

            daily_log = DailyProductionLog(
                product_id=target_output_product_id,
                factory_id=run_data.factory_id,
                batch_number=unified_batch_number,
                quantity_produced=good_qty,
                production_date=date.today()
            )
            db.add(daily_log)

            ledger_fg = StockLedger(
                entity_type="FACTORY",
                entity_id=run_data.factory_id,
                product_id=target_output_product_id,
                batch_number=unified_batch_number,
                transaction_type="FG_PRODUCED",
                reference_document=run_reference,
                quantity_change=good_qty,
                closing_balance=new_closing_balance
            )
            db.add(ledger_fg)

        # =================================================================
        # 7. CAPTURE THE GRANULAR SCRAP / WASTE
        # =================================================================
        if hasattr(run_data, 'scrap_details'):
            for scrap in run_data.scrap_details:
                scrap_reason = db.query(ScrapReason).filter(ScrapReason.id == scrap.reason_id).first()
                if not scrap_reason:
                    continue

                run_scrap = ProductionRunScrap(
                    run_id=new_run.id,
                    reason_id=scrap.reason_id,
                    qty=scrap.qty
                )
                db.add(run_scrap)

                # Route hard-loss scrap to ScrapInventory
                if not scrap_reason.is_recoverable:
                    scrap_record = db.query(ScrapInventory).filter(
                        ScrapInventory.factory_id == run_data.factory_id,
                        ScrapInventory.product_id == run_data.product_id
                    ).with_for_update().first()

                    new_scrap_balance = scrap.qty

                    if scrap_record:
                        scrap_record.current_qty += scrap.qty
                        new_scrap_balance = scrap_record.current_qty
                    else:
                        scrap_record = ScrapInventory(
                            factory_id=run_data.factory_id,
                            product_id=run_data.product_id,
                            current_qty=scrap.qty,
                            uom=current_stage.input_uom
                        )
                        db.add(scrap_record)

                    ledger_scrap = FactoryLedger(
                        factory_id=run_data.factory_id,
                        product_id=run_data.product_id,
                        batch_number=unified_batch_number,
                        stage_id=current_stage.id,
                        transaction_type="SCRAP_PRODUCED",
                        reference_document=run_reference,
                        quantity_change=scrap.qty,
                        closing_balance=new_scrap_balance
                    )
                    db.add(ledger_scrap)

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

    internal_batch_number = data.custom_batch_number or data.vendor_lot_number

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
        if getattr(run, 'is_reversed', False):
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
        if hasattr(run, 'is_reversed'):
            run.is_reversed = True

        db.commit()

        return {"status": "success", "message": f"Run {run.id} successfully reversed."}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reverse run: {str(e)}")