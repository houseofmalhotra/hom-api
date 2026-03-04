from cryptography.hazmat.primitives.twofactor.hotp import HOTPHashTypes
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import date
from src.app.models.sales_primary import PrimaryOrder, PrimaryInvoice
from src.app.models.product import ProductMaster
from src.app.services.stock_service import StockService
from src.app.services.pricing_service import PricingService
from src.app.services.finance_service import FinanceService
from src.app.models.logistics import Shipment
from src.app.schemas.orders import DispatchPayload
from src.app.models.sales_tertiary import TertiaryOrder
from src.app.models.partner import Retailer
import datetime
from datetime import date, datetime
from decimal import Decimal


class OrderService:
    @staticmethod
    def dispatch_primary_order(db: Session, order_id: int, dispatch_data: DispatchPayload):
        order = db.query(PrimaryOrder).filter(PrimaryOrder.id == order_id).first()
        if not order or order.status not in ["Pending", "Partially Dispatched"]:
            raise HTTPException(status_code=400, detail="Order cannot be dispatched")

        total_invoice_amount = Decimal("0.00")

        from_entity_type, to_entity_type = OrderService.get_routing_entities(order.type)

        is_completely_fulfilled = True
        actual_items_dispatched = 0

        for item in order.items:
            if item.backordered_cases == 0 and item.dispatched_cases > 0:
                continue

            qty_to_fulfill = item.backordered_cases if item.backordered_cases > 0 else item.quantity_cases

            available_stock = StockService.check_available_stock(
                db, from_entity_type, order.from_entity_id, item.product_id, item.batch_number
            )

            dispatch_qty = min(qty_to_fulfill, available_stock)
            backorder_qty = qty_to_fulfill - dispatch_qty

            if backorder_qty > 0:
                is_completely_fulfilled = False

            if dispatch_qty == 0:
                item.backordered_cases = qty_to_fulfill
                continue

            actual_items_dispatched += 1

            product = db.query(ProductMaster).filter(ProductMaster.id == item.product_id).first()
            final_price, free_qty = PricingService.calculate_item_pricing(
                db, product.id, product.base_price, dispatch_qty
            )

            if (dispatch_qty + free_qty) > available_stock:
                free_qty = available_stock - dispatch_qty

            gst_multiplier = Decimal("1") + (Decimal(str(product.gst_percent)) / Decimal("100"))
            amount = Decimal(str(dispatch_qty)) * final_price * gst_multiplier

            total_invoice_amount += amount

            item.dispatched_cases += dispatch_qty
            item.backordered_cases = backorder_qty
            item.free_cases += free_qty
            item.final_price_per_case = final_price

            total_physical_deduction = dispatch_qty + free_qty

            StockService.update_stock(
                db=db, entity_type=from_entity_type, entity_id=order.from_entity_id,
                product_id=item.product_id, batch_number=item.batch_number,
                qty_change=-total_physical_deduction, ref_doc=order.order_number,
                trans_type=f"DISPATCH_OUT_{from_entity_type.upper()}"
            )
            StockService.update_stock(
                db=db, entity_type="InTransit", entity_id=order.id,
                product_id=item.product_id, batch_number=item.batch_number,
                qty_change=total_physical_deduction, ref_doc=order.order_number,
                trans_type="DISPATCH_IN_TRANSIT"
            )

        if actual_items_dispatched == 0:
            raise HTTPException(status_code=400, detail="Insufficient stock for all items. Order is fully backordered.")

        invoice_num = f"INV-{order.order_number}-{datetime.now().strftime('%M%S')}"
        invoice = PrimaryInvoice(
            primary_order_id=order.id, invoice_number=invoice_num,
            final_amount=total_invoice_amount, invoice_date=date.today()
        )
        db.add(invoice)

        FinanceService.record_transaction(
            db=db, party_type=to_entity_type, party_id=order.to_entity_id,
            trans_type="INVOICE", amount=total_invoice_amount, ref_doc=invoice_num
        )

        shipment = Shipment(
            primary_order_id=order.id,
            transporter_name=dispatch_data.transporter_name,
            vehicle_number=dispatch_data.vehicle_number,
            lr_number=dispatch_data.lr_number,
            driver_phone=dispatch_data.driver_phone,
            estimated_arrival_date=dispatch_data.estimated_arrival_date
        )
        db.add(shipment)

        order.status = "Dispatched" if is_completely_fulfilled else "Partially Dispatched"
        db.commit()

        return {
            "message": f"Order {order.status}",
            "invoice_number": invoice_num,
            "amount_billed": total_invoice_amount,
            "tracking_lr": shipment.lr_number
        }

    @staticmethod
    def receive_primary_order(db: Session, order_id: int):
        order = db.query(PrimaryOrder).filter(PrimaryOrder.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status == "Received":
            return {"message": "Order already processed"}
        if order.status != "Dispatched" and order.status != "Partially Dispatched":
            raise HTTPException(status_code=400, detail=f"Cannot receive order. Current status is {order.status}.")

        from_entity_type, to_entity_type = OrderService.get_routing_entities(order.type)

        for item in order.items:
            actual_received_qty = item.dispatched_cases + item.free_cases

            if actual_received_qty > 0:
                StockService.update_stock(
                    db=db,
                    entity_type="InTransit",
                    entity_id=order.id,
                    product_id=item.product_id,
                    batch_number=item.batch_number,
                    qty_change=-actual_received_qty,
                    ref_doc=order.order_number,
                    trans_type="RECEIPT_OUT_TRANSIT"
                )

                StockService.update_stock(
                    db=db,
                    entity_type=to_entity_type,
                    entity_id=order.to_entity_id,
                    product_id=item.product_id,
                    batch_number=item.batch_number,
                    qty_change=actual_received_qty,
                    ref_doc=order.order_number,
                    trans_type=f"RECEIPT_IN_{to_entity_type.upper()}"
                )


        order.status = "Received"
        db.commit()
        return {"message": f"Stock successfully delivered to {to_entity_type}."}

    @staticmethod
    def get_routing_entities(order_type: str):
        """Returns (from_entity_type, to_entity_type) based on order type"""
        order_type = order_type.upper()
        if order_type == "FACTORY_TO_SS":
            return "Factory", "SuperStockist"
        elif order_type == "FACTORY_TO_DB":
            return "Factory", "Distributor"
        elif order_type == "SS_TO_DB":
            return "SuperStockist", "Distributor"
        else:
            raise HTTPException(status_code=400, detail=f"Invalid order type: {order_type}")

    @staticmethod
    def approve_territory_order(db: Session, order_id: int, current_user):
        if not current_user.role or current_user.role != "SO":
            raise HTTPException(status_code=403, detail="Only Sales Officers can approve Tertiary Orders.")
        order = db.query(TertiaryOrder).filter(TertiaryOrder.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Tertiary Order not found")
        if order.status == "Approved_by_SO":
            raise HTTPException(status_code=400, detail="Order is already approved")
        retailer = db.query(Retailer).filter(Retailer.id == order.fulfilled_by_retailer_id).first()
        if not retailer:
            raise HTTPException(status_code=404, detail="Retailer fulfilling this order not found.")

        if retailer.territory_id != current_user.assigned_territory_id:
            raise HTTPException(
                status_code = 403,
                detail = "This order belongs to a Retailer outside your assigned territory."
            )
        try:
            StockService.update_stock(
                db=db,
                entity_type="Retailer",
                entity_id=order.fulfilled_by_retailer_id,
                product_id=order.product_id,
                qty_change=-order.quantity,
                ref_doc=f"TERT-{order.id}",
                batch_number=order.batch_number,
                trans_type="RETAIL_SALE"
            )

            order.status = "Approved_by_SO"
            db.commit()
            db.refresh(order)

            return {"message": "Order approved successfully", "order_id": order.id, "status": order.status}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))

