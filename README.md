# fastbase

Тонкая инфраструктура поверх FastAPI для быстрого и единообразного построения транспортного (API) слоя приложения.

Пакет — фасад для типового: короткий boilerplate, единый формат ошибок, готовая структура проекта. Для нетипового — escape hatch в голый FastAPI.

- Python ≥ 3.11, FastAPI ≥ 0.110, pydantic ≥ 2.5, pydantic-settings ≥ 2.1, uvicorn ≥ 0.27.
- Зависимости — только FastAPI и его экосистема. Никаких сторонних библиотек, включая CLI (stdlib argparse).
- API-слой не содержит бизнес-логику: она подключается снаружи через `Depends`.

---

## Установка

```bash
pip install git+https://github.com/senia-glitch/fastapi-transport.git
```

Установка для разработки самого пакета:

```bash
git clone https://github.com/senia-glitch/fastapi-transport.git
cd fastapi-transport
pip install -e ".[dev]"
```

---

## Quickstart

```bash
# 1. Сгенерировать структуру проекта в текущей папке
fastapi-transport init

# 2. Отредактировать .env.fastbase (при необходимости)

# 3. Запустить приложение
python -m app.main
```

Откройте <http://127.0.0.1:8000/docs>.

Три команды — и рабочий API. Точка входа `app/main.py` уже собрана: роутинг, обработчики ошибок, middleware — на месте.

---

## Что генерирует `init`

```
app/
├── main.py                     # точка входа: create_app() + run_api()
├── core/
│   ├── config.py               # Settings(BaseAppSettings) — ваши поля
│   ├── exceptions.py           # доменные исключения (наследники от fastbase)
│   └── env.py                  # путь к .env.fastbase, если нужно явно
├── api/
│   ├── v1/
│   │   ├── routes/
│   │   │   └── health.py       # health-check (пример роутера)
│   │   └── dependencies.py     # провайдеры Depends
│   └── handlers.py             # дополнительные exception handlers
├── schemas/
│   └── example.py              # пример pydantic-схемы
├── .env.fastbase               # настройки пакета (префикс FAT_)
└── pyproject.toml              # создаётся, только если его ещё нет
```

Правила генератора:

- каждый созданный файл начинается с маркера `# fastbase: generated`;
- файлы без маркера **никогда** не перезаписываются;
- файлы с маркером перезаписываются только при `--force`;
- `.env.fastbase` кладётся в корень (там, где запущен `init`);
- существующий `pyproject.toml` не трогается;
- после работы печатается дерево и next steps.

---

## Конфигурация

Все настройки читаются через pydantic-settings. Префикс — `FAT_`. Файл по умолчанию — `.env.fastbase`. Реальные env-переменные **побеждают** значения из файла.

| Переменная | Тип | Дефолт | Описание |
|---|---|---|---|
| `FAT_TITLE` | str | `API` | Заголовок OpenAPI. |
| `FAT_VERSION` | str | `0.0.0` | Версия в OpenAPI. |
| `FAT_DESCRIPTION` | str | `` | Описание OpenAPI. |
| `FAT_API_PREFIX` | str | `/api/v1` | Префикс, под который монтируются все роутеры. |
| `FAT_DOCS_URL` | str \| null | `/docs` | URL Swagger UI. `null` — выключить. |
| `FAT_OPENAPI_URL` | str \| null | `/openapi.json` | URL OpenAPI-схемы. |
| `FAT_REDOC_URL` | str \| null | `/redoc` | URL ReDoc. |
| `FAT_REQUEST_ID_ENABLED` | bool | `true` | Включить `RequestIdMiddleware`. |
| `FAT_REQUEST_ID_HEADER` | str | `X-Request-ID` | Имя заголовка для request-id. |
| `FAT_LOG_LEVEL` | str | `info` | Уровень логирования пакета. |
| `FAT_LOG_FORMAT` | `plain` \| `json` | `plain` | Формат лог-записей. |
| `FAT_ACCESS_LOG` | bool | `true` | Включить `AccessLogMiddleware`. |
| `FAT_ERROR_CODES` | JSON `{str: int}` | `{}` | Переопределение числовых кодов. |
| `FAT_ERROR_CODE_FALLBACK` | int | `3500` | Код для нераспознанных исключений. |
| `FAT_HOST` | str | `127.0.0.1` | Хост uvicorn. |
| `FAT_PORT` | int | `8000` | Порт uvicorn. |
| `FAT_RELOAD` | bool | `false` | Uvicorn reload. При `true` форсит `workers=1`. |
| `FAT_WORKERS` | int | `1` | Количество воркеров. |
| `FAT_BACKLOG` | int | `2048` | Backlog uvicorn. |
| `FAT_TIMEOUT_KEEP_ALIVE` | int | `5` | Keep-alive timeout. |
| `FAT_ROOT_PATH` | str | `` | ASGI root_path (за прокси). |
| `FAT_APP_PATH` | str | `app.main:app` | Import string приложения. |
| `FAT_ENV_FILE` | str \| null | `null` | Опциональный env-файл для uvicorn. |

