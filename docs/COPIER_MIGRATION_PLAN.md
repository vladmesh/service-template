# План миграции на Copier Template

Этот документ описывает пошаговый план превращения service-template в Copier-шаблон для генерации новых проектов.

## Цели

1. Генерация нового проекта с выбранными модулями одной командой
2. Возможность обновления инфраструктуры в существующих проектах (`copier update`)
3. Сохранение пользовательского кода при обновлениях
4. Простой интерфейс для AI-агентов (CLI с `--data` параметрами)

---

## Фаза 1: Подготовка структуры

### 1.1 Определить модули и их зависимости

**Доступные модули:**

| Модуль | Описание | Зависимости |
|--------|----------|-------------|
| `backend` | FastAPI REST API + PostgreSQL | redis (опционально) |
| `tg_bot` | Telegram бот на FastStream | redis, backend |
| `notifications` | Worker для email/telegram | redis |
| `frontend` | Node.js статический фронтенд | backend (API) |
| `monitoring` | Prometheus + Grafana стек | - |

**Задачи:**
- [ ] Финализировать список модулей
- [ ] Определить обязательные vs опциональные зависимости между модулями
- [ ] Решить вопрос с `test_service` — убрать или оставить как пример

### 1.2 Определить параметры шаблона

**Основные переменные:**

```yaml
# Метаданные проекта
project_name: "my-project"           # Имя проекта (slug)
project_description: "Description"   # Описание
author_name: "Your Name"
author_email: "you@example.com"

# Выбор модулей
modules: ["backend"]                 # Мультиселект

# Опции инфраструктуры
use_redis: true                      # Авто-включается если выбран tg_bot/notifications
use_postgres: true                   # Авто-включается если выбран backend
python_version: "3.12"
node_version: "20"                   # Если выбран frontend
```

**Задачи:**
- [ ] Составить полный список переменных
- [ ] Определить defaults и валидации
- [ ] Продумать derived-переменные (например, `use_redis` автоматически если есть event-driven модули)

---

## Фаза 2: Создание Copier конфигурации

### 2.1 Базовый `copier.yml`

**Задачи:**
- [ ] Создать `copier.yml` в корне репозитория
- [ ] Настроить вопросы с валидацией
- [ ] Добавить Jinja extensions если нужны (например, slugify)

**Пример структуры:**

```yaml
_min_copier_version: "9.0.0"
_subdirectory: template
_templates_suffix: .jinja
_answers_file: .copier-answers.yml

# Вопросы
project_name:
  type: str
  help: "Имя проекта (lowercase, без пробелов)"
  validator: "{% if not project_name | regex_search('^[a-z][a-z0-9_-]*$') %}Invalid name{% endif %}"

modules:
  type: str  # "backend,tg_bot,frontend"
  help: "Модули через запятую: backend, tg_bot, notifications, frontend, monitoring"
  default: "backend"
```

### 2.2 Настройка update-политики

**Задачи:**
- [ ] Определить `_skip_if_exists` — файлы которые не перезаписываются при update
- [ ] Определить `_exclude` — что исключить из копирования в зависимости от модулей
- [ ] Настроить `.copier-answers.yml` preservation

**Категории файлов:**

| Категория | Поведение при update | Примеры |
|-----------|---------------------|---------|
| Инфраструктура | Обновляется | `infra/*.yml`, `Makefile`, `Dockerfile` |
| Конфиги проекта | Skip if exists | `.env`, `services.yml` |
| Пользовательский код | Никогда не трогать | `services/*/src/controllers/`, `services/*/src/app/` |
| Сгенерированный код | Обновляется | `shared/generated/` |
| Спецификации | Skip if exists | `shared/spec/*.yaml` |
| Документация | Обновляется | `CONTRIBUTING.md`, `ARCHITECTURE.md` |
| README проекта | Skip if exists | `README.md` |

---

## Фаза 3: Темплейтизация файлов

### 3.1 Реорганизация директорий

**Текущая структура → Целевая:**

```
service-template/
├── copier.yml              # NEW: конфигурация Copier
├── template/               # NEW: всё что копируется
│   ├── {{project_name}}/   # или без вложенности
│   ├── services/
│   ├── shared/
│   ├── infra/
│   └── ...
├── docs/                   # Документация шаблона (не копируется)
└── tests/                  # Тесты шаблона (не копируется)
```

