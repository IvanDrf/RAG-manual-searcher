# Информация по разработке

## Работа с Backend

Создайте файл ```.env``` и создайте в нем переменные окрудения, необходимые для работы приложения

```bash
cat .env.example > env
```

Желательно поменять чувствительные переменные окружения такие как ```user``` и ```password```

Перейдите в директорию `back/`

```bash
cd back
```

Перед началом работы установите зависимости

```bash
uv sync --dev
```

Желательно поменять чувствительные переменные окружения такие как ```user``` и ```password```

Чтобы запустить необходимые контейнеры для разработки перейдите на директорию выше. (корневая директория проекта)
```bash
cd ..
```

Запустите контейнеры для разработки

```bash
make back-dev-up
```

---

Для поддержания актуальной версии СУБД, в данном случае PostgreSQL, применить все миграции к базе данных

Зайдите в директорию `back/`
```bash
cd back/
```

Примените миграции

```bash
uv run alembic upgrade head
```

Запускать различные скрипты или сам backend сервер, нужно из директории `back/`:

Запуск backend сервера:

```bash
uv run -m src.app.main
```

Запуск миграции данных в СУБД PostgreSQL:

```bash
uv run -m scripts.data.data_migration
```

## Работа с Makefile

Небольшой Makefile для управления dev- и prod-окружением бэкенда (`back/`) через `docker-compose`.

---

### Требования

- `make`
- `docker` и `docker-compose`
- Файл `.env` в **корне репозитория**
- Docker & docker-compose файлы в `infrastructure/back/`:
  - `docker-compose.dev.yml`
  - `docker-compose.prod.yml`
  - `Dockerfile`

---

## Быстрый старт

### Разработка
```bash
# Поднять dev-окружение с пересборкой образа
make back-dev-up-build

# Поднять dev-окружение
make back-dev-up

# Остановить
make back-dev-down

# Остановить с удалением данных
make back-dev-down-volumes

```

### Прод

```bash
# Поднять prod-окружение с пересборкой образа
make back-prod-up-build

# Поднять prod-окружение
make back-prod-up

# Остановить
make back-prod-down

# Остановить с удалением данных
make back-prod-down-volumes

# Смотреть логи
make back-prod-app-logs

# Остановить
make back-prod-down
```
