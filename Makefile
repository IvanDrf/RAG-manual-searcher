COMPOSE	:= docker-compose 
COMPOSE_BACK_DEV := $(COMPOSE) --env-file .env -f infrastructure/back/docker-compose.dev.yml
COMPOSE_BACK_PROD := $(COMPOSE) --env-file .env -f infrastructure/back/docker-compose.prod.yml

# BACK

#  dev
.PHONY: back-dev-up-build
back-dev-up-build:
	$(COMPOSE_BACK_DEV) up -d --build

.PHONY: back-dev-up
back-dev-up:
	$(COMPOSE_BACK_DEV) up -d 

.PHONY: back-dev-down
back-dev-down:
	$(COMPOSE_BACK_DEV) down 

.PHONY: back-dev-down-volumes
back-dev-down-volumes:
	$(COMPOSE_BACK_DEV) down -v 

# prod
.PHONY: back-prod-up-build
back-prod-up-build:
	$(COMPOSE_BACK_PROD) up -d --build

.PHONY: back-prod-up
back-prod-up:
	$(COMPOSE_BACK_PROD) up -d 

.PHONY: back-prod-down
back-prod-down:
	$(COMPOSE_BACK_PROD) down 

.PHONY: back-prod-down-volumes
back-prod-down-volumes:
	$(COMPOSE_BACK_PROD) down -v 

.PHONY: back-prod-app-logs
back-prod-app-logs:
	$(COMPOSE_BACK_PROD) logs rag_searcher_app 
