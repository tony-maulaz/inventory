from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_db, get_user

router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(user):
    roles = set(user.get("roles", []))
    if "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


@router.get("/", response_model=List[schemas.UserRoleRead])
def list_users(db: Session = Depends(get_db), user=Depends(get_user)):
    _require_admin(user)
    crud.ensure_roles_exist(db)
    records = crud.list_user_roles(db)
    return [schemas.UserRoleRead(username=r.username, display_name=r.display_name, roles=r.roles_list) for r in records]


@router.put("/{username}", response_model=schemas.UserRoleRead)
def upsert_user_roles(username: str, payload: schemas.UserRoleUpdate, db: Session = Depends(get_db), user=Depends(get_user)):
    _require_admin(user)
    crud.ensure_roles_exist(db)
    record = crud.upsert_user_roles(db, username=username, roles=payload.roles, display_name=payload.display_name)
    return schemas.UserRoleRead(username=record.username, display_name=record.display_name, roles=record.roles_list)
