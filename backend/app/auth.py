from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from ldap3 import Connection, Server, ALL

from .config import get_settings, Settings
from . import crud

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def authenticate_with_ldap(username: str, password: str, settings: Settings) -> bool:
    server = Server(settings.ldap_server, get_info=ALL)
    user_dn = settings.ldap_user_dn_template.format(username=username)
    try:
        with Connection(server, user=user_dn, password=password, auto_bind=True) as conn:
            conn.search(
                search_base=settings.ldap_search_base,
                search_filter=settings.ldap_search_filter.format(username=username),
                attributes=["cn", "uid"],
            )
            return True
    except Exception:
        return False


def create_access_token(data: dict, settings: Settings) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def _get_roles_from_db(username: str):
    try:
        from .database import SessionLocal

        with SessionLocal() as db:
            record = crud.get_user_roles(db, username)
            if record:
                return record.roles_list
    except Exception:
        return None
    return None


def get_current_user(token: str | None = Depends(oauth2_scheme), settings: Settings = Depends(get_settings)):
    if settings.auth_disabled:
        # Dev mode: no token required, fallback to seeded test user or config.
        try:
            from .database import SessionLocal
            from . import models

            with SessionLocal() as db:
                record = crud.get_user_roles(db, settings.dev_user)
                if record:
                    return {
                        "id": record.id,
                        "username": record.username,
                        "display_name": record.display_name,
                        "roles": record.roles_list,
                    }
                test_user = db.get(models.TestUser, settings.dev_user_id)
                if not test_user:
                    test_user = db.query(models.TestUser).order_by(models.TestUser.id.asc()).first()
                if test_user:
                    return {
                        "id": test_user.id,
                        "username": test_user.username,
                        "display_name": test_user.display_name,
                        "roles": test_user.roles_list,
                    }
        except Exception:
            pass
        return {"username": settings.dev_user, "roles": settings.dev_roles}

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        # No token provided -> reject
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    roles = payload.get("roles", []) or []
    db_roles = _get_roles_from_db(username)
    display_name = None
    if db_roles is not None:
        roles = db_roles
        try:
            from .database import SessionLocal

            with SessionLocal() as db:
                record = crud.get_user_roles(db, username)
                if record:
                    display_name = record.display_name
        except Exception:
            pass
    return {"username": username, "roles": roles, "display_name": display_name}


def login(form_data: OAuth2PasswordRequestForm = Depends(), settings: Settings = Depends(get_settings)):
    if settings.auth_disabled:
        user = {"username": settings.dev_user, "roles": settings.dev_roles}
        access_token = create_access_token({"sub": user["username"], "roles": user["roles"]}, settings)
        return {"access_token": access_token, "token_type": "bearer"}

    if not authenticate_with_ldap(form_data.username, form_data.password, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid LDAP credentials")

    roles = _get_roles_from_db(form_data.username) or ["employee"]
    access_token = create_access_token({"sub": form_data.username, "roles": roles}, settings)
    return {"access_token": access_token, "token_type": "bearer"}