### `FAT_ERROR_CODES`

Значение — JSON-объект «имя класса исключения → целое число». Пример в `.env.fastbase`:

```dotenv
FAT_ERROR_CODES={"UserNotFoundError": 2001, "PaymentFailed": 2002}
```

Домены можно разделять по диапазонам: `2xxx` — ваш домен, `3xxx` — зарезервировано за пакетом (обёртки над ошибками FastAPI).

Пользовательские поля в наследнике `BaseAppSettings` тоже читаются из env — просто с тем же префиксом `FAT_`:

```python
from fastbase import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = ""
    jwt_secret: str = ""


settings = Settings()
```

---

## Ошибки

Единый конверт для **всех** ошибок — доменных, `HTTPException`, `RequestValidationError`, необработанных:

```json
{
  "success": false,
  "error": {
    "code": 2001,
    "message": "User not found",
    "details": null
  }
}
```

- `code` — целое число;
- `message` — строка;
- `details` — `null` или произвольная JSON-структура.

Успешные ответы — сырой JSON. Envelope не вводится.

### Иерархия исключений

```python
from fastbase import (
    BaseHTTPError,     # 500
    NotFoundError,     # 404
    ValidationError,   # 422
    ConflictError,     # 409
    UnauthorizedError, # 401
    ForbiddenError,    # 403
    InternalError,     # 500
)
```

Свои исключения наследуются от базовых:

```python
from fastbase import NotFoundError


class UserNotFoundError(NotFoundError):
    message = "User not found"
```

Числовой код резолвится в таком порядке:

1. `exc.code` — явный override в `__init__`;
2. `exc.default_code` — атрибут класса;
3. первое совпадение по `type(exc).__mro__` в маппинге (например, `UserNotFoundError` без записи в маппинге получит код `NotFoundError`);
4. `FAT_ERROR_CODE_FALLBACK`.

HTTP-статус и числовой код независимы: код можно задать через `FAT_ERROR_CODES`, а статус — через атрибут класса или `http_status`.

### Как задать свой код

```dotenv
FAT_ERROR_CODES={"UserNotFoundError": 2001}
```

---

## Middleware

Пакет ставит два middleware:

- **`RequestIdMiddleware`** — читает заголовок `FAT_REQUEST_ID_HEADER` из запроса или генерирует `uuid4().hex`. Кладёт значение в `request.state.request_id` и в ответный заголовок.
- **`AccessLogMiddleware`** — пишет строку `METHOD PATH STATUS DURATION_MS request_id=...` в логгер `fastbase.access`.

Порядок — Request-ID снаружи, Access Log внутри. Request-ID доступен в логе и в заголовке ответа даже если access-лог упадёт.

### Что **не** входит

CORS, GZip, TrustedHost — пакет их не ставит. Ставьте сами, как в голом FastAPI:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app: FastAPI = create_app(settings, routers)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Запуск

