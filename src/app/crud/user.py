from sqlalchemy.orm import Session
from passlib.context import CryptContext
from src.app.models.user import User, Role, Permission
from src.app.schemas.user import UserCreate, UserUpdate
from src.app.models.geography import Territory, Area, Region, State

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    user_data = user.model_dump()
    user_data["password_hash"] = hashed_password

    del user_data["password"]
    if user_data.get("assigned_territory_id"):
        territory = db.query(Territory).filter(Territory.id == user_data["assigned_territory_id"]).first()
        if territory:
            user_data["assigned_area_id"] = territory.area_id
            area = db.query(Area).filter(Area.id == territory.area_id).first()
            if area:
                user_data["assigned_region_id"] = area.region_id
                region = db.query(Region).filter(Region.id == area.region_id).first()
                if region:
                    user_data["assigned_state_id"] = region.state_id
                    state = db.query(State).filter(State.id == region.state_id).first()
                    if state:
                        user_data["assigned_zone_id"] = state.zone_id

    db_user = User(**user_data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()


def update_user(db: Session, user_id: int, user_in: UserUpdate):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None

    update_data = user_in.model_dump(exclude_unset=True)

    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data["password"])
        del update_data["password"]

    if update_data.get("assigned_territory_id"):
        territory = db.query(Territory).filter(Territory.id == update_data["assigned_territory_id"]).first()
        if territory:
            update_data["assigned_area_id"] = territory.area_id
            area = db.query(Area).filter(Area.id == territory.area_id).first()
            if area:
                update_data["assigned_region_id"] = area.region_id
                region = db.query(Region).filter(Region.id == area.region_id).first()
                if region:
                    update_data["assigned_state_id"] = region.state_id
                    state = db.query(State).filter(State.id == region.state_id).first()
                    if state:
                        update_data["assigned_zone_id"] = state.zone_id

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.is_active = False  # Soft delete
        db.commit()
        return True
    return False



def create_role(db: Session, role_in):
    db_role = Role(name=role_in.name, description=role_in.description)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role


def get_roles(db: Session):
    return db.query(Role).all()


def update_role(db: Session, role_id: int, role_in):
    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        return None
    db_role.name = role_in.name
    db_role.description = role_in.description
    db.commit()
    db.refresh(db_role)
    return db_role


def delete_role(db: Session, role_id: int):
    db_role = db.query(Role).filter(Role.id == role_id).first()
    if db_role:
        db.delete(db_role)
        db.commit()
        return True
    return False



def get_all_permissions(db: Session):
    return db.query(Permission).all()


def update_role_permissions(db: Session, role_id: int, permission_ids: list[int]):
    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        return None

    if db_role.name.lower() == "admin":
        raise ValueError("Cannot modify permissions for the master Admin role.")

    db_role.permissions = []
    db.flush()

    if permission_ids:
        perms = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        db_role.permissions.extend(perms)

    db.commit()
    db.refresh(db_role)
    return db_role