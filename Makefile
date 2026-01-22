PROJECT?=inventory

DC=docker compose
BASE_COMPOSE=docker-compose.base.yml
DEV_COMPOSE=docker-compose.dev.yml
STAGING_COMPOSE=docker-compose.staging.yml
PROD_COMPOSE=docker-compose.prod.yml

.PHONY: dev-up dev-down dev-migrate dev-init staging-up staging-down staging-migrate staging-init prod-up prod-down prod-migrate

dev-up:
	$(DC) -f $(BASE_COMPOSE) -f $(DEV_COMPOSE) up --build

dev-down:
	$(DC) -f $(BASE_COMPOSE) -f $(DEV_COMPOSE) down -v

dev-migrate:
	$(DC) -f $(BASE_COMPOSE) -f $(DEV_COMPOSE) exec backend poetry run alembic upgrade head

dev-init:
	$(DC) -f $(BASE_COMPOSE) -f $(DEV_COMPOSE) exec backend python init_db.py

staging-up:
	$(DC) -p $(PROJECT)-staging -f $(BASE_COMPOSE) -f $(STAGING_COMPOSE) up --build -d

staging-down:
	$(DC) -p $(PROJECT)-staging -f $(BASE_COMPOSE) -f $(STAGING_COMPOSE) down

staging-migrate:
	$(DC) -p $(PROJECT)-staging -f $(BASE_COMPOSE) -f $(STAGING_COMPOSE) exec backend poetry run alembic upgrade head

staging-init:
	$(DC) -p $(PROJECT)-staging -f $(BASE_COMPOSE) -f $(STAGING_COMPOSE) exec backend python init_db.py

prod-up:
	$(DC) -p $(PROJECT)-prod -f $(BASE_COMPOSE) -f $(PROD_COMPOSE) up --build -d

prod-down:
	$(DC) -p $(PROJECT)-prod -f $(BASE_COMPOSE) -f $(PROD_COMPOSE) down

prod-migrate:
	$(DC) -p $(PROJECT)-prod -f $(BASE_COMPOSE) -f $(PROD_COMPOSE) exec backend poetry run alembic upgrade head
