"""Клиент API chat completions для генерации и автоматической оценки."""

from httpx import AsyncClient, codes
from loguru import logger
from pydantic import ValidationError

from src.core.config import LLMConfig
from src.core.exc import ExternalError
from src.domain.schemas import ChatCompletion
from src.infrastructure.clients.utils import circuit_breaker


@circuit_breaker(exc=ExternalError, attempts=3, base_delay=0.5)
async def send_request_to_llm(
    client: AsyncClient,
    *,
    settings: LLMConfig,
    prompt: str,
    json_response: bool = False,
) -> str:
    """Получить непустой ответ модели в текстовом или JSON-режиме."""
    payload = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    if json_response:
        payload["response_format"] = {"type": "json_object"}

    api_key = settings.llm_api_key
    response = await client.post(
        url=settings.llm_url,
        headers={"Authorization": f"Bearer {api_key}"} if api_key else None,
        json=payload,
    )

    if response.status_code != codes.OK:
        logger.error("invalid LLM status code", status_code=response.status_code)
        raise ExternalError(f"LLM не вернула ответ, HTTP {response.status_code}")

    try:
        content = ChatCompletion.model_validate_json(response.text)
    except ValidationError as error:
        raise ExternalError("LLM вернула некорректный ответ") from error

    if not content.choices or not content.choices[0].message.content.strip():
        raise ExternalError("LLM вернула некорректный ответ")

    return content.choices[0].message.content.strip()
