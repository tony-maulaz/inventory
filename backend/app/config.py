from functools import lru_cache
from typing import List, Union
from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    app_name: str = "Inventory API"
    debug: bool = False
    environment: str = Field(default="dev", regex="^(dev|prod|staging)$")

    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/inventory"

    jwt_secret_key: str = Field(default="changeme", env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 12

    ldap_server: str = Field(default="ldap://localhost:389", env="LDAP_SERVER")
    ldap_user_dn_template: str = Field(default="uid={username},ou=people,dc=example,dc=org")
    ldap_search_base: str = Field(default="ou=people,dc=example,dc=org")
    ldap_search_filter: str = Field(default="(uid={username})")
    ldap_bind_dn: str | None = Field(default=None, env="LDAP_BIND_DN")
    ldap_bind_password: str | None = Field(default=None, env="LDAP_BIND_PASSWORD")

    auth_disabled: bool = False
    dev_user: str = "dev-user"  # fallback name if lookup by ID fails
    dev_user_id: int = 1
    dev_roles: List[str] = ["admin"]

    @validator("dev_roles", pre=True)
    def parse_roles(cls, v: Union[str, List[str]]):
        if isinstance(v, str):
            # Allow comma-separated roles in env (e.g. "admin,user")
            return [part.strip() for part in v.split(",") if part.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
