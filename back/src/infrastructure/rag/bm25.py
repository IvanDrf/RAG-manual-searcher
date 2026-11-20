import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.repository.postgresql.chunk_repo import get_all_chunks


class BM25:
    """Реализауция BM25 и TF-iDF"""

    def __init__(self):
        # Массив уникальных слов (столбцы матрицы)
        self._words_in_db: list[str] = []
        # количество сторок
        self._count_texts: int = 0
        self._matrix: np.ndarray | None = None

    async def make_matrix(self, session: AsyncSession) -> None:
        """Функция для инициализации матрицы"""
        # Получаю чанки из бд асинхронно через генератор
        iter_db_chunk = get_all_chunks(session)
        counter_row = 0
        unique_words: set[str] = set()

        async for chunk in iter_db_chunk:
            counter_row += 1
            unique_words.update(chunk.content.split())

        self._words_in_db = sorted(unique_words)
        self._matrix = np.zeros((len(self._words_in_db), counter_row))

    async def TF_iDF(self, session: AsyncSession) -> None:
        """Заготовка заполнения матрицы посредством TF-IDF."""
        iter_db_chunk = get_all_chunks(session)

        async for chunk in iter_db_chunk:
            for word in chunk.content.split():
                _count = chunk.content.count(word)
                _all_chunks_db = get_all_chunks(session)
