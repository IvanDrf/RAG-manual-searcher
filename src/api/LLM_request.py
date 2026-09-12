from rag import rag


def chat_with_LLM(text_message: str, k: int = 3) -> str:
    """Отправка и получение сообщения от LLM"""
    if not isinstance(text_message, str) or not isinstance(k, int):
        raise TypeError("text_message must be string and k must be intager")
    elif k < 0:
        raise ValueError("k must be more then 0")
    text_message = rag(text_message, k)


if __name__ == "__main__":
    print(chat_with_LLM("Что такое дисперсия?"))
