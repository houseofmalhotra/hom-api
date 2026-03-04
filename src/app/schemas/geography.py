from pydantic import BaseModel, ConfigDict
from typing import Optional

class GeoBase(BaseModel):
    name: str

class ZoneCreate(GeoBase):
    pass

class StateCreate(GeoBase):
    zone_id: int

class RegionCreate(GeoBase):
    state_id: int

class AreaCreate(GeoBase):
    region_id: int

class TerritoryCreate(GeoBase):
    area_id: int

class ZoneRead(GeoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class StateRead(GeoBase):
    id: int
    zone_id: int
    model_config = ConfigDict(from_attributes=True)

class RegionRead(GeoBase):
    id: int
    state_id: int
    model_config = ConfigDict(from_attributes=True)

class AreaRead(GeoBase):
    id: int
    region_id: int
    model_config = ConfigDict(from_attributes=True)

class TerritoryRead(GeoBase):
    id: int
    area_id: int
    model_config = ConfigDict(from_attributes=True)

class ZoneUpdate(BaseModel):
    name: Optional[str] = None

class StateUpdate(BaseModel):
    name: Optional[str] = None
    zone_id: Optional[int] = None