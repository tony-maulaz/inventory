from datetime import datetime, date, time
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, validator


class SecurityLevel(str, Enum):
    standard = "standard"
    avance = "avance"
    critique = "critique"


class RoleName(str, Enum):
    employee = "employee"
    gestionnaire = "gestionnaire"
    expert = "expert"
    admin = "admin"


class DeviceTypeBase(BaseModel):
    name: str
    description: Optional[str] = None


class DeviceTypeCreate(DeviceTypeBase):
    pass


class DeviceTypeRead(DeviceTypeBase):
    id: int

    class Config:
        orm_mode = True


class DeviceStatusBase(BaseModel):
    name: str


class DeviceStatusCreate(DeviceStatusBase):
    pass


class DeviceStatusRead(DeviceStatusBase):
    id: int

    class Config:
        orm_mode = True


class DeviceBase(BaseModel):
    inventory_number: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    description: Optional[str] = None
    location: Optional[str] = None
    type_id: int
    status_id: int
    security_level: SecurityLevel = SecurityLevel.standard

    @validator("inventory_number", "name", pre=True)
    def strip_device_text(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    inventory_number: Optional[str] = Field(None, min_length=2)
    name: Optional[str] = Field(None, min_length=2)
    description: Optional[str] = None
    location: Optional[str] = None
    type_id: Optional[int] = None
    status_id: Optional[int] = None
    security_level: Optional[SecurityLevel] = None

    @validator("inventory_number", "name", pre=True)
    def strip_device_text(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class DeviceRead(DeviceBase):
    id: int
    type: DeviceTypeRead
    status: DeviceStatusRead
    current_loan: Optional["LoanRead"] = None

    class Config:
        orm_mode = True


class LoanBase(BaseModel):
    device_id: int
    borrower_id: int
    borrower_display_name: Optional[str] = None
    usage_location: Optional[str] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None

    @validator("due_date", pre=True)
    def parse_due_date(cls, v):
        if v in (None, "", "null"):
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime.combine(v, time.min)
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                try:
                    # Handle date-only strings (YYYY-MM-DD)
                    d = date.fromisoformat(v)
                    return datetime.combine(d, time.min)
                except ValueError:
                    raise
        return v


class LoanCreate(LoanBase):
    pass


class LoanReturn(BaseModel):
    device_id: int
    notes: Optional[str] = None


class LoanRead(BaseModel):
    id: int
    device_id: int
    borrower_id: int
    borrower_display_name: Optional[str] = None
    usage_location: Optional[str] = None
    loaned_at: datetime
    due_date: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        orm_mode = True


class ScanDecision(BaseModel):
    device_id: int
    inventory_number: str
    action: str  # "loan" or "return"
    status: str


class ScanRequest(BaseModel):
    inventory_number: str


class PagedResult(BaseModel):
    total: int
    items: List[DeviceRead]


class UserRead(BaseModel):
    username: str
    display_name: Optional[str] = None
    roles: List[str] = []

    class Config:
        orm_mode = True


class UserRoleRead(BaseModel):
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    roles: List[str] = []

    class Config:
        orm_mode = True


class UserRoleUpdate(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: List[RoleName]


# Resolve forward refs
LoanRead.update_forward_refs()
DeviceRead.update_forward_refs()
