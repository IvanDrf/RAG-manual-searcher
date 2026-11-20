"""Веса разреженного индекса Okapi BM25."""

from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Mapping
from math import log1p
from uuid import UUID

K1 = 1.2
B = 0.75
BLOCK_SIZE = 1000


def term_coordinates(terms: Iterable[str]) -> dict[str, tuple[int, int]]:
    """Сопоставить термам блоки и координаты с нумерацией от нуля."""
    return {term: divmod(position, BLOCK_SIZE) for position, term in enumerate(sorted(terms))}


class BM25:
    """Подсчитать статистику корпуса и веса только для ненулевых координат."""

    def __init__(self, documents: Iterable[tuple[UUID, str]]) -> None:
        self._counts: dict[UUID, Counter[str]] = {}
        document_frequency: Counter[str] = Counter()
        total_length = 0

        for chunk_id, normalized_text in documents:
            counts = Counter(normalized_text.split())
            self._counts[chunk_id] = counts
            document_frequency.update(counts.keys())
            total_length += counts.total()

        document_count = len(self._counts)
        self._average_length = total_length / document_count if document_count else 0.0
        self._coordinates = term_coordinates(document_frequency)
        self._idf = {term: log1p((document_count - frequency + 0.5) / (frequency + 0.5)) for term, frequency in document_frequency.items()}

    @property
    def coordinates(self) -> Mapping[str, tuple[int, int]]:
        """Вернуть координаты словаря, использованные при расчёте весов."""
        return self._coordinates

    def weighted_blocks(self) -> Iterator[tuple[UUID, int, dict[int, float]]]:
        """Выдать заполненные блоки векторов корпуса."""
        for chunk_id, counts in self._counts.items():
            if not counts:
                continue

            length_ratio = counts.total() / self._average_length
            normalization = K1 * (1 - B + B * length_ratio)
            blocks: dict[int, dict[int, float]] = defaultdict(dict)

            for term, frequency in counts.items():
                block, coordinate = self._coordinates[term]
                weight = self._idf[term] * frequency * (K1 + 1)
                blocks[block][coordinate] = weight / (frequency + normalization)

            for block, weights in blocks.items():
                yield chunk_id, block, weights
