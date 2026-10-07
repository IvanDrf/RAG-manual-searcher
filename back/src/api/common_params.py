from typing import Annotated, Final

from fastapi import Query

MIN_LIMIT: Final[int] = 1
MAX_LIMIT: Final[int] = 40

MIN_OFFSET: Final[int] = 0


def get_limit_and_offset(
    limit: Annotated[int, Query(ge=MIN_LIMIT, le=MAX_LIMIT)], offset: Annotated[int, Query(ge=MIN_OFFSET)]
) -> tuple[int, int]:
    return limit, offset
