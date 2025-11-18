# ТЗ: Автогенерация API-моделей и каркаса REST по спецификации

Цель: реализовать минимальную, но расширяемую систему **spec-first генерации** Pydantic-моделей и каркаса REST-ручек из YAML-спецификаций. Это ядро, которое дальше можно наращивать для low-code/LLM-платформы.

## 1. Общая идея

1. Источник истины — **YAML-спеки** в `spec/`.
2. Генератор читает спеки и пересобирает код в `shared/generated/`.
3. Любые изменения интерфейсов (структура данных, сигнатуры REST-ручек) вносятся **только через спеки**, а не руками в коде.
4. В CI генератор запускается, и если после его работы есть diff по `shared/generated/` — пайплайн должен падать.

## 2. Структура проекта (минимум для этой задачи)

Текущая реальная структура репозитория примерно такая:

* в корне: `docker-compose` файлы, `tests/`, разные вспомогательные скрипты;
* есть папка `shared/` для общих вещей между сервисами;
* есть папка `scripts/` для служебных скриптов.

Для этой задачи договоримся так:

```text
project_root/
  docker-compose.yml / другие compose-файлы
  tests/
  scripts/
    generate_from_spec.py    # скрипт-генератор, запускается в отдельном Docker-контейнере

  shared/
    spec/
      models.yaml            # спецификация моделей/DTO
      rest.yaml              # спецификация REST API (поверх моделей)

    shared/generated/
      __init__.py
      schemas.py             # Pydantic-модели, генерятся из shared/shared/spec/models.yaml
      routers/
        __init__.py
        rest.py              # базовый каркас REST-ручек из shared/shared/spec/rest.yaml (один файл на MVP)

  app/
    # пользовательский код конкретного сервиса/сервисов,
    # может импортировать shared.generated.schemas и shared.generated.routers

```

Ключевые моменты:

* все спеки и сгенерированный код лежат в `shared/`, так как они потенциально общие для нескольких сервисов;
* генератор живёт в `scripts/generate_from_spec.py`, откуда его можно удобно дергать из Docker-контейнеров;
* сервисы используют код из `shared/shared/generated/` через обычные импорты (например, `from shared.generated.schemas import UserPublic`).

## 3. Формат `shared/shared/spec/models.yaml`

Формат `shared/spec/models.yaml`

Назначение: описать **канонические модели/DTO**, из которых генерируются Pydantic-классы.

Минимальный формат (YAML):

```yaml
models:
  User:
    fields:
      id:
        type: uuid
        primary_key: true
        readonly: true
      email:
        type: string
        format: email
        unique: true
      name:
        type: string
      locale:
        type: string
        default: "en"
      hashed_password:
        type: string
        internal: true

    variants:
      Create:
        exclude: [id, hashed_password]
      Update:
        optional: [email, name, locale]
      Public:
        exclude: [hashed_password]
```

### 3.1. Поддерживаемые типы полей

Минимальный набор:

* `string`
* `int`
* `bool`
* `uuid`
* `datetime`
* `float`

Доп. атрибуты (опциональны):

* `format`: например, `email`.
* `default`: любое скалярное значение.
* `primary_key`: bool (используется на будущее, сейчас можно игнорировать).
* `readonly`: bool — поле только для чтения (не входит в create/update варианты по умолчанию).
* `unique`, `internal`: можно пока игнорировать в генерации, но не падать при их наличии.

### 3.2. Варианты (`variants`)

Цель: разные представления одной модели для разных use-case (create, update, public и т.п.).

Поддерживаем 2 ключа внутри варианта:

* `exclude: [field1, field2, ...]` — убрать поля из варианта.
* `optional: [field1, field2, ...]` — сделать поля опциональными.

На основе `models.yaml` надо сгенерировать:

* базовую Pydantic-модель: `class User(BaseModel): ...`
* варианты Pydantic-моделей:

  * `UserCreate`
  * `UserUpdate`
  * `UserPublic`

Правила именования вариантов (жёстко зашить):

* `<ModelName>` — базовая модель.
* `<ModelName><VariantName>` — вариант.

  * `User` + `Create` → `UserCreate`.

### 3.3. Правила построения Pydantic-моделей

Для базовой модели `<ModelName>`:

