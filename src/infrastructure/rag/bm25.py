import bm25s
import pandas as pd

from src.infrastructure.rag.chuncking import tokinizing_text_from_LLM


def start_bm25(text: str, k: int) -> list[str]:
    """Text tokinize in function"""
    corpus = list(pd.read_csv("database.csv")["lemma_text"].dropna())
    corpus_tokens = bm25s.tokenize(corpus, stopwords=[])

    retriever = bm25s.BM25()
    retriever.index(corpus_tokens)

    text = tokinizing_text_from_LLM(text)
    query_tokens = bm25s.tokenize(text, stopwords=[])

    results = retriever.retrieve(query_tokens, k=k)

    answer: list[str] = []
    for i in range(results.shape[1]):  # type: ignore
        answer.append(corpus[results[0, i]])  # type: ignore

    return answer
