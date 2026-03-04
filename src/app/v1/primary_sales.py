from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.app.core.database import get_db
from src.app.core.security import get_current_user, check_permissions
from src.app.models.user import User
from src.app.models.partner import SuperStockist, Distributor
from src.app.models.sales_primary import PrimaryOrder, PrimaryOrderItems
from src.app.schemas.orders import PrimaryOrderCreate, PrimaryOrderRead, DispatchPayload
from src.app.crud.primary_sales import create_primary_order
from src.app.services.order_service import OrderService
from src.app.services.permission_service import PermissionService
from sqlalchemy import or_, and_
router = APIRouter()


def verify_primary_ownership(db: Session, order: PrimaryOrder, current_user: User):
    role_name = current_user.role.name if current_user.role else ""
    if role_name == "SuperStockist":
        ss = db.query(SuperStockist).filter(SuperStockist.user_id == current_user.id).first()
        if not ss or (order.to_entity_id != ss.id and order.from_entity_id != ss.id):
            raise HTTPException(status_code=403, detail="Unauthorized: You do not own this order.")
    elif role_name == "Distributor":
        dist = db.query(Distributor).filter(Distributor.user_id == current_user.id).first()
        if not dist or order.to_entity_id != dist.id:
            raise HTTPException(status_code=403, detail="Unauthorized: You do not own this order.")
    else:
        target_model = SuperStockist if order.type == 'FACTORY_TO_SS' else Distributor
        PermissionService.verify_internal_jurisdiction(db, current_user, target_model, order.to_entity_id)


@router.get("/", response_model=list[PrimaryOrderRead])
def get_all_primary_orders(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    user_perms = [p.name for p in current_user.role.permissions] if current_user.role else []
    is_admin = "manage_roles" in user_perms

    if not is_admin and "view_own_orders" not in user_perms and "view_all_orders" not in user_perms:
        raise HTTPException(status_code=403, detail="Security Clearance Denied.")

    query = db.query(PrimaryOrder)
    role_name = current_user.role.name if current_user.role else ""

    if is_admin or "view_all_orders" in user_perms:
        return query.order_by(PrimaryOrder.id.desc()).all()

    if role_name == "SuperStockist":
        ss = db.query(SuperStockist).filter(SuperStockist.user_id == current_user.id).first()
        if ss:
            query = query.filter((PrimaryOrder.to_entity_id == ss.id) | (PrimaryOrder.from_entity_id == ss.id))
        return query.order_by(PrimaryOrder.id.desc()).all()

    elif role_name == "Distributor":
        distributor = db.query(Distributor).filter(Distributor.user_id == current_user.id).first()
        if distributor:
            query = query.filter(PrimaryOrder.to_entity_id == distributor.id)
        return query.order_by(PrimaryOrder.id.desc()).all()

    elif role_name == "Retailer":
        return []


    allowed_ss_query = db.query(SuperStockist.id)
    allowed_dist_query = db.query(Distributor.id)

    allowed_ss = PermissionService.apply_geo_filter(allowed_ss_query, SuperStockist, current_user).all()
    allowed_dist = PermissionService.apply_geo_filter(allowed_dist_query, Distributor, current_user).all()

    ss_ids = [s[0] for s in allowed_ss]
    dist_ids = [d[0] for d in allowed_dist]

    conditions = []
    if ss_ids:
        conditions.append(and_(PrimaryOrder.type == 'FACTORY_TO_SS', PrimaryOrder.to_entity_id.in_(ss_ids)))
    if dist_ids:
        conditions.append(
            and_(PrimaryOrder.type.in_(['FACTORY_TO_DB', 'SS_TO_DB']), PrimaryOrder.to_entity_id.in_(dist_ids)))

    if conditions:
        query = query.filter(or_(*conditions))
    else:
        return []

    return query.order_by(PrimaryOrder.id.desc()).all()


@router.post("/", response_model=PrimaryOrderRead, status_code=status.HTTP_201_CREATED)
def place_primary_order(
        order_in: PrimaryOrderCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("create_primary_order"))
):
    # Spoofing Protection
    role_name = current_user.role.name if current_user.role else ""
    if role_name == "SuperStockist":
        ss = db.query(SuperStockist).filter(SuperStockist.user_id == current_user.id).first()
        if not ss or (order_in.from_entity_id != ss.id and order_in.to_entity_id != ss.id):
            raise HTTPException(status_code=403, detail="Spoofing detected: Cannot place order for another entity.")

        elif role_name == "Distributor":
            dist = db.query(Distributor).filter(Distributor.user_id == current_user.id).first()
            if not dist or (order_in.from_entity_id != dist.id and order_in.to_entity_id != dist.id):
                raise HTTPException(status_code=403, detail="Spoofing detected: Cannot place order for another entity.")

    try:
        db_order = create_primary_order(db, order_in)
        db.commit()
        db.refresh(db_order)
        return db_order
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/dispatch")
def dispatch_order(
        order_id: int,
        dispatch_data: DispatchPayload,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("dispatch_order"))
):
    order = db.query(PrimaryOrder).filter(PrimaryOrder.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    verify_primary_ownership(db, order, current_user)

    try:
        return OrderService.dispatch_primary_order(db, order_id, dispatch_data)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/receive")
def receive_order(
        order_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("receive_order"))
):
    order = db.query(PrimaryOrder).filter(PrimaryOrder.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    verify_primary_ownership(db, order, current_user)

    return OrderService.receive_primary_order(db, order_id)


@router.put("/{order_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_primary_order(
        order_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("cancel_order"))
):
    order = db.query(PrimaryOrder).filter(PrimaryOrder.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    verify_primary_ownership(db, order, current_user)

    if order.status != "Pending":
        raise HTTPException(status_code=400, detail=f"Cannot cancel order in '{order.status}' status.")

    order.status = "Cancelled"
    db.commit()
    return {"message": f"Order {order.order_number} cancelled."}


@router.put("/{order_id}", status_code=status.HTTP_200_OK)
def update_primary_order(
        order_id: int,
        update_in: PrimaryOrderCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("update_order"))
):
    order = db.query(PrimaryOrder).filter(PrimaryOrder.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    verify_primary_ownership(db, order, current_user)

    if order.status != "Pending":
        raise HTTPException(status_code=400, detail="Cannot update non-pending order.")

    db.query(PrimaryOrderItems).filter(PrimaryOrderItems.primary_order_id == order_id).delete()
    db.flush()

    for item in update_in.items:
        new_item = PrimaryOrderItems(
            primary_order_id=order.id, product_id=item.product_id, batch_number=item.batch_number,
            quantity_cases=item.quantity, dispatched_cases=0, backordered_cases=0, free_cases=0
        )
        db.add(new_item)

    db.commit()
    return {"message": f"Order {order.order_number} updated successfully."}