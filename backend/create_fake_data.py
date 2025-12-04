"""
Ajoute les données de démo (appareils + utilisateurs de test) sans toucher au reste.
Usage :
    poetry run python create_fake_data.py
Les constantes viennent de init_db.py.
"""

from app.database import SessionLocal
from init_db import seed_demo, seed_core


def main():
    with SessionLocal() as session:
        # Ensure base schema/lookup data exist before inserting demo fixtures
        seed_core(session)
        seed_demo(session)
        print("Données de démo ajoutées.")


if __name__ == "__main__":
    main()
