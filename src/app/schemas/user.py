from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class UserBase(BaseModel):
    username: str
    is_active: bool = True
    email : Optional[str] = None
    phone_number: Optional[str] = None
    role_id: Optional[int] = None
    assigned_zone_id: Optional[int] = None
    assigned_region_id: Optional[int] = None
    assigned_area_id: Optional[int] = None
    assigned_territory_id: Optional[int] = None
    assigned_state_id: Optional[int] = None

class UserCreate(UserBase):
    password: str
    role_id: int

class UserRead(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role_id: Optional[int] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    assigned_zone_id: Optional[int] = None
    assigned_region_id: Optional[int] = None
    assigned_area_id: Optional[int] = None
    assigned_territory_id: Optional[int] = None
    assigned_state_id : Optional[int] = None

class PermissionRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleRead(RoleBase):
    id: int
    permissions: List[PermissionRead] = []
    model_config = ConfigDict(from_attributes=True)

class RolePermissionUpdate(BaseModel):
    permission_ids: List[int]