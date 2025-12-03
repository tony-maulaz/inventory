from datetime import datetime, timedelta
from typing import Optional
import logging
from ldap3.utils.uri import parse_uri

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from ldap3 import Connection, Server, ALL

from .config import get_settings, Settings
from . import crud

# Use uvicorn logger so messages show up in container logs without extra config
logger = logging.getLogger("uvicorn.error")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def authenticate_with_ldap(username: str, password: str, settings: Settings) -> bool:
    # Confirm debug flag is read from env/settings
    logger.warning("Auth debug flag: debug=%s", settings.debug)

    uri = parse_uri(settings.ldap_server)
    use_ssl = uri["ssl"]
    server = Server(settings.ldap_server, get_info=ALL, use_ssl=use_ssl)
    search_filter = settings.ldap_search_filter.format(username=username)
    user_dn = settings.ldap_user_dn_template.format(username=username)

    try:
        if settings.ldap_bind_dn and settings.ldap_bind_password:
            # Bind with service account then search for user's DN
            logger.warning(
                "LDAP service bind attempt: server=%s, bind_dn=%s, search_base=%s, search_filter=%s, use_ssl=%s",
                settings.ldap_server,
                settings.ldap_bind_dn,
                settings.ldap_search_base,
                search_filter,
                use_ssl,
            )
            with Connection(
                server,
                user=settings.ldap_bind_dn,
                password=settings.ldap_bind_password,
                auto_bind=True,
            ) as conn:
                found = conn.search(
                    search_base=settings.ldap_search_base,
                    search_filter=search_filter,
                    attributes=["cn", "uid", "sAMAccountName", "distinguishedName"],
                )
                if not found or not conn.entries:
                    logger.warning(
                        "LDAP search returned no entries for filter=%s", search_filter
                    )
                    return False
                user_dn = str(conn.entries[0].entry_dn)
                logger.warning("LDAP user DN found: %s", user_dn)
            # Now bind as the user with provided password
            logger.warning(
                "LDAP user bind attempt: server=%s, user_dn=%s, use_ssl=%s",
                settings.ldap_server,
                user_dn,
                use_ssl,
            )
            with Connection(server, user=user_dn, password=password, auto_bind=True) as conn_user:
                conn_user.search(
                    search_base=settings.ldap_search_base,
                    search_filter=search_filter,
                    attributes=["cn", "uid", "sAMAccountName"],
                )
                return True
        else:
            # Direct user bind
            logger.warning(
                "LDAP direct bind attempt: server=%s, user_dn=%s, search_base=%s, search_filter=%s, use_ssl=%s",
                settings.ldap_server,
                user_dn,
                settings.ldap_search_base,
                search_filter,
                use_ssl,
            )
            with Connection(server, user=user_dn, password=password, auto_bind=True) as conn:
                conn.search(
                    search_base=settings.ldap_search_base,
                    search_filter=search_filter,
                    attributes=["cn", "uid", "sAMAccountName"],
                )
                return True
    except Exception as exc:
        logger.warning(
            "LDAP authentication failed: server=%s, port=%s, user_dn=%s, error=%s, debug=%s",
            settings.ldap_server,
            getattr(server, "port", None),
            user_dn,
            str(exc),
            settings.debug,
        )
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
            user = crud.get_user(db, username)
            if user:
                return [r.name for r in user.roles]
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
                user = crud.get_user(db, settings.dev_user)
                if user:
                    return {
                        "username": user.username,
                        "display_name": user.display_name,
                        "roles": [r.name for r in user.roles],
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

    roles = _get_roles_from_db(form_data.username)
    if roles is None or not roles:
        # If user not present, auto-provision with default role employee
        try:
            from .database import SessionLocal

            with SessionLocal() as db:
                crud.ensure_roles_exist(db)
                user = crud.upsert_user_with_roles(db, username=form_data.username, roles=["employee"])
                roles = [r.name for r in user.roles]
        except Exception:
            roles = ["employee"]
    access_token = create_access_token({"sub": form_data.username, "roles": roles}, settings)
    return {"access_token": access_token, "token_type": "bearer"}
