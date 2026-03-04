from pydantic import BaseModel, ConfigDict
from typing import Optional
from decimal import Decimal

class SuperStockistBase(BaseModel):
    zone_id: int
    firm_name: str
    contact_number: Optional[str] = None
    gstin: Optional[str] = None
    contact_person: Optional[str] = None
    user_id: Optional[int] = None
    is_active: Optional[bool] = True
    user_id: Optional[int] = None

class SuperStockistCreate(SuperStockistBase):
    pass

class SuperStockistRead(SuperStockistBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
    outstanding_balance: Optional[Decimal] = 0.00

class DistributorBase(BaseModel):
    state_id: int
    parent_ss_id: Optional[int] = None
    is_direct_party: Optional[bool] = False
    firm_name: Optional[str] = None
    contact_person : Optional[str] = None
    contact_number: Optional[str] = None
    gstin: Optional[str] = None
    user_id: Optional[int] = None
    is_active: Optional[bool] = True
    user_id: Optional[int] = None

class DistributorCreate(DistributorBase):
    pass

class DistributorRead(DistributorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
    outstanding_balance: Optional[Decimal] = 0.00


class RetailerBase(BaseModel):
    territory_id: int
    linked_distributor_id: Optional[int] = None
    shop_name: Optional[str] = None
    # shop_type: Optional[str] = None
    contact_number: Optional[str] = None
    contact_person: Optional[str] = None
    gstin: Optional[str] = None
    user_id: Optional[int] = None
    is_active: Optional[bool] = True

class RetailerCreate(RetailerBase):
    pass

class RetailerRead(RetailerBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
    outstanding_balance: Optional[Decimal] = 0.00


class EndConsumerBase(BaseModel):
    territory_id: int
    name: str
    type: Optional[str] = None
    mobile_number: Optional[str] = None
    is_active: Optional[bool] = True
    contact_person: Optional[str] = None
    address: Optional[str] = None

class EndConsumerCreate(EndConsumerBase):
    pass

class EndConsumerUpdate(BaseModel):
    territory_id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None
    mobile_number: Optional[str] = None
    is_active: Optional[bool] = None

class EndConsumerRead(EndConsumerBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
    outstanding_balance: Optional[Decimal] = 0.00

class SuperStockistUpdate(BaseModel):
    zone_id: Optional[int] = None
    firm_name: Optional[str] = None
    contact_number: Optional[str] = None
    contact_person: Optional[str] = None
    gstin: Optional[str] = None
    user_id: Optional[int] = None
    is_active: Optional[bool] = None
    user_id: Optional[int] = None

class DistributorUpdate(BaseModel):
    state_id: Optional[int] = None
    parent_ss_id: Optional[int] = None
    is_direct_party: Optional[bool] = None
    firm_name: Optional[str] = None
    contact_person: Optional[str] = None
    contact_number: Optional[str] = None
    gstin: Optional[str] = None
    user_id: Optional[int] = None
    is_active: Optional[bool] = None
    user_id: Optional[int] = None

class RetailerUpdate(BaseModel):
    territory_id: Optional[int] = None
    linked_distributor_id: Optional[int] = None
    shop_name: Optional[str] = None
    shop_type: Optional[str] = None
    contact_person: Optional[str] = None
    contact_number: Optional[str] = None
    gstin: Optional[str] = None
    user_id: Optional[int] = None
    is_active: Optional[bool] = None