# fastbase

Тонкий API-фасад поверх FastAPI. Управляется через переменные окружения (префикс `FAT_`, файл `.env.fastbase`). Даёт: авто-сборку роутеров, единый конверт ошибок, middleware request-id и access-log, готовую сборку приложения одной функцией `make_app()` и запуск uvicorn одной функцией `start()`.

В связке с `event-infra` и `core-package` образует полный стек: см. [full-stack.md](./full-stack.md).

---

## Команды

| Команда | Что делает | Когда использовать |
|---|---|---|
| `pip install git+https://github.com/senia-glitch/fastapi-transport.git` | Устанавливает только fastbase | Если нужен API без core/event-infra |
| `pip install "fastbase[full] @ git+https://github.com/senia-glitch/fastapi-transport.git"` | Ставит fastbase + core-package + event-infra | Для полного стека |
| `pip install "fastbase[dev] @ git+https://github.com/senia-glitch/fastapi-transport.git"` | Ставит с тестовыми зависимостями | Для разработки самого fastbase |
| `fb init` | Создаёт `app/`, `.env.fastbase`, `pyproject.toml`, `docs/` | Один раз, при старте проекта |
| `fb init --path <путь>` | Кладёт код приложения в другую папку (по умолчанию `app`) | Если хочется `svc/` или `api/` |
| `fb init --force` | Перезаписывает файлы с маркером `# fastbase: generated` | После обновления пакета |
| `fb check` | Проверяет проект: файлы на месте, env валидны, `app.main:app` импортируется | Диагностика перед запуском |
| `fb version` | Печатает версию пакета | Для отчёта о проблеме |
| `fb help` | Справка со ссылкой на GitHub | Первое знакомство |

Алиасы `fastbase` и `fastapi-transport` работают идентично `fb`.

---

## Что генерирует `fb init`

- **`app/main.py`** — точка входа: `app = make_app()`, `if __name__ == "__main__": start()`.
- **`app/core/config.py`** — `Settings(BaseAppSettings)` для своих полей.
- **`app/core/exceptions.py`** — место для доменных исключений (наследников от `fastbase`).
- **`app/api/v1/routes/health.py`** — пример роута (`health_router`).
- **`app/api/v1/dependencies.py`** — место для `Depends`-провайдеров.
- **`app/api/handlers.py`** — место для дополнительных exception handlers.
- **`app/schemas/example.py`** — пример pydantic-схемы.
- **`.env.fastbase`** — конфиг пакета.
- **`pyproject.toml`** — если его ещё нет.
- **`docs/`** — четыре файла документации (этот и три других).

---

## Конфигурация `.env.fastbase`

Основные переменные (полный список — в самом файле):

| Переменная | Описание | По умолчанию |
|---|---|---|
| `FAT_TITLE` | Заголовок OpenAPI | `API` |
| `FAT_API_PREFIX` | Префикс для всех роутеров | `/api/v1` |
| `FAT_ROUTES_PACKAGE` | Пакет с роутами для авто-сборки | `app.api.v1.routes` |
| `FAT_INTEGRATIONS` | Интеграции: пусто или `core,event-infra` | пусто |
| `FAT_CORE_DISCOVER` | Пакет со сценариями (для core) | пусто |
| `FAT_HOST` / `FAT_PORT` | Адрес uvicorn | `127.0.0.1` / `8000` |
| `FAT_RELOAD` | Перезагрузка при изменении файлов | `false` |
| `FAT_WORKERS` | Число воркеров uvicorn | `1` |
| `FAT_LOG_LEVEL` | Уровень логов | `info` |
| `FAT_REQUEST_ID_ENABLED` | Заголовок `X-Request-ID` | `true` |
| `FAT_ERROR_CODES` | JSON-маппинг «класс → код» | `{}` |

---

## Авто-сборка роутеров

`make_app()` сканирует пакет `FAT_ROUTES_PACKAGE`. В каждом модуле ищет:

- **`router: APIRouter`** — обязательное имя атрибута, если модуль хочет что-то добавить.
- **`prefix: str`** — необязательный префикс модуля (прибавится к `FAT_API_PREFIX`).

Правила:
- модули, начинающиеся с `_`, — пропускаются;
- модули без `router` — пропускаются;
- ошибка импорта модуля — warning, продолжаем;
- если ни один роут не найден — монтируется только `health_router`.

Пример роута:

```python
# app/api/v1/routes/users.py
from fastapi import APIRouter

router = APIRouter(tags=["users"])

@router.get("/users")
async def list_users(): ...
Единый конверт ошибок
Все ошибки — доменные, HTTPException, RequestValidationError, необработанные — приводятся к виду:

json
{
  "success": false,
  "error": {
    "code": 2001,
    "message": "User not found",
    "details": null
  }
}
Иерархия исключений в fastbase.errors:

BaseHTTPError (500)

NotFoundError (404)

ValidationError (422)

ConflictError (409)

UnauthorizedError (401)

ForbiddenError (403)

InternalError (500)

Свой числовой код задаётся через FAT_ERROR_CODES:

env
FAT_ERROR_CODES={"UserNotFoundError": 2001}
Middleware
RequestIdMiddleware — читает или генерирует X-Request-ID, кладёт в request.state.request_id и в ответный заголовок.

AccessLogMiddleware — пишет строку METHOD PATH STATUS DURATION request_id=... в логгер fastbase.access.

Порядок — Request-ID снаружи, Access Log внутри. CORS, GZip, TrustedHost — не ставятся, добавляй сам, как в обычном FastAPI.

Escape hatch
Пакет можно выкинуть из проекта без переписывания приложения:

python
# было
from fastbase import make_app, start
app = make_app()
start()

# стало — голый FastAPI
from fastapi import FastAPI
import uvicorn

app = FastAPI()
uvicorn.run("app.main:app")
Роуты, Depends, pydantic-схемы, OpenAPI — всё остаётся работать.

Ограничения
start() блокирует процесс (это uvicorn).

FAT_RELOAD=true и FAT_WORKERS>1 требуют, чтобы app был доступен как import-string — то есть определён на уровне модуля, что и делает make_app().

Обработчик Exception ловит исключения из роутов, но не из ASGI-middleware.