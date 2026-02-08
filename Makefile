# Détection de l'OS
ifeq ($(OS),Windows_NT)
    # Sur Windows, Docker Desktop gère souvent la conversion des droits
    # automatiquement vers l'utilisateur courant, on peut souvent omettre le --user
    USER_ARG =
else
    # Sur Linux/Mac, on récupère l'UID/GID pour éviter les problèmes de droits
    USER_ARG = --user $(shell id -u):$(shell id -g)
endif

DC=docker compose
EXEC=$(DC) exec api

migrate-gen:
	$(DC) exec $(USER_ARG) api alembic revision --autogenerate -m "$(msg)"

migrate-up:
	$(EXEC) alembic upgrade head

migrate-down:
	$(EXEC) alembic downgrade -1

build_docker:
	$(DC) build

rebuild_docker:
	$(DC) build --no-cache

start_docker:
	$(DC) up -d

stop_docker:
	$(DC) down

restart_api:
	$(DC) restart api

