from httpx import AsyncClient

from src.core.config import CONFIG


class LLMClient:
    def __init__(self) -> None:
        self.http_client = AsyncClient(timeout=CONFIG.llm_timeout, base_url=CONFIG.llm_url)

    async def send_promt_to_llm(self, promt: str):
        pass
