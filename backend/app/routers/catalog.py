from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import crud, schemas, models
from ..dependencies import get_db, get_user

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/types", response_model=list[schemas.DeviceTypeRead])
def list_types(db: Session = Depends(get_db), user=Depends(get_user)):
    return crud.list_device_types(db)


@router.post("/types", response_model=schemas.DeviceTypeRead)
def create_type(payload: schemas.DeviceTypeCreate, db: Session = Depends(get_db), user=Depends(get_user)):
    return crud.create_device_type(db, payload)


@router.get("/statuses", response_model=list[schemas.DeviceStatusRead])
def list_statuses(db: Session = Depends(get_db), user=Depends(get_user)):
    return crud.list_statuses(db)


@router.post("/statuses", response_model=schemas.DeviceStatusRead)
def create_status(payload: schemas.DeviceStatusCreate, db: Session = Depends(get_db), user=Depends(get_user)):
    return crud.create_status(db, payload)


@router.get("/users", response_model=list[schemas.UserRead])
def list_users(db: Session = Depends(get_db), user=Depends(get_user)):
    # Only intended for dev/test; returns seeded test users with roles list.
    test_users = db.scalars(select(models.TestUser)).all()

    def _roles(u: models.TestUser):
        # Accept legacy string values just in case.
        if isinstance(u.roles, str):
            return [part.strip() for part in u.roles.split(",") if part.strip()]
        return u.roles_list

    return [
        schemas.UserRead(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            roles=_roles(u),
        )
        for u in test_users
    ]
