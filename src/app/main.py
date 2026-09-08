from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, status
from uvicorn import run

from src.core.config import CONFIG
from src.core.logger import configure_logger, get_logger


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logger(CONFIG)
    yield


app = FastAPI(title="RAG-research app", lifespan=lifespan)


@app.get("/health", status_code=status.HTTP_200_OK)
def health() -> dict[str, str]:
    return {"status": "AVAILABLE"}


@app.middleware("http")
async def measure_response_time(request: Request, call_next):
    log = get_logger().bind(method=request.method, url=request.url)

    start = perf_counter()
    response = await call_next(request)
    end = perf_counter()

    await log.ainfo("", request_time=f"{(end - start):.3f}")

    return response


if __name__ == "__main__":
    run(app=app, host=CONFIG.app_host, port=CONFIG.app_port)
