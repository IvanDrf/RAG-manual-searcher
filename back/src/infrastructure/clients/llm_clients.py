from httpx import AsyncClient, codes
from loguru import logger
from pydantic import ValidationError

from src.core.exc import ExternalError
from src.domain.schemas import ChatCompletion
from src.infrastructure.clients.utils import circuit_breaker


@circuit_breaker(exc=ExternalError, attempts=3, base_delay=0.5)
async def send_request_to_llm(client: AsyncClient, *, model: str, llm_url: str, api_key: str, promt: str) -> str:
    response = await client.post(
        url=llm_url,
        headers={
            "Authorization": f"Bearer {api_key}",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": promt}],
        },
    )

    if response.status_code != codes.OK:
        logger.error("invalid LLM status code", status_code=response.status_code, content=response.json())
        raise ExternalError("LLM не вернула ответ")

    try:
        content = ChatCompletion.model_validate_json(response.text)
    except ValidationError as e:
        logger.critical("invalid LLM response", error=e)
        raise ExternalError("LLM вернула некорректный ответ")

    if not content.choices:
        raise ExternalError("LLM вернула некорректный ответ")

    return content.choices[0].message.content