**Альтернатива — без поддиректории:**
```
service-template/
├── copier.yml
├── services/               # Темплейтизированные файлы напрямую
├── shared/
├── infra/
├── {% if 'frontend' in modules %}frontend{% endif %}/
└── ...
```

**Задачи:**
- [ ] Выбрать подход (subdirectory vs flat)
- [ ] Создать структуру
- [ ] Перенести файлы

### 3.2 Темплейтизация по категориям

#### 3.2.1 Метаданные проекта

**Файлы:**
- [ ] `README.md.jinja` — название, описание, badges
- [ ] `pyproject.toml` файлы — имя пакета
- [ ] `package.json` (frontend) — имя проекта
- [ ] `.env.example` — с учётом выбранных модулей

#### 3.2.2 Docker и инфраструктура

**Файлы:**
- [ ] `infra/compose.base.yml.jinja` — только выбранные сервисы
- [ ] `infra/compose.dev.yml.jinja` — volume mounts для выбранных сервисов
- [ ] `infra/compose.prod.yml.jinja`
- [ ] `infra/compose.tests.*.yml.jinja`
- [ ] `Makefile.jinja` — команды для выбранных модулей

#### 3.2.3 Сервисы (условное включение)

**Логика:**
```jinja
{% if 'backend' in modules %}
services/backend/...
{% endif %}

{% if 'tg_bot' in modules %}
services/tg_bot/...
{% endif %}
```

**Задачи:**
- [ ] Темплейтизировать `services.yml.jinja`
- [ ] Условно включать директории сервисов
- [ ] Убедиться что shared/spec содержит только нужные модели

#### 3.2.4 CI/CD

**Файлы:**
- [ ] `.github/workflows/ci.yml.jinja` — джобы для выбранных модулей
- [ ] `.github/workflows/deploy.yml.jinja` (если нужен)

**Задачи:**
- [ ] Создать базовые GitHub Actions
- [ ] Условно включать шаги lint/test для каждого модуля

---

## Фаза 4: Тестирование

### 4.1 Unit-тесты шаблона

**Что тестировать:**
- [ ] Генерация с каждой комбинацией модулей
- [ ] Валидность сгенерированных YAML/JSON файлов
- [ ] Отсутствие Jinja-артефактов в output (`{{`, `{%`)

**Инструменты:**
- `pytest` + `copier` Python API
- Временные директории для генерации

**Пример теста:**

```python
import copier
import pytest
from pathlib import Path

@pytest.mark.parametrize("modules", [
    "backend",
    "backend,tg_bot",
    "backend,frontend",
    "backend,tg_bot,notifications,frontend,monitoring",
])
def test_generation(tmp_path: Path, modules: str):
    copier.run_copy(
        ".",
        tmp_path,
        data={"project_name": "test_project", "modules": modules},
        defaults=True,
        unsafe=True,
    )
    
    # Проверяем что проект создался
    assert (tmp_path / "Makefile").exists()
    assert (tmp_path / "services.yml").exists()
    
    # Проверяем что нет Jinja артефактов
    for file in tmp_path.rglob("*"):
        if file.is_file() and file.suffix in [".py", ".yml", ".yaml", ".md"]:
            content = file.read_text()
            assert "{{" not in content, f"Jinja artifact in {file}"
            assert "{%" not in content, f"Jinja artifact in {file}"
```

### 4.2 Integration-тесты

**Что тестировать:**
- [ ] `make lint` проходит в сгенерированном проекте
- [ ] `make tests` проходит
- [ ] Docker Compose валиден (`docker compose config`)
- [ ] Сервисы запускаются

**Пример:**

```python
def test_generated_project_passes_lint(tmp_path: Path):
    copier.run_copy(".", tmp_path, data={...}, defaults=True, unsafe=True)
    
    result = subprocess.run(
        ["make", "lint"],
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode()
```

### 4.3 Update-тесты

**Что тестировать:**
- [ ] `copier update` не ломает существующий проект
- [ ] Пользовательские файлы сохраняются
- [ ] Новые infra-файлы добавляются

**Пример:**

