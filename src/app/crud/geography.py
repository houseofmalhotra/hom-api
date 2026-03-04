from sqlalchemy.orm import Session
from src.app.models.geography import Zone, State, Region, Area, Territory
from src.app.schemas.geography import TerritoryCreate, ZoneCreate, StateCreate, RegionCreate, AreaCreate


def get_zones(db: Session):
    return db.query(Zone).all()

def get_territories_by_area(db: Session, area_id: int):
    return db.query(Territory).filter(Territory.area_id == area_id).all()

def create_zone(db: Session, zone: ZoneCreate):
    db_zone = Zone(name=zone.name)
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    return db_zone

def create_territory_in_db(db: Session, territory: TerritoryCreate):
    db_territory = Territory(
        name=territory.name,
        area_id=territory.area_id
    )
    db.add(db_territory)
    db.commit()
    db.refresh(db_territory)
    return db_territory

def create_state(db: Session, state: StateCreate):
    db_state = State(name=state.name, zone_id=state.zone_id)
    db.add(db_state)
    db.commit()
    db.refresh(db_state)
    return db_state

def get_states_by_zone(db: Session, zone_id: int):
    return db.query(State).filter(State.zone_id == zone_id).all()


def create_region(db: Session, region: RegionCreate):
    db_region = Region(name=region.name, state_id=region.state_id)
    db.add(db_region)
    db.commit()
    db.refresh(db_region)
    return db_region

def get_regions_by_state(db: Session, state_id: int):
    return db.query(Region).filter(Region.state_id == state_id).all()


def create_area(db: Session, area: AreaCreate):
    db_area = Area(name=area.name, region_id=area.region_id)
    db.add(db_area)
    db.commit()
    db.refresh(db_area)
    return db_area

def get_areas_by_region(db: Session, region_id: int):
    return db.query(Area).filter(Area.region_id == region_id).all()