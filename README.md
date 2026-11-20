# RAG-manual-searcher

Сервис для поиска ответов в учебных пособиях и вузовских конспектах по математике.
Пользователь задаёт вопрос на русском языке, а сервис ищет подходящие фрагменты
материалов и передаёт их языковой модели как контекст для ответа — подход RAG
(Retrieval-Augmented Generation).

## Возможности

- Регистрация, вход, выход и обновление сессии.
- Вопросы по учебным материалам с ответами языковой модели.
- Создание чата при первом вопросе, получение списка чатов и истории, удаление чата.
- Просмотр названий книг, используемых для контекста.
- Управление ролями и блокировками пользователей администратором.

Сценарии использования, ограничения и направления развития описаны
в [продуктовой документации](spec/docs/product.md).

## Стек и структура

Backend: Python 3.12+, FastAPI, Pydantic, SQLAlchemy и Alembic.
Хранение данных: PostgreSQL с расширением pgvector и Redis.
Поиск: BM25; генерация ответа: внешний LLM API.
Окружение: uv, Docker Compose, Prometheus и Grafana.

| Путь | Содержимое |
| --- | --- |
| `back/src/` | API, доменные модели, поиск и работа с хранилищами |
| `back/alembic/` | Миграции схемы PostgreSQL |
| `back/scripts/` | Подготовка и импорт учебных материалов |
| `back/tests/` | Тесты backend |
| `data/` | PDF, текстовые материалы и промежуточные данные |
| `infrastructure/back/` | Docker Compose и настройки мониторинга |
| `spec/docs/` | Продуктовая документация и описание API |
| `spec/dev/` | Руководства для разработчиков |

## Подготовка окружения разработки

Нужны Python 3.12+, uv, Docker с Compose и make.
Команды ниже выполняются из корня репозитория, затем из `back/`, как указано в примере.
При незавершённом слиянии сначала необходимо разрешить конфликты в коде.

```bash
cp .env.example .env
cd back
uv sync --dev
```

Заполните `.env` в корне репозитория:

- `LLM_URL` — адрес API chat completions, `LLM_API_KEY` — ключ провайдера.
  Модели для запросов задаются в `back/src/api/chat.py`.
- `JWT_SECRET` — собственный секрет подписи токенов.
- `APP_PASSWORD_SALT` — корректная bcrypt-соль. Сгенерировать её из `back/`:
  `uv run python -c 'import bcrypt; print(bcrypt.gensalt().decode())'`.
- `POSTGRES_*` и `REDIS_*` — параметры подключения. При локальном запуске приложения
  порты подключения должны совпадать с опубликованными портами `*_OUTPUT_PORT`.
- `BOOKS_DIR` — путь к PDF. Для запуска скриптов из `back/` используйте
  `../data/student_book_pdf` вместо пути из примера окружения.

Далее поднимите PostgreSQL и Redis и примените миграции:

```bash
cd ..
make back-dev-up
cd back
uv run alembic upgrade head
```

Для импорта PDF в PostgreSQL нужны ресурсы NLTK. Импорт изменяет содержимое БД;
выполняйте его для подготовленного корпуса, а не при каждом запуске:

```bash
uv run python -m nltk.downloader stopwords punkt punkt_tab
uv run -m scripts.data.data_migration
```

Импорт PDF и подготовка поискового корпуса — отдельные этапы. Перед запуском
вопросов проверьте источник данных в `back/src/infrastructure/rag/bm25.py`:
импорт в PostgreSQL сам по себе не гарантирует готовность индекса поиска.

Запуск backend из `back/`:

```bash
uv run -m src.app.main
```

При стандартных `APP_HOST=localhost` и `APP_PORT=8080`:

- Swagger UI: <http://localhost:8080/docs>.
- Актуальная OpenAPI-схема запущенного приложения: <http://localhost:8080/openapi.json>.
- Проверка доступности PostgreSQL и Redis: <http://localhost:8080/health>.

Остановка окружения из корня репозитория: `make back-dev-down`.
Подробности окружения и команды Makefile — в [руководстве разработчика](spec/dev/manual.md).

## Документация

- [Описание продукта и пользовательские сценарии](spec/docs/product.md).
- [Описание API](spec/docs/api.md) и [сохранённая OpenAPI-схема](spec/docs/openapi.json).
  Статические документы могут отставать от кода; текущие маршруты смотрите в Swagger UI.
- [Запуск и разработка](spec/dev/manual.md).
- [Правила работы с репозиторием](CONTRIBUTING.md).
- [Лицензия](LICENSE).
