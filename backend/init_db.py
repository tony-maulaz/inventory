import os
from sqlalchemy.orm import Session
from sqlalchemy import text

from app import models
from app.database import Base, engine, SessionLocal

BASE_ROLES = ["employee", "gestionnaire", "expert", "admin"]
# Par défaut on ne charge pas les données de démo
SEED_DEMO_DATA = os.getenv("SEED_DEMO_DATA", "false").lower() == "true"

DEFAULT_STATUSES = ["available", "loaned", "maintenance"]
DEFAULT_TYPES = [
    {"name": "multimeter", "description": "Multimètres de table ou portables"},
    {"name": "oscilloscope", "description": "Oscilloscopes numériques"},
    {"name": "function-generator", "description": "Générateurs BF/HF"},
    {"name": "unknown", "description": "Type non défini"},
]

DEFAULT_DEVICES = [
    {
        "inventory_number": "INV-1001",
        "name": "Multimètre Fluke 87V",
        "description": "Multimètre de référence",
        "location": "Atelier banc A",
        "type": "multimeter",
        "status": "available",
    },
    {
        "inventory_number": "INV-2001",
        "name": "Oscilloscope Rigol DS1054Z",
        "description": "4 canaux, 50 MHz",
        "location": "Salle mesure 2",
        "type": "oscilloscope",
        "status": "available",
    },
    {
        "inventory_number": "INV-3001",
        "name": "Générateur BK Precision 4005B",
        "description": "5 MHz",
        "location": "Réserve",
        "type": "function-generator",
        "status": "maintenance",
    },
]

DEFAULT_USERS = [
    {"username": "aline.bernard", "display_name": "Aline Bernard", "roles": "admin"},
    {"username": "lucas.durand", "display_name": "Lucas Durand", "roles": "expert"},
    {"username": "sophie.martin", "display_name": "Sophie Martin", "roles": "gestionnaire"},
    {"username": "maxime.roche", "display_name": "Maxime Roche", "roles": "gestionnaire"},
    {"username": "julie.robin", "display_name": "Julie Robin", "roles": "employee"},
    {"username": "paul.morel", "display_name": "Paul Morel", "roles": "employee"},
    {"username": "lea.mercier", "display_name": "Léa Mercier", "roles": "employee"},
    {"username": "quentin.dupont", "display_name": "Quentin Dupont", "roles": "employee"},
    {"username": "ines.nguyen", "display_name": "Inès Nguyen", "roles": "employee"},
    {"username": "nora.diallo", "display_name": "Nora Diallo", "roles": "employee"},
]


def ensure_schema():
    # Add new columns if they are missing (simple dev migration helper)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE loans ADD COLUMN IF NOT EXISTS due_date TIMESTAMP NULL;"))
        conn.execute(text("ALTER TABLE loans ADD COLUMN IF NOT EXISTS usage_location VARCHAR(200) NULL;"))
        conn.execute(text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS location VARCHAR(200) NULL;"))
        conn.execute(
            text("ALTER TABLE devices ADD COLUMN IF NOT EXISTS security_level VARCHAR(20) NOT NULL DEFAULT 'standard';")
        )


def seed_core(session: Session):
    ensure_schema()
    Base.metadata.create_all(bind=engine)
    # Ensure base roles exist
    for role_name in BASE_ROLES:
        existing = session.query(models.Role).filter_by(name=role_name).first()
        if not existing:
            session.add(models.Role(name=role_name))
    session.commit()

    statuses = {}
    for status_name in DEFAULT_STATUSES:
        status = session.query(models.DeviceStatus).filter_by(name=status_name).first()
        if not status:
            status = models.DeviceStatus(name=status_name)
            session.add(status)
            session.commit()
        statuses[status_name] = status

    types = {}
    for type_payload in DEFAULT_TYPES:
        type_obj = session.query(models.DeviceType).filter_by(name=type_payload["name"]).first()
        if not type_obj:
            type_obj = models.DeviceType(**type_payload)
            session.add(type_obj)
            session.commit()
        types[type_payload["name"]] = type_obj

    # Patch existing rows missing foreign keys (possible après anciennes bases)
    default_status = statuses["available"]
    unknown_type = types["unknown"]
    session.query(models.Device).filter(models.Device.status_id.is_(None)).update(
        {"status_id": default_status.id}, synchronize_session=False
    )
    session.query(models.Device).filter(models.Device.type_id.is_(None)).update(
        {"type_id": unknown_type.id}, synchronize_session=False
    )
    session.query(models.Device).filter(models.Device.security_level.is_(None)).update(
        {"security_level": "standard"}, synchronize_session=False
    )
    session.commit()


def seed_demo(session: Session):
    statuses = {s.name: s for s in session.query(models.DeviceStatus).all()}
    types = {t.name: t for t in session.query(models.DeviceType).all()}

    for device_payload in DEFAULT_DEVICES:
        existing = session.query(models.Device).filter_by(inventory_number=device_payload["inventory_number"]).first()
        if existing:
            continue
        type_obj = types[device_payload["type"]]
        status_obj = statuses[device_payload["status"]]
        device = models.Device(
            inventory_number=device_payload["inventory_number"],
            name=device_payload["name"],
            description=device_payload["description"],
            location=device_payload.get("location"),
            type_id=type_obj.id,
            status_id=status_obj.id,
            security_level="standard",
        )
        session.add(device)
    session.commit()

    # Reset test users to ensure the default set is applied
    session.query(models.TestUser).delete()
    session.commit()

    for user_payload in DEFAULT_USERS:
        existing = session.query(models.TestUser).filter_by(username=user_payload["username"]).first()
        if existing:
            continue
        user = models.TestUser(**user_payload)
        session.add(user)
    session.commit()

    for user_payload in DEFAULT_USERS:
        existing_roles = session.query(models.UserRole).filter_by(username=user_payload["username"]).first()
        if existing_roles:
            existing_roles.roles = user_payload["roles"]
            existing_roles.display_name = user_payload["display_name"]
        else:
            session.add(
                models.UserRole(
                    username=user_payload["username"],
                    display_name=user_payload["display_name"],
                    roles=user_payload["roles"],
                )
            )
    session.commit()


if __name__ == "__main__":
    session = SessionLocal()
    try:
        seed_core(session)
        if SEED_DEMO_DATA:
            seed_demo(session)
            print("Database initialized with demo data.")
        else:
            print("Database initialized (core data only).")
    finally:
        session.close()
