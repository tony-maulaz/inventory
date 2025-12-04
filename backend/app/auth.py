from datetime import datetime, timedelta
from typing import Optional
import logging
from ldap3.utils.uri import parse_uri
from sqlalchemy import func, select

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import ssl
from ldap3 import Connection, Server, ALL, Tls

from .config import get_settings, Settings
from . import crud
from .database import SessionLocal

# Use uvicorn logger so messages show up in container logs without extra config
logger = logging.getLogger("uvicorn.error")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def ldap_auth_and_profile(username: str, password: str, settings: Settings) -> dict:
    """
    Recherche l'utilisateur via le compte de service (si fourni), bind avec son mot de passe,
    et retourne les attributs utiles.
    """
    # Force TLS 1.2 for compat with some AD/LDAPS endpoints that reset on newer defaults
    tls_config = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
    search_filter = settings.ldap_search_filter.format(username=username)
    uri = parse_uri(settings.ldap_server)
    use_ssl = uri["ssl"]
    server = Server(settings.ldap_server, get_info=ALL, use_ssl=use_ssl, tls=tls_config)

    # Si compte de service, on l'utilise pour trouver le DN de l'utilisateur
    user_dn = settings.ldap_user_dn_template.format(username=username)
    try:
        if settings.ldap_bind_dn and settings.ldap_bind_password:
            with Connection(
                server,
                user=settings.ldap_bind_dn,
                password=settings.ldap_bind_password,
                auto_bind=True,
            ) as conn:
                found = conn.search(
                    search_base=settings.ldap_search_base,
                    search_filter=search_filter,
                    attributes=[
                        "cn",
                        "uid",
                        "sAMAccountName",
                        "distinguishedName",
                        "mail",
                        "givenName",
                        "sn",
                    ],
                )
                if not found or not conn.entries:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid LDAP credentials",
                    )
                user_dn = str(conn.entries[0].entry_dn)

        # Bind avec les credentials utilisateur
        with Connection(
            server, user=user_dn, password=password, auto_bind=True
        ) as conn_user:
            found = conn_user.search(
                search_base=settings.ldap_search_base,
                search_filter=search_filter,
                attributes=[
                    "displayName",
                    "givenName",
                    "sn",
                    "cn",
                    "mail",
                    "sAMAccountName",
                ],
            )
            if not found or not conn_user.entries:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid LDAP credentials",
                )
            attrs = conn_user.entries[0].entry_attributes_as_dict
            first_name = attrs.get("givenName")
            if isinstance(first_name, list):
                first_name = first_name[0] if first_name else None
            last_name = attrs.get("sn")
            if isinstance(last_name, list):
                last_name = last_name[0] if last_name else None
            email = attrs.get("mail")
            if isinstance(email, list):
                email = email[0] if email else None
            username_out = attrs.get("sAMAccountName")
            if isinstance(username_out, list):
                username_out = username_out[0] if username_out else None
            username_out = username_out or username
            display_name_attr = attrs.get("displayName")
            if isinstance(display_name_attr, list):
                display_name_attr = display_name_attr[0] if display_name_attr else None
            display_name = display_name_attr or " ".join(filter(None, [first_name, last_name])) or username_out
            return {
                "username": username_out,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "display_name": display_name,
            }
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("LDAP auth/profile error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid LDAP credentials"
        )


def create_access_token(data: dict, settings: Settings) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def _get_user_from_db(username: str):
    try:
        with SessionLocal() as db:
            return crud.get_user(db, username)
    except Exception:
        return None


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
):
    if settings.auth_disabled:
        # Dev mode: no token required, fallback to seeded test user if present in DB.
        try:
            from . import models

            with SessionLocal() as db:
                test_user = db.get(models.TestUser, settings.dev_user_id)
                if not test_user:
                    test_user = (
                        db.query(models.TestUser)
                        .order_by(models.TestUser.id.asc())
                        .first()
                    )
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
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        username_raw = payload.get("sub")
        username: Optional[str] = username_raw[0] if isinstance(username_raw, list) else username_raw
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    roles = payload.get("roles", []) or []
    db_user = _get_user_from_db(username)
    display_name = db_user.display_name if db_user else None
    email = db_user.email if db_user else None
    first_name = db_user.first_name if db_user else None
    last_name = db_user.last_name if db_user else None
    if db_user:
        roles = [r.name for r in db_user.roles] or roles
    return {
        "username": username,
        "roles": roles,
        "display_name": display_name,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
    }


def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    settings: Settings = Depends(get_settings),
):
    if settings.auth_disabled:
        user = {"username": settings.dev_user, "roles": settings.dev_roles}
        access_token = create_access_token(
            {"sub": user["username"], "roles": user["roles"]}, settings
        )
        return {"access_token": access_token, "token_type": "bearer"}

    profile = ldap_auth_and_profile(
        form_data.username, form_data.password, settings=settings
    )
    user_username = profile.get("username") or form_data.username
    email = profile.get("email")
    first_name = profile.get("first_name")
    last_name = profile.get("last_name")

    db_user = _get_user_from_db(user_username)
    roles = [r.name for r in db_user.roles] if db_user else None
    if roles is None or not roles:
        if not settings.auto_provision_users:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not provisioned. Contact an administrator.",
            )
        # Auto-provision user. If first user ever, make admin; otherwise employee.
        try:
            with SessionLocal() as db:
                crud.ensure_roles_exist(db)
                has_any_user = db.scalar(select(func.count()).select_from(crud.models.User)) > 0  # type: ignore[attr-defined]
                default_roles = ["admin"] if not has_any_user else ["employee"]
                user = crud.upsert_user_with_roles(
                    db,
                    username=user_username,
                    roles=default_roles,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )
                roles = [r.name for r in user.roles]
                db_user = user
        except Exception:
            roles = ["employee"]
    else:
        # Mettre à jour les infos si manquantes
        if db_user:
            with SessionLocal() as db:
                crud.update_user_profile(
                    db,
                    username=user_username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )
    access_token = create_access_token({"sub": user_username, "roles": roles}, settings)
    return {"access_token": access_token, "token_type": "bearer"}
