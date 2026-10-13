from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from httpx import AsyncClient
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.common_params import get_limit_and_offset
from src.api.dependencies import get_http_client, get_llm_api_key, get_llm_url, get_session
from src.api.limiter import limiter
from src.api.middleware import auth_middleware
from src.api.utils import handle_errors
from src.core.exc import ExternalError
from src.domain.models import ChatORM, HistoryORM
from src.domain.rules import MAX_CHAT_NAME_LENGTH, get_current_time
from src.domain.schemas import ChatSchema, HistorySchema, LLMPromtSchema, LLMResponseSchema
from src.infrastructure.clients.llm_clients import send_request_to_llm
from src.infrastructure.rag import rag
from src.infrastructure.repository.postgresql.chat_repo import add_chat, delete_chat, find_chat_for_user, find_chats_for_user
from src.infrastructure.repository.postgresql.history_repo import add_history, find_history_for_user

MODELS = ("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "meta-llama/llama-3.3-70b-instruct:free")


chat_router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@chat_router.get("", status_code=status.HTTP_200_OK, description="Получение названий чатов и их id")
async def get_user_chats(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[UUID, Depends(auth_middleware)],
    limit_offset: Annotated[tuple[int, int], Depends(get_limit_and_offset)],
) -> list[ChatSchema]:
    limit, offset = limit_offset

    chats = await find_chats_for_user(session, user_id=user_id, limit=limit, offset=offset)
    if not chats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не удалось найти чатов для пользователя")

    return [ChatSchema(chat_id=chat.chat_id, name=chat.name) for chat in chats]


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
    chat_id: UUID | None = None,
) -> LLMResponseSchema:
    if not chat_id:
        chat = ChatORM(chat_id=uuid4(), name=create_chat_name(promt.message), user_id=user_id)
        await add_chat(session, chat)

    else:
        chat = await find_chat_for_user(session, user_id=user_id, chat_id=chat_id)
        if not chat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Не удалось найти чат с {chat_id}")

    chat.edited_at = get_current_time()

    promt_with_context = rag(promt.message, k=3)

    llm_response, model = await send_request_to_llm_fallback(
        client, llm_url=llm_url, api_key=llm_api_key, promt=promt_with_context, models=MODELS
    )

    history = HistoryORM(record_id=uuid4(), chat_id=chat.chat_id, user_request=promt.message, llm_response=llm_response, llm_model=model)
    await add_history(session, history)

    chat_id = chat.chat_id
    await session.commit()
    return LLMResponseSchema(chat_id=chat_id, model=model, response=llm_response)


async def send_request_to_llm_fallback(
    client: AsyncClient, *, llm_url: str, api_key: str, promt: str, models: tuple[str, ...]
) -> tuple[str, str]:
    for model in models:
        try:
            llm_response = await send_request_to_llm(client, model=model, llm_url=llm_url, api_key=api_key, promt=promt)
            return llm_response, model
        except ExternalError as e:
            logger.error("model returned error", error=e, model=model)

    raise ExternalError("Ни одна из LLM не вернула валидный ответ")


def create_chat_name(user_request: str, max_name_length: int = MAX_CHAT_NAME_LENGTH) -> str:
    if len(user_request) >= max_name_length:
        return user_request[:max_name_length]

    return user_request


@chat_router.get("/history", status_code=status.HTTP_200_OK, description="Получить историю переписки пользователя с LLM для чата")
@limiter.limit("5/minute")
@limiter.limit("100/day")
@handle_errors
async def get_user_history(
    request: Request,
    chat_id: UUID,
    limit_offset: Annotated[tuple[int, int], Depends(get_limit_and_offset)],
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[UUID, Depends(auth_middleware)],
) -> list[HistorySchema]:
    limit, offset = limit_offset

    histories = await find_history_for_user(session, user_id=user_id, chat_id=chat_id, limit=limit, offset=offset)
    if not histories:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="не удалось найти историю для данного пользователя")

    return [
        HistorySchema(
            user_request=history.user_request,
            llm_response=history.llm_response,
            llm_model=history.llm_model,
            dialog_time=history.dialog_time,
        )
        for history in histories
    ]


@chat_router.delete("", status_code=status.HTTP_204_NO_CONTENT, description="Удаление чата с LLM")
async def delete_chat_with_llm(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[UUID, Depends(auth_middleware)],
    chat_id: UUID,
) -> None:
    chat = await find_chat_for_user(session, user_id=user_id, chat_id=chat_id, block=True)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Не удалось найти чат с {chat_id}")

    await delete_chat(session, chat, commit=True)
