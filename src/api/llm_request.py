import json
import os

import requests
from dotenv import load_dotenv

from src.infrastructure.rag.rag import rag


def chat_with_LLM(text_message: str, k: int = 3) -> str:
    """Отправка и получение сообщения от LLM"""
    if not isinstance(text_message, str) or not isinstance(k, int):
        raise TypeError("text_message must be string and k must be intager")
    elif k < 0:
        raise ValueError("k must be more then 0")
    load_dotenv()
    promt: str = rag(text_message, k)

    key = os.getenv("OPENROUTER_API_KEY")

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
        },
        data=json.dumps({"model": "nvidia/nemotron-3.5-lightning:free", "messages": [{"role": "user", "content": promt}]}),
    )

    response.raise_for_status()
    answer = response.json()["choices"][0]["message"]["content"]

    return answer


if __name__ == "__main__":
    print(chat_with_LLM("что такое дисперсия?"))
