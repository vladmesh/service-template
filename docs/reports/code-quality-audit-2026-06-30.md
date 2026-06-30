# Аудит качества кода — service-template

**Дата:** 2026-06-30
**Охват:** вся кодовая база (`framework/`, `template/`, `tests/`, скрипты, инфраструктура). Зеркало `template/.framework/` не рассматривалось отдельно, т.к. это копия `framework/`.
**Метод:** пять параллельных глубоких ревью по срезам плюс независимая перепроверка ключевых находок чтением исходников и `grep` по всему дереву.

## Статус выполнения

Обновлено 2026-06-30. Разделы 1 (корректность) и 3 (мёртвый код) сделаны на ветке `vladmesh/audit_fixes` (PR #15). Находка 2.5 (модель→JSON-schema) сделана на ветке `vladmesh/audit-2.5-json-schema`. Находки 2.1 (один fold для dispatch по `TypeSpec`), 2.2 (`render_to_file` в `BaseGenerator`), 2.3 (типизированный контекст в шаблоны) и 2.4 (структурный `domain_key`) сделаны на ветке `vladmesh/audit-2.1-typespec-fold`. Дедупликация 2.6 (`unwrap_list`), 2.7 (`load_service_specs`) и 2.8 (единый `computed_return_type`) сделаны на ветке `vladmesh/audit-2.6-2.8-dedup`. Раздел 2 закрыт полностью. Из косметики раздела 4 сделаны быстрые механические находки 4.3, 4.4, 4.5, 4.6, 4.9 (PR #22) и 4.7 (атомарные записи файлов); 4.1, 4.2, 4.8 отложены по согласованию (требуют либо решения по дизайну, либо более широкой правки).

| Находка | Статус | Коммит |
|---|---|---|
| 1.1 OpenAPI list-ответы | ✅ сделано | `f5b2b72` |
| 1.2 Воркер: get_broker() | ✅ сделано | `239b960` |
| 1.3 MockSession | ✅ сделано (session-less адаптер) | `428356d` |
| 1.4 tz-мутация ORM | ✅ сделано (TzAwareDateTime) | `9f94c00` |
| 1.5 двойной exception-handler | ✅ сделано | `3aedd84` |
| 1.6 OpenAPI uuid-параметр | ✅ сделано | `3e89d61` |
| 2.5 модель→JSON-schema + `FieldSpec.is_required` | ✅ сделано | `f2ec7cf` |
| 2.1 один fold для dispatch по `TypeSpec` | ✅ сделано | `61329dc` |
| 2.2 `render_to_file` в `BaseGenerator` | ✅ сделано | `af9839d` |
| 2.3 типизированный контекст в шаблоны | ✅ сделано | `af9839d` |
| 2.4 структурный `domain_key` (имена/путь) | ✅ сделано | — |
| 2.6 `unwrap_list` (распаковка `list[X]`) | ✅ сделано | — |
| 2.7 `load_service_specs` (единый ридер реестра) | ✅ сделано | — |
| 2.8 единый `computed_return_type` | ✅ сделано | — |
| 3.1, 3.2, 3.4 compose-рендер + service_info | ✅ сделано | `078649c` |
| 3.3 stub_missing_methods | ✅ сделано | `090282b` |
| 3.5 raw_type | ✅ сделано | `bcea93e` |
| 3.6 async_handlers + fallback | ✅ сделано | `a47feea` |
| 4.10 покрытие test_openapi | ✅ сделано | `55dc5e6` |
| 4.3 `_validate_required_env_vars` | ✅ сделано | — |
| 4.4 `http_client` os.getenv с дефолтом | ✅ сделано | — |
| 4.5 stdlib logging → structlog | ✅ сделано | — |
| 4.6 `async_database_url` substring-эвристика | ✅ сделано | — |
| 4.9 diff в check-framework-sync.sh + routers→domains | ✅ сделано | — |
| 4.7 неатомарные записи файлов | ✅ сделано | — |
| 4.1, 4.2, 4.8 косметика | ⏭ отложено | — |

Проверка: `make test` (112), `make lint`, `make lint-template`, `make check-sync` зелёные; `make test-copier` (86) зелёный. На сгенерированных проектах прогнаны юнит-тесты backend (13) и notifications_worker (4); mypy воркера чист при `warn_unused_ignores=True`.

Уточнение к 1.3/1.4 при реализации:
- 1.3: «переиспользовать DB-модуль backend/shared» оказалось невозможно (в `shared` нет движка БД, воркер не зависит от БД). Сделан session-less вариант: `get_session` в `event_adapter.py.j2` стал опциональным, воркер вызывает `create_event_adapter` без сессии.
- 1.4: вместо правки на границе тестов использован тип-колонки `TzAwareDateTime` (no-op на Postgres, доклеивает UTC на SQLite при чтении). Это не дёргает живой ORM-инстанс и не помечает его «грязным», в отличие от conftest-хука на событие загрузки.

## Вердикт

Структурно кодовая база **не чистая**. Идея «спецификации как единственный источник правды + кодогенерация» здравая, основной поток работает, но есть три системные проблемы, которые по строгой планке должны блокировать одобрение:

1. **Баги корректности, попадающие в каждый сгенерированный проект** (неверный OpenAPI для коллекций, рассинхрон wire-формата брокера, мутация ORM в горячем пути и др.).
2. **«Канонический фасад»**: слои централизации существуют (`base.py`, `OperationContextBuilder`, конвертеры `TypeSpec`, `ModelsSpec.to_json_schema`), но потребители их обходят и переписывают ту же логику по 3–6 раз, иногда расходясь в поведении.
3. **~500 строк осиротевшего мёртвого кода**, которые тянутся через `sync-framework` и CI и держатся зелёными только собственными тестами.

Ни один файл не превышает 1000 строк, поэтому речь о структуре, а не о размере.

## Сквозной паттерн, объясняющий бóльшую часть находок

Снова и снова создаётся канонический слой, который затем не используется:

| Канонический механизм (существует) | Кто его обходит и переписывает заново |
|---|---|
| `type_spec_to_python` / `type_spec_to_json_schema` (`spec/types.py`) | `frontend/generator.py:23` добавляет 3-й рукописный dispatch по `TypeSpec`; `openapi/generator.py:20` добавляет 4-й, строковый |
| `ModelsSpec.to_json_schema()` (`spec/models.py:235`) | `OpenAPIGenerator._model_to_schema/_variant_to_schema` (`openapi:86,104`) переписывают то же с **другой, более багованной логикой `required`** |
| `BaseGenerator` (`generators/base.py`) | 4 генератора строят `Jinja Environment` инлайн и заново делают render→write→format |
| типизированный `OperationContext` (`generators/context.py:53`) | каждый генератор тут же расплющивает его обратно в нетипизированный `dict` |
| соглашение об именах `domain_key` → protocol | переописано в **5 местах `split("/")` + 5 местах `…capitalize()+ControllerProtocol`** в 4 файлах и шаблоне Jinja |
| `get_broker()` с `BinaryMessageFormatV1` (`events.py.j2`) | `notifications_worker/main.py:41` создаёт свой `RedisBroker` без формата |

Каждая строка таблицы ниже разбирается как отдельная находка.

---

## 1. Критические находки (баги в сгенерированном коде)

Эти дефекты копируются в каждый проект, созданный шаблоном, поэтому их вес выше обычного.

### 1.1 [MAJOR] OpenAPI теряет ответы-коллекции `list[...]`
**Статус:** ✅ Сделано (`f5b2b72`). Покрыто тестом в 4.10.
**Где:** `framework/openapi/generator.py:196-204`
**Проблема:** контекст уже моделирует коллекции (`OperationContext.response_many` ставится из `operation.response_many`, а `ctx.output_model` уже «развёрнут» до базовой модели в `context.py:151,155`). `_operation_to_openapi` игнорирует `ctx.response_many` и всегда отдаёт `{"$ref": ".../{output_model}"}`. Операция `output: list[UserRead]` (например `list_users` в шаблоне) даёт в OpenAPI схему одиночного `UserRead`. Контракт всех коллекционных эндпоинтов неверен.
**Проверено:** в исходнике. Тест `test_openapi` этот случай не покрывает.
**Как чинить:**
```python
response_schema = {"$ref": f"#/components/schemas/{ctx.output_model}"}
if ctx.response_many:
    response_schema = {"type": "array", "items": response_schema}
```

### 1.2 [MAJOR] Воркер уведомлений создаёт свой `RedisBroker` без `message_format`
**Статус:** ✅ Сделано (`239b960`). Воркер берёт `get_broker()`; AGENTS.md обновлён.
**Где:** `template/services/notifications_worker/src/main.py:37-41`
**Проблема:** канонический `get_broker()` (`shared/.../events.py`, шаблон `events.py.j2:22`) создаёт `RedisBroker(redis_url, message_format=BinaryMessageFormatV1)`. Воркер же делает `RedisBroker(redis_url)` без формата и сам перечитывает `REDIS_URL`. Издатели (tg_bot, backend через `get_broker()`) кодируют сообщения `BinaryMessageFormatV1`, а подписчик воркера (регистрируется на этом «голом» брокере в `event_adapter.py.j2:56`) декодирует дефолтным форматом. Как только проект реально опубликует `user_registered`, форматы на проводе разойдутся.
**Проверено:** firsthand, оба места.
**Как чинить:** убрать локальный `RedisBroker(...)` и чтение `REDIS_URL`; импортировать и передавать `get_broker()` из `shared.generated.events` в `create_event_adapter(broker=get_broker(), ...)`. Одно определение брокера, один формат, одно чтение env.

### 1.3 [MAJOR, латентный] `MockSession` как продакшн-фабрика сессий
**Статус:** ✅ Сделано (`428356d`). `get_session` в шаблоне адаптера опционален; воркер session-less. См. уточнение в «Статус выполнения».
**Где:** `template/services/notifications_worker/src/main.py:22-33`
**Проблема:** класс с буквальным именем `MockSession` и no-op `commit`/`rollback` отдаётся в сгенерированный адаптер, где хэндлер делает `await controller.handler(session, ...)` и `await session.commit()` (`event_adapter.py.j2:67-68`). Сейчас безвреден (контроллер `NotificationsController.on_user_registered` только логирует), но это мина: первый же хэндлер воркера, который запишет в БД, «успешно» ничего не сохранит.
**Проверено:** firsthand, включая то, что контроллер не пишет в БД.
**Как чинить:** определить контракт воркера. Либо дать реальную сессию на базе `AsyncSessionLocal` (переиспользовать модуль БД из backend/shared), либо генерировать вариант адаптера без сессии/коммита. Не отгружать объект `Mock*` как рантайм-сессию.

### 1.4 [MAJOR] Тестовый патч tzinfo для SQLite в горячем пути продакшна
**Статус:** ✅ Сделано (`9f94c00`). `_to_schema` сведён к `model_validate`; tz через тип-колонки `TzAwareDateTime`.
**Где:** `template/services/backend/src/controllers/users.py:39-45`
**Проблема:** `_to_schema` на каждом сериализуемом пользователе (`list/get/create/update`) выполняет ad-hoc спецслучай, существующий только потому, что тесты на SQLite. Хуже того, он **мутирует живой ORM-инстанс** (`user.created_at = user.created_at.replace(...)`) внутри открытой сессии, и «грязный» атрибут может быть записан обратно на `commit()` запроса.
**Проверено:** firsthand, вызывается из всех read-хэндлеров.
**Как чинить:** перенести заботу на границу тестов (tz-aware хранение в тестовой БД через `TypeDecorator` или connect-time настройку SQLite, либо тесты на Postgres). Тогда `_to_schema` сводится к `UserRead.model_validate(user, from_attributes=True)` без ветвления и мутации.

### 1.5 [MAJOR] Двойная обработка исключений: middleware затеняет `register_exception_handler`
**Статус:** ✅ Сделано (`3aedd84`). `register_exception_handler` удалён; оставлен middleware.
**Где:** `template/services/backend/src/app/middleware.py:60-83` и `:89-102`, связаны в `app/__init__.py:16-17`
**Проблема:** `RequestLoggingMiddleware.dispatch` оборачивает `call_next` в `try/except Exception`, логирует `"unhandled_exception"` и возвращает 500. Поскольку `BaseHTTPMiddleware` стоит снаружи Starlette-овского `ServerErrorMiddleware` (куда подключён `@app.exception_handler(Exception)`), необработанное исключение роута перехватывается **middleware первым** и до `register_exception_handler` не доходит. Оба механизма дают идентичный лог и идентичный 500. Один из двух мёртв для случая, ради которого написан.
**Проверено:** firsthand, обе регистрации присутствуют в `create_app`.
**Как чинить:** оставить один. Версия в middleware лучше (есть `duration_ms` и привязка contextvars), поэтому удалить `register_exception_handler` и его вызов.

### 1.6 [MAJOR, латентный] OpenAPI: uuid-параметр пути → битый `$ref`
**Статус:** ✅ Сделано (`3e89d61`). Маппинг примитивов теперь раньше эвристики заглавной буквы. Покрыто тестом в 4.10.
**Где:** `framework/openapi/generator.py:20-35` (используется в `:179`)
**Проблема:** `type_to_openapi_schema(type_str)` — второй, строковый конвертер схемы, принимающий уже сконвертированное Python-имя типа (`ctx.params[].type` прошёл `type_spec_to_python`). Эвристика «модель, если первая буква заглавная» (`type_str[0].isupper()`, строка 23) срабатывает **раньше** маппинга на строке 33: для uuid `type` = `"UUID"` → возвращается `{"$ref": "#/components/schemas/UUID"}` (висячий ref на несуществующую схему), а запись `"UUID"` в маппинге — мёртвая. В дефолтном шаблоне латентно (все path-параметры `int`), но реальный баг для любого uuid-параметра пути. Плюс неизвестные типы тихо проваливаются в `{"type": "string"}`.
**Как чинить:** см. 2.3 — передавать в схему параметра исходный примитив через канонический `type_spec_to_json_schema(parse_type_spec(...))`, удалить `type_to_openapi_schema` и эвристику с заглавной буквой.

---

## 2. Дублирование и «канонический фасад»

**Статус раздела:** закрыт. 2.5 (`f2ec7cf`), 2.1 (`61329dc`), 2.2, 2.3 (`af9839d`), 2.4, а также дедупликация 2.6–2.8 — все сделаны.

### 2.1 [MAJOR] Тройной (и четвёртый) dispatch по `TypeSpec`
**Статус:** ✅ Сделано (`61329dc`). Введён `fold_type_spec(spec, renderer)` с протоколом `TypeRenderer` из 5 листовых хуков — единственный обход union. `type_spec_to_python/_json_schema/_typescript` схлопнуты в тонкие обёртки над рендерерами. TS-конвертер перенесён в `types.py` (реэкспортится из `frontend/generator`), обработка ошибки выровнена на `raise`. Для валидных спеков вывод байт-в-байт прежний (seed `backend/docs/openapi.json` регенерируется без изменений); единственное поведенческое отличие — `raise` на не-`TypeSpec` объекте вместо возврата `"unknown"`. Покрыто тестами в `tests/unit/test_spec_types.py`.
**Где:** `spec/types.py:105` (`type_spec_to_python`), `spec/types.py:140` (`type_spec_to_json_schema`), `frontend/generator.py:23` (`type_spec_to_typescript`), плюс строковый `openapi/generator.py:20`
**Проблема:** три функции вручную «разбирают» закрытый union из 5 вариантов идентичной цепочкой `isinstance` с идентичной структурной рекурсией; различается только рендер листа. Добавление 6-го варианта требует правок в трёх местах в двух файлах, и ничто это не форсит. `type_spec_to_typescript` ещё и осиротел в генераторе вместо `types.py` и на неизвестном варианте возвращает `"unknown"` (две сестринские функции — `raise`).
**Как чинить (judo):** вынести структурную рекурсию один раз. Либо маленький протокол-рендерер с 5 хуками-листьями и единым `render(spec, renderer)`, владеющим обходом; тогда `to_python/to_json_schema/to_typescript` схлопываются в ~6 строк без рекурсии и dispatch. Перенести TS-конвертер в `types.py`, выровнять обработку ошибки на `raise`.

### 2.2 [MAJOR] `base.py` — тонкая обёртка; Jinja-бойлерплейт продублирован 4×
**Статус:** ✅ Сделано (`af9839d`). В `BaseGenerator` добавлены кешируемое свойство `env` и метод `render_to_file(template_name, output_file, *, add_header=True, **ctx)`. Все 4 генератора сведены на него, инлайн-`Environment(` остался только в `base.py`. Вывод байт-в-байт прежний (регенерация seed'ов старым vs новым кодом даёт идентичное дерево).
**Где:** `generators/base.py:18-53` против `controllers.py:77-85`, `protocols.py:72-90`, `events.py:47-56`, `event_adapter.py:84-109`
**Проблема:** `BaseGenerator` владеет только `write_file` + `format_file`. Сам поток (`Environment(FileSystemLoader(...), trim_blocks=True, lstrip_blocks=True, autoescape=False)` → `get_template` → `render` → `write_file` → `format_file`) переписан байт-в-байт в четырёх генераторах, вместе с повторяющимся `# noqa: S701`. Подтверждено `grep`: 4 инлайн-конструкции `Environment(`.
**Как чинить:** добавить в базу кешируемое свойство `self.env` и метод `render_to_file(template_name, output_file, *, add_header=True, **ctx)`. Хвост каждого генератора сводится к одному вызову.

### 2.3 [MAJOR] Типизированный `OperationContext` строится и выбрасывается в ad-hoc dict-ы
**Статус:** ✅ Сделано (`af9839d`). Три блока `handler_ctx = {...}` удалены; `OperationContext`/`ParamContext` передаются в шаблоны напрямую. Шаблоны читают атрибуты контекста (`input_model`, `computed_return_type`/`return_type`, `publish_channel`, …). Расхождение `return_type` (protocol) vs `computed_return_type` (controller) оставлено как есть — это 2.8, отложено.
**Где:** `context.py:53-107` против `controllers.py:56-62`, `protocols.py:45-55`, `event_adapter.py:61-68`
**Проблема:** `OperationContextBuilder` выдаёт типизированный объект, а каждый генератор тут же переупаковывает его в нетипизированный `handler_ctx` для Jinja, вручную переотбирая поля. Строка `"params": [{"name": p.name, "type": p.type} for p in ctx.params]` идентична в `controllers.py:58` и `protocols.py:47`. Дублирование, которое контекст должен был убрать, просто переехало на слой выше. Типизированный контракт умирает на границе шаблона.
**Как чинить:** Jinja прекрасно читает атрибуты — передавать `OperationContext`/`ParamContext` прямо в шаблон, удалив все три блока `handler_ctx = {...}`. Парой идёт 2.4.

### 2.4 [MAJOR] Деривация имён `domain_key`/protocol-name дублирована по 4 файлам
**Статус:** ✅ Сделано. Ключ стал структурным: `DomainSpec` получил поле `service_name` (ставит loader, как `ServiceManifest.service`) и свойства `protocol_name`/`controller_class_name` — единственный владелец конвенции имён. Все 5 `domain_key.split("/")` и 5 ручных `…capitalize()+ControllerProtocol` (включая `controller.py.j2` и линтер) сведены к `domain.service_name`/`domain.name`/`domain.protocol_name`. Путь к файлу контроллера (общий у генератора и линтера — реальная пара риска рассинхрона) вынесен в хелпер `controller_path(repo_root, domain)` в `context.py`. Уточнение к рецепту: имена живут свойствами на `DomainSpec`, а не свободными функциями `protocol_name_for(...)` — единый владелец = сама модель; `module_name` отдельной обёрткой не вводился, т.к. `DomainSpec.name` уже и есть имя модуля. Вывод генераторов байт-в-байт прежний (регенерация old vs new даёт идентичное дерево, включая контроллеры).
**Где:** `lint/controller_sync.py:75,80`, `generators/controllers.py:28,70`, `generators/protocols.py:32,39`, `generators/event_adapter.py:38,51`, плюс шаблон `controller.py.j2:21`
**Проблема:** подтверждено `grep`: `service_name, … = domain_key.split("/")` в **5 местах**; `f"{module_name.capitalize()}ControllerProtocol"` в **5 местах** (включая Jinja-шаблон и линтер). `DomainSpec` не несёт ни имени сервиса, ни имени протокола, поэтому каждый потребитель парсит составной ключ заново. Линтер `controller_sync` независимо переписывает то же соглашение — конкретный риск рассинхрона.
**Как чинить:** сделать ключ структурным. Свойства `DomainSpec.service_name` / `.module_name` и хелперы `protocol_name_for(module)` / `controller_path(...)` в `generators/context.py`. Все 5+ мест сводятся к одному вызову.

### 2.5 [MAJOR] Модель→JSON-schema продублирована и расходится по `required`
**Статус:** ✅ Сделано (`f2ec7cf`). Удалены `_model_to_schema`/`_variant_to_schema` в OpenAPI; `_generate_schemas` возвращает канонические `definitions`. Введён `FieldSpec.is_required`, через него идут и построение модель-схемы, и TS-генератор. Seed `backend/docs/openapi.json` регенерирован отдельным коммитом (`4bbb5de`). Покрыто тестом в 4.10.
**Где:** `openapi/generator.py:68-122` против `spec/models.py:235-290`
**Проблема:** обе итерируют модели+варианты, зовут `field_spec.to_json_schema()` и строят `{type, title, properties, required, additionalProperties:False}`. OpenAPI-копия выводит `required` **неверно**: `_model_to_schema:93` использует `field_spec.default is None and not field_name.startswith("_")` (игнорирует `optional: true`, тащит ad-hoc спецслучай с подчёркиванием), а `_variant_to_schema:113` проверяет только `default is None` (полностью игнорирует variant-level `optional`). Две OpenAPI-функции даже между собой несогласованы. Канонический `ModelsSpec.to_json_schema()` делает это правильно; внутри схем нет `$ref`, так что разница `definitions` vs `components/schemas` неважна.
**Как чинить:** удалить все три метода; в `_generate_schemas` вернуть `self.specs.models.to_json_schema()["definitions"]` (опционально добавить методу `ModelsSpec` возврат «голого» словаря определений).

Связанная находка: **«обязательность поля» выводится 4 разными способами** — `models.py:276`, `openapi:93`, `openapi:113`, `frontend/generator.py:110`. Канонический ответ — свойство `FieldSpec.is_required`, используемое везде.

### 2.6 [MINOR] Распаковка `list[X]`/`List[X]` в 6 местах / 3 файлах
**Статус:** ✅ Сделано. Введён `unwrap_list(ref) -> tuple[bool, str]` в `spec/operations.py` — единый владелец соглашения «ссылка на список моделей». `OperationSpec.response_many`/`base_output_model` и `loader.extract_base_model` сведены к нему. Шорткат-парсер `list[...]`/`dict[...]` в `parse_type_spec` (`types.py`) не трогался: это отдельная грамматика типов (рекурсия + dict), а не ссылка на модель; `unwrap_list` там не применим без расширения принимаемого синтаксиса.
**Где:** `operations.py:120,127,129`, `loader.py:131,133`, `types.py:188` (подтверждено `grep`)
**Проблема:** один и тот же протокол `startswith("list[")/("List[")` + срез `[5:-1]` переописан в `extract_base_model`, `base_output_model` и наполовину в `response_many`. У соглашения «ссылка на список моделей» нет единого владельца.
**Как чинить:** один хелпер `unwrap_list(ref) -> tuple[bool, str]`; три места схлопываются.

### 2.7 [MINOR] Загрузка реестра `services.yml` переписана 3–4 раза
**Статус:** ✅ Сделано. Две из трёх копий-ридеров (`compose_blocks.load_registry`, `service_info`) уже удалены в 3.1. Оставшийся `build_service_specs(registry: dict)` был мёртв (ноль вызовов, даже в тестах) и брал уже загруженный dict. Заменён каноническим `load_service_specs(path) -> list[ServiceSpec]` в `lib/service_scaffold.py`, читающим файл через `loader.load_yaml_file`; конвертация dict→`ServiceSpec` ушла в приватный `_specs_from_registry`. Теперь единственные ридеры `services.yml` — канонический `load_yaml_file` и existence-проверки в `lib/env.py` (не загрузка). Добавлен тест `test_load_service_specs_reads_registry`.
**Где:** `compose_blocks.py:207` (`load_registry`), `service_info.py:25-41`, `service_scaffold.py:60-90` (`build_service_specs`), против `spec/loader.py:45` (`load_yaml_file`)
**Проблема:** загрузка `services.yml` и обход `registry["services"]` с `isinstance`-гардами существуют в трёх копиях, возвращающих `dict[str, Any]`, плюс четвёртый YAML-загрузчик в spec-слое. `service_info` даже импортирует типизированный `build_service_specs`, но в `gather_tests` снова ходит по сырым dict-ам через `iter_services` — два несогласованных пути по одному файлу в одном модуле. `Any` течёт везде из-за отсутствия типизированной модели реестра.
**Как чинить:** один канонический `load_service_specs(path) -> list[ServiceSpec]`, переиспользующий `loader.load_yaml_file`. (Частично растворяется удалением мёртвого кода из раздела 3.)

### 2.8 [MINOR] `return_type` против `computed_return_type`: риск рассинхрона protocol/controller
**Статус:** ✅ Сделано. `protocols.py.j2` теперь рендерит `computed_return_type` (как и `controller.py.j2` и линтер `controller_sync`). Осиротевшие `OperationContext.return_type` (поле + присваивание) и `OperationSpec.return_type` (свойство) удалены. Для валидных спеков шаблона вывод байт-в-байт прежний (регенерация seed `backend/.../generated/protocols.py` даёт идентичный файл), т.к. при написании `list[Model]` оба свойства совпадают; расхождение возникало бы только на `List[Model]` (capital L), который теперь сводится к `list[Model]` в обоих местах.
**Где:** `protocols.py:50` (`ctx.return_type`) против `controllers.py:61` (`ctx.computed_return_type`)
**Проблема:** сигнатура протокола и сигнатура его реализации должны совпадать точно, но протокол рендерит сырой `return_type`, а контроллер — пересобранный `computed_return_type`. Сегодня совпадают; при ином написании `list[...]` в спеке разойдутся молча.
**Как чинить:** оставить одно свойство (`computed_return_type`), читать его и там, и там.

---

## 3. Мёртвый код (главный judo-ход: удаление)

### 3.1 [BLOCKER] Подсистема рендера compose-блоков + весь `service_info.py` осиротели
**Статус:** ✅ Сделано (`078649c`). Оба модуля удалены целиком; `compose_blocks.py` тоже (после удаления `service_info` потребителей не осталось).
**Где:** `framework/lib/compose_blocks.py` (≈250 из 332 строк) + `framework/service_info.py` (весь файл, 168 строк)
**Проблема:** прослежены все потребители. `render_service_templates`, `build_service_block`, `replace_block`, `indent_template`, `COMPOSE_TARGETS`, маркеры `START_MARKER/END_MARKER`, `_apply_placeholders`, `_unit_test_target`, `_cov_source`, блоки `dev`/`tests_unit` в `DEFAULT_TEMPLATES` — **ноль вызывающих** в `framework/`, `scripts/`, `Makefile`, `copier.yml`, сгенерированном `template/`, CI и git-хуках. `service_info` — единственное, что трогает `compose_blocks.compose_template_for_spec`, и сам `service_info` импортируется только тестами и `tests/tooling/conftest.py` (reload-бухгалтерия). Генерируемый `Makefile.jinja` гонит `log`/`tests` через `docker compose` и глоб `services/*/tests/` напрямую (строки 84, 119), не дёргая `service_info`. Это легаси-дизайн «регенерировать compose из `services.yml`», полностью вытесненный статическими Copier-шаблонами `template/infra/compose.*.yml.jinja`.

**Уточнение к первичному ревью:** маркер-файл всё же существует, `infra/compose.framework.yml:2` содержит `# >>> services (auto-generated from services.yml)`. Но ни одна функция его не перегенерирует, т.е. файл статический, а машинерия под него мёртвая.

**Как чинить:** удалить `service_info.py` и его тесты; удалить рендер-машинерию в `compose_blocks.py` (`DEFAULT_TEMPLATES`-строки, `COMPOSE_TARGETS`, маркеры, `render_service_templates`, `build_service_block`, `indent_template`, `replace_block`, `_apply_placeholders`, `_unit_test_target`, `_cov_source`, `_render_depends_on`, `load_registry`). Единственный реально извлекаемый факт (`gather_logs` → «контейнер этого типа логируемый?») это `service_type != "default"`, при нужде однострочный предикат. Это доминирующий ход: убирает ~400 строк и весь хотспот «YAML строками» разом.

### 3.2 [MAJOR] Строковая хирургия YAML в `_apply_placeholders`
**Статус:** ✅ Растворилось вместе с удалением `compose_blocks.py` (`078649c`).
**Где:** `compose_blocks.py:248-287`
**Проблема:** compose-записи строятся `str.replace` токенов `__SLUG__`, затем `depends_on` вставляется поиском строки `startswith("ports:")` и склейкой срезов списка, а `profiles` — `lines.insert(1, ...)`. Классический хотспот «должны быть данные, а не строки»: позиционная хирургия молча ломается, если в шаблоне нет `ports:` или есть комментарии.
**Как чинить:** растворяется при удалении по 3.1. Если что-то возродится — строить `dict` на сервис и один `yaml.dump`, а не token-replace + склейку строк.

### 3.3 [MAJOR] `stub_missing_methods` — мёртвая вторая реализация генерации стабов
**Статус:** ✅ Сделано (`090282b`). Функция и её экспорт из `lint/__init__.py` удалены.
**Где:** `framework/lint/controller_sync.py:114-160`
**Проблема:** экспортируется из `lint/__init__.py`, но не вызывается ничем (ни CLI, ни генератором, ни тестом). Руками строит исходник стабов f-строками и дописывает в файл после подстрокового поиска `class ... Controller`. Живой путь стабинга — `ControllersGenerator` через шаблон `controller.py.j2` + `OperationContextBuilder`. Это параллельный, менее качественный кодоген.
**Как чинить:** удалить `stub_missing_methods` и его экспорт.

### 3.4 [MINOR] `_render_depends_on` мёртв и дублирует инлайн-логику
**Статус:** ✅ Растворилось вместе с удалением `compose_blocks.py` (`078649c`).
**Где:** `compose_blocks.py:237-245` (подтверждено `grep`: не вызывается; то же рендерится инлайн в `_apply_placeholders:264-277`). Растворяется в 3.1.

### 3.5 [MINOR] Мёртвое поле `raw_type` + no-op if/else
**Статус:** ✅ Сделано (`bcea93e`). Поле удалено, ветка схлопнута.
**Где:** `spec/models.py:30` (декларация), `:65-71` (ветка), присваивания `:56,76`
**Проблема:** (а) if/else `66-71` имеет идентичные тела в обеих ветках, решение ничего не выбирает; (б) `raw_type` помечен `exclude=True` «для реконструкции», но подтверждено `grep`: только пишется (4 места), нигде не читается. Чистое write-only мёртвое состояние.
**Как чинить:** удалить поле и схлопнуть ветку до `type_spec = parse_type_spec(type_data)`.

### 3.6 [MINOR] Мёртвый флаг `async_handlers`
**Статус:** ✅ Сделано (`a47feea`). Флаг убран из обоих генераторов; недостижимый `or "dict"` тоже.
**Где:** `controllers.py:74`, `protocols.py:89` — передаётся в оба шаблона, но ни `controller.py.j2`, ни `protocols.py.j2` его не используют (хардкод `async def`). Удалить. Заодно недостижимый fallback `ctx.input_model or "dict"` в `event_adapter.py:66` (инвариант `validate_events_models` уже гарантирует `input_model`).

---

## 4. Средние и мелкие находки

### 4.1 [MINOR] `nullable: true` это словарь OpenAPI 3.0, а вывод объявлен 3.1.0
**Где:** `spec/types.py:162-165` (ветка Optional) и `spec/models.py:109-110`; всплывает под `openapi/generator.py:55` (`"openapi": "3.1.0"`)
**Проблема:** `nullable` убран в JSON Schema 2020-12 / OpenAPI 3.1, где ожидается `anyOf`/`{"type": [..., "null"]}`. Валидаторы 3.1 сочтут `nullable` неизвестным ключом без эффекта.
**Как чинить:** в каноническом `type_spec_to_json_schema` (ветка Optional) эмитить 3.1-стиль; обе точки потребления чинятся разом, т.к. идут через канонический конвертер.

### 4.2 [MINOR] Frontend генерирует enum-декларации, которые никто не использует
**Где:** `frontend/generator.py:78-83,100-103` против `:49-52`
**Проблема:** `_generate_enum` эмитит `export enum ...`, но для enum-поля `type_spec_to_typescript` возвращает инлайн-union `"a" | "b"`. Интерфейсы на сгенерированные enum-ы не ссылаются — блок enum это мёртвый вывод.
**Как чинить:** выбрать одно: либо ссылаться на именованный enum из свойства интерфейса, либо убрать `_generate_enum` и оставить инлайн-union.

### 4.3 [MINOR] `Settings._validate_required_env_vars` дублирует валидацию pydantic
**Статус:** ✅ Сделано (PR #22). Метод и вызов удалены.
**Где:** `template/services/backend/src/core/settings.py:22-43`, вызов `:118`
**Проблема:** 8 перечисленных переменных уже объявлены как обязательные поля; `Settings()` на строке 117 кинет `ValidationError` до строки 118. Ручной цикл ценен только для пустых строк и требует ручной синхронизации со списком полей (риск дрейфа). Не нарушение «без дефолтов env» (корректно падает), но избыточный слой.
**Как чинить:** удалить метод и вызов; при желании дружелюбного сообщения выводить недостающие из `model_fields`/`model_validator`.

### 4.4 [MINOR] `http_client` использует `os.getenv` с дефолтом
**Статус:** ✅ Сделано (PR #22). `os.getenv(base_url_env) or ""`, `raise` ниже не тронут.
**Где:** `template/shared/shared/http_client.py:41` — `os.getenv(base_url_env, "")`
**Проблема:** по духу правила корректно (пустая строка тут же триггерит `raise`), но буквально это форма `os.getenv(VAR, "default")`, которую правило запрещает, и так читается на ревью и grep-линте.
**Как чинить:** `os.getenv(base_url_env)` без дефолта, далее тот же `if not ...: raise`.

### 4.5 [MINOR] Контроллер уведомлений использует stdlib `logging` вместо structlog
**Статус:** ✅ Сделано (PR #22). `structlog.stdlib.get_logger()` + структурированные kwargs. Смок-тест переведён с `caplog` на `structlog.testing.capture_logs()` (structlog не идёт через stdlib logging без явной `configure_logging()`, которую этот тест не вызывает).
**Где:** `template/services/notifications_worker/src/controllers/notifications.py:3,9` — рендерится (общий корневой хендлер маршрутизирует stdlib через structlog), но теряет структурированные kwargs/contextvars, принятые везде. Привести к `structlog.stdlib.get_logger()`.

### 4.6 [MINOR] `async_database_url` нюхает подстроку `+async`
**Статус:** ✅ Сделано (PR #22). Эвристика удалена, остался только явный `async_database_url_override`.
**Где:** `settings.py:91` — `if ... and "+async" in self.database_url_override:`. Хрупкая эвристика; опереться на уже существующее явное поле `async_database_url_override`.

### 4.7 [MINOR] Неатомарные записи файлов
**Статус:** ✅ Сделано. Добавлен `framework/lib/fs.py::atomic_write_text` (temp-file в той же директории + `os.replace`, с очисткой temp-файла в `except`). `BaseGenerator.write_file`, `generate_openapi` и `generate_typescript` переведены на него. В `SchemasGenerator.generate` codegen теперь пишет в scratch-файл (`tempfile.mkstemp` рядом с целевым путём), regex-чистка идёт в памяти над прочитанным scratch-содержимым, и в целевой путь идёт один вызов `write_file` (уже атомарный) — было «codegen → regex-чистка поверх финального файла → перезапись». Проверено побайтово: `generate_openapi`/`generate_typescript` дают идентичный seed; для `schemas.py` regen старым и новым кодом в одном окружении даёт идентичный вывод (расхождение с закоммиченным seed — независимый от этой правки env-дрейф `datamodel-code-generator`, тот же, что и в обновлении 2.6–2.8). Проверка: `make test` (122), `make lint`, `make lint-template`, `make check-sync`, `make test-copier` (86) зелёные.
**Было:** `generators/base.py:36-41` (`write_text`), `schemas.py:33-56` (три последовательные записи в один путь: codegen → regex-чистка → запись), `openapi/generator.py:228-231`, `frontend/generator.py:136-138`. Прерывание оставляет усечённый артефакт в read-only зоне.

### 4.8 [MINOR] Два рукописных AST-walker'а с расходящимся swallow
**Где:** `enforce_spec_compliance.py:36-75` (`except SyntaxError: return set()`) и `lint/controller_sync.py:40-60` (`except Exception: print(...); return []`). Общий хелпер `parse_python(path) -> ast.Module | None` унифицировал бы. Плюс `is_violation(node, content, ...)` не использует параметр `content`. Низкий приоритет.

### 4.9 [MINOR] `check-framework-sync.sh` прячет diff; naming-дрейф
**Статус:** ✅ Сделано (PR #22). Скрипт печатает реальный diff при рассинхроне; `routers` → `domains` в генераторе, шаблоне и docstring `context.py`. Регенерация seed `backend/.../generated/protocols.py` даёт идентичный файл (переименование не меняет вывод).
- `scripts/check-framework-sync.sh:15-21`: `diff -r ... > /dev/null` сообщает о рассинхроне, но не показывает что именно отличается. Преамбула путей продублирована в обоих скриптах.
- `protocols.py:86`: `routers=domains_context  # Template expects 'routers' key` и `protocols.py.j2:25` `{% for router in routers %}` — генератора `routers` в пайплайне нет. Переименовать в `domains`, убрать комментарий-обходку, поправить docstring `context.py:3-4`.

### 4.10 [MINOR] Неглубокие тесты пропускают баги
**Статус:** ✅ Сделано. `55dc5e6` добавил кейсы на list-ответы, uuid/int-параметры, форму `required` без дефолтов; `f2ec7cf` — корректность `required` для field/variant-optional и дефолтных полей (вместе с 2.5).
**Где:** `tests/tooling/test_openapi.py` ассертит только версию OpenAPI, наличие одного пути и одного имени схемы. Не проверяет `list[...]`-ответы, корректность `required`, типы параметров, схемы вариантов. Именно поэтому баги 1.1, 1.6 и расхождение `required` (2.5) проходят. Расширить покрытие на эти случаи.

---

## 5. Что реально чисто (трогать не нужно)

- `framework/spec/loader.py` — канонический валидированный загрузчик, чёткие ошибки, одна ответственность. Граница валидации «модельные проверки на моделях, кросс-спек проверки в загрузчике» правильная, не дублирование.
- `framework/generators/context.py` (`OperationContextBuilder`) — настоящий канонический слой и реально переиспользуется (проблема только в расплющивании на выходе, 2.3). `_PARAM_TYPE_IMPORTS`/`_PYTHON_TO_SPEC` — чистый единый источник.
- `core/logging.py` — корректный тонкий адаптер над `shared/logging.py` (инъекция `service_name`/level из настроек), а не дубль.
- `get_async_db` (`core/db.py:43-58`) — образцовый: commit на успехе, rollback с ре-raise на исключении, close в `finally`.
- Lazy broker в сгенерированном `events.py` и в backend `lifespan` — корректно (`get_broker()`, модульный `_broker = None`).
- `ServiceClient` (retry 5xx/`ConnectError`, fail-fast на 4xx, экспоненциальный backoff) — переиспользуется через наследование (`BackendClient`), не хардкодится.
- `user` repository/controller — не пустые pass-through: репозиторий переиспользует `get_by_telegram_id` для проверок уникальности, контроллер держит реальную логику (404/409/400).
- Bash-скрипты тонкие (`rsync --delete`, `diff -r`), не дублируют Python-логику. Граница правильная.
- `ScaffoldReport` + `scaffold_service` — типизированы, поддерживают dry-run (`apply`).

---

## 6. Приоритизированный план

Шаги 1–5 (разделы 1 и 3) выполнены, см. «Статус выполнения». Шаги 6–10 (раздел 2) и косметика отложены.

**Сначала корректность (попадает в каждый проект):** ✅ выполнено
1. OpenAPI: учитывать `response_many` для коллекций (1.1).
2. Воркер: брать `get_broker()` вместо своего `RedisBroker` (1.2), убрать `MockSession` (1.3).
3. Backend: убрать tz-мутацию ORM из `_to_schema` (1.4); удалить дублирующий exception-handler (1.5).
4. Расширить `test_openapi` на list-ответы/required/типы параметров (4.10), чтобы зафиксировать регрессии.

**Затем главный judo-ход (удаление):** ✅ выполнено
5. Снести подсистему рендера compose + `service_info.py` (~400 строк, 3.1–3.4), затем `raw_type` и `async_handlers` (3.5, 3.6), `stub_missing_methods` (3.3).

**Затем централизация (схлопнуть фасад):**
6. ✅ Один fold для dispatch по `TypeSpec` (2.1) и перенос TS-конвертера в `types.py` — сделано (`61329dc`).
7. ✅ `render_to_file` в `BaseGenerator` (2.2); `OperationContext` в шаблоны напрямую (2.3) — сделано (`af9839d`).
8. ✅ Структурный `domain_key`: `DomainSpec.service_name` + свойства `protocol_name`/`controller_class_name` + хелпер `controller_path` (2.4) — сделано.
9. ✅ OpenAPI переиспользует `ModelsSpec.to_json_schema`; `FieldSpec.is_required` как единый источник «обязательности» (2.5) — сделано (`f2ec7cf`).
10. ✅ `unwrap_list` (2.6), единый `load_service_specs` (2.7), единый `computed_return_type` (2.8) — сделано.

**Косметика по остаточному принципу:** ✅ частично (4.3, 4.4, 4.5, 4.6, 4.7, 4.9). Осталось 4.1, 4.2, 4.8.

## Планка одобрения

Не одобрено. Блокеры: баги корректности раздела 1 (отгружаются в каждый проект), ~500 строк мёртвого кода (3.1), и систематический «канонический фасад», сохраняющий побочную сложность там, где виден ход на её удаление.

**Обновление (ветка `vladmesh/audit_fixes`):** два из трёх блокеров сняты. Баги корректности раздела 1 исправлены и покрыты тестами; мёртвый код раздела 3 удалён. Оставшийся блокер — «канонический фасад» раздела 2, отложен до отдельного захода.

**Обновление (раздел 2 закрыт):** снят и третий блокер. «Канонический фасад» разобран полностью (2.1–2.8): dispatch по `TypeSpec`, Jinja-бойлерплейт, типизированный контекст, деривация имён `domain_key`, модель→JSON-schema, распаковка `list[X]`, ридер `services.yml` и `return_type` сведены к единым владельцам. Остаётся только косметика 4.1–4.9 (MINOR).

**Обновление (2.5):** начат разбор «канонического фасада». 2.5 (модель→JSON-schema через канонический `ModelsSpec.to_json_schema`, единый `FieldSpec.is_required`) сделана. Остаток раздела 2 (2.1–2.4, 2.6–2.8) отложен.

**Обновление (2.1):** разбор фасада продолжен. 2.1 (один `fold_type_spec` для dispatch по `TypeSpec`, перенос TS-конвертера в `types.py`) сделана (`61329dc`). Остаток раздела 2 (2.2–2.4, 2.6–2.8) отложен.

**Обновление (2.2 + 2.3):** разбор фасада продолжен. 2.2 (`render_to_file` + кешируемый `env` в `BaseGenerator`, схлопывание 4 инлайн-`Environment`) и 2.3 (передача типизированного `OperationContext`/`ParamContext` в шаблоны вместо ad-hoc `handler_ctx`) сделаны (`af9839d`). Вывод генераторов байт-в-байт прежний. Остаток раздела 2 (2.4, 2.6–2.8) отложен.

**Обновление (2.4):** разбор фасада продолжен. 2.4 (структурный `domain_key`: поле `DomainSpec.service_name` + свойства `protocol_name`/`controller_class_name`, хелпер `controller_path`; все 5+ мест ручной деривации сведены к одному владельцу) сделана. Вывод генераторов байт-в-байт прежний. Остаток раздела 2 — только MINOR-дедупликация 2.6–2.8.

**Обновление (2.6–2.8):** раздел 2 закрыт. 2.6 (`unwrap_list` — единый владелец распаковки `list[X]`), 2.7 (канонический `load_service_specs` через `loader.load_yaml_file`; мёртвый `build_service_specs` удалён) и 2.8 (единый `computed_return_type` в протокол-шаблоне; осиротевшие `OperationContext.return_type`/`OperationSpec.return_type` удалены) сделаны на ветке `vladmesh/audit-2.6-2.8-dedup`. Вывод генераторов байт-в-байт прежний (регенерация seed'ов old vs new даёт идентичное дерево, кроме не относящегося к правкам env-дрейфа `datamodel-code-generator` в `schemas.py`). Проверка: `make test` (122), `make lint`, `make lint-template`, `make check-sync` зелёные; `make test-copier` (86) зелёный. Остаётся только косметика 4.1–4.9.

**Обновление (косметика 4.3, 4.4, 4.5, 4.6, 4.9):** на ветке `vladmesh/audit-4-cosmetics` (PR #22) разобраны быстрые, механические находки раздела 4: удалена дублирующая ручная валидация env-переменных и хрупкая substring-эвристика в `settings.py` (4.3, 4.6), `http_client` больше не использует `os.getenv` с дефолтом (4.4), контроллер уведомлений переведён на `structlog` (4.5, со смок-тестом на `capture_logs()` вместо `caplog`), `check-framework-sync.sh` печатает diff при рассинхроне, а `routers` в генераторе/шаблоне протоколов переименован в `domains` (4.9). Регенерация seed `protocols.py` byte-identical. Проверка: `make test` (122), `make lint`, `make lint-template`, `make check-sync`, `make test-copier` (86) зелёные; сгенерированный проект (backend+notifications) — реальные unit-тесты backend и notifications_worker в отдельном venv (17) зелёные. Остаются 4.1, 4.2, 4.8 — требуют либо решения по дизайну (4.2), либо более широкой правки с обновлением тестов (4.1), либо многофайлового рефакторинга (4.8).

**Обновление (4.7):** разобрана находка про неатомарные записи файлов. Введён `framework/lib/fs.py::atomic_write_text` (temp-file + `os.replace`); на него переведены `BaseGenerator.write_file`, `generate_openapi`, `generate_typescript`. `SchemasGenerator.generate` теперь гонит datamodel-codegen через scratch-файл и делает regex-чистку в памяти до единственной записи в целевой путь — вместо «codegen-запись → regex поверх финального файла → перезапись». Регенерация seed'ов `openapi.json`/`types.ts` byte-identical; для `schemas.py` побайтовое сравнение вывода старого и нового кода в одном окружении тоже совпадает (расхождение с закоммиченным seed — независимый env-дрейф `datamodel-code-generator`, не связанный с этой правкой). Проверка: `make test` (122), `make lint`, `make lint-template`, `make check-sync`, `make test-copier` (86) зелёные.
