#!/bin/sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing dependencies"
sh "$SCRIPT_DIR/dependencies.sh"

echo "Applying PostgreSQL ORM migrations"
uv run alembic -c migrations/postgresql/alembic.ini upgrade head

echo "Starting app"
uv run -m src.app.main