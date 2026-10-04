FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_NO_DEV=1

WORKDIR /app

COPY back/pyproject.toml back/uv.lock ./
RUN uv sync --locked --no-dev

COPY back/ .

COPY data/ ./data/

COPY .env .

RUN chmod +x shell/entry.sh shell/dependencies.sh

EXPOSE 8080

ENTRYPOINT ["./shell/entry.sh"]