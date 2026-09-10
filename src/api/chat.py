from fastapi import APIRouter, Depends, status

from src.api.middleware import auth_middleware
from src.api.utils import handle_errors
from src.domain.schemas import LLMPromtSchema

chat_router = APIRouter(prefix="/api/v1/chat", tags=["chat"], dependencies=[Depends(auth_middleware)])


@chat_router.post("/promt", status_code=status.HTTP_200_OK, description="Отправить запрос в чат с LLM")
@handle_errors
async def send_promt_to_llm(promt: LLMPromtSchema):
    pass