* Все поля из `fields` попадают в класс.
* Если у поля есть `default` — использовать как `Field(default=...)`.
* Если `default` нет и `readonly != true` → поле required.
* `readonly` и т.п. пока не влияют на сам класс, кроме логики вариантов.

Для варианта `<ModelName><VariantName>`:

* начинать с копии базовой модели;
* применить `exclude` → удалить поля;
* применить `optional` → сделать поля `Optional[...]` с `default=None`.

На этом этапе ORM / SQLAlchemy не трогаем, генерим только Pydantic.

## 4. Формат `shared/spec/rest.yaml`

Назначение: описать REST-эндпоинты, которые используют модели/варианты из `shared/spec/models.yaml`, а также базовые настройки роутера.

### 4.1. Структура YAML

Минимальный формат:

```yaml
rest:
  router:
    prefix: "/api"          # общий prefix для всех путей (FastAPI APIRouter(prefix=...))
    tags: ["users"]         # теги по умолчанию для всех handlers (можно опустить)
    async_handlers: true      # если true — генерируем async def, иначе def (на MVP можно всегда считать true)

  handlers:
    list_users:
      method: GET
      path: "/users"        # путь относительно router.prefix
      response:
        model: User
        variant: Public
        many: true            # если many: true — List[UserPublic], иначе просто UserPublic
        status_code: 200      # опционально, по умолчанию 200 для GET/PUT/PATCH/DELETE
        tags: ["users", "list"]  # опционально, переопределяет/расширяет router.tags

    create_user:
      method: POST
      path: "/users"
      request:
        model: User
        variant: Create
      response:
        model: User
        variant: Public
        status_code: 201
        tags: ["users", "create"]
```

Требуется поддержать:

* `router` (опционально, но желательно):

  * `prefix`: строка, которую нужно передать в `APIRouter(prefix=...)`. Если не задана — используем пустую строку.
  * `tags`: список строк, которые передаются в `APIRouter(tags=...)` и используются по умолчанию для всех handlers.
  * `async_handlers`: bool — если `true`, генерируем `async def` для всех обработчиков, если `false` — `def`. На первой итерации можно зашить `true` и игнорировать отсутствие этого флага.

* `handlers`: словарь `handler_name -> описание`.

  * `method`: один из `GET`, `POST`, `PUT`, `PATCH`, `DELETE`.
  * `path`: строка, относительная к `router.prefix`.
  * `request` (опционально):

    * `model`: имя модели из `models.yaml`.
    * `variant`: имя варианта или опустить (если нет — используется базовая модель).
  * `response` (обязательно):

    * `model`: имя модели.
    * `variant`: опционально.
    * `many`: bool (опционально). Если `true` → `List[<ResponseModel>]`, иначе одиночный объект.
    * `status_code`: int (опционально). Если не задан:

      * для `POST` по умолчанию 201,
      * для остальных методов — 200.
    * `tags`: список строк (опционально). Если указан — используется для конкретного handler’а. Если нет — берётся `router.tags` (если они есть).

### 4.2. Генерация FastAPI роутера

На базе `shared/spec/rest.yaml` нужно сгенерировать один модуль `shared/generated/routers/rest.py` с FastAPI-роутером:

```python
from typing import List

from fastapi import APIRouter

from shared.generated.schemas import UserPublic, UserCreate

router = APIRouter(prefix="/api", tags=["users"])

@router.get("/users", response_model=List[UserPublic], status_code=200, tags=["users", "list"])
async def list_users():
    # TODO: implement
    raise NotImplementedError

@router.post("/users", response_model=UserPublic, status_code=201, tags=["users", "create"])
async def create_user(payload: UserCreate):
    # TODO: implement
    raise NotImplementedError
```

Правила генерации:

* Всегда создаём один `APIRouter` с именем `router`.

  * `prefix` и `tags` берём из `rest.router`, если они заданы.
