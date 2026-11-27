from asyncio import run

from src.core.config import CONFIG
from src.infrastructure.repository.postgresql.connection import connect_to_postgresql, ensure_vector_extension


async def prepare_postgresql() -> None:
    engine, _ = connect_to_postgresql(CONFIG)
    try:
        await ensure_vector_extension(engine)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    run(prepare_postgresql())
