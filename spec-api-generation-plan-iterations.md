# План итеративной реализации spec-first генерации API

## Итерация 1 — Подготовка структуры и очистка
- **Цель.** Освободить `shared/` от легаси и подготовить директории/пакеты, куда генератор будет складывать спецификации и результат.
- **Шаги.**
  - Удалить текущие подпапки `shared/contracts/**`.
  - Создать `shared/spec/` и `shared/generated/routers/`, добавить `__init__.py`, чтобы `shared.generated` можно было импортировать из сервисов.
  - Обновить `.gitignore`, если понадобится исключить временные файлы генератора.
- **Валидация.** `python -m compileall shared` (через tooling контейнер) проходит; существующие сервисы не падают на `import shared.generated`.

## Итерация 2 — Перенос текущих схем и REST в YAML
- **Цель.** Задать спецификации, эквивалентные существующим Pydantic-схемам и user-роутеру, чтобы генерация могла воспроизвести их.
- **Шаги.**
  - Проанализировать `services/backend/src/app/schemas/user.py` и `services/backend/src/app/api/v1/users.py`.
  - Сформировать `shared/spec/models.yaml` с описанием модели `User` (поля: `id`, `telegram_id`, `is_admin`, `created_at`, `updated_at`) и вариантов `Base`, `Create`, `Update`, `Read/Public` с теми же required/optional/default правилами. Поле `readonly` временно не используем.
  - Создать `shared/spec/rest.yaml`, описав router.prefix `/users` (или `/api` + относительные пути, чтобы совпало с текущими ручками), router.tags `["users"]`, async по умолчанию, и handlers `create_user`, `get_user`, `update_user`, `delete_user` с нужными методами, путями, статусами, множественностью (`many` только для list если появится в будущем).
- **Валидация.** YAML проходит `yamllint` (или `python - <<'PY' import yaml`) и содержит всю информацию, которая была закодирована в исходных Python-схемах/маршрутах.

## Итерация 3 — Реализация `scripts/generate_from_spec.py`
- **Цель.** Написать идемпотентный генератор для схем и роутеров.
- **Шаги.**
  - Выбрать YAML-парсер (PyYAML присутствует в зависимостях backend). Реализовать загрузку `shared/spec/models.yaml` и `shared/spec/rest.yaml` с валидацией структуры.
  - Добавить маппинг типов (`string`, `int`, `bool`, `uuid`, `datetime`, `float`) на Python типы/Pydantic поля, учитывать `default`, `optional`, `exclude`. Поскольку `readonly` пока не поддерживается, просто игнорировать, но не падать.
  - Генерировать `shared/generated/schemas.py` с шапкой `# AUTO-GENERATED ...`, импортами, базовыми моделями и вариантами. Добавить `class Config: orm_mode = True` там, где это нужно для `from_orm`.
  - Генерировать `shared/generated/routers/rest.py` с учётом правил префикса, тегов, async/def, статусов, `response_model=List[...]` если `many: true`. Все функции должны поднимать `NotImplementedError`.
  - Следить за стабильной сортировкой (например, алфавитный порядок моделей/handlers), чтобы запуск дважды не давал diff.
- **Валидация.** Два последовательных запуска `python scripts/generate_from_spec.py` не меняют git-дифф; `python -m compileall shared/generated` проходит.

## Итерация 4 — Интеграция генератора в backend
- **Цель.** Перевести сервис на использование сгенерированного кода.
- **Шаги.**
  - Удалить `services/backend/src/app/schemas/user.py` и все импорты внутренних схем/роутов, которые мы дублируем.
  - В `services/backend/src/app/api/v1/users.py` заменить импорты на `from shared.generated.schemas import UserCreate, UserUpdate, UserPublic` и/или подключить общий сгенерированный роутер `shared.generated.routers.rest.router` на верхнем уровне (если хотим заменять весь users-модуль). На этапе MVP достаточно использовать сгенерированные модели, а пользовательский код оставить как есть.
  - Убедиться, что `PYTHONPATH`/package layout позволяет backend импортировать `shared.generated`.
- **Валидация.** `make tests service=backend` проходит, ручки продолжают работать с новыми импортами.

## Итерация 5 — Makefile + CI интеграция и тесты генератора
- **Цель.** Обеспечить автоматический запуск генератора локально и в CI.
- **Шаги.**
  - Добавить цель `generate-from-spec` в `Makefile`, которая внутри tooling-контейнера выполняет `python scripts/generate_from_spec.py`.
  - В `.github/workflows/pr.yml` и `verify.yml` вставить шаги `make generate-from-spec` и `git diff --exit-code` (до линтера/тестов или после — но до завершения workflow).
  - Добавить pytest-модуль (например, `tests/tooling/test_generate_from_spec.py`), который поднимает временный репозиторий, кидает мини-спеки, запускает генератор и проверяет, что файлы совпадают с ожиданиями/идемпотентны.
- **Валидация.** `make generate-from-spec` работает локально, CI проходит, новый тест отлавливает регрессии генератора.

## Итерация 6 — Финишные штрихи и документация
- **Цель.** Обновить документацию и провести smoke-check.
- **Шаги.**
  - Обновить `README.md`/`AGENTS.md` с описанием spec-first workflow (новая команда `make generate-from-spec`, требование держать `shared/spec` в синке).
  - Добавить инструкцию в `services/backend/README.md`, как использовать сгенерированные модели/роутеры.
  - Провести финальный прогона `make lint`, `make tests`, `make generate-from-spec`, проверить отсутствие изменений.
- **Валидация.** Документация описывает новый процесс; репозиторий чистый после полного набора make-команд.

## Итерация 7 — TODO на будущее
- **Уточнить поддержку `readonly`.** Решить, как правильно трактовать `readonly` поля (например, делать их необязательными в create/update схемах, выставлять `Field(..., const=True)` и т.д.) и расширить генератор, чтобы эти правила соблюдались автоматически. Пока флаг игнорируется; нужно вернуться после MVP.
