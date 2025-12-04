from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..dependencies import get_db, get_user

router = APIRouter(prefix="/loans", tags=["loans"])

STATUS_AVAILABLE = "available"
STATUS_LOANED = "loaned"
STATUS_MAINTENANCE = "maintenance"


def _get_status(db: Session, name: str):
    status = crud.get_status_by_name(db, name)
    if not status:
        raise HTTPException(
            status_code=500, detail=f"Status '{name}' not found. Run init_db."
        )
    return status


@router.get("/", response_model=list[schemas.LoanRead])
def list_loans(db: Session = Depends(get_db), user=Depends(get_user)):
    return db.scalars(select(models.Loan).order_by(models.Loan.loaned_at.desc())).all()


@router.post("/loan", response_model=schemas.LoanRead)
def loan_device(
    payload: schemas.LoanCreate, db: Session = Depends(get_db), user=Depends(get_user)
):
    status_loaned = _get_status(db, STATUS_LOANED)
    status_maintenance = _get_status(db, STATUS_MAINTENANCE)
    try:
        return crud.create_loan(
            db,
            payload,
            status_loaned=status_loaned,
            status_maintenance=status_maintenance,
            user_roles=user.get("roles", []),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/return", response_model=schemas.LoanRead)
def return_device(
    payload: schemas.LoanReturn, db: Session = Depends(get_db), user=Depends(get_user)
):
    status_available = _get_status(db, STATUS_AVAILABLE)
    status_maintenance = _get_status(db, STATUS_MAINTENANCE)
    try:
        return crud.close_loan(
            db,
            payload,
            status_available=status_available,
            status_maintenance=status_maintenance,
            user_roles=user.get("roles", []),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/scan", response_model=schemas.ScanDecision)
def scan_inventory_number(
    payload: schemas.ScanRequest, db: Session = Depends(get_db), user=Depends(get_user)
):
    device = crud.get_device_by_inventory(db, payload.inventory_number)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    status_available = _get_status(db, STATUS_AVAILABLE)
    try:
        crud._check_security(device, user.get("roles", []))
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    action = "loan" if device.status_id == status_available.id else "return"
    return schemas.ScanDecision(
        device_id=device.id,
        inventory_number=device.inventory_number,
        action=action,
        status=device.status.name,
    )
