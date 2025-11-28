from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session

from . import models, schemas


def get_device(db: Session, device_id: int) -> Optional[models.Device]:
    return db.get(models.Device, device_id)


def get_device_by_inventory(db: Session, inventory_number: str) -> Optional[models.Device]:
    stmt = select(models.Device).where(models.Device.inventory_number == inventory_number)
    return db.scalar(stmt)


def list_devices(
    db: Session,
    search: Optional[str] = None,
    status_id: Optional[int] = None,
    type_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[int, List[models.Device]]:
    stmt = select(models.Device).join(models.Device.type).join(models.Device.status)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                models.Device.name.ilike(like),
                models.Device.inventory_number.ilike(like),
                models.Device.description.ilike(like),
                models.DeviceType.name.ilike(like),
            )
        )
    if status_id:
        stmt = stmt.where(models.Device.status_id == status_id)
    if type_id:
        stmt = stmt.where(models.Device.type_id == type_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.offset(skip).limit(limit)).all()

    # Attach open loans info (current loan) for each device
    device_ids = [d.id for d in items]
    if device_ids:
        loan_stmt = (
            select(models.Loan)
            .where(models.Loan.device_id.in_(device_ids), models.Loan.returned_at.is_(None))
            .order_by(models.Loan.loaned_at.desc())
        )
        loans = db.scalars(loan_stmt).all()
        latest_open = {}
        for loan in loans:
            if loan.device_id not in latest_open:
                latest_open[loan.device_id] = loan
        for d in items:
            if d.id in latest_open:
                setattr(d, "current_loan", latest_open[d.id])
    return total, items


def create_device(db: Session, device: schemas.DeviceCreate) -> models.Device:
    db_device = models.Device(**device.dict())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


def update_device(db: Session, db_device: models.Device, payload: schemas.DeviceUpdate) -> models.Device:
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(db_device, key, value)
    db.commit()
    db.refresh(db_device)
    return db_device


def delete_device(db: Session, db_device: models.Device) -> None:
    db.delete(db_device)
    db.commit()


def list_device_types(db: Session) -> List[models.DeviceType]:
    return db.scalars(select(models.DeviceType)).all()


def create_device_type(db: Session, payload: schemas.DeviceTypeCreate) -> models.DeviceType:
    obj = models.DeviceType(**payload.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_statuses(db: Session) -> List[models.DeviceStatus]:
    return db.scalars(select(models.DeviceStatus)).all()


def get_status_by_name(db: Session, name: str) -> Optional[models.DeviceStatus]:
    return db.scalar(select(models.DeviceStatus).where(models.DeviceStatus.name == name))


def create_status(db: Session, payload: schemas.DeviceStatusCreate) -> models.DeviceStatus:
    obj = models.DeviceStatus(**payload.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def create_loan(db: Session, payload: schemas.LoanCreate, status_loaned: models.DeviceStatus) -> models.Loan:
    device = db.get(models.Device, payload.device_id)
    if not device:
        raise ValueError("Device not found")
    if device.status_id == status_loaned.id:
        raise ValueError("Device already loaned")

    loan = models.Loan(**payload.dict())
    device.status_id = status_loaned.id
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def close_loan(
    db: Session, payload: schemas.LoanReturn, status_available: models.DeviceStatus
) -> models.Loan:
    device = db.get(models.Device, payload.device_id)
    if not device:
        raise ValueError("Device not found")

    loan_stmt = (
        select(models.Loan)
        .where(models.Loan.device_id == payload.device_id, models.Loan.returned_at.is_(None))
        .order_by(models.Loan.loaned_at.desc())
    )
    loan = db.scalar(loan_stmt)
    if not loan:
        raise ValueError("No open loan for device")

    loan.returned_at = datetime.utcnow()
    if payload.notes:
        loan.notes = payload.notes
    device.status_id = status_available.id
    db.commit()
    db.refresh(loan)
    return loan


def get_open_loan(db: Session, device_id: int) -> Optional[models.Loan]:
    stmt = (
        select(models.Loan)
        .where(models.Loan.device_id == device_id, models.Loan.returned_at.is_(None))
        .order_by(models.Loan.loaned_at.desc())
    )
    return db.scalar(stmt)
