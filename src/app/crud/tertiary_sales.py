from sqlalchemy.orm import Session
from src.app.models.sales_tertiary import TertiaryOrder, EndConsumer
from src.app.schemas.orders import TertiaryOrderCreate
from src.app.schemas.partner import EndConsumerCreate, EndConsumerUpdate
from datetime import date
from src.app.models.partner import Retailer
from src.app.models.geography import Territory, Area, Region, State


def create_tertiary_sale(db: Session, sale_in: TertiaryOrderCreate):
    """Creates a new tertiary sale record and stamps the full geography."""

    retailer = db.query(Retailer).filter(Retailer.id == sale_in.fulfilled_by_retailer_id).first()

    territory_id = retailer.territory_id if retailer else None
    area_id = None
    region_id = None
    state_id = None
    zone_id = None

    if territory_id:
        territory = db.query(Territory).filter(Territory.id == territory_id).first()
        if territory:
            area_id = territory.area_id
            area = db.query(Area).filter(Area.id == area_id).first()
            if area:
                region_id = area.region_id
                region = db.query(Region).filter(Region.id == region_id).first()
                if region:
                    state_id = region.state_id
                    state = db.query(State).filter(State.id == state_id).first()
                    if state:
                        zone_id = state.zone_id

    db_order = TertiaryOrder(
        end_consumer_id=sale_in.end_consumer_id,
        fulfilled_by_retailer_id=sale_in.fulfilled_by_retailer_id,
        product_id=sale_in.product_id,
        quantity=sale_in.quantity,
        batch_number=sale_in.batch_number,
        assigned_so_id=sale_in.assigned_so_id,
        request_date=date.today(),
        status="Pending",

        zone_id=zone_id,
        state_id=state_id,
        region_id=region_id,
        area_id=area_id,
        territory_id=territory_id
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def get_tertiary_order_by_id(db: Session, order_id: int):
    return db.query(TertiaryOrder).filter(TertiaryOrder.id == order_id).first()

def get_tertiary_orders_by_so(db: Session, so_id: int):
    return db.query(TertiaryOrder).filter(TertiaryOrder.assigned_so_id == so_id).all()

def update_tertiary_status(db: Session, order_id: int, status: str):
    db_order = db.query(TertiaryOrder).filter(TertiaryOrder.id == order_id).first()
    if db_order:
        db_order.status = status
        db.commit()
        db.refresh(db_order)
    return db_order


def get_scoped_pending_orders(db: Session, scope_filter: dict):
    query = db.query(TertiaryOrder).filter(TertiaryOrder.status == "Pending")

    if not scope_filter or "id" in scope_filter:
        return []

    return query.filter_by(**scope_filter).all()


def create_end_consumer(db: Session, consumer_in: EndConsumerCreate):
    db_consumer = EndConsumer(**consumer_in.model_dump())
    db.add(db_consumer)
    db.commit()
    db.refresh(db_consumer)
    return db_consumer

def get_end_consumers(db: Session):
    return db.query(EndConsumer).filter(EndConsumer.is_active == True).all()

def update_end_consumer(db: Session, consumer_id: int, consumer_in: EndConsumerUpdate):
    db_consumer = db.query(EndConsumer).filter(EndConsumer.id == consumer_id).first()
    if db_consumer:
        update_data = consumer_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_consumer, key, value)
        db.commit()
        db.refresh(db_consumer)
    return db_consumer

def delete_end_consumer(db: Session, consumer_id: int):
    db_consumer = db.query(EndConsumer).filter(EndConsumer.id == consumer_id).first()
    if db_consumer:
        db_consumer.is_active = False
        db.commit()
        return True
    return False