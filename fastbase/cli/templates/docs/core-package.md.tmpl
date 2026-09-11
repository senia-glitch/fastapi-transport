# core-package

Ядро бизнес-логики: базовый класс сценариев, реестр, DI-контейнер, утилиты (JWT, bcrypt, работа с датами, валидаторы), встроенные реализации кеша, логгера и метрик.

Пакет **не привязан** к конкретной БД. Он предоставляет абстракции (`IDatabase`, `ICache`, `ILogger`, `IMetrics`), а реализации подключаются снаружи — например, через адаптер к `event-infra`.

В связке с `event-infra` и `fastbase` образует полный стек: см. [full-stack.md](./full-stack.md).

---

## Команды

| Команда | Что делает | Когда использовать |
|---|---|---|
| `pip install git+https://github.com/senia-glitch/core-package.git` | Устанавливает пакет | Один раз, при старте проекта |
| `pip install "core-package[event-infra] @ git+https://github.com/senia-glitch/core-package.git"` | Ставит core + event-infra одной командой | Если нужна связка БД + сценарии |
| `core-init` | Создаёт `scenarios/`, `interfaces/`, `utils/`, `.core-package.env`, примеры | Один раз, при старте проекта |
| `core-init --target-dir <путь>` | Создаёт структуру внутри указанной папки (по умолчанию `core_project`) | Когда хочется положить в `app/` |
| `core-init --force` | Перезаписывает сгенерированные файлы | После обновления пакета |

---

## Что генерирует `core-init`

- **`<target>/scenarios/`** — папка для сценариев (наследников `BaseScenario`).
- **`<target>/interfaces/`** — папка для собственных адаптеров, если хочется работать не через `event-infra`.
- **`<target>/utils/`** — папка для своих утилит.
- **`<target>/examples/`** — примеры (`main_example.py` — in-memory, `main_with_event_infra_example.py` — со связкой).
- **`.core-package.env`** — конфиг для JWT/bcrypt/логов/метрик. **Не обязателен**, если все настройки уже в `.env.fastbase`.
- **`pyproject.toml`, `README.md`** — если их ещё нет.

---

## Конфигурация `.core-package.env`

| Переменная | Описание | По умолчанию |
|---|---|---|
| `CORE_JWT_SECRET` | Секрет для подписи JWT | `change-me-in-production` |
| `CORE_ACCESS_TOKEN_MINUTES` | Время жизни access-токена (мин) | `15` |
| `CORE_REFRESH_TOKEN_DAYS` | Время жизни refresh-токена (дни) | `30` |
| `CORE_BCRYPT_ROUNDS` | Раунды bcrypt | `12` |
| `CORE_METRICS_ENABLED` | Включить сбор метрик | `true` |
| `CORE_LOG_LEVEL` | Уровень логов | `INFO` |
| `CORE_LOG_FILE` | Файл для логов (пусто = stdout) | пусто |

Файл ищется в текущей директории и вверх по дереву. Можно указать явно через `CORE_ENV_PATH`.

---

## Как использовать в коде

**1. Сценарий** — класс-наследник `BaseScenario`, помеченный `@register_scenario("имя")`:

```python
from pydantic import BaseModel
from core import BaseScenario, register_scenario, tracked_scenario


class MyDTO(BaseModel):
    name: str


@register_scenario("greet")
@tracked_scenario("greet")
class GreetScenario(BaseScenario):
    async def execute(self, dto: MyDTO):
        return {"message": f"Hello, {dto.name}!"}
2. Запуск ядра и вызов сценария:

python
from core import start_core, run

await start_core(db=my_db, discover="app.scenarios")
result = await run("greet", MyDTO(name="Alice"))
3. Доступ к зависимостям из любого места:

python
from core import get_db, get_cache, get_logger, get_core_metrics
Регистрация сценариев
Способ 1 — декоратор (рекомендуется):

python
@register_scenario("greet")
class GreetScenario(BaseScenario): ...
Срабатывает при импорте модуля. Чтобы модуль импортировался, вызови start_core(discover="app.scenarios") — пакет обойдёт все .py в папке и импортирует.

Способ 2 — вручную:

python
from core import ScenarioRegistry
ScenarioRegistry.register("greet", GreetScenario)
Абстракции
IDatabase — create, read, update, delete, custom.

ICache — get, set, delete, clear.

ILogger — debug, info, warning, error, critical.

IMetrics — record, increment.

Встроенные реализации: InMemoryCache, ConsoleLogger, InMemoryMetrics — работают из коробки, если ничего не передано.

Ограничения
start_core() — синглтон на процесс. Повторный вызов бросит RuntimeError. Для тестов есть reset_core().

Нет собственного ORM — вся работа с БД через IDatabase.

Нет своего роутинга — это задача fastbase.