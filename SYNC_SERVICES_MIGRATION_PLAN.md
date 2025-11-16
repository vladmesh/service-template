# Sync-Services Migration Plan

Пошаговый план перевода репозитория на новый spec-driven процесс, в котором `services.yml` хранит только базовые поля (`name`, `type`, `description`), а вся генерация происходит через `sync_services` с двумя режимами (создание отсутствующих артефактов и проверка расхождений без автофикса).

## Итерация 0 — Сбор требований и фиксация договорённостей
- Утвердить, что каждая служба живёт в `services/<slug>/` и использует структуру из `template_service_spec.md` (Dockerfile + `src/`, `tests/`, `AGENTS.md`).
- Зафиксировать допустимые значения `type` (например, `python`, `default`) и ответственность за расширение списка.
- Описать ожидаемые артефакты, которые будут генерироваться автоматически (`services/<slug>/...`, `infra/compose.services/<slug>/...`, блоки в `infra/compose.*.yml`).
- Принять решение о CLI для двух режимов `sync_services`: `sync_services create-missing` и `sync_services check` (или аналогичные флаги).
- Обновить `AGENTS.md` и `SERVICE_AUTOMATION_PLAN.md`, чтобы команда/агенты понимали новую модель перед началом миграции.

### Результат итерации 0
- Canonical layout: `services/<slug>/` с шаблоном из `template_service_spec.md` (Dockerfile, `src/`, `tests/`, `AGENTS.md`, README). README/AGENTS остаются ручными.
- Единственный источник правды — `services.yml`, где для каждого сервиса хранятся ровно три поля: `name` (slug = название каталога), `type`, `description`.
- Допустимые типы: `python` и `default`. Добавление новых типов требует отдельного RFC + обновления `templates/services/<type>`.
- Автоматизация покрывает: каркас сервиса (`services/<slug>/`), compose-шаблоны (`infra/compose.services/<slug>/base.yml` и `dev.yml`), а также секции с маркерами `# >>> services`/`# <<< services` в `infra/compose.base.yml` и `infra/compose.dev.yml`.
- CLI согласован: `sync_services check` (не изменяет файлы, только выводит расхождения; будет запускаться как `make sync-services`) и `sync_services create-missing` (создаёт отсутствующие артефакты; `make sync-services create`).
- Документация обновлена (`AGENTS.md`, этот план) — ссылка на rollout, список поддерживаемых типов, описание артефактов и режимов `sync_services`.

## Итерация 1 — Приведение текущих сервисов к целевой структуре
- Для `backend`, `tg_bot`, `notifications_worker` (и любых других) перенести код и тесты под `services/<name>/src` и `services/<name>/tests` согласно шаблону из `template_service_spec.md`. Обновить импорты, Dockerfile-ы и Compose-файлы.
- Создать/обновить per-service `AGENTS.md` и README вручную (без автозаполнения), чтобы далее `sync_services` мог просто проверять их наличие.
- Переложить интеграционные тесты в `tests/integration`, если ещё не соответствуют структуре.
- Прогнать `make format`, `make lint`, `make tests` после каждого переноса.

### Результат итерации 1
- Каталог `apps/` переименован в `services/`; все сервисы (backend, tg_bot, notifications_worker, frontend) теперь лежат в `services/<slug>/` и сохраняют прежнюю внутреннюю структуру (`Dockerfile`, `src/`, `tests/`, вспомогательные скрипты).
- Все ссылки на `apps/...` и `apps.` в Dockerfile-ах, compose-стэках, Makefile, шаблонах и CI обновлены на `services/...` / `services.`. Обновлены пути в `services.yml`, `scripts/add_service.py`, `README.md`, `AGENTS.md` и остальных документах.
- Добавлены `services/backend/AGENTS.md` и `services/tg_bot/AGENTS.md`, существующие AGENTS (notifications_worker + шаблон) переведены на новый путь.
- Compose-файлы (`infra/compose.*`, `infra/compose.services/*`) и тестовые контейнеры теперь собирают docker-образы из `services/<slug>/Dockerfile`. Команда запуска backend-а (`uvicorn services.backend...`) и все тулзы (migrate/start scripts, pytest конфиг, GitHub Actions) используют новый модульный путь.
- `Makefile` и developer docs переключены на `services` (ruff/mypy цели, инструктаж о миграциях). `make services-validate` проходит с новой структурой.

