# Inventaire & prêts — Vue/Vuetify + FastAPI + PostgreSQL

Application monopage permettant de gérer les appareils en stock et leurs prêts/retours. Pile technique : Vue 3 + Vuetify pour le front, FastAPI + SQLAlchemy pour l'API, PostgreSQL comme base, Docker/docker-compose pour l'orchestration.

## Prérequis
- Docker et docker-compose
- (Optionnel) Poetry pour un lancement backend hors Docker
- Ports libres : 5173 (front dev), 4173 (front prod preview), 8000 (API), 5432 (Postgres)

## Configuration
1. Copier `.env.example` en `.env` (racine) et ajuster au besoin :
   - `DATABASE_URL` : URL SQLAlchemy Postgres
   - `AUTH_DISABLED=true` pour le mode dev sans authentification (un utilisateur simulé est injecté).
   - Variables LDAP (`LDAP_SERVER`, `LDAP_USER_DN_TEMPLATE`, …) pour l'auth réelle.
   - `DEV_ROLES` attendu au format JSON (ex: `["admin"]`).
   - `DEV_USER_ID` pour choisir l'utilisateur de test (semé par `init_db.py`) lorsqu'on est en mode dev sans auth.
2. Frontend : copier `frontend/.env.example` en `frontend/.env` et définir `VITE_API_URL` vers l'URL publique de l'API (ex: `https://exemple.ch:3000/api` ou `http://localhost:8000`). Le docker-compose lit `VITE_API_URL` depuis l'environnement, sinon valeur par défaut `http://localhost:8000` en dev et `http://backend-prod:8000` en prod.
3. (Optionnel) Modifier les données de démonstration dans `backend/init_db.py`.

## Démarrage en développement (hot-reload)
```
docker compose --profile dev up --build
```
- API : http://localhost:8000/docs
- Front : http://localhost:5173 (variable `VITE_API_URL` déjà définie dans le service dev)
- Auth désactivée par défaut en dev (`AUTH_DISABLED=true`).
- Base : `postgres/postgres`, DB `inventory`.
- Pour remplir des données exemples : `docker compose exec backend python init_db.py`

## Démarrage en prod (profil prod)
```
docker compose --profile prod up --build
```
- API : http://localhost:8000
- Front : http://localhost:4173
- Auth activée par défaut, basée sur LDAP + JWT (`/auth/token`). Pensez à définir `JWT_SECRET_KEY`.

## Structure
- `backend/` : FastAPI, modèles SQLAlchemy, routes (devices, loans, catalog), authentification LDAP/JWT, script `init_db.py`, packaging géré par Poetry (`pyproject.toml`).
- `frontend/` : Vue 3 + Vuetify, écran unique avec recherche/filtrage, fiches modales (création/édition), prêt/retour, saisie ou scan de numéro d'inventaire.
- `docker-compose.yml` : services `db`, `backend/backend-prod`, `frontend/frontend-dev` selon le profil.

## Scripts utiles
- Backend local hors Docker (Poetry) : `cd backend && poetry install && poetry run uvicorn app.main:app --reload`
- Initialiser la base : `cd backend && poetry run python init_db.py`
- Front local hors Docker : `cd frontend && npm install && npm run dev -- --host`

## Notes sur l'authentification
- Route de token : `POST /auth/token` (OAuth2 password). En mode dev (`AUTH_DISABLED=true`), un token de test est généré sans appel LDAP.
- Quand Keycloak sera branché, l'API peut recevoir un `sub` et récupérer les attributs LDAP via les hooks déjà prévus (see `app/auth.py`).

## Points de vigilance
- Le code crée la base via `Base.metadata.create_all` au démarrage pour simplifier la mise en route. Prévoir des migrations (Alembic) avant la prod.
- Les statuts attendus sont `available`, `loaned`, `maintenance`. `init_db.py` les insère avec des jeux d'appareils de test.
