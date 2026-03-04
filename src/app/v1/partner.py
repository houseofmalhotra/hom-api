from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from src.app.core.database import get_db

from src.app.core.security import get_current_user, check_permissions
from src.app.models.user import User
from src.app.services.permission_service import PermissionService

from src.app.models.partner import SuperStockist, Distributor, Retailer
from src.app.models.geography import Territory, Area, Region, State
from src.app.schemas.partner import (
    SuperStockistCreate, SuperStockistRead, SuperStockistUpdate,
    DistributorCreate, DistributorRead, DistributorUpdate,
    RetailerCreate, RetailerRead, RetailerUpdate
)
from src.app.crud.partner import (
    create_super_stockist, create_distributor, create_retailer
)

router = APIRouter()

@router.post("/super-stockists", response_model=SuperStockistRead, status_code=status.HTTP_201_CREATED)
def add_super_stockist(
        ss_in: SuperStockistCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    return create_super_stockist(db, ss_in)


@router.get("/super-stockists", response_model=list[SuperStockistRead])
def list_super_stockists(
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_partners"))
):
    query = db.query(SuperStockist)

    if not current_user.role: return []
    user_perms = [p.name for p in current_user.role.permissions]
    if "manage_roles" in user_perms: return query.all()

    if current_user.role.name == "SuperStockist":
        return query.filter(SuperStockist.user_id == current_user.id).all()
    elif current_user.role.name == "Distributor":
        dist = db.query(Distributor).filter(Distributor.user_id == current_user.id).first()
        if dist and dist.parent_ss_id:
            return query.filter(SuperStockist.id == dist.parent_ss_id).all()
        if dist and dist.zone_id:
            return query.filter(SuperStockist.zone_id == dist.zone_id).all()
        return []
    elif current_user.role.name == "Retailer":
        return []

    return PermissionService.apply_geo_filter(query, SuperStockist, current_user).all()


@router.patch("/super-stockists/{ss_id}", response_model=SuperStockistRead)
def update_super_stockist(
        ss_id: int,
        ss_in: SuperStockistUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    PermissionService.verify_internal_jurisdiction(db, current_user, SuperStockist, ss_id)

    db_ss = db.query(SuperStockist).filter(SuperStockist.id == ss_id).first()
    if not db_ss:
        raise HTTPException(status_code=404, detail="Super Stockist not found")

    update_data = ss_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_ss, key, value)

    db.commit()
    db.refresh(db_ss)
    return db_ss


@router.delete("/super-stockists/{ss_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_super_stockist(
        ss_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    PermissionService.verify_internal_jurisdiction(db, current_user, SuperStockist, ss_id)

    db_ss = db.query(SuperStockist).filter(SuperStockist.id == ss_id).first()
    if not db_ss:
        raise HTTPException(status_code=404, detail="Super Stockist not found")
    db_ss.is_active = False
    db.commit()
    return None


@router.post("/distributors", response_model=DistributorRead, status_code=status.HTTP_201_CREATED)
def add_distributor(
        dist_in: DistributorCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    return create_distributor(db, dist_in)


@router.get("/distributors", response_model=list[DistributorRead])
def list_distributors(
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_partners"))
):
    query = db.query(Distributor)

    if not current_user.role: return []
    user_perms = [p.name for p in current_user.role.permissions]
    if "manage_roles" in user_perms: return query.all()

    if current_user.role.name == "Distributor":
        return query.filter(Distributor.user_id == current_user.id).all()
    elif current_user.role.name == "SuperStockist":
        ss = db.query(SuperStockist).filter(SuperStockist.user_id == current_user.id).first()
        if ss: return query.filter(Distributor.parent_ss_id == ss.id).all()
    elif current_user.role.name == "Retailer":
        ret = db.query(Retailer).filter(Retailer.user_id == current_user.id).first()
        if ret and ret.linked_distributor_id:
            return query.filter(Distributor.id == ret.linked_distributor_id).all()
        if ret and ret.state_id:
            return query.filter(Distributor.state_id == ret.state_id).all()
        return []

    return PermissionService.apply_geo_filter(query, Distributor, current_user).all()


@router.patch("/distributors/{dist_id}", response_model=DistributorRead)
def update_distributor(
        dist_id: int,
        dist_in: DistributorUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    PermissionService.verify_internal_jurisdiction(db, current_user, Distributor, dist_id)

    db_dist = db.query(Distributor).filter(Distributor.id == dist_id).first()
    if not db_dist:
        raise HTTPException(status_code=404, detail="Distributor not found")

    update_data = dist_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_dist, key, value)

    if "state_id" in update_data and update_data["state_id"]:
        state = db.query(State).filter(State.id == update_data["state_id"]).first()
        if state:
            db_dist.zone_id = state.zone_id

    db.commit()
    db.refresh(db_dist)
    return db_dist


@router.delete("/distributors/{dist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_distributor(
        dist_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    PermissionService.verify_internal_jurisdiction(db, current_user, Distributor, dist_id)

    db_dist = db.query(Distributor).filter(Distributor.id == dist_id).first()
    if not db_dist:
        raise HTTPException(status_code=404, detail="Distributor not found")
    db_dist.is_active = False
    db.commit()
    return None


@router.post("/retailers", response_model=RetailerRead, status_code=status.HTTP_201_CREATED)
def add_retailer(
        ret_in: RetailerCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    return create_retailer(db, ret_in)


@router.get("/retailers", response_model=list[RetailerRead])
def list_retailers(
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_partners"))
):
    query = db.query(Retailer)

    if not current_user.role: return []
    user_perms = [p.name for p in current_user.role.permissions]
    if "manage_roles" in user_perms: return query.all()

    if current_user.role.name == "Retailer":
        return query.filter(Retailer.user_id == current_user.id).all()
    elif current_user.role.name == "Distributor":
        dist = db.query(Distributor).filter(Distributor.user_id == current_user.id).first()
        if dist: return query.filter(Retailer.linked_distributor_id == dist.id).all()
    elif current_user.role.name == "SuperStockist":
        return []

    return PermissionService.apply_geo_filter(query, Retailer, current_user).all()


@router.patch("/retailers/{ret_id}", response_model=RetailerRead)
def update_retailer(
        ret_id: int,
        ret_in: RetailerUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    PermissionService.verify_internal_jurisdiction(db, current_user, Retailer, ret_id)

    retailer = db.query(Retailer).filter(Retailer.id == ret_id).first()
    if not retailer:
        raise HTTPException(status_code=404, detail="Retailer not found")

    update_data = ret_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(retailer, key, value)

    if "territory_id" in update_data and update_data["territory_id"]:
        territory = db.query(Territory).filter(Territory.id == update_data["territory_id"]).first()
        if territory:
            retailer.area_id = territory.area_id
            area = db.query(Area).filter(Area.id == territory.area_id).first()
            if area:
                retailer.region_id = area.region_id
                region = db.query(Region).filter(Region.id == area.region_id).first()
                if region:
                    retailer.state_id = region.state_id
                    state = db.query(State).filter(State.id == region.state_id).first()
                    if state:
                        retailer.zone_id = state.zone_id

    db.commit()
    db.refresh(retailer)
    return retailer


@router.delete("/retailers/{ret_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_retailer(
        ret_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    PermissionService.verify_internal_jurisdiction(db, current_user, Retailer, ret_id)

    db_ret = db.query(Retailer).filter(Retailer.id == ret_id).first()
    if not db_ret:
        raise HTTPException(status_code=404, detail="Retailer not found")

    db_ret.is_active = False
    db.commit()
    return None