import nltk
import pandas as pd
import pymorphy3
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


def lemman_text_and_write_to_bd() -> None:
    nltk.download("punkt_tab")
    nltk.download("stopwords")

    stopwords_russian: set[str] = set(stopwords.words("russian"))

    morph = pymorphy3.MorphAnalyzer()
    df: pd.DataFrame = pd.read_csv("database.csv")

    df["chunc_text"] = df["chunc_text"].str.replace("\n", " ")
    df["chunc_text"] = df["chunc_text"].str.casefold()

    cache: dict[str, str] = {}
    lemmen_text: list[str] = []
    for idx in range(len(df)):
        chunk = df.iloc[idx]["chunc_text"]
        chunk: list[str] = word_tokenize(chunk, language="russian")
        new_string = [word for word in chunk if word.isalpha() and word not in stopwords_russian]

        for i, word in enumerate(new_string):
            if word not in cache:
                cache[word] = morph.parse(word)[0].normal_form
            new_string[i] = cache[word]

        lemmen_text.append(" ".join(new_string))

    df["lemma_text"] = pd.Series(lemmen_text)
    df.to_csv("../database.csv", index=False)


def tokinizing_text_from_LLM(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be string")

    morph = pymorphy3.MorphAnalyzer()
    stop_words: set[str] = set(stopwords.words("russian"))
    tokinized_words: list[str] = word_tokenize(text.casefold(), language="russian")
    tokinized_words = [word for word in tokinized_words if word.isalpha() and word not in stop_words]

    cache: dict[str, str] = {}
    for idx, word in enumerate(tokinized_words):
        if word not in cache:
            cache[word] = morph.parse(word)[0].normal_form
        tokinized_words[idx] = cache[word]

    return " ".join(tokinized_words)
