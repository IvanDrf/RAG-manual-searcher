# Руководство по работе с репозиторием

Базовые правила, названия веток/коммитов/пул рекветсов. Основной стек 

## Наименование

### Ветки
Ветки должны называться в таком формате:

```
type/info
```

Types:
- feat (feauture)
- ref (refactor)
- tests (tests)
- dev (development)
- docs (documents)

Пример:

```
feat/llm_client
tests/unit_tests
```

### Коммиты

Коммиты должны называться в таком формате:

```
[type]:message
```

Types:
- feat (feauture)
- ref (refactor)
- tests (tests)
- dev (development)
- docs (documents)

Пример:

```
[feat]: add RAG for llm
[tests]: add unit tests for auth service
[dev]: add qwen llm client
```

### Пул реквесты

Пул реквесты должны называться в таком формате:

```
[direction:type]:message
```

Directions:
- front (frontend)
- back (backend)
- ml (machine learning)


Types:
- feat (feauture)
- ref (refactor)
- tests (tests)
- dev (development)
- docs (documents)

Пример:

```
[back:feat]: add llm client for search service
```

## Основной стек и правила

Пакетный менеджер для части приложения, написанного на Python - [**uv**](https://docs.astral.sh/uv/).

Использование [**pre-commit**](https://pre-commit.com/) для автоматического форматирования и проверки кода на Python.

Линтер кода для Python - [**ruff**](https://docs.astral.sh/ruff/).