## Итерация 2 — Упрощение `services.yml`
- Создать промежуточную версию `services.yml`, в которой для каждого сервиса указаны:
  - `name` — slug (будет соответствовать `services/<name>` и `infra/compose.services/<name>`).
  - `type` — влияет на выбор шаблона (python/default).
  - `description` — человекочитаемый текст; используем также в README-заглушках.
- Временные поля (`path`, `compose`, `logs`, `tests`, `tags`) удалить.
- Добавить миграционный скрипт/one-off, который прочитает старую схему и выпишет только нужные поля, чтобы снизить риск человеческих ошибок.
- Актуализировать `scripts/services_registry.py` так, чтобы он валидировал новую схему (и больше ничего). Пока можно оставить команды `validate/list`, но они должны знать про новый формат.

### Результат итерации 2
- `services.yml` переведён на версию 2: внутри каждого объекта осталось три поля (`name`, `type`, `description`). Все дополнительные данные (пути, compose-блоки, тестовые матрицы, логи) исчезли.
- `scripts/services_registry.py` переписан под новую схему: валидация проверяет только slug/type/description и существование производного пути `services/<slug>` (для `integration` — `tests/`). Команды `list`, `logs`, `tests` теперь вычисляют данные автоматически:
  - логтаргеты строятся по наличию `infra/compose.services/<slug>/base.yml`;
  - юнит-тесты формируются по службам, для которых в `infra/compose.tests.unit.yml` заведён контейнер `<slug>-tests-unit`;
  - интеграционный тест подхватывается из `infra/compose.tests.integration.yml` при наличии сервиса `integration-tests`.
- `scripts/compose_sync.py` больше не читаeт compose-шаблоны из YAML — путь `infra/compose.services/<slug>/<template>.yml` выводится из имени сервиса.
- `scripts/add_service.py` обновлён: скрипт копирует шаблон в `services/<slug>`, генерирует compose-шаблоны и дописывает в `services.yml` только три базовых поля. Промпты про compose service/log/tests/README/AGENTS удалены.

## Итерация 3 — Общая библиотека генерации артефактов
- Выделить переиспользуемые функции из `scripts/add_service.py` (копирование шаблонов, генерация compose-шаблонов) в новый модуль, например `scripts/lib/service_scaffold.py`.
- Добавить генерацию недостающих файлов на основе имени:
  - директория `services/<name>` копируется из шаблона `templates/services/<type>`;
  - `infra/compose.services/<name>/base.yml` и `dev.yml` формируются по правилам из `template_service_spec.md`;
  - README/AGENTS создаются как заглушки (без автотекста).
- В библиотеку включить проверку, что файлы уже существуют, и возврат диагностик вместо немедленных правок (это понадобится для режима `check`).

### Результат итерации 3
- Появился пакет `scripts/lib/service_scaffold.py` с датаклассами `ServiceSpec`/`ScaffoldReport` и общей функцией `scaffold_service(spec, apply=...)`. Она:
  - копирует шаблон из `templates/services/<type>` в `services/<slug>`, подставляя плейсхолдеры;
  - гарантирует наличие README/AGENTS — при отсутствии создаёт заглушки;
  - генерирует `infra/compose.services/<slug>/base.yml` и, по необходимости, `dev.yml` с единым содержимым.
- Функция возвращает отчёт о созданных/пропущенных/отсутствующих артефактах и не перезаписывает существующие файлы, что позволит в будущем реализовать режим `check`.
- `scripts/add_service.py` теперь использует библиотеку вместо локального кода: после ввода slug/type/description он вызывает `scaffold_service`, печатает отчёт и только затем вносит запись в `services.yml`.

