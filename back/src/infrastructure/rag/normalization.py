from functools import lru_cache

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from pymorphy3 import MorphAnalyzer


@lru_cache(maxsize=1)
def russian_stopwords() -> frozenset[str]:
    return frozenset(stopwords.words("russian"))


@lru_cache(maxsize=1)
def morphology() -> MorphAnalyzer:
    return MorphAnalyzer()


@lru_cache(maxsize=20_000)
def normalize_word(word: str) -> str:
    return morphology().parse(word)[0].normal_form


def normalize_text(text: str) -> str:
    stop_words = russian_stopwords()
    tokens = word_tokenize(text.casefold(), language="russian")
    return " ".join(normalize_word(word) for word in tokens if word.isalpha() and word not in stop_words)
