from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, status
from loguru import logger
from uvicorn import run

from src.api.auth import auth_router
from src.api.dependencies import ping_database
from src.core.config import CONFIG
from src.core.logger import configure_logger


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logger(CONFIG)
    await ping_database()
    yield


app = FastAPI(title="RAG-research app", lifespan=lifespan)
app.include_router(auth_router)


@app.get("/health", status_code=status.HTTP_200_OK, description="health check для проверки сервера на работоспособность")
def health() -> dict[str, str]:
    return {"status": "AVAILABLE"}


@app.middleware("http")
async def measure_response_time(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)
    end = perf_counter()

    logger.info("Request time", method=request.method, url=request.url, request_time=f"{(end - start):.3f}")

    return response


if __name__ == "__main__":
    run(app=app, host=CONFIG.app_host, port=CONFIG.app_port, log_config=None)
