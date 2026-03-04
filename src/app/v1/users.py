from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.app.core.database import get_db
from src.app.core.security import check_permissions, get_current_user

from src.app.models.user import User, Role, Permission
from src.app.schemas.user import (
    UserCreate, UserRead, UserUpdate,
    RoleCreate, RoleRead, RolePermissionUpdate, PermissionRead
)
from src.app.crud.user import (
    create_user, create_role, get_all_permissions, update_role_permissions
)

router = APIRouter()

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def add_new_user(
        user_in: UserCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_users"))
):
    return create_user(db, user_in)

@router.get("/", response_model=list[UserRead])
def list_users(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return db.query(User).all()

@router.patch("/{user_id}", response_model=UserRead)
def edit_user(
        user_id: int,
        user_in: UserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_users"))
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permissions("manage_users"))
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.is_active = False
    db.commit()
    return None

@router.post("/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def add_new_role(
    role_in: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permissions("manage_roles"))
):
    return create_role(db, role_in)

@router.get("/roles", response_model=list[RoleRead])
def list_roles_and_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Role).all()

@router.get("/permissions", response_model=list[PermissionRead])
def list_available_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_all_permissions(db)

@router.put("/roles/{role_id}/permissions", response_model=RoleRead)
def modify_role_permissions(
    role_id: int,
    perm_in: RolePermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permissions("manage_roles"))
):
    try:
        role = update_role_permissions(db, role_id, perm_in.permission_ids)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/me", response_model=UserRead)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Fetch the profile and role details of the currently logged-in user."""
    return current_user


@router.post("/seed-permissions", status_code=status.HTTP_201_CREATED)
def seed_default_permissions(db: Session = Depends(get_db)):
    """Run this ONCE to populate your database with the permission checkboxes"""

    default_permissions = [
        {"name": "view_dashboard", "description": "Can access the main dashboard"},
        {"name": "view_inventory", "description": "Can view stock levels"},
        {"name": "manage_inventory", "description": "Can adjust or add stock"},
        {"name": "view_own_orders", "description": "Can view orders assigned to their geo-scope"},
        {"name": "view_all_orders", "description": "Can view ALL company orders (Admin/ZSM level)"},
        {"name": "create_primary_order", "description": "Can place primary factory orders"},
        {"name": "create_secondary_order", "description": "Can place secondary orders to retailers"},
        {"name": "create_tertiary_order", "description": "Can register consumers and place tertiary orders"},
        {"name": "manage_users", "description": "Can create and edit user accounts"},
        {"name": "manage_roles", "description": "Can create and edit roles and permissions"}
    ]

    added = 0
    for p in default_permissions:
        exists = db.query(Permission).filter(Permission.name == p["name"]).first()
        if not exists:
            new_perm = Permission(name=p["name"], description=p["description"])
            db.add(new_perm)
            added += 1

    db.commit()
    return {"message": f"Successfully added {added} new permissions to the Matrix."}