FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_NO_DEV=1

WORKDIR /app

COPY .python-version .
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --locked --no-dev

COPY . .
RUN chmod +x shell/entry.sh shell/dependencies.sh

EXPOSE 8080

ENTRYPOINT [ "./shell/entry.sh" ]
