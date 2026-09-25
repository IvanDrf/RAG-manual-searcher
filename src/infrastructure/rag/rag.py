from src.infrastructure.rag.bm25 import start_bm25


def rag(text: str, k: int = 3) -> str:
    """Return promt with chuncks"""
    if not isinstance(text, str):
        raise TypeError("text must be string")
    if not isinstance(k, int):
        raise TypeError("k must be int")

    array_chunks: list[str] = start_bm25(text, k)
    context_block = "\n\n".join(f"[CHUNK {i + 1}]\n{chunk}" for i, chunk in enumerate(array_chunks))

    prompt = f"""Ты — ассистент по вузовским конспектам по математике.

Отвечай СТРОГО по CONTEXT ниже.
Правила:
1. Используй только факты из CONTEXT.
2. Если в CONTEXT нет ответа — напиши ровно: "Недостаточно данных в конспекте".
3. Не добавляй знания извне, даже если тема тебе знакома.
4. Пиши кратко и по делу, на русском языке.
5. Если опираешься на фрагмент, укажи номер чанка, например [CHUNK 1].

QUESTION:
{text}

CONTEXT:
{context_block}
"""
    return prompt
