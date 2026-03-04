from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from src.app.core.database import Base
from sqlalchemy import Table

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)

    role_id = Column(Integer, ForeignKey("roles.id"))

    assigned_zone_id = Column(Integer, ForeignKey("zone.id"), nullable=True)
    assigned_region_id = Column(Integer, ForeignKey("region.id"), nullable=True)
    assigned_area_id = Column(Integer, ForeignKey("area.id"), nullable=True)
    assigned_territory_id = Column(Integer, ForeignKey("territory.id"), nullable=True)
    assigned_state_id = Column(Integer, ForeignKey("state.id"), nullable=True)

    zone = relationship("Zone")
    region = relationship("Region")
    area = relationship("Area")
    territory = relationship("Territory")
    state = relationship("State")

    role = relationship("Role")


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)

    description = Column(String(255), nullable=True)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True)

    description = Column(String(255), nullable=True)

    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")