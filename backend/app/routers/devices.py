from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_db, get_user

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("/", response_model=schemas.PagedResult)
@router.get(
    "", include_in_schema=False
)  # allow /devices without trailing slash (avoid 307 redirect)
def list_devices(
    search: str | None = Query(
        default=None, description="Recherche par nom, numéro ou type"
    ),
    status_id: int | None = None,
    type_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user=Depends(get_user),
):
    total, items = crud.list_devices(
        db, search=search, status_id=status_id, type_id=type_id, skip=skip, limit=limit
    )
    return {"total": total, "items": items}


@router.post(
    "/", response_model=schemas.DeviceRead, status_code=status.HTTP_201_CREATED
)
@router.post(
    "", response_model=schemas.DeviceRead, status_code=status.HTTP_201_CREATED, include_in_schema=False
)
def create_device(
    device: schemas.DeviceCreate, db: Session = Depends(get_db), user=Depends(get_user)
):
    existing = crud.get_device_by_inventory(db, device.inventory_number)
    if existing:
        raise HTTPException(status_code=400, detail="Inventory number already exists")
    return crud.create_device(db, device)


@router.get("/{device_id}", response_model=schemas.DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db), user=Depends(get_user)):
    device = crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.put("/{device_id}", response_model=schemas.DeviceRead)
def update_device(
    device_id: int,
    payload: schemas.DeviceUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_user),
):
    device = crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return crud.update_device(db, device, payload)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int, db: Session = Depends(get_db), user=Depends(get_user)
):
    device = crud.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    crud.delete_device(db, device)
    return None
