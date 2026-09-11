# event-infra

Асинхронный инфраструктурный слой доступа к PostgreSQL: пулы соединений, очереди задач, миграции через Alembic, универсальный CRUD. Работает внутри одного Python-процесса как библиотека, не требует отдельного сервера.

В связке с `core-package` и `fastbase` образует полный стек: см. [full-stack.md](./full-stack.md).

---

## Команды

| Команда | Что делает | Когда использовать |
|---|---|---|
| `pip install git+https://github.com/senia-glitch/event-infra.git` | Устанавливает пакет и все зависимости | Один раз, при старте нового проекта |
| `infra-init` | Создаёт `models.py`, `.infra.env`, `alembic/`, `run_infrastructure.py` | Один раз, при старте проекта |
| `infra-init --force` | Перезаписывает сгенерированные файлы | После обновления пакета, если хочется свежие шаблоны |
| `infra-reset <db_url>` | Удаляет все файлы миграций, чистит кеш модулей, дропает все таблицы в `public` | Начать с чистого листа, когда миграции запутались |
| `infra-monitor [interval]` | Подключается к работающему приложению по адресу `API_URL` и печатает метрики | Диагностика запущенного приложения |
| `infra test [-v]` | Прогон встроенных тестов пакета (нужна тестовая БД) | Проверка, что установка корректна |

---

## Что генерирует `infra-init`

- **`models.py`** — шаблон моделей SQLModel. Это **единственный источник истины** о схеме БД. Всё, что попадает в `metadata`, автоматически уходит в БД.
- **`.infra.env`** — конфигурация: `DB_URL`, `DB_URL_ASYNC`, список каналов, размеры пулов, retry, cache.
- **`alembic/`** — рабочая папка миграций (`env.py`, `script.py.mako`, `versions/`). Файлы миграций генерируются автоматически при запуске приложения.
- **`run_infrastructure.py`** — модуль с функцией `start_infrastructure()`. Нужен, если запускать event-infra отдельно или подключать к своему коду.

---

## Конфигурация `.infra.env`

Файл читается автоматически. Основные переменные:

| Переменная | Описание | Пример |
|---|---|---|
| `DB_URL` | Синхронный URL для миграций (psycopg2) | `postgresql://user:pass@localhost:5432/db` |
| `DB_URL_ASYNC` | Асинхронный URL для работы (asyncpg) | `postgresql+asyncpg://user:pass@localhost:5432/db` |
| `CHANNELS` | Список каналов через запятую | `read,write,admin` |
| `{NAME}_POOL_SIZE` | Размер пула канала | `READ_POOL_SIZE=20` |
| `{NAME}_MAX_OVERFLOW` | Доп. соединения при пике | `READ_MAX_OVERFLOW=10` |
| `{NAME}_QUEUE_MAXSIZE` | Размер очереди задач канала | `READ_QUEUE_MAXSIZE=500` |
| `POOL_RECYCLE` | Время жизни соединения (сек) | `3600` |
| `POOL_PRE_PING` | Проверка соединения через SELECT 1 | `True` |
| `RETRY_MAX_RETRIES` | Число retry при ошибках соединения | `3` |
| `CACHE_ENABLED` | Кеш чтения | `True` |

Полный список — с комментариями в самом `.infra.env`.

---

## Как использовать в коде

```python
from run_infrastructure import start_infrastructure

router = await start_infrastructure()
try:
    # CRUD
    user = await router.create("users", {"username": "alice"})
    data = await router.read("users", 1)

    # Произвольный SQL
    rows = await router.custom("SELECT * FROM users", channel="read")
finally:
    await router.shutdown()
start_infrastructure():

Читает .infra.env.

Применяет миграции: сравнивает models.py с реальной БД и создаёт ревизию, если что-то изменилось.

Создаёт пулы, очереди и диспетчеры для каждого канала.

Возвращает EventRouter.

Каналы
Каждый канал — это отдельный пул соединений и очередь задач. По умолчанию три: read, write, admin. Можно добавлять свои (report, analytics, …) через CHANNELS в .infra.env.

Смысл разделения — изолировать нагрузку: тяжёлые аналитические запросы не блокируют быстрые транзакционные.

Ограничения
Только PostgreSQL (asyncpg).

Одна БД на процесс.

Очереди FIFO, без приоритетов.

Метрики — через свой endpoint, отдельный сервер для мониторинга нужен только для infra-monitor.

