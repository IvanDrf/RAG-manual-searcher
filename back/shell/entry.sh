#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

parse_flag() {
    case "$2" in
        true|True|TRUE|1) printf '1\n' ;;
        false|False|FALSE|0) printf '0\n' ;;
        *) printf '%s must be true, false, 1 or 0\n' "$1" >&2; exit 2 ;;
    esac
}

run_postgresql=$(parse_flag RUN_POSTGRES_MIGRATIONS "${RUN_POSTGRES_MIGRATIONS-true}")
run_clickhouse=$(parse_flag RUN_CLICKHOUSE_MIGRATIONS "${RUN_CLICKHOUSE_MIGRATIONS-true}")
run_data=$(parse_flag RUN_DATA_MIGRATION "${RUN_DATA_MIGRATION-true}")

if [ "$run_postgresql" = 1 ]; then
    echo "Preparing PostgreSQL extensions"
    uv run --locked --no-sync -m scripts.prepare_postgresql

    echo "Applying PostgreSQL migrations"
    uv run --locked --no-sync alembic -c migrations/postgresql/alembic.ini upgrade head
else
    echo "Skipping PostgreSQL extensions and migrations"
fi

if [ "$run_clickhouse" = 1 ]; then
    echo "Applying ClickHouse migrations"
    uv run --locked --no-sync alembic -c migrations/clickhouse/alembic.ini upgrade head
else
    echo "Skipping ClickHouse migrations"
fi

if [ "$run_data" = 1 ]; then
    echo "Importing books and building BM25 index"
    uv run --locked --no-sync -m scripts.data.data_migration
else
    echo "Skipping books import and BM25 rebuild"
fi

echo "Starting app"
exec uv run --locked --no-sync -m src.app.main
