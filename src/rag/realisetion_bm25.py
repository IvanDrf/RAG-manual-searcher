import bm25s
import pandas as pd
import pymorphy3
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


def start_bm25(text: str, k: int):
    """Text tokinize in function"""
    corpus = list(pd.read_csv("../database.csv")["lemma_text"].dropna())
    corpus_tokens = bm25s.tokenize(corpus, stopwords=None)

    retriever = bm25s.BM25()
    retriever.index(corpus_tokens)

    text = tokinizing_text_from_LLM(text)
    query_tokens = bm25s.tokenize(text, stopwords=None)

    results = retriever.retrieve(query_tokens, k=k)

    answer: list[str] = []
    for i in range(results.shape[1]):
        answer.append(corpus[results[0, i]])
    return answer


def tokinizing_text_from_LLM(text: str) -> str:
    """Лемматизация слов для запроса в LLM"""
    if not isinstance(text, str):
        raise TypeError("text must be string")

    morph = pymorphy3.MorphAnalyzer()
    stop_words: set[str] = set(stopwords.words("russian"))
    # привидение к нижнему регистру, и токенизируя
    tokinized_words: list[str] = word_tokenize(text.casefold(), language="russian")
    tokinized_words = [word for word in tokinized_words if word.isalpha() and word not in stop_words]

    cache: dict[str, str] = {}
    for idx, word in enumerate(tokinized_words):
        if word not in cache:
            cache[word] = morph.parse(word)[0].normal_form
        tokinized_words[idx] = cache[word]

    return " ".join(tokinized_words)


if __name__ == "__main__":
    text = "формула "
    array = start_bm25(text, 4)
    print([1 for chunk in array if "ньютон" in chunk])