```python
def test_update_preserves_user_code(tmp_path: Path):
    # Генерируем проект
    copier.run_copy(".", tmp_path, data={...}, defaults=True, unsafe=True)
    
    # Добавляем "пользовательский" код
    user_file = tmp_path / "services/backend/src/controllers/custom.py"
    user_file.write_text("# My custom code")
    
    # Обновляем
    copier.run_update(tmp_path, defaults=True, unsafe=True)
    
    # Проверяем что код сохранился
    assert user_file.exists()
    assert "My custom code" in user_file.read_text()
```

---

## Фаза 5: Документация

### 5.1 Документация шаблона (для разработчиков шаблона)

**Файлы:**
- [ ] `docs/TEMPLATE_DEVELOPMENT.md` — как развивать шаблон
- [ ] `docs/TESTING.md` — как запускать тесты шаблона

### 5.2 Документация сгенерированного проекта

**Файлы которые генерируются:**
- [ ] `README.md.jinja` — quickstart для конкретного проекта
- [ ] `AGENTS.md.jinja` — инструкции для AI с учётом выбранных модулей
- [ ] `ARCHITECTURE.md.jinja` — архитектура с учётом модулей
- [ ] `CONTRIBUTING.md` — правила (можно оставить статичным)

### 5.3 Актуализация существующей документации

**Задачи:**
- [ ] Обновить корневой `README.md` — теперь это README шаблона, не проекта
- [ ] Добавить секцию "Quick Start" с `copier copy`
- [ ] Обновить `MANIFESTO.md` если нужно
- [ ] Обновить `backlog.md` — отметить Copier как DONE

---

## Фаза 6: CI/CD для шаблона

### 6.1 GitHub Actions

**Workflows:**
- [ ] `test-template.yml` — запуск тестов шаблона на каждый PR
- [ ] `release.yml` — тегирование версий шаблона

**Пример test-template.yml:**

```yaml
name: Test Template

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        modules:
          - "backend"
          - "backend,tg_bot"
          - "backend,frontend"
          - "backend,tg_bot,notifications,frontend,monitoring"
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      
      - name: Install dependencies
        run: pip install copier pytest
      
      - name: Generate project
        run: |
          copier copy . /tmp/test-project \
            --data project_name=test_project \
            --data modules=${{ matrix.modules }} \
            --defaults --trust
      
      - name: Validate generated project
        run: |
          cd /tmp/test-project
          docker compose -f infra/compose.base.yml config
          # make lint (если есть tooling container)
```

---

## Порядок выполнения

### Итерация 1: MVP (backend only)
1. [ ] Создать `copier.yml` с минимальными параметрами
2. [ ] Темплейтизировать core файлы (README, Makefile, compose)
3. [ ] Сделать backend единственным модулем
4. [ ] Написать базовые тесты генерации
5. [ ] Проверить что сгенерированный проект работает

### Итерация 2: Модульность
6. [ ] Добавить выбор модулей (tg_bot, notifications)
7. [ ] Условная генерация services/
8. [ ] Условная генерация docker-compose сервисов
9. [ ] Расширить тесты на комбинации модулей

### Итерация 3: Frontend и мониторинг
10. [ ] Добавить frontend модуль
11. [ ] Добавить monitoring модуль (Prometheus/Grafana)
12. [ ] Интеграционные тесты

### Итерация 4: Update flow
13. [ ] Настроить `_skip_if_exists` и `_exclude`
14. [ ] Тесты на `copier update`
15. [ ] Документация по обновлению

### Итерация 5: Polish
16. [ ] Полная документация
17. [ ] CI для шаблона
18. [ ] Финальное тестирование всех комбинаций

---

## Открытые вопросы

1. **Версионирование шаблона** — семвер? Как коммуницировать breaking changes?

2. **Monorepo vs отдельный репо для шаблона** — держать шаблон в этом же репо или вынести?

3. **Примеры vs чистый шаблон** — оставлять ли example implementations (User model, etc.) или генерировать пустой проект?

4. **Shared specs** — как обрабатывать `shared/spec/` при update? Мержить или skip?

5. **Secrets management** — добавлять ли интеграцию с vault/doppler как опцию?

---

## Ссылки

- [Copier Documentation](https://copier.readthedocs.io/)
- [Copier GitHub](https://github.com/copier-org/copier)
- [Jinja2 Template Designer](https://jinja.palletsprojects.com/en/3.1.x/templates/)
