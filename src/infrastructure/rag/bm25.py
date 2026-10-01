import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.rag.chuncking import tokinizing_text_from_LLM
from src.infrastructure.repository.postgresql.chunk_repo import get_all_chanks


class BM25:
    """Реализауция BM25 и TF-iDF"""

    def __init__(self):
        # Массив уникальных слов (столбцы матрицы)
        self._words_in_db: list[str] = []
        # количество сторок
        self._count_texts: int = 0
        self._matrix: np.ndarray | None = None

    async def make_matrix(self, session: AsyncSession):
        """Функция для инициализации матрицы"""
        # Получаю чанки из бд асинхронно через генератор
        iter_db_chunk = get_all_chanks(session)
        counter_row = 0
        unique_words: set[str] = set()

        async for chunk in iter_db_chunk:
            counter_row += 1
            unique_words.update(tokinizing_text_from_LLM(chunk.content).split())

        self._words_in_db = sorted(unique_words)
        self._matrix = np.zeros((len(self._words_in_db), counter_row))

    # def TF-iDF(self):
