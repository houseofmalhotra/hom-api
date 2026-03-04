from sqlalchemy.orm import Session
from src.app.models.sales_secondary import SecondaryOrder, SecondaryOrderItems
from src.app.models.partner import Distributor, Retailer
from src.app.models.geography import Territory, Area, Region, State


def create_secondary_order(db: Session, retailer_id: int, distributor_id: int, items_in: list, total_amount: float):
    distributor = db.query(Distributor).filter(Distributor.id == distributor_id).first()
    retailer = db.query(Retailer).filter(Retailer.id == retailer_id).first()

    territory_id = retailer.territory_id if retailer else None
    area_id = None
    region_id = None
    state_id = distributor.state_id if distributor else None
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
    elif state_id:
        state = db.query(State).filter(State.id == state_id).first()
        if state:
            zone_id = state.zone_id

    db_order = SecondaryOrder(
        retailer_id=retailer_id,
        distributor_id=distributor_id,
        total_amount=total_amount,
        status="Pending",

        zone_id=zone_id,
        state_id=state_id,
        region_id=region_id,
        area_id=area_id,
        territory_id=territory_id
    )
    db.add(db_order)
    db.flush()

    for item in items_in:
        db_item = SecondaryOrderItems(
            secondary_order_id=db_order.id,
            product_id=item['product_id'],
            quantity_units=item['quantity'],
            batch_number=item['batch_number']
        )
        db.add(db_item)

    return db_order