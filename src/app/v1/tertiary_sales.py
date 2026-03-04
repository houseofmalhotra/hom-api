from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.app.core.database import get_db
from src.app.core.security import get_current_user, check_permissions
from src.app.models.user import User
from src.app.models.sales_tertiary import TertiaryOrder
from src.app.models.partner import Retailer

from src.app.schemas.orders import TertiaryOrderCreate
from src.app.schemas.partner import EndConsumerCreate, EndConsumerRead, EndConsumerUpdate

from src.app.services.permission_service import PermissionService
from src.app.services.order_service import OrderService

from src.app.crud.tertiary_sales import (
    create_tertiary_sale,
    get_tertiary_orders_by_so,
    get_scoped_pending_orders,
    create_end_consumer,
    get_end_consumers,
    update_end_consumer,
    delete_end_consumer
)

router = APIRouter()



def verify_tertiary_ownership(db: Session, order: TertiaryOrder, current_user: User):
    role_name = current_user.role.name if current_user.role else ""
    if role_name == "Retailer":
        ret = db.query(Retailer).filter(Retailer.user_id == current_user.id).first()
        if not ret or order.fulfilled_by_retailer_id != ret.id:
            raise HTTPException(status_code=403, detail="Unauthorized: You do not own this order.")


@router.get("/")
def get_all_tertiary_orders(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Fetch Tertiary Orders scoped dynamically based on user role and geography."""
    user_perms = [p.name for p in current_user.role.permissions] if current_user.role else []
    is_admin = "manage_roles" in user_perms

    if not is_admin and "view_own_orders" not in user_perms and "view_all_orders" not in user_perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Security Clearance Denied. Requires order viewing permission.")

    query = db.query(TertiaryOrder)

    if not current_user.role:
        return []

    role_name = current_user.role.name

    if is_admin or "view_all_orders" in user_perms:
        return query.order_by(TertiaryOrder.id.desc()).all()

    if role_name == "Retailer":
        retailer = db.query(Retailer).filter(Retailer.user_id == current_user.id).first()
        if not retailer: return []  # Fail-Closed
        query = query.filter(TertiaryOrder.fulfilled_by_retailer_id == retailer.id)
        return query.order_by(TertiaryOrder.id.desc()).all()

    elif role_name in ["SuperStockist", "Distributor"]:
        return []

    else:
        query = query.join(Retailer, TertiaryOrder.fulfilled_by_retailer_id == Retailer.id)
        query = PermissionService.apply_geo_filter(query, Retailer, current_user)
        query = query.with_entities(TertiaryOrder)
        return query.order_by(TertiaryOrder.id.desc()).all()


@router.get("/pending")
def get_my_pending_requests(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    user_perms = [p.name for p in current_user.role.permissions] if current_user.role else []
    is_admin = "manage_roles" in user_perms

    if not is_admin and "view_own_orders" not in user_perms and "view_all_orders" not in user_perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Security Clearance Denied.")

    query = db.query(TertiaryOrder).filter(TertiaryOrder.status.in_(["PENDING", "Pending"]))
    role_name = current_user.role.name if current_user.role else ""

    if role_name == "Retailer":
        retailer = db.query(Retailer).filter(Retailer.user_id == current_user.id).first()
        if not retailer: return []
        return query.filter(TertiaryOrder.fulfilled_by_retailer_id == retailer.id).all()

    query = query.join(Retailer, TertiaryOrder.fulfilled_by_retailer_id == Retailer.id)
    query = PermissionService.apply_geo_filter(query, Retailer, current_user)
    query = query.with_entities(TertiaryOrder)
    return query.order_by(TertiaryOrder.id.desc()).all()


@router.post("/", status_code=status.HTTP_201_CREATED)
def record_tertiary_sale(
        sale_in: TertiaryOrderCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("create_tertiary_order"))
):
    """
    Consumer or Retailer logs a sale.
    This is just a 'request' until approved by the Sales Officer (SO).
    """
    role_name = current_user.role.name if current_user.role else ""
    retailer = db.query(Retailer).filter(Retailer.id == sale_in.fulfilled_by_retailer_id).first()

    if role_name == "Retailer":
        if not retailer or retailer.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Spoofing detected.")

    new_sale = create_tertiary_sale(db, sale_in)

    if retailer:
        new_sale.zone_id = retailer.zone_id
        new_sale.state_id = retailer.state_id
        new_sale.region_id = retailer.region_id
        new_sale.area_id = retailer.area_id
        new_sale.territory_id = retailer.territory_id
        db.commit()

    return {"message": "Tertiary sale logged successfully", "order_id": new_sale.id}


@router.get("/so/{so_id}/pending")
def get_pending_requests(
        so_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Fetch pending sales for a specific Sales Officer to review."""
    user_perms = [p.name for p in current_user.role.permissions] if current_user.role else []
    is_admin = "manage_roles" in user_perms

    if not is_admin and "view_own_orders" not in user_perms and "view_all_orders" not in user_perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Security Clearance Denied.")

    return get_tertiary_orders_by_so(db, so_id)


@router.patch("/{order_id}/approve")
def approve_tertiary_order(
        order_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("approve_order"))
):
    """
    Approves the sale and DEDUCTS stock from the Retailer. Only permitted SO can execute.
    """
    return OrderService.approve_tertiary_order(db, order_id, current_user)


