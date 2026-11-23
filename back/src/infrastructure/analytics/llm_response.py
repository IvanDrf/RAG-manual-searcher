from time import perf_counter
from typing import Protocol
from uuid import uuid4

from loguru import logger

from src.core.exc import InternalError
from src.domain.models.clickhouse import LLMResponseORM
from src.domain.rules import get_current_time


class IStatisticsRepo(Protocol):
    async def add_llm_statistics(self, llm_statistics: list[LLMResponseORM]) -> None: ...


class LLMStatisticsScraper:
    def __init__(self, batch_size: int, statistics_repo: IStatisticsRepo) -> None:
        self._batch_size = batch_size
        self._batch: list[None | LLMResponseORM] = [None] * batch_size
        self._pos = 0

        self._statistics_repo: IStatisticsRepo = statistics_repo

    def measure_time(self):
        self._start = perf_counter()
        self._dialog_at = get_current_time()

    async def save(
        self,
        model: str,
        promt: str,
        is_success: bool,
        is_found_context: bool | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
    ):
        reasoning_time = perf_counter() - self._start

        if self._batch[-1] is not None:
            try:
                # all values in buckets is not None, so type ignore
                await self._statistics_repo.add_llm_statistics(self._batch)  # type: ignore

                self._batch = [None] * self._batch_size
                self._pos = 0
            except InternalError as e:
                logger.critical("can't save llm statistics in database", error=e)

                # if batch size is significatn more than standart size, just drop new record
                if len(self._batch) >= 3 * self._batch_size:
                    return

                self._batch.append(None)  # add additional slot for new record, don't increment size

        self._batch[self._pos] = LLMResponseORM(
            record_id=uuid4(),
            model=model,
            promt=promt,
            is_success=is_success,
            is_found_context=is_found_context,
            error_type=error_type,
            error_message=error_message,
            reasoning_time=reasoning_time,
            responsed_at=self._dialog_at,
        )
        self._pos += 1

    def is_found_context(self, llm_response: str) -> bool:
        return "Недостаточно данных в конспекте" not in llm_response
