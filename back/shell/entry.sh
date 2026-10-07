#!/bin/sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing dependencies"
sh "$SCRIPT_DIR/dependencies.sh"

echo "Applying ORM migrations"
uv run alembic upgrade head

echo "Starting app"
uv run -m src.app.main