* Для каждого handler из `rest.handlers`:

  * выбираем нужный декоратор: `@router.get`, `@router.post` и т.д. по `method`.
  * параметр `path` декоратора берём из `handler.path`.
  * `response_model` строим так:

    * находим модель и вариант в `schemas.py` (`User`, `UserPublic`, `UserCreate` и т.д.).
    * если `many: true` → `List[<ResponseModel>]` + добавляем `from typing import List`.
    * если `many` не задан или `false` → одиночная модель.
  * `status_code`:

    * если указан в YAML — подставляем явно,
    * если нет — используем 201 для `POST`, 200 для остальных методов.
  * `tags`:

    * если указаны в handler → передаём их в декоратор `tags=[...]`,
    * если нет — можно не указывать в декораторе, тогда будут применяться `router.tags`.
  * сигнатура функции:

    * если `rest.router.async_handlers == true` (или флаг отсутствует, но мы на MVP решили всегда делать async) → `async def handler_name(...):`,
    * если `async_handlers == false` → `def handler_name(...):`.
  * аргументы функции:

    * если есть `request` → один параметр `payload: <RequestModel>`.
    * если `request` нет → функция без параметров (на MVP не поддерживаем path/query-параметры).
  * тело функции — всегда `raise NotImplementedError`.

На первой итерации можно не поддерживать:

* path-параметры (`/users/{id}`),
* query-параметры,
* сложные комбинации нескольких моделей в ответе.

## 5. Скрипт-генератор `scripts/generate_from_spec.py`

`scripts/generate_from_spec.py`

Задача: синхронизировать `spec/*` → `shared/generated/*`.

Поведение:

1. Читает `shared/spec/models.yaml`.
2. Генерит/перезаписывает `shared/generated/schemas.py`.
3. Читает `shared/spec/rest.yaml`.
4. Генерит/перезаписывает `shared/generated/routers/rest.py`.
5. Скрипт **идемпотентен**: повторный запуск без изменений в спеках не должен менять файлы (чтобы `git diff` был пустой).
6. При любой ошибке в спеке или невозможности сгенерировать код — падать с внятным исключением, ничего не генерить частично.

Внутренние детали генерации:

* Можно использовать любой YAML-парсер (`pyyaml` и т.п.).
* Код можно собирать через простые шаблоны (f-строки) или `jinja2` — на выбор.
* В начале сгенерированных файлов добавить комментарий:

  * `# AUTO-GENERATED FROM shared/spec/models.yaml – DO NOT EDIT MANUALLY`

## 6. Интеграция в CI

В пайплайне нужно сделать шаг:

```bash
python scripts/generate_from_spec.py
git diff --exit-code
```

Ожидаемое поведение:

* Если разработчик изменил спеки и не прогнал генератор локально → CI перегенерит файлы, `git diff` будет непустой → пайплайн упадёт.
* Если кто-то руками поправил `shared/generated/*` → генератор перетрёт, снова будет diff → пайплайн упадёт.

Это гарантирует, что в main-ветке `spec/*` и `shared/generated/*` всегда согласованы.

## 7. Ограничения и то, что делать НЕ нужно на этом этапе

1. **Не реализовывать ORM/SQLAlchemy**: сейчас фокус только на Pydantic и REST.
2. **Не описывать бизнес-валидацию** в спеках (никаких условных правил, только типы и простые атрибуты).
3. **Не моделировать события (events/Kafka)** — можно зарезервировать `spec/events.yaml` на будущее, но не реализовывать.
4. **Не делать per-service спеки**: одна общая `models.yaml`, один `rest.yaml`.
5. **Не пытаться генерировать тесты**: автогенерация тестов вне скоупа этой задачи.

## 8. Проверка результата (sanity check)

После реализации должно выполняться:

1. Я могу описать модель в `shared/spec/models.yaml`, включая несколько `variants`.
2. После запуска `python scripts/generate_from_spec.py` в `shared/generated/schemas.py` появляются Pydantic-классы `<Model>` и `<Model><Variant>`.
3. Я могу описать один или несколько REST-эндпоинтов в `shared/spec/rest.yaml`.
4. После генерации в `shared/generated/routers/rest.py` появляется FastAPI-роутер с нужными декораторами и сигнатурами.
5. Запуск `generate_from_spec.py` два раза подряд не даёт diff-а в git, если спеки не менялись.
6. В CI при изменённых спеках и не обновлённых сгенерённых файлах пайплайн падает на `git diff --exit-code`.

Этого достаточно, чтобы дальше подключать LLM-агентов, которые будут:

* редактировать `shared/spec/models.yaml` и `shared/spec/rest.yaml`,
* вызывать `generate_from_spec.py`,
* и уже работать с понятными, стабильно сгенерированными Pydantic-моделями и каркасом API.
