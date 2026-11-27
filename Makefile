COMPOSE ?= docker compose
COMPOSE_BACK_DEV := $(COMPOSE) --env-file .env -f infrastructure/back/docker-compose.dev.yml
COMPOSE_BACK_PROD := $(COMPOSE) --env-file .env -f infrastructure/back/docker-compose.prod.yml
COMPOSE_BACK_BENCH ?= docker compose --env-file .env -f infrastructure/back/docker-compose.benchmark.yml
COMPOSE_BACK_TEST ?= docker compose -f infrastructure/back/docker-compose.test.yml
UV ?= uv
BENCH_CONCURRENCY ?= 4
BACK_BOOKS_DIR ?= ../data/student_book_pdf

# BACK

.PHONY: back-setup
back-setup:
	$(UV) sync --project back --locked --dev
	cd back && $(UV) run --locked --no-sync python -m nltk.downloader stopwords punkt punkt_tab

.PHONY: back-migrate-postgresql
back-migrate-postgresql:
	cd back && $(UV) run --locked --no-sync alembic -c migrations/postgresql/alembic.ini upgrade head

.PHONY: back-migrate-clickhouse
back-migrate-clickhouse:
	cd back && $(UV) run --locked --no-sync alembic -c migrations/clickhouse/alembic.ini upgrade head

.PHONY: back-data-migrate
back-data-migrate:
	cd back && $(UV) run --locked --no-sync -m scripts.data.data_migration --books-dir "$(BACK_BOOKS_DIR)"

.PHONY: back-data-reindex
back-data-reindex:
	cd back && $(UV) run --locked --no-sync -m scripts.data.data_migration --reindex

.PHONY: back-run
back-run:
	cd back && $(UV) run --locked --no-sync -m src.app.main

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
.PHONY: back-prod-up-build back-prod-up
back-prod-up-build back-prod-up:
	@set -eu; \
	prod_started_at=$$(date -u +%Y-%m-%dT%H:%M:%SZ); \
	$(COMPOSE_BACK_PROD) up -d $(if $(filter back-prod-up-build,$@),--build); \
	$(COMPOSE_BACK_PROD) logs --follow --since "$$prod_started_at" rag_searcher_app & \
	prod_logs_pid=$$!; \
	cleanup() { \
		prod_status=$$?; \
		trap - EXIT; \
		kill "$$prod_logs_pid" 2>/dev/null || true; \
		wait "$$prod_logs_pid" 2>/dev/null || true; \
		exit "$$prod_status"; \
	}; \
	trap cleanup EXIT; \
	trap 'exit 129' HUP; \
	trap 'exit 130' INT; \
	trap 'exit 143' TERM; \
	prod_waited=0; \
	while [ "$$prod_waited" -lt 1800 ]; do \
		prod_state=$$($(COMPOSE_BACK_PROD) ps --all --format '{{.State}} {{.Health}}' rag_searcher_app); \
		case "$$prod_state" in \
			"running healthy") echo "Backend is ready; containers continue running in the background"; exit 0 ;; \
			""|exited*|dead*|*unhealthy*) echo "Backend failed to become ready: $$prod_state" >&2; exit 1 ;; \
		esac; \
		sleep 1; \
		prod_waited=$$((prod_waited + 1)); \
	done; \
	echo "Backend readiness timeout after 1800 seconds" >&2; \
	exit 1

.PHONY: back-prod-down
back-prod-down:
	$(COMPOSE_BACK_PROD) down 

.PHONY: back-prod-down-volumes
back-prod-down-volumes:
	$(COMPOSE_BACK_PROD) down -v 

.PHONY: back-prod-app-logs
back-prod-app-logs:
	$(COMPOSE_BACK_PROD) logs --follow --tail 100 rag_searcher_app

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

.PHONY: back-bench
back-bench:
	@set -eu; \
	$(UV) sync --project back --locked --no-install-project; \
	cleanup() { \
		bench_status=$$?; \
		trap - EXIT; \
		$(COMPOSE_BACK_BENCH) down || { \
			if [ "$$bench_status" -eq 0 ]; then bench_status=1; fi; \
		}; \
		exit "$$bench_status"; \
	}; \
	trap cleanup EXIT; \
	trap 'exit 129' HUP; \
	trap 'exit 130' INT; \
	trap 'exit 143' TERM; \
	$(COMPOSE_BACK_BENCH) up -d --wait --wait-timeout 120; \
	$(COMPOSE_BACK_BENCH) exec -T database sh -c 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -f /docker-entrypoint-initdb.d/init.sql'; \
	bench_report="../data/benchmark/benchmark_$$(date +%Y-%m-%d_%H-%M-%S).json"; \
	(cd back && \
		$(UV) run --locked --no-sync alembic -c migrations/postgresql/alembic.ini upgrade head && \
		$(UV) run --locked --no-sync -m scripts.benchmark_rag --output "$$bench_report" --concurrency "$(BENCH_CONCURRENCY)")
