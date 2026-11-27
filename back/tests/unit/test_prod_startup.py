import json
import os
import subprocess
from collections.abc import Callable
from itertools import product
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts import prepare_postgresql as preparation
from scripts.data import data_migration
from src.domain.models.postgresql import BookORM

FLAGS = ("RUN_POSTGRES_MIGRATIONS", "RUN_CLICKHOUSE_MIGRATIONS", "RUN_DATA_MIGRATION")
STAGES = ["extension", "postgresql", "clickhouse", "import", "app"]
type EntrypointRunner = Callable[[dict[str, str], str | None], tuple[subprocess.CompletedProcess[str], list[dict[str, str]]]]


@pytest.fixture
def run_entrypoint(tmp_path: Path) -> EntrypointRunner:
    log = tmp_path / "calls.jsonl"
    stub = tmp_path / "uv"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "args = sys.argv[1:]\n"
        "if 'scripts.prepare_postgresql' in args:\n"
        "    stage = 'extension'\n"
        "elif 'migrations/postgresql/alembic.ini' in args:\n"
        "    stage = 'postgresql'\n"
        "elif 'migrations/clickhouse/alembic.ini' in args:\n"
        "    stage = 'clickhouse'\n"
        "elif 'scripts.data.data_migration' in args:\n"
        "    stage = 'import'\n"
        "elif 'src.app.main' in args:\n"
        "    stage = 'app'\n"
        "else:\n"
        "    raise AssertionError(args)\n"
        "with open(os.environ['STARTUP_TEST_LOG'], 'a') as log:\n"
        "    log.write(json.dumps({'stage': stage, 'cwd': os.getcwd()}) + '\\n')\n"
        "sys.exit(17 if os.environ.get('STARTUP_TEST_FAIL') == stage else 0)\n"
    )
    stub.chmod(0o755)
    backend = Path(__file__).resolve().parents[2]

    def run(flags: dict[str, str], failure_stage: str | None = None) -> tuple[subprocess.CompletedProcess[str], list[dict[str, str]]]:
        environment = {key: value for key, value in os.environ.items() if key not in FLAGS}
        environment.update(
            PATH=f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
            STARTUP_TEST_LOG=str(log),
            STARTUP_TEST_FAIL=failure_stage or "",
        )
        environment.update(flags)
        result = subprocess.run(
            ["sh", str(backend / "shell/entry.sh")], cwd=tmp_path, env=environment, capture_output=True, text=True, check=False
        )
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        assert all(call["cwd"] == str(backend) for call in calls)
        return result, calls

    return run


@pytest.mark.parametrize("failure_stage", [None, *STAGES])
def test_entrypoint_order_and_failure_stops_startup(run_entrypoint: EntrypointRunner, failure_stage: str | None) -> None:
    result, calls = run_entrypoint({}, failure_stage)

    expected = STAGES if failure_stage is None else STAGES[: STAGES.index(failure_stage) + 1]
    assert [call["stage"] for call in calls] == expected
    assert result.returncode == (17 if failure_stage else 0)


@pytest.mark.parametrize("flag", FLAGS)
@pytest.mark.parametrize("value", ["false", "0", "False", "FALSE"])
def test_disabled_migration_stage_is_not_executed(run_entrypoint: EntrypointRunner, flag: str, value: str) -> None:
    result, calls = run_entrypoint({flag: value}, None)

    skipped = {
        "RUN_POSTGRES_MIGRATIONS": {"extension", "postgresql"},
        "RUN_CLICKHOUSE_MIGRATIONS": {"clickhouse"},
        "RUN_DATA_MIGRATION": {"import"},
    }[flag]
    assert result.returncode == 0
    assert [call["stage"] for call in calls] == [stage for stage in STAGES if stage not in skipped]
    assert "Skipping" in result.stdout


@pytest.mark.parametrize("flag", FLAGS)
@pytest.mark.parametrize("value", ["true", "1", "True", "TRUE"])
def test_enabled_migration_stage_preserves_default_order(run_entrypoint: EntrypointRunner, flag: str, value: str) -> None:
    result, calls = run_entrypoint({flag: value}, None)

    assert result.returncode == 0
    assert [call["stage"] for call in calls] == STAGES


@pytest.mark.parametrize("values", list(product(["0", "1"], repeat=3)))
def test_migration_flags_are_independent(run_entrypoint: EntrypointRunner, values: tuple[str, str, str]) -> None:
    result, calls = run_entrypoint(dict(zip(FLAGS, values, strict=True)), None)

    expected = []
    if values[0] == "1":
        expected.extend(["extension", "postgresql"])
    if values[1] == "1":
        expected.append("clickhouse")
    if values[2] == "1":
        expected.append("import")
    expected.append("app")
    assert result.returncode == 0
    assert [call["stage"] for call in calls] == expected


@pytest.mark.parametrize("flag", FLAGS)
@pytest.mark.parametrize("value", ["", "yes", "no", "2"])
def test_invalid_migration_flag_fails_before_database_access(run_entrypoint: EntrypointRunner, flag: str, value: str) -> None:
    result, calls = run_entrypoint({flag: value}, None)

    assert result.returncode == 2
    assert calls == []
    assert flag in result.stderr


@pytest.mark.parametrize("fails", [False, True])
async def test_postgresql_extension_is_prepared_and_engine_closed(monkeypatch: pytest.MonkeyPatch, fails: bool) -> None:
    engine = MagicMock()
    engine.dispose = AsyncMock()
    connection = engine.begin.return_value.__aenter__.return_value
    connection.execute = AsyncMock(side_effect=RuntimeError("database unavailable") if fails else None)
    monkeypatch.setattr(preparation, "connect_to_postgresql", MagicMock(return_value=(engine, MagicMock())))

    if fails:
        with pytest.raises(RuntimeError, match="database unavailable"):
            await preparation.prepare_postgresql()
    else:
        await preparation.prepare_postgresql()

    connection.execute.assert_awaited_once()
    assert connection.execute.await_args is not None
    assert str(connection.execute.await_args.args[0]) == "CREATE EXTENSION IF NOT EXISTS vector"
    engine.dispose.assert_awaited_once()


@pytest.mark.parametrize("indexed", [0, 1])
async def test_import_requires_searchable_corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, indexed: int) -> None:
    (tmp_path / "book.pdf").write_bytes(b"fake PDF parsed by stub")
    engine = MagicMock()
    engine.dispose = AsyncMock()
    sessions = MagicMock()
    monkeypatch.setattr(data_migration, "connect_to_postgresql", MagicMock(return_value=(engine, sessions)))
    monkeypatch.setattr(data_migration, "lock_index_for_update", AsyncMock())
    monkeypatch.setattr(data_migration, "process_book", AsyncMock(return_value=(BookORM(), [])))
    monkeypatch.setattr(data_migration, "import_book", AsyncMock())
    monkeypatch.setattr(data_migration, "rebuild_index", AsyncMock(return_value=indexed))

    if indexed == 0:
        with pytest.raises(ValueError, match="нет фрагментов"):
            await data_migration.migrate_books(tmp_path)
    else:
        await data_migration.migrate_books(tmp_path)

    exit_args = sessions.begin.return_value.__aexit__.await_args.args
    assert exit_args[0] is (ValueError if indexed == 0 else None)
    engine.dispose.assert_awaited_once()