@router.get("/pending")
def get_my_pending_requests(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    user_perms = [p.name for p in current_user.role.permissions] if current_user.role else []
    is_admin = "manage_roles" in user_perms

    if not is_admin and "view_own_orders" not in user_perms and "view_all_orders" not in user_perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Security Clearance Denied.")

    query = db.query(TertiaryOrder).filter(TertiaryOrder.status.in_(["PENDING", "Pending"]))
    role_name = current_user.role.name if current_user.role else ""

    if role_name == "Retailer":
        retailer = db.query(Retailer).filter(Retailer.user_id == current_user.id).first()
        if not retailer: return []
        return query.filter(TertiaryOrder.fulfilled_by_retailer_id == retailer.id).all()

    query = query.join(Retailer, TertiaryOrder.fulfilled_by_retailer_id == Retailer.id)
    query = PermissionService.apply_geo_filter(query, Retailer, current_user)
    return query.order_by(TertiaryOrder.id.desc()).all()


@router.post("/consumers", response_model=EndConsumerRead, status_code=status.HTTP_201_CREATED)
def register_end_consumer(
        consumer_in: EndConsumerCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    return create_end_consumer(db, consumer_in)


@router.get("/consumers", response_model=list[EndConsumerRead])
def list_end_consumers(
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("view_partners"))
):
    return get_end_consumers(db)


@router.patch("/consumers/{consumer_id}", response_model=EndConsumerRead)
def modify_end_consumer(
        consumer_id: int,
        consumer_in: EndConsumerUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    updated = update_end_consumer(db, consumer_id, consumer_in)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="End Consumer not found")
    return updated


@router.delete("/consumers/{consumer_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_end_consumer(
        consumer_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_partners"))
):
    success = delete_end_consumer(db, consumer_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="End Consumer not found")
    return None


@router.put("/{order_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_tertiary_order(
        order_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("cancel_order"))
):
    """Cancels a tertiary order if it is still pending."""
    order = db.query(TertiaryOrder).filter(TertiaryOrder.id == order_id).first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tertiary Order not found")

    verify_tertiary_ownership(db, order, current_user)

    if order.status not in ["Pending", "PENDING"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order. Current status is '{order.status}'."
        )

    order.status = "Cancelled"
    db.commit()
    return {"message": f"Tertiary Order {order.id} has been cancelled successfully."}


@router.put("/{order_id}", status_code=status.HTTP_200_OK)
def update_tertiary_order(
        order_id: int,
        update_in: TertiaryOrderCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("update_order"))
):
    """Updates the tertiary order before fulfillment."""
    order = db.query(TertiaryOrder).filter(TertiaryOrder.id == order_id).first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tertiary Order not found")

    verify_tertiary_ownership(db, order, current_user)

    if order.status not in ["Pending", "PENDING"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update order in '{order.status}' status."
        )

    order.end_consumer_id = update_in.end_consumer_id
    order.fulfilled_by_retailer_id = update_in.fulfilled_by_retailer_id
    order.assigned_so_id = update_in.assigned_so_id
    order.product_id = update_in.product_id
    order.quantity = update_in.quantity
    order.batch_number = update_in.batch_number

    db.commit()
    return {"message": f"Tertiary Order {order.id} updated successfully."}