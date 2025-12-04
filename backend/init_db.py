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
    {
        "username": "aline.bernard",
        "first_name": "Aline",
        "last_name": "Bernard",
        "email": "aline.bernard@example.com",
        "roles": "admin",
    },
    {
        "username": "lucas.durand",
        "first_name": "Lucas",
        "last_name": "Durand",
        "email": "lucas.durand@example.com",
        "roles": "expert",
    },
    {
        "username": "sophie.martin",
        "first_name": "Sophie",
        "last_name": "Martin",
        "email": "sophie.martin@example.com",
        "roles": "gestionnaire",
    },
    {
        "username": "maxime.roche",
        "first_name": "Maxime",
        "last_name": "Roche",
        "email": "maxime.roche@example.com",
        "roles": "gestionnaire",
    },
    {
        "username": "julie.robin",
        "first_name": "Julie",
        "last_name": "Robin",
        "email": "julie.robin@example.com",
        "roles": "employee",
    },
    {
        "username": "paul.morel",
        "first_name": "Paul",
        "last_name": "Morel",
        "email": "paul.morel@example.com",
        "roles": "employee",
    },
    {
        "username": "lea.mercier",
        "first_name": "Léa",
        "last_name": "Mercier",
        "email": "lea.mercier@example.com",
        "roles": "employee",
    },
    {
        "username": "quentin.dupont",
        "first_name": "Quentin",
        "last_name": "Dupont",
        "email": "quentin.dupont@example.com",
        "roles": "employee",
    },
    {
        "username": "ines.nguyen",
        "first_name": "Inès",
        "last_name": "Nguyen",
        "email": "ines.nguyen@example.com",
        "roles": "employee",
    },
    {
        "username": "nora.diallo",
        "first_name": "Nora",
        "last_name": "Diallo",
        "email": "nora.diallo@example.com",
        "roles": "employee",
    },
]


def ensure_schema():
    # Add new columns if they are missing (simple dev migration helper)
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE loans ADD COLUMN IF NOT EXISTS due_date TIMESTAMP NULL;")
        )
        conn.execute(
            text(
                "ALTER TABLE loans ADD COLUMN IF NOT EXISTS usage_location VARCHAR(200) NULL;"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE devices ADD COLUMN IF NOT EXISTS location VARCHAR(200) NULL;"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE devices ADD COLUMN IF NOT EXISTS security_level VARCHAR(20) NOT NULL DEFAULT 'standard';"
            )
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
        type_obj = (
            session.query(models.DeviceType)
            .filter_by(name=type_payload["name"])
            .first()
        )
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
    roles = {r.name: r for r in session.query(models.Role).all()}

    for device_payload in DEFAULT_DEVICES:
        existing = (
            session.query(models.Device)
            .filter_by(inventory_number=device_payload["inventory_number"])
            .first()
        )
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
        existing = (
            session.query(models.TestUser)
            .filter_by(username=user_payload["username"])
            .first()
        )
        if existing:
            continue
        display_name = f"{user_payload.get('first_name','')} {user_payload.get('last_name','')}".strip()
        user = models.TestUser(
            username=user_payload["username"],
            display_name=display_name or user_payload["username"],
            roles=user_payload["roles"],
        )
        session.add(user)
    session.commit()

    # Seed real users + roles table for demo
    for user_payload in DEFAULT_USERS:
        user = (
            session.query(models.User)
            .filter_by(username=user_payload["username"])
            .first()
        )
        if not user:
            user = models.User(
                username=user_payload["username"],
                email=user_payload.get("email"),
                first_name=user_payload.get("first_name"),
                last_name=user_payload.get("last_name"),
            )
            session.add(user)
            session.commit()
        # Attach role
        role_name = user_payload["roles"] or "employee"
        role_obj = (
            roles.get(role_name)
            or session.query(models.Role).filter_by(name=role_name).first()
        )
        if role_obj and role_obj not in user.roles:
            user.roles.append(role_obj)
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
