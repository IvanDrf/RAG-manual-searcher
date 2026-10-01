from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from httpx import AsyncClient
from loguru import logger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.common_params import get_limit_and_offset
from src.api.dependencies import get_http_client, get_llm_api_key, get_llm_url, get_session
from src.api.limiter import limiter
from src.api.middleware import auth_middleware
from src.api.utils import handle_errors
from src.domain.models import HistoryORM
from src.domain.schemas import ChatCompletion, HistorySchema, LLMPromtSchema, LLMResponseSchema
from src.infrastructure.rag import rag
from src.infrastructure.repository.postgresql.history_repo import add_history, find_history_for_user

chat_router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@chat_router.post("/promt", status_code=status.HTTP_200_OK, description="Отправить запрос в чат с LLM")
@limiter.limit("5/minute")
@limiter.limit("100/day")
@handle_errors
async def send_promt_to_llm(
    request: Request,
    promt: LLMPromtSchema,
    client: Annotated[AsyncClient, Depends(get_http_client)],
    llm_url: Annotated[str, Depends(get_llm_url)],
    llm_api_key: Annotated[str, Depends(get_llm_api_key)],
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[UUID, Depends(auth_middleware)],
    backgorund_tasks: BackgroundTasks,
) -> LLMResponseSchema:
    promt_with_context = rag(promt.message, k=3)

    MODEL = "nvidia/nemotron-3.5-lightning:free"
    response = await client.post(
        url=llm_url,
        headers={
            "Authorization": f"Bearer {llm_api_key}",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": promt_with_context}],
        },
    )

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="LLM не вернула ответ")

    try:
        content = ChatCompletion.model_validate_json(response.text)
    except ValidationError as e:
        logger.critical("invalid llm response", error=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="LLM вернула некорректный ответ")

    if not content.choices:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="LLM вернула некорректный ответ")

    llm_response = content.choices[0].message.content
    backgorund_tasks.add_task(save_dialog_in_history, session, user_id, promt.message, llm_response)
    return LLMResponseSchema(model=MODEL, response=llm_response)


async def save_dialog_in_history(session: AsyncSession, user_id: UUID, user_request: str, llm_response: str) -> None:
    history = HistoryORM(record_id=uuid4(), user_id=user_id, user_request=user_request, llm_response=llm_response)

    try:
        await add_history(session, history, commit=True)
    except ConnectionRefusedError as e:
        logger.critical("can't save history in database", error=e)


@chat_router.get("/history", status_code=status.HTTP_200_OK, description="Получить историю переписки пользователя с LLM")
@limiter.limit("5/minute")
@limiter.limit("100/day")
@handle_errors
async def get_user_history(
    request: Request,
    limit_offset: Annotated[tuple[int, int], Depends(get_limit_and_offset)],
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[UUID, Depends(auth_middleware)],
) -> list[HistorySchema]:
    limit, offset = limit_offset

    histories = await find_history_for_user(session, user_id, limit=limit, offset=offset, order_by="time")
    if not histories:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="не удалось найти историю для данного пользователя")

    return [
        HistorySchema(user_request=history.user_request, llm_response=history.llm_response, dialog_time=history.dialog_time)
        for history in histories
    ]
