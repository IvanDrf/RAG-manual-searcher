import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import pandas as pd
import pymorphy3


def lemman_text_and_write_to_csv() -> None:
    """Лемматизация чанков"""
    nltk.download("punkt_tab")
    nltk.download("stopwords")
    stopwords_russian: set[str] = set(stopwords.words('russian'))
    morph = pymorphy3.MorphAnalyzer()
    cache: dict[str, str] = {} # кэш для леммантизированных слов
    lemmen_text: list[str] = [] # массив лемантизированных слов
    df: pd.DataFrame = pd.read_csv("../database.csv")

    df['chunc_text'] = df['chunc_text'].str.replace('\n', ' ') # заменяем переходы на пробелы
    df['chunc_text'] = df['chunc_text'].str.casefold() # опускаем в нижний регистр

    for idx in range(len(df)):
        chunk: str = df.iloc[idx]['chunc_text']
        chunk: list[str] = word_tokenize(chunk, language='russian')
        new_string = [word for word in chunk if word.isalpha() and word not in stopwords_russian]
        for i, word in enumerate(new_string):
            if word not in cache: # если слово уже приведенно в начальную форму
                cache[word] = morph.parse(word)[0].normal_form
            new_string[i] = cache[word]
        lemmen_text.append(' '.join(new_string))
    
    df['lemma_text'] = pd.Series(lemmen_text)
    df.to_csv('../database.csv', index=False)

def tokinizing_text_from_LLM(text: str) -> str:
    """Лемматизация слов для запроса в LLM"""
    if not isinstance(text, str):
        raise TypeError("text must be string")
    cache: dict[str, str] = {}
    morph = pymorphy3.MorphAnalyzer()
    stop_words: set[str] = set(stopwords.words("russian"))
    # привидение к нижнему регистру, и токенизируя
    tokinized_words: list[str] = word_tokenize(text.casefold(), language='russian') 
    tokinized_words = [word for word in tokinized_words if word.isalpha() and word not in stop_words]
    for idx, word in enumerate(tokinized_words):
        if word not in cache:
            cache[word] = morph.parse(word)[0].normal_form
        tokinized_words[idx] = cache[word]
    return ' '.join(tokinized_words)


if __name__ == "__main__":
    text = (
        "Студенты решали сложные уравнения на лекциях. ",
        "Матрицы были квадратными, а собственные значения — действительными. ",
        "В теореме доказали непрерывность функции на отрезке [a, b]. ",
        "Это было очень важно для понимания!",
    )
    for tx in text:
        print(tokinizing_text_from_LLM(tx))