Единственная точка входа — `run_api()`:

```python
from fastbase import run_api


def main() -> None:
    run_api("app.main:app")


if __name__ == "__main__":
    main()
```

`run_api` блокирует процесс. Все параметры uvicorn читаются из настроек пакета: `FAT_HOST`, `FAT_PORT`, `FAT_RELOAD`, `FAT_WORKERS`, `FAT_LOG_LEVEL`, `FAT_APP_PATH`, `FAT_ENV_FILE`. Access-log uvicorn отключается автоматически — за него отвечает `AccessLogMiddleware`.

Три режима:

```bash
# Основной
python -m app.main

# Внешний ASGI
uvicorn app.main:app

# Dev с autoreload
uvicorn app.main:app --reload
```

Graceful shutdown — через `lifespan`, который передаётся в `create_app`:

```python
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    # startup
    yield
    # shutdown


app = create_app(settings, routers, lifespan=lifespan)
```

---

## CLI

Команда пакета — `fastapi-transport`. Есть алиасы `fastbase` и `fb`; работают идентично.

```bash
fastapi-transport help   # список команд + ссылка на GitHub
```

### `fastapi-transport init [--path app] [--force]`

Генерирует каноничную структуру. `--path` — целевая папка (по умолчанию `app`). `--force` перезаписывает файлы с маркером `# fastbase: generated`; файлы без маркера не трогаются никогда.

Статусы в выводе:

- `created:` — файл создан;
- `overwrite:` — файл перезаписан (`--force` + маркер);
- `skip:` — файл существует и не перезаписан;
- `skip (user code):` — файл без маркера, пользовательский код.

### `fastapi-transport check`

Read-only проверка проекта:

- обязательные файлы на месте;
- `BaseAppSettings` валидируется;
- `app.main:app` импортируется;
- все роутеры из `app/api/v1/routes/*.py` подключены в `main.py`;
- нет дублей `prefix`;
- нет конфликта `FAT_RELOAD=true` и `FAT_WORKERS>1`.

Печатает `ok` / `warn` / `fail`. Код возврата `1` при `fail`, иначе `0`.

### `fastapi-transport version`

Печатает версию пакета одной строкой.

---

## Escape hatch

Пакет можно выкинуть из проекта без переписывания приложения:

```python
# было
from fastbase import create_app, run_api
app = create_app(settings, routers)
run_api("app.main:app")

# стало — голый FastAPI
from fastapi import FastAPI
import uvicorn

app = FastAPI()
for r in routers:
    app.include_router(r, prefix="/api/v1")

uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
```

Что остаётся работать без изменений:

- роуты — обычные `APIRouter`;
- DI — обычный `Depends`;
- схемы — обычный `pydantic`;
- OpenAPI — штатный.

`create_app` возвращает обычный `FastAPI`, `health_router` — обычный `APIRouter`. Их можно использовать вручную или не использовать вовсе.

---

## Ограничения

Пакет **не** делает:

- не содержит бизнес-логику и не провоцирует её класть в API-слой;
- не вводит свой DI — используется `Depends`;
- не вводит свою валидацию — используется pydantic v2;
- не вводит свой роутинг — используется `APIRouter`;
- не диктует ORM, БД, аутентификацию, брокеры;
- не заменяет OpenAPI;
- не подключает сторонние библиотеки;
- не забирает контроль над запуском проекта;
- не вводит CORS / GZip / TrustedHost — ставит их клиент;
- не вводит envelope успешных ответов;
- не делает auto-discovery роутов;
- не реализует команду `upgrade`;
- не публикуется на PyPI (только GitHub).
- обработчик `Exception` ловит исключения из роутов и зависимостей, но не из ASGI-middleware: исключения, брошенные внутри middleware, возвращаются в формате Starlette, а не в едином конверте.
---

## Лицензия

MIT. См. [LICENSE](LICENSE).