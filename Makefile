PROJECT?=inventory

DC=docker compose
BASE_COMPOSE=docker-compose.yml
STAGING_COMPOSE=docker-compose.staging.yml

.PHONY: dev-up dev-down dev-migrate dev-init staging-up staging-down staging-migrate staging-init prod-up prod-down prod-migrate

dev-up:
	$(DC) --profile dev up --build

dev-down:
	$(DC) --profile dev down -v

dev-migrate:
	$(DC) --profile dev exec backend poetry run alembic upgrade head

dev-init:
	$(DC) --profile dev exec backend python init_db.py

staging-up:
	$(DC) -p $(PROJECT)-staging -f $(BASE_COMPOSE) -f $(STAGING_COMPOSE) --profile staging up --build -d

staging-down:
	$(DC) -p $(PROJECT)-staging -f $(BASE_COMPOSE) -f $(STAGING_COMPOSE) --profile staging down

staging-migrate:
	$(DC) -p $(PROJECT)-staging -f $(BASE_COMPOSE) -f $(STAGING_COMPOSE) --profile staging exec backend-staging poetry run alembic upgrade head

staging-init:
	$(DC) -p $(PROJECT)-staging -f $(BASE_COMPOSE) -f $(STAGING_COMPOSE) --profile staging exec backend-staging python init_db.py

prod-up:
	$(DC) -p $(PROJECT)-prod --profile prod up --build -d

prod-down:
	$(DC) -p $(PROJECT)-prod --profile prod down

prod-migrate:
	$(DC) -p $(PROJECT)-prod --profile prod exec backend-prod poetry run alembic upgrade head
