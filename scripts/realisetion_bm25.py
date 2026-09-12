import bm25s
import pandas as pd
from chuncking import tokinizing_text_from_LLM


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


if __name__ == "__main__":
    text = "формула "
    array = start_bm25(text, 4)
    print([1 for chunk in array if "ньютон" in chunk])
