COMPOSE	:= docker-compose 
COMPOSE_BACK_DEV := $(COMPOSE) --env-file .env -f infrastructure/back/docker-compose.dev.yml
COMPOSE_BACK_PROD := $(COMPOSE) --env-file .env -f infrastructure/back/docker-compose.prod.yml
COMPOSE_BACK_TEST ?= docker compose -f infrastructure/back/docker-compose.test.yml
UV ?= uv

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

# TESTS
.PHONY: run-test
run-test:
	@set -eu; \
	$(UV) sync --project back --locked --dev; \
	cleanup() { \
		run_status=$$?; \
		trap - EXIT; \
		$(COMPOSE_BACK_TEST) down --remove-orphans || { \
			if [ "$$run_status" -eq 0 ]; then run_status=1; fi; \
		}; \
		exit "$$run_status"; \
	}; \
	trap cleanup EXIT; \
	trap 'exit 129' HUP; \
	trap 'exit 130' INT; \
	trap 'exit 143' TERM; \
	$(COMPOSE_BACK_TEST) up -d --wait --wait-timeout 120; \
	(cd back && $(UV) run --locked --no-sync pytest -m '' tests/)