## Итерация 4 — Реализация `sync_services`
- Написать новый скрипт `scripts/sync_services.py` с двумя режимами:
  1. `create-missing` (или `--apply`): проходит по всем сервисам в `services.yml`, для каждого проверяет наличие требуемых артефактов; если чего-то нет — создаёт из шаблона/генерирует compose-шаблон, но не трогает существующие файлы.
  2. `check`: выполняет те же проверки, но только собирает список расхождений (отсутствующие директории, файлы, compose-шаблоны, блоки в `infra/compose.*.yml`, несоответствие списков сервисов). Возвращает ненулевой код, чтобы пайплайн мог упасть. Никакого автофикса.
- Результат проверок должен включать:
  - отсутствующие каталоги/файлы;
  - несовпадение содержимого блоков в `infra/compose.*.yml` с тем, что собрал синк (например, через сравнение с временными файлами);
  - предупреждения, если `services.yml` содержит неизвестный `type`.
- Удалить интерактивные промпты: скрипт полностью работает от spec.

### Результат итерации 4
- Добавлен `scripts/sync_services.py` с режимами `check` и `create`. Он читает `services.yml`, строит `ServiceSpec` для каждого сервиса и вызывает `scaffold_service` с `apply=True/False`, тем самым либо создавая недостающие файлы, либо только фиксируя расхождения.
- Скрипт также проверяет compose-файлы (`infra/compose.base.yml`, `infra/compose.dev.yml`): собирает блоки из `infra/compose.services/<slug>/<template>.yml`, сравнивает с секциями между маркерами `# >>> services` и `# <<< services`, и в `create`-режиме пересобирает их автоматически.
- Для общих compose-хелперов создан модуль `scripts/lib/compose_blocks.py`, которым теперь пользуются и `scripts/compose_sync.py`, и новый `sync_services`.
- В режиме `check` утилита завершает работу с кодом 1, если найдены отсутствующие артефакты или compose-блоки расходятся; в режиме `create` она печатает сводку и выходит с ненулевым кодом только при ошибках (например, отсутствует шаблон типа).

## Итерация 5 — Интеграция с Makefile и Compose
- Добавить новую цель `make sync-services` (по умолчанию `check`, чтобы агентов стимулировать держать репо в консистентном состоянии) и `make sync-services create` для режима создания.
- Цель должна запускать новый скрипт внутри tooling-контейнера, аналогично текущим `services-validate` и `compose-sync`.
- Переписать `scripts/compose_sync.py`, чтобы он использовал ту же библиотеку генерации и не требовал ручного перечисления шаблонов (они теперь жёстко выводятся из имён сервисов).
- В пайплайны (pre-commit hook, CI) добавить `make sync-services` в режиме `check`. Блокировать пуши/PR, если есть расхождения.

## Итерация 6 — Декомиссия старых инструментов и документация
- Удалить `scripts/add_service.py`, цель `make add-service` и упоминания о ней в `AGENTS.md`, README и других доках.
- Переписать разделы про добавление сервиса: теперь процесс — отредактировать `services.yml`, запустить `make sync-services create`, вручную заполнить README/AGENTS, закоммитить.
- Обновить `template_service_spec.md` при необходимости, чтобы в нём явно описывалась связь с `sync_services`.
- Сообщить команде (и ботам), что любые новые сервисы должны начинаться с PR, где добавляется запись в `services.yml` и прогоняется `make sync-services`.

## Итерация 7 — Тестирование и контроль качества
- Написать unit-тесты для библиотечных функций (например, через `pytest` внутри tooling-контейнера) — проверять, что генерация файлов корректна и не перетирает существующие данные.
- Добавить e2e тест `make sync-services` в CI (создание временного сервиса в фикстуре, запуск обоих режимов, проверка exit code).
- После мёрджа мониторить несколько PR, чтобы убедиться: разработчики и агенты выполняют новый поток, пайплайн корректно ловит расхождения, ручная доработка README/AGENTS не забывается.

В конце этих итераций репозиторий будет управляться через декларативный `services.yml` + `sync_services`, без интерактивного генератора и без дополнительных полей, которые раньше приходилось синхронизировать вручную.
