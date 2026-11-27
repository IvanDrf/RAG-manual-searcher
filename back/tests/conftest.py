import os

from bcrypt import gensalt

os.environ.update(
    APP_PASSWORD_SALT=gensalt().decode(),
    APP_EMBEDDING_SIZE="3",
    APP_STATISTICS_BATCH_SIZE="2",
    JWT_SECRET="unit-test-signing-key-not-for-production",
    JWT_ACCESS_EXP="5",
    JWT_REFRESH_EXP="15",
    LLM_URL="https://llm.invalid/chat/completions",
    LLM_API_KEY="unit-test-key",
    POSTGRES_HOST="127.0.0.1",
    POSTGRES_PORT="25432",
    POSTGRES_USER="rag_test",
    POSTGRES_PASSWORD="rag_test",
    POSTGRES_DB="rag_test",
    REDIS_HOST="127.0.0.1",
    REDIS_PORT="26379",
    REDIS_DB="0",
    CLICKHOUSE_HOST="127.0.0.1",
    CLICKHOUSE_PORT="28123",
    CLICKHOUSE_USER="rag_test",
    CLICKHOUSE_PASSWORD="rag_test",
    CLICKHOUSE_DB="rag_test",
)
