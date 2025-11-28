from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from .database import SessionLocal
from .auth import get_current_user


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user(user=Depends(get_current_user)):
    return user
