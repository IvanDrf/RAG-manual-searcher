from asyncio import create_task

from httpx import AsyncClient, codes
from loguru import logger
from pydantic import ValidationError

from src.core.config import LLMConfig
from src.core.exc import ExternalError
from src.domain.schemas import ChatCompletion
from src.infrastructure.analytics.llm_response import LLMStatisticsScraper
from src.infrastructure.clients.utils import circuit_breaker


@circuit_breaker(exc=ExternalError, attempts=3, base_delay=0.5)
async def send_request_to_llm(
    client: AsyncClient,
    *,
    model: str,
    llm_url: str,
    api_key: str,
    promt: str,
    scraper: LLMStatisticsScraper | None = None,
    json_response: bool = False,
    deterministic: bool = False,
) -> str:
    if scraper is not None:
        scraper.measure_time()
    payload = {"model": model, "messages": [{"role": "user", "content": promt}]}
    if deterministic:
        payload["temperature"] = 0
    if json_response:
        payload["response_format"] = {"type": "json_object"}

    response = await client.post(
        url=llm_url,
        headers={
            "Authorization": f"Bearer {api_key}",
        },
        json=payload,
    )

    if response.status_code != codes.OK:
        if scraper is not None:
            create_task(
                scraper.save(model=model, promt=promt, is_success=False, error_type=ExternalError.__name__, error_message=response.text)
            )

        logger.error("invalid LLM status code", status_code=response.status_code, content=response.text)
        raise ExternalError("LLM не вернула ответ")

    try:
        content = ChatCompletion.model_validate_json(response.text)
    except ValidationError as e:
        if scraper is not None:
            create_task(
                scraper.save(
                    model=model,
                    promt=promt,
                    is_success=False,
                    error_type=ExternalError.__name__,
                    error_message=str(e),
                    is_found_context=scraper.is_found_context(response.text),
                )
            )

        logger.critical("invalid LLM response", error=e)
        raise ExternalError("LLM вернула некорректный ответ")

    if not content.choices or not content.choices[0].message.content.strip():
        if scraper is not None:
            create_task(
                scraper.save(
                    model=model,
                    promt=promt,
                    is_success=False,
                    error_type=ExternalError.__name__,
                    error_message="choices are empty",
                    is_found_context=scraper.is_found_context(response.text),
                )
            )

        logger.error("empty response choices", llm_response=response.text)
        raise ExternalError("LLM вернула некорректный ответ")

    if scraper is not None:
        create_task(
            scraper.save(
                model=model, promt=promt, is_success=True, is_found_context=scraper.is_found_context(content.choices[0].message.content)
            )
        )
    return content.choices[0].message.content


async def request_completion(
    client: AsyncClient,
    *,
    settings: LLMConfig,
    prompt: str,
    json_response: bool = False,
) -> str:
    """Выполнить автономный RAG-запрос или оценку без сбора статистики чата."""
    return (
        await send_request_to_llm(
            client,
            model=settings.llm_model,
            llm_url=settings.llm_url,
            api_key=settings.llm_api_key,
            promt=prompt,
            json_response=json_response,
            deterministic=True,
        )
    ).strip()
