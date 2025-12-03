from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text

from .database import Base, engine
from .config import get_settings
from .auth import login, get_current_user
from .routers import devices, loans, catalog, users

settings = get_settings()


def apply_dev_migrations():
    # Minimal migrations for dev environments to add new columns if missing
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE IF EXISTS loans ADD COLUMN IF NOT EXISTS due_date TIMESTAMP NULL;"))
        conn.execute(text("ALTER TABLE IF EXISTS loans ADD COLUMN IF NOT EXISTS usage_location VARCHAR(200) NULL;"))
        conn.execute(text("ALTER TABLE IF EXISTS devices ADD COLUMN IF NOT EXISTS location VARCHAR(200) NULL;"))


# Create/patch schema only in dev to avoid clashes with Alembic-managed envs
if settings.environment == "dev":
    apply_dev_migrations()
    Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/auth/token")
def auth_token(
    form_data: OAuth2PasswordRequestForm = Depends(), settings_dep=Depends(get_settings)
):
    # Pass resolved settings explicitly to avoid Depends object
    return login(form_data=form_data, settings=settings_dep)


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.get("/auth/me")
def me(user=Depends(get_current_user)):
    return user


app.include_router(devices.router)
app.include_router(loans.router)
app.include_router(catalog.router)
app.include_router(users.router)
