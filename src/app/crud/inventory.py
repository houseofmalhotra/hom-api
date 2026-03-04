from sqlalchemy.orm import Session
from src.app.models.inventory import DistributorInventory, StockLedger

def get_distributor_stock(db:Session, distributor_id:int, product_id:int):
    return db.query(DistributorInventory).filter_by(
        distributor_id=distributor_id,
        product_id=product_id
    ).first()

def create_ledger_entry(db:Session, ledger_data: dict):
    db_entry = StockLedger(**ledger_data)
    db.add(db_entry)
    db.flush()
    return db_entry



