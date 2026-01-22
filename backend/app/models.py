from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    users = relationship("User", secondary="user_roles", back_populates="roles")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(200), nullable=True)
    first_name = Column(String(200), nullable=True)
    last_name = Column(String(200), nullable=True)

    roles = relationship("Role", secondary="user_roles", back_populates="users")
    loans = relationship("Loan", back_populates="borrower")

    @property
    def display_name(self) -> str:
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else self.username


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id = Column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )


class DeviceType(Base):
    __tablename__ = "device_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    devices = relationship("Device", back_populates="type")


class DeviceStatus(Base):
    __tablename__ = "device_statuses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    devices = relationship("Device", back_populates="status")


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("inventory_number", name="uq_inventory_number"),)

    id = Column(Integer, primary_key=True, index=True)
    inventory_number = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(200), nullable=True)
    type_id = Column(Integer, ForeignKey("device_types.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("device_statuses.id"), nullable=False)
    security_level = Column(
        String(20), nullable=False, default="standard", server_default="standard"
    )

    type = relationship("DeviceType", back_populates="devices")
    status = relationship("DeviceStatus", back_populates="devices")
    loans = relationship("Loan", back_populates="device", cascade="all, delete-orphan")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    borrower_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    borrower_display_name = Column(String(200), nullable=True)
    usage_location = Column(String(200), nullable=True)
    loaned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=True)
    returned_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    device = relationship("Device", back_populates="loans")
    borrower = relationship("User", back_populates="loans")


class TestUser(Base):
    __tablename__ = "test_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=True)
    roles = Column(String(200), default="", nullable=False)  # comma-separated roles

    @property
    def roles_list(self):
        if not self.roles:
            return []
        return [part.strip() for part in self.roles.split(",") if part.strip()]
