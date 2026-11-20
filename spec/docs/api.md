# RAG-research app — Документация API

**Версия:** 0.1.0
**Спецификация:** OpenAPI 3.1.0

---

## Содержание

1. [Общая информация](#общая-информация)
2. [Аутентификация (authorization)](#аутентификация-authorization)
   - [POST /api/v1/auth/register](#post-apiv1authregister)
   - [POST /api/v1/auth/login](#post-apiv1authlogin)
   - [POST /api/v1/auth/logout](#post-apiv1authlogout)
   - [GET /api/v1/auth/me](#get-apiv1authme)
   - [POST /api/v1/auth/refresh](#post-apiv1authrefresh)
3. [Администрирование (admin)](#администрирование-admin)
   - [GET /api/v1/admin/users](#get-apiv1adminusers)
   - [PATCH /api/v1/admin/users/role](#patch-apiv1adminusersrole)
   - [POST /api/v1/admin/users/block](#post-apiv1adminusersblock)
   - [DELETE /api/v1/admin/users/block](#delete-apiv1adminusersblock)
4. [Чат (chat)](#чат-chat)
   - [POST /api/v1/chat/promt](#post-apiv1chatpromt)
5. [Служебные](#служебные)
   - [GET /health](#get-health)
6. [Схемы данных (components/schemas)](#схемы-данных-componentsschemas)

---

## Общая информация

Базовый URL: `http://<host>:<port>`

Все защищённые эндпоинты используют **cookie-параметр** `access-token`. Для обновления сессии используется **cookie-параметр** `refresh-token`.

Формат данных — `application/json`.

Стандартные ответы ошибок:
- `422` — Validation Error (см. схему `HTTPValidationError`)

---

## Аутентификация (authorization)

### POST /api/v1/auth/register

**Описание:** Метод для регистрации пользователя со стандартной ролью — пользователь.

**Тело запроса** (`application/json`, обязательное):

| Поле | Тип | Ограничения | Обязательное |
|------|-----|-------------|--------------|
| `username` | string | minLength: 4, maxLength: 20 | да |
| `password` | string | minLength: 5, maxLength: 30 | да |

**Схема:** `RegisterUserSchema`

**Ответы:**

| Код | Описание |
|-----|----------|
| 204 | Successful Response |
| 422 | Validation Error (`HTTPValidationError`) |

---

### POST /api/v1/auth/login

**Описание:** Логин пользователя.

**Тело запроса** (`application/json`, обязательное):

| Поле | Тип | Ограничения | Обязательное |
|------|-----|-------------|--------------|
| `username` | string | minLength: 4, maxLength: 20 | да |
| `password` | string | minLength: 5, maxLength: 30 | да |

**Схема:** `LoginUserSchema`

**Ответы:**

| Код | Описание |
|-----|----------|
| 204 | Successful Response |
| 422 | Validation Error (`HTTPValidationError`) |

---

### POST /api/v1/auth/logout

**Описание:** Выйти из аккаунта.

**Параметры:** отсутствуют.

**Ответы:**

| Код | Описание |
|-----|----------|
| 204 | Successful Response |

---

### GET /api/v1/auth/me

**Описание:** Информация о пользователе.

**Параметры:**

| Имя | В | Тип | Обязательный | Описание |
|-----|---|-----|--------------|----------|
| `access-token` | cookie | string | да | Access-токен |

**Ответы:**

| Код | Описание | Схема |
|-----|----------|-------|
| 200 | Successful Response | `UserInfoSchema` |
| 422 | Validation Error | `HTTPValidationError` |

**Пример ответа 200:**
```json
{
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "user_role": "user"
}
```

---

### POST /api/v1/auth/refresh

**Описание:** Обновление токенов по refresh токену.

**Параметры:**

| Имя | В | Тип | Обязательный | Описание |
|-----|---|-----|--------------|----------|
| `refresh-token` | cookie | string | да | Refresh-токен |

**Ответы:**

| Код | Описание |
|-----|----------|
| 204 | Successful Response |
| 422 | Validation Error (`HTTPValidationError`) |

---

## Администрирование (admin)

### GET /api/v1/admin/users

**Описание:** Получение списка пользователей для админа.

**Параметры:**

| Имя | В | Тип | Обязательный | Ограничения | Описание |
|-----|---|-----|--------------|-------------|----------|
| `user_role` | query | `UserRole` \| null | нет | — | Фильтр по роли |
| `limit` | query | integer | да | min: 1, max: 40 | Кол-во записей |
| `offset` | query | integer | да | min: 0 | Смещение |
| `access-token` | cookie | string | да | — | Access-токен |

**Ответы:**

| Код | Описание | Схема |
|-----|----------|-------|
| 200 | Successful Response | array of `UserForAdminSchema` |
| 422 | Validation Error | `HTTPValidationError` |

**Пример ответа 200:**
```json
[
  {
    "username": "admin",
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "user_role": "admin"
  }
]
```

---

### PATCH /api/v1/admin/users/role

**Описание:** Изменить роль пользователю.

**Параметры:**

| Имя | В | Тип | Обязательный | Описание |
|-----|---|-----|--------------|----------|
| `access-token` | cookie | string | да | Access-токен |

**Тело запроса** (`application/json`, обязательное):

| Поле | Тип | Ограничения | Обязательное |
|------|-----|-------------|--------------|
| `username` | string | minLength: 4, maxLength: 20 | да |
| `user_role` | `UserRole` | enum: `admin`, `user` | да |

**Схема:** `ChangeUserRoleSchema`

**Ответы:**

| Код | Описание |
|-----|----------|
| 204 | Successful Response |
| 422 | Validation Error (`HTTPValidationError`) |

---

### POST /api/v1/admin/users/block

**Описание:** Заблокировать пользователя.

**Параметры:**

| Имя | В | Тип | Обязательный | Описание |
|-----|---|-----|--------------|----------|
| `access-token` | cookie | string | да | Access-токен |

**Тело запроса** (`application/json`, обязательное):

| Поле | Тип | Ограничения | Обязательное |
|------|-----|-------------|--------------|
| `username` | string | minLength: 4, maxLength: 20 | да |

**Схема:** `BlockUserSchema`

**Ответы:**

| Код | Описание |
|-----|----------|
| 204 | Successful Response |
| 422 | Validation Error (`HTTPValidationError`) |

---

### DELETE /api/v1/admin/users/block

**Описание:** Разблокировать пользователя.

**Параметры:**

| Имя | В | Тип | Обязательный | Описание |
|-----|---|-----|--------------|----------|
| `access-token` | cookie | string | да | Access-токен |

**Тело запроса** (`application/json`, обязательное):

| Поле | Тип | Ограничения | Обязательное |
|------|-----|-------------|--------------|
| `username` | string | minLength: 4, maxLength: 20 | да |

**Схема:** `BlockUserSchema`

**Ответы:**

| Код | Описание |
|-----|----------|
| 204 | Successful Response |
| 422 | Validation Error (`HTTPValidationError`) |

---

## Чат (chat)

### POST /api/v1/chat/promt

**Описание:** Отправить запрос в чат с LLM.

**Параметры:**

| Имя | В | Тип | Обязательный | Описание |
|-----|---|-----|--------------|----------|
| `access-token` | cookie | string | да | Access-токен |

**Тело запроса** (`application/json`, обязательное):

| Поле | Тип | Ограничения | Обязательное |
|------|-----|-------------|--------------|
| `message` | string | minLength: 1, maxLength: 100 | да |

**Схема:** `LLMPromtSchema`

**Ответы:**

| Код | Описание | Схема |
|-----|----------|-------|
| 200 | Successful Response | `LLMResponseSchema` |
| 422 | Validation Error | `HTTPValidationError` |

**Пример ответа 200:**
```json
{
  "model": "gpt-4",
  "response": "Ответ модели на запрос пользователя"
}
```

---

## Служебные

### GET /health

**Описание:** Health check для проверки сервера на работоспособность.

**Параметры:** отсутствуют.

**Ответы:**

| Код | Описание | Схема |
|-----|----------|-------|
| 200 | Successful Response | object with additional string properties |

**Пример ответа 200:**
```json
{
  "status": "ok"
}
```

---

## Схемы данных (components/schemas)

### BlockUserSchema

| Поле | Тип | Ограничения | Обязательное |
|------|-----|-------------|--------------|
| `username` | string | minLength: 4, maxLength: 20 | да |

---

### ChangeUserRoleSchema

| Поле | Тип | Ограничения | Обязательное |
|------|-----|-------------|--------------|
| `username` | string | minLength: 4, maxLength: 20 | да |
| `user_role` | `UserRole` | enum: `admin`, `user` | да |

---

### HTTPValidationError

| Поле | Тип | Обязательное |
|------|-----|--------------|
| `detail` | array of `ValidationError` | нет |

---

### LLMPromtSchema

| Поле | Тип | Ограничения | Обязательное |
|------|-----|-------------|--------------|
| `message` | string | minLength: 1, maxLength: 100 | да |

---

### LLMResponseSchema

| Поле | Тип | Обязательное |
|------|-----|--------------|
| `model` | string | да |
| `response` | string | да |

---

### LoginUserSchema

| Поле | Тип | Ограничения | Обязательное |
|------|-----|-------------|--------------|
| `password` | string | minLength: 5, maxLength: 30 | да |
| `username` | string | minLength: 4, maxLength: 20 | да |

---

### RegisterUserSchema

| Поле | Тип | Ограничения | Обязательное |
|------|-----|-------------|--------------|
| `password` | string | minLength: 5, maxLength: 30 | да |
| `username` | string | minLength: 4, maxLength: 20 | да |

---

### UserForAdminSchema

| Поле | Тип | Формат | Обязательное |
|------|-----|--------|--------------|
| `username` | string | minLength: 4, maxLength: 20 | да |
| `user_id` | string | uuid | да |
| `user_role` | `UserRole` | enum: `admin`, `user` | да |

---

### UserInfoSchema

| Поле | Тип | Формат | Обязательное |
|------|-----|--------|--------------|
| `user_id` | string | uuid | да |
| `user_role` | `UserRole` | enum: `admin`, `user` | да |

---

### UserRole

**Тип:** string
**Допустимые значения:** `admin`, `user`

---

### ValidationError

| Поле | Тип | Обязательное |
|------|-----|--------------|
| `loc` | array of (string \| integer) | да |
| `msg` | string | да |
| `type` | string | да |
| `input` | any | нет |
| `ctx` | object | нет |

---

*Конец документации.*