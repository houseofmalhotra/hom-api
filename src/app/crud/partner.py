from sqlalchemy.orm import Session
from src.app.models.partner import SuperStockist, Distributor, Retailer
from src.app.models.geography import Territory, Area, Region, State
from src.app.schemas.partner import SuperStockistCreate, DistributorCreate, RetailerCreate


def create_super_stockist(db: Session, ss_in: SuperStockistCreate):
    db_ss = SuperStockist(**ss_in.model_dump())
    db.add(db_ss)
    db.commit()
    db.refresh(db_ss)
    return db_ss


def create_distributor(db: Session, dist_in: DistributorCreate):
    dist_data = dist_in.model_dump()

    if dist_data.get("state_id"):
        state = db.query(State).filter(State.id == dist_data["state_id"]).first()
        if state:
            dist_data["zone_id"] = state.zone_id

    db_dist = Distributor(**dist_data)
    db.add(db_dist)
    db.commit()
    db.refresh(db_dist)
    return db_dist


def create_retailer(db: Session, ret_in: RetailerCreate):
    ret_data = ret_in.model_dump()

    if ret_data.get("territory_id"):
        territory = db.query(Territory).filter(Territory.id == ret_data["territory_id"]).first()
        if territory:
            ret_data["area_id"] = territory.area_id
            area = db.query(Area).filter(Area.id == territory.area_id).first()
            if area:
                ret_data["region_id"] = area.region_id
                region = db.query(Region).filter(Region.id == area.region_id).first()
                if region:
                    ret_data["state_id"] = region.state_id
                    state = db.query(State).filter(State.id == region.state_id).first()
                    if state:
                        ret_data["zone_id"] = state.zone_id

    db_ret = Retailer(**ret_data)
    db.add(db_ret)
    db.commit()
    db.refresh(db_ret)
    return db_ret