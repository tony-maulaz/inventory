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
# (optionnel) Appliquer les migrations si tu veux coller au schéma Alembic
# docker compose exec backend poetry run alembic upgrade head
# (optionnel) Charger les données de démo
# docker compose exec backend python init_db.py
```
- API : http://localhost:8000/docs
- Front : http://localhost:5173 (variable `VITE_API_URL` déjà définie dans le service dev)
- Auth désactivée par défaut en dev (`AUTH_DISABLED=true`).
- Base : `postgres/postgres`, DB `inventory`.
- Pour remplir des données exemples : `docker compose exec backend python init_db.py`

## Démarrage en prod (profil prod)
```
docker compose --profile prod up --build
# (recommandé) Appliquer les migrations avant démarrage si non déjà fait
# docker compose exec backend-prod poetry run alembic upgrade head
```
- API : http://localhost:8000
- Front : http://localhost:4173
- Auth activée par défaut, basée sur LDAP + JWT (`/auth/token`). Pensez à définir `JWT_SECRET_KEY`.

## Déploiement sur un serveur (ports, CORS, reverse proxy)
- Backend et front écoutent par défaut sur 8000 (API) et 4173 (front build) en prod. Si seul le port 80 est ouvert, place un reverse proxy (Nginx/Traefik) qui sert le front et proxifie `/api` (ou équivalent) vers le backend.
  - Exemple de mapping : `https://exemple.ch` → frontend, `https://exemple.ch/api` → proxy vers `backend-prod:8000`.
  - Dans ce cas, configure `VITE_API_URL` sur l’URL publique (ex: `https://exemple.ch/api`).
- CORS : actuellement ouvert (`*`). Avec un reverse proxy sur le même domaine, tu peux laisser ainsi ou restreindre à ton domaine via une config FastAPI dédiée si tu le souhaites.
- Ports :
  - **Local dev** : front 5173, API 8000, DB 5432 (profil `dev`).
  - **Serveur dev/test** : même mapping que local ou derrière un reverse proxy selon ta politique d’ouverture de ports.
  - **Serveur prod** : idéalement via reverse proxy en 80/443 (front + proxy `/api` vers backend).

### Modes recommandés
- **Dev local** : `docker compose --profile dev up --build` (front hot-reload 5173, API 8000). Base dev `db-dev`. Si tu utilises Alembic : `docker compose exec backend poetry run alembic upgrade head` puis `docker compose exec backend python init_db.py` pour les données de démo.
- **Staging / test sur serveur** : utiliser le profil `prod` (stack identique à la prod) avec un vhost dédié (ex: `dev.exemple.ch`). Commande : `docker compose --profile prod up --build -d`. Côté front, `VITE_API_URL` = `https://dev.exemple.ch/api`. Proxy Nginx : vhost `dev.exemple.ch` vers le front (port 4173 de la stack prod) et `/api` vers le backend (8000).
- **Prod** : profil `prod` avec les vraies variables (`DATABASE_URL` prod/managée, `JWT_SECRET_KEY`, `AUTH_DISABLED=false`). `VITE_API_URL` = `https://exemple.ch/api`. Proxy Nginx : vhost `exemple.ch` vers le front (4173) et `/api` vers le backend (8000).

### Faire tourner deux stacks prod-like (prod + staging) sur le même serveur
- Utilise des noms de projet et des ports/env distincts. Exemple :
  - Prod : `docker compose -p inventory-prod --profile prod up -d` (ports 8000/4173, DB prod)
  - Staging : `docker compose -p inventory-staging -f docker-compose.yml -f docker-compose.staging.yml --profile staging up -d` (ports 8001/4174, DB staging)
- Ajuste `VITE_API_URL` et `DATABASE_URL` pour chaque stack.
- Nginx : deux vhosts (ex: `exemple.ch` → ports prod, `dev.exemple.ch` → ports staging), chacun avec `/` vers le front correspondant et `/api` vers le backend correspondant.

### Exemple de reverse proxy Nginx (prod et dev)
Créer un fichier de site Nginx (ex: `/etc/nginx/sites-available/inventory.conf`) :
```nginx
server {
    listen 80;
    server_name exemple.ch;

    # Redirige vers HTTPS si certifs présents (optionnel)
    # return 301 https://$host$request_uri;

    # Front (prod) servi par le conteneur frontend sur 4173
    location / {
        proxy_pass http://127.0.0.1:4173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API prod (proxy /api vers backend-prod:8000)
    location /api/ {
        rewrite ^/api/(.*)$ /$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
Activer le site (`ln -s /etc/nginx/sites-available/inventory.conf /etc/nginx/sites-enabled/`) et recharger Nginx.

#### Installation rapide de Nginx sur Ubuntu
```
sudo apt update
sudo apt install -y nginx
sudo ln -s /etc/nginx/sites-available/inventory.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```
Ajoute un second vhost pour l’environnement dev (ex: `dev.exemple.ch`) si besoin, en adaptant les `proxy_pass` vers les ports dev.

#### Faire tourner dev et prod sur le même serveur
- Utilise des ports distincts : par exemple, prod sur 8000/4173, dev sur 8001/5174 (ajuste `docker-compose` ou lance une deuxième stack avec des overrides).
- Ajoute un second vhost Nginx (ex: `dev.exemple.ch`) pointant vers les ports dev (`proxy_pass http://127.0.0.1:5174` pour le front dev, `/api` vers `http://127.0.0.1:8001`).
- Dans l’environnement dev du front (frontend/.env), mets `VITE_API_URL` = `https://dev.exemple.ch/api`.

