from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
import uuid
from src.app.core.database import get_db
from src.app.schemas.invoice import InvoiceCreate
from src.app.crud.invoice import get_invoice_by_order, create_invoice
from src.app.services.invoice_service import generate_invoice_pdf
from src.app.models.sales_primary import PrimaryOrder

router = APIRouter()

@router.post("/{order_id}/generate", response_class=Response, responses={
    200: {
        "content": {"application/pdf": {}},
        "description": "Returns the generated invoice as a PDF file."
    }
})

def generate_and_download_invoice(order_id: int, db: Session = Depends(get_db)):
    """
    Generates a PDF invoice based on actual PrimaryOrder data in the database.
    """
    order = db.query(PrimaryOrder).filter(PrimaryOrder.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail=f"Primary Order with ID {order_id} not found.")

    existing_invoice = get_invoice_by_order(db, order_id=order_id)

    order_items = []
    calculated_total = 0.0

    for item in order.items:
        price = float(item.final_price_per_case) if item.final_price_per_case else 0.0
        qty = item.quantity_cases or 0

        order_items.append({
            "name": f"Product ID: {item.product_id} (Batch: {item.batch_number})",
            "quantity": qty,
            "price": price
        })

        calculated_total += (qty * price)

    if existing_invoice:
        invoice_number = existing_invoice.invoice_number
        total_amount = existing_invoice.total_amount
    else:
        invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        total_amount = calculated_total


        invoice_in = InvoiceCreate(
            order_id=order_id,
            invoice_number=invoice_number,
            total_amount=total_amount
        )
        create_invoice(db=db, obj_in=invoice_in)

    pdf_bytes = generate_invoice_pdf(
        invoice_number=invoice_number,
        order_items=order_items,
        total_amount=total_amount
    )

    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{invoice_number}.pdf"'
        }
    )