# fastbase

Тонкая инфраструктура поверх FastAPI для быстрого и единообразного построения транспортного (API) слоя приложения.

Пакет — фасад для типового: короткий boilerplate, единый формат ошибок, автозагрузка роутеров, готовые интеграции. Для нетипового — escape hatch в голый FastAPI.

- Python ≥ 3.11, FastAPI ≥ 0.110, pydantic ≥ 2.5, pydantic-settings ≥ 2.1, uvicorn ≥ 0.27.
- Зависимости — только FastAPI и его экосистема. Никаких сторонних библиотек, включая CLI (stdlib argparse).
- API-слой не содержит бизнес-логику: она подключается снаружи через `Depends`.
- Всё поведение — через переменные окружения (префикс `FAT_`, файл `.env.fastbase`).

---

## Установка

```bash
# Только fastbase
pip install git+https://github.com/senia-glitch/fastapi-transport.git

# fastbase + core-package + event-infra (для интеграций)
pip install "fastbase[full] @ git+https://github.com/senia-glitch/fastapi-transport.git"

# Разработка
pip install "fastbase[dev] @ git+https://github.com/senia-glitch/fastapi-transport.git"
Quickstart
bash
# 1. Сгенерировать структуру проекта в текущей папке
fb init

# 2. Отредактировать .env.fastbase (при необходимости)

# 3. Запустить приложение
python -m app.main
Откройте http://127.0.0.1:8000/docs.

Три команды — и рабочий API. Точка входа app/main.py уже собрана: авто-загрузка роутеров, обработчики ошибок, middleware — на месте.

Единственный способ запуска
python
# app/main.py
from fastbase import make_app, start

app = make_app()

if __name__ == "__main__":
    start()
Никаких аргументов, никаких вариантов. Всё поведение читается из .env.fastbase.

make_app() — собирает FastAPI по env. Возвращает app. Используй для тестов, интеграции с TestClient, а также для ASGI-режима (uvicorn app.main:app).

start() — запускает uvicorn с параметрами из env. Блокирует процесс.

Для --reload и --workers > 1 (uvicorn требует import-string) — используйте штатные переменные FAT_RELOAD и FAT_WORKERS. start() подхватит их и передаст в uvicorn. При этом app должен быть определён на уровне модуля — что и делается через make_app().

Конфигурация
Все настройки читаются через pydantic-settings. Префикс — FAT_. Файл по умолчанию — .env.fastbase. Реальные env-переменные побеждают значения из файла.

API
Переменная	Тип	Дефолт	Описание
FAT_TITLE	str	API	Заголовок OpenAPI.
FAT_VERSION	str	0.0.0	Версия в OpenAPI.
FAT_DESCRIPTION	str	``	Описание OpenAPI.
FAT_API_PREFIX	str	/api/v1	Префикс, под который монтируются все роутеры.
Routes
Переменная	Тип	Дефолт	Описание
FAT_ROUTES_PACKAGE	str	app.api.v1.routes	Пакет с роутерами для авто-сборки.
Контракт модуля роутера:

python
# app/api/v1/routes/users.py
from fastapi import APIRouter

router = APIRouter(tags=["users"])   # обязательный атрибут

@router.get("/")
async def list_users(): ...
Опционально — prefix: str на уровне модуля:

python
# app/api/v1/routes/admin.py
from fastapi import APIRouter

prefix = "/admin"           # прибавится к FAT_API_PREFIX
router = APIRouter(tags=["admin"])

@router.get("/stats")
async def stats(): ...
Итоговый путь: {FAT_API_PREFIX}{module_prefix}{path}.

Правила сканера:

модули с _ в начале — пропускаются;

модуль без router: APIRouter — пропускается;

ошибка импорта модуля — warning, продолжаем;

если ни один роутер не найден — монтируется только health_router (warning).

Integrations
Переменная	Тип	Дефолт	Описание
FAT_INTEGRATIONS	str	``	Пусто или core,event-infra.
FAT_CORE_DISCOVER	str | null	null	Пакет со сценариями core-package.
Если FAT_INTEGRATIONS=core,event-infra, при старте приложения:

start_infrastructure() — поднимается event-infra, применяются миграции;

start_core(router=router, discover=FAT_CORE_DISCOVER) — поднимается core-package;

Регистрируется обработчик core.exceptions.CoreError — ошибки core автоматически конвертируются в единый конверт fastbase.

На shutdown — обратный порядок: reset_core() → router.shutdown().

Требуется pip install "fastbase[full]".

Docs
Переменная	Тип	Дефолт	Описание
FAT_DOCS_URL	str | null	/docs	URL Swagger UI. null — выключить.
FAT_OPENAPI_URL	str | null	/openapi.json	URL OpenAPI-схемы.
FAT_REDOC_URL	str | null	/redoc	URL ReDoc.
FAT_OPENAPI_TAGS	JSON [{name, description}]	`[]`	Упорядоченный список тегов для OpenAPI.

FAT_OPENAPI_TAGS задаёт порядок и описание тегов в /docs. Порядок тегов детерминирован и не зависит от порядка файлов роутов:

dotenv
FAT_OPENAPI_TAGS='[{"name": "users", "description": "Пользователи"}, {"name": "admin", "description": "Админка"}]'
Request-ID
Переменная	Тип	Дефолт	Описание
FAT_REQUEST_ID_ENABLED	bool	true	Включить RequestIdMiddleware.
FAT_REQUEST_ID_HEADER	str	X-Request-ID	Имя заголовка.
Logging
Переменная	Тип	Дефолт	Описание
FAT_LOG_LEVEL	str	info	Уровень логирования.
FAT_LOG_FORMAT	plain | json	plain	Формат лог-записей.
FAT_ACCESS_LOG	bool	true	Включить AccessLogMiddleware.
Errors
Переменная	Тип	Дефолт	Описание
FAT_ERROR_CODES	JSON {str: int}	{}	Переопределение числовых кодов.
FAT_ERROR_CODE_FALLBACK	int	3500	Код для нераспознанных исключений.
Uvicorn
Переменная	Тип	Дефолт	Описание
FAT_HOST	str	127.0.0.1	Хост uvicorn.
FAT_PORT	int	8000	Порт uvicorn.
FAT_RELOAD	bool	false	Uvicorn reload. При true форсит workers=1.
FAT_WORKERS	int	1	Количество воркеров.
FAT_BACKLOG	int	2048	Backlog uvicorn.
FAT_TIMEOUT_KEEP_ALIVE	int	5	Keep-alive timeout.
FAT_ROOT_PATH	str	``	ASGI root_path (за прокси).
FAT_APP_PATH	str	app.main:app	Import string приложения.
FAT_ENV_FILE	str | null	null	Опциональный env-файл для uvicorn.
Пользовательские поля в наследнике BaseAppSettings тоже читаются из env — с тем же префиксом FAT_:

python
from fastbase import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = ""
    jwt_secret: str = ""


settings = Settings()
Ошибки
Единый конверт для всех ошибок — доменных, HTTPException, RequestValidationError, необработанных:

json
{
  "success": false,
  "error": {
    "code": 2001,
    "message": "User not found",
    "details": null
  }
}
code — целое число;

message — строка;

details — null или произвольная JSON-структура.

Успешные ответы — сырой JSON. Envelope не вводится.

Иерархия исключений
python
from fastbase import (
    BaseHTTPError,     # 500
    NotFoundError,     # 404
    ValidationError,   # 422
    ConflictError,     # 409
    UnauthorizedError, # 401
    ForbiddenError,    # 403
    InternalError,     # 500
)
Свои исключения наследуются от базовых:

python
from fastbase import NotFoundError


class UserNotFoundError(NotFoundError):
    message = "User not found"
Числовой код резолвится в таком порядке:

exc.code — явный override в __init__;

exc.default_code — атрибут класса;

первое совпадение по type(exc).__mro__ в маппинге;

FAT_ERROR_CODE_FALLBACK.

Свой код задаётся через env:

dotenv
FAT_ERROR_CODES={"UserNotFoundError": 2001}
Интеграция с core-package
Если FAT_INTEGRATIONS=core,event-infra, при старте приложения автоматически:

Поднимается event-infra (start_infrastructure()), применяются миграции;

Поднимается core-package (start_core(router=router, discover=FAT_CORE_DISCOVER));

Регистрируется обработчик core.exceptions.CoreError — все ошибки core автоматически конвертируются в единый конверт fastbase.

Из роутов можно сразу использовать сценарии и get_db:

python
from fastapi import APIRouter, Depends
from core import get_db, run

router = APIRouter(tags=["users"])


@router.post("/users")
async def create_user(dto: CreateUserDTO) -> dict:
    result = await run("register_user", dto)
    return result.model_dump()
Если FAT_INTEGRATIONS="" (по умолчанию) — никаких интеграций. Пользователь сам решает, как подключать БД, через Depends.

Также поддерживается режим FAT_INTEGRATIONS=core (только core-package без event-infra). В этом случае регистрируется обработчик CoreError, но lifespan не создаётся.

scenario_route — автоматический response_model

Декоратор scenario_route автоматически подставляет response_model из реестра сценариев core-package:

python
from fastapi import APIRouter
from fastbase import scenario_route

router = APIRouter(tags=["users"])

@scenario_route(router, "/users", method="post", scenario="register_user")
async def create_user(dto: CreateUserDTO):
    result = await run("register_user", dto)
    return result

Если core-package установлен — response_model берётся из реестра. Если не установлен — логируется warning, роут работает без response_model.

Middleware
Пакет ставит два middleware:

RequestIdMiddleware — читает заголовок FAT_REQUEST_ID_HEADER из запроса или генерирует uuid4().hex. Кладёт значение в request.state.request_id и в ответный заголовок.

AccessLogMiddleware — пишет строку METHOD PATH STATUS DURATION_MS request_id=... в логгер fastbase.access.

Порядок — Request-ID снаружи, Access Log внутри. Request-ID доступен в логе и в заголовке ответа даже если access-лог упадёт.

Что не входит
CORS, GZip, TrustedHost — пакет их не ставит. Ставьте сами после make_app():

python
from fastapi.middleware.cors import CORSMiddleware
from fastbase import make_app

app = make_app()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
CLI
Алиасы fastbase и fb работают идентично.

fb init [--path app] [--force]
Генерирует каноничную структуру. --path — целевая папка (по умолчанию app). --force перезаписывает файлы с маркером # fastbase: generated; файлы без маркера не трогаются никогда.

Статусы: created:, overwrite:, skip:, skip (user code):.

fb check
Read-only проверки:

обязательные файлы на месте;

BaseAppSettings валидируется;

app.main:app импортируется;

FAT_ROUTES_PACKAGE импортируется;

дубли prefix в main.py;

конфликт FAT_RELOAD=true и FAT_WORKERS>1.

Печатает ok / warn / fail. Код возврата 1 при fail.

fb version
Версия пакета одной строкой.

fb upgrade [--check]
Обновление пакета до последней версии с GitHub. НЕ затрагивает файлы проекта (app/, .env.fastbase, pyproject.toml).

fb upgrade — проверяет версию на GitHub, если доступна новая → выполняет pip install --upgrade.
fb upgrade --check — только проверяет, не обновляет (полезно в CI).

Проверка совместимости: если новая версия требует другой Python — спрашивает подтверждение yes/no.

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
uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
Что остаётся работать без изменений:

роуты — обычные APIRouter;

DI — обычный Depends;

схемы — обычный pydantic;

OpenAPI — штатный.

Ограничения
Пакет не делает:

не содержит бизнес-логику;

не вводит свой DI — используется Depends;

не вводит свою валидацию — pydantic v2;

не вводит свой роутинг — APIRouter + авто-сборка;

не диктует ORM, БД, аутентификацию, брокеры;

не заменяет OpenAPI;

не подключает сторонние библиотеки;

не вводит CORS / GZip / TrustedHost;

не вводит envelope успешных ответов.

Обработчик Exception ловит исключения из роутов и зависимостей, но не из ASGI-middleware: исключения, брошенные внутри middleware, возвращаются в формате Starlette.

Лицензия
MIT. См. LICENSE.