#### Résumé des variables à ajuster
- Front : `VITE_API_URL` (dans `frontend/.env` ou variable d’env docker).
- Backend :
  - Dev (compose) : `DATABASE_URL` pointe par défaut sur `db-dev` (`postgresql+psycopg2://postgres:postgres@db-dev:5432/inventory_dev`)
  - Prod (compose) : `DATABASE_URL` pointe par défaut sur `db-prod` (`postgresql+psycopg2://postgres:postgres@db-prod:5432/inventory_prod`)
  - `JWT_SECRET_KEY`, `AUTH_DISABLED` (`false` en prod), `LDAP_*` si utilisé.

#### Bases de données séparées dev/prod
- Compose définit deux services Postgres avec volumes distincts :
  - `db-dev` (profil dev) : volume `db-data-dev`, port 5432 exposé.
  - `db-prod` (profil prod) : volume `db-data-prod`, port 5433 exposé sur l’hôte pour éviter le conflit.
- En prod/staging, privilégie une base managée externe et remplace `DATABASE_URL` en conséquence.

## Structure
- `backend/` : FastAPI, modèles SQLAlchemy, routes (devices, loans, catalog), authentification LDAP/JWT, script `init_db.py`, packaging géré par Poetry (`pyproject.toml`).
- `frontend/` : Vue 3 + Vuetify, écran unique avec recherche/filtrage, fiches modales (création/édition), prêt/retour, saisie ou scan de numéro d'inventaire.
- `docker-compose.yml` : services `db`, `backend/backend-prod`, `frontend/frontend-dev` selon le profil.

### Services docker-compose (résumé)
- `db-dev` : Postgres 15 pour le profil dev, base `inventory_dev` (volume `db-data-dev`).
- `db-prod` : Postgres 15 pour le profil prod, base `inventory_prod` (volume `db-data-prod`). Ports exposés 5433->5432 pour éviter le conflit local.
- `backend` (profil `dev`) : API FastAPI avec hot-reload, auth désactivée par défaut, monte le code local (`./backend`).
- `backend-prod` (profil `prod`) : API FastAPI en mode prod (sans reload, auth activée).
- `frontend-dev` (profil `dev`) : serveur Vite (Vue 3) avec hot-reload, variable `VITE_API_URL` configurée pour appeler l’API.
- `frontend` (profil `prod`) : front buildé servi via `serve`, `VITE_API_URL` à définir vers l’API prod.

### Migrations (Alembic)
- Alembic est configuré dans `backend/alembic` avec une migration initiale `0001_initial`.
- Appliquer les migrations : `cd backend && poetry run alembic upgrade head`
- Créer une nouvelle migration : `cd backend && poetry run alembic revision --autogenerate -m "message"`
- L’URL DB utilisée est celle de `DATABASE_URL` (surchargée via `.env` ou variables d’environnement), donc la même commande s’applique en dev/prod selon l’URL active.
#### Flux recommandé
- Générer la migration initiale (si tu repars de zéro) :  
  `cd backend && poetry run alembic revision --autogenerate -m "initial schema"` puis `poetry run alembic upgrade head`
- Après chaque changement de modèle :  
  `cd backend && poetry run alembic revision --autogenerate -m "feat: ..."` puis `poetry run alembic upgrade head`
- Évite de réécrire les anciennes migrations : ajoute-en de nouvelles, sauf en dev jetable où tu droppes la base et régénères tout.
- Dans l’état actuel, l’app crée encore les tables au démarrage (pour simplifier le bootstrap). En prod/staging, il est préférable de s’appuyer uniquement sur Alembic et de ne pas compter sur `create_all`.

## Scripts utiles
- Backend local hors Docker (Poetry) : `cd backend && poetry install && poetry run uvicorn app.main:app --reload`
- Initialiser la base : `cd backend && poetry run python init_db.py`
- Front local hors Docker : `cd frontend && npm install && npm run dev -- --host`
- Makefile (tâches docker compose) :
  - `make dev-up` / `make dev-down` / `make dev-migrate` / `make dev-init`
  - `make staging-up` / `make staging-down` / `make staging-migrate` / `make staging-init`
  - `make prod-up` / `make prod-down` / `make prod-migrate`

## Notes sur l'authentification
- Route de token : `POST /auth/token` (OAuth2 password). En mode dev (`AUTH_DISABLED=true`), un token de test est généré sans appel LDAP.
- Quand Keycloak sera branché, l'API peut recevoir un `sub` et récupérer les attributs LDAP via les hooks déjà prévus (see `app/auth.py`).
- La variable `ENVIRONMENT` (dev|prod|staging) est lue par l’application pour exposer l’état dans `/health` et pour distinguer certains comportements (ex: `AUTH_DISABLED` typiquement activé en dev). Elle ne remplace pas le choix de profil docker (`--profile dev/prod`) mais sert de flag runtime.
- Rôles supportés : `employee`, `gestionnaire`, `expert`, `admin` (stockés en base dans `user_roles`). Seul `admin` peut modifier les rôles via l’API `/users`.
- Niveaux de sécurité des appareils : `standard` (tous), `avance` (gestionnaire/expert/admin), `critique` (expert/admin). Le prêt/retour est bloqué backend + frontend selon ce niveau.
- Seed : `SEED_DEMO_DATA=true|false` (par défaut true). Quand false, `init_db.py` crée uniquement les rôles/types/statuts sans injecter les appareils et utilisateurs de démo.

## Points de vigilance
- Le code crée la base via `Base.metadata.create_all` au démarrage pour simplifier la mise en route. Prévoir des migrations (Alembic) avant la prod.
- Les statuts attendus sont `available`, `loaned`, `maintenance`. `init_db.py` les insère avec des jeux d'appareils de test.
