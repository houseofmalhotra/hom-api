from sqlalchemy.orm import Session
from src.app.models.invoice import Invoice
from src.app.schemas.invoice import InvoiceCreate

def get_invoice_by_order(db: Session, order_id: int):
    """Check if an invoice already exists for this order."""
    return db.query(Invoice).filter(Invoice.order_id == order_id).first()

def create_invoice(db: Session, obj_in: InvoiceCreate):
    """Save a new invoice record to the database."""
    db_obj = Invoice(
        order_id=obj_in.order_id,
        invoice_number=obj_in.invoice_number,
        total_amount=obj_in.total_amount
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj