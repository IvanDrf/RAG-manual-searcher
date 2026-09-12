from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from httpx import AsyncClient

from src.api.dependencies import get_http_client, get_llm_api_key, get_llm_url
from src.api.middleware import auth_middleware
from src.api.utils import handle_errors
from src.domain.schemas import LLMPromtSchema, LLMResponseSchema
from src.infrastructure.rag import rag

chat_router = APIRouter(prefix="/api/v1/chat", tags=["chat"], dependencies=[Depends(auth_middleware)])


@chat_router.post("/promt", status_code=status.HTTP_200_OK, description="Отправить запрос в чат с LLM")
@handle_errors
async def send_promt_to_llm(
    promt: LLMPromtSchema,
    client: Annotated[AsyncClient, Depends(get_http_client)],
    llm_url: Annotated[str, Depends(get_llm_url)],
    llm_api_key: Annotated[str, Depends(get_llm_api_key)],
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

    if content := response.json():
        return LLMResponseSchema(model=MODEL, response=content["choices"][0]["message"]["content"])

    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="пустой ответ от модели")
