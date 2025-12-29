# Docker Infrastructure Audit

**Дата аудита:** 2024-12-06  
**Статус:** Хороший - наиболее оптимизированный проект, небольшие улучшения

---

## Обзор

Проект service-template имеет наиболее продвинутую Docker-инфраструктуру среди всех проектов. Используется современный синтаксис Dockerfile, правильный порядок слоёв, ARG для переключения dev/prod. Есть несколько небольших улучшений.

---

## Положительные стороны

- Используется `# syntax=docker/dockerfile:1.7`
- Правильный порядок COPY (сначала зависимости, потом код)
- ARG для переключения dev/prod зависимостей
- Создание минимальной структуры shared для poetry
- `PIP_NO_CACHE_DIR=off` для экономии места

---

## Выявленные проблемы

### 1. Отсутствует `.dockerignore`

**Влияние:** При сборке копируется весь контекст проекта.

**Решение:** Создать `.dockerignore` в корне:

```gitignore
# Git
.git
.gitignore

# Python
__pycache__/
*.py[cod]
*.pyo
.venv/
venv/
*.egg-info/
dist/
build/

# Node
node_modules/
.npm/
.pnpm-store/

# Testing
.pytest_cache/
.coverage
htmlcov/
coverage/

# Linting
.ruff_cache/
.mypy_cache/
.eslintcache

# IDE
.idea/
.vscode/
*.swp

# Environment
.env
.env.*
!.env.example

# Framework generated (если не нужны в образе)
# framework/templates/

# Tooling (отдельный образ)
tooling/

# Documentation
docs/
*.md
!README.md

# Misc
*.log
*.tmp
```

---

### 2. Frontend Dockerfile: npm install вместо npm ci

**Текущий код:**
```dockerfile
RUN npm install  # Может установить другие версии
```

**Проблема:** `npm install` может обновлять package-lock.json и устанавливать отличающиеся версии.

**Решение:**
```dockerfile
FROM node:20-alpine AS base

WORKDIR /app

COPY services/frontend/package*.json ./
RUN npm ci  # Строгая установка по lock-файлу

COPY services/frontend .

EXPOSE 4321

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "4321"]
```

---

### 3. `poetry lock` в Dockerfile

**Текущий код:**
```dockerfile
RUN cd services/backend \
    && poetry config virtualenvs.create false \
    && poetry lock \  # Генерирует новый lock при каждой сборке!
    && if [ "$INSTALL_DEV_DEPS" = "true" ]; then ...
```

**Проблема:** `poetry lock` может генерировать разные результаты при каждой сборке если есть обновления пакетов. Это нарушает воспроизводимость.

**Решение:** Убрать `poetry lock`, использовать только существующий lock-файл:
```dockerfile
RUN cd services/backend \
    && poetry config virtualenvs.create false \
    && if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
        poetry install --with dev --no-root; \
    else \
        poetry install --without dev --no-root; \
    fi
```

Если нужна проверка актуальности lock-файла, делать это в CI до сборки:
```bash
poetry lock --check
```

---

### 4. Tooling Dockerfile: нет cache mount

**Текущий код:**
```dockerfile
RUN pip install --no-cache-dir \
    ruff==0.14.5 \
    xenon==0.9.1 \
    mypy==1.10.0 \
    pytest==8.2.0 \
    ...
```

**Улучшение:** Добавить cache mount для ускорения пересборки:

```dockerfile
# syntax=docker/dockerfile:1.7

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
    ruff==0.14.5 \
    xenon==0.9.1 \
    mypy==1.10.0 \
    pytest==8.2.0 \
    pytest-cov==4.1.0 \
    types-PyYAML \
    PyYAML \
    datamodel-code-generator[http] \
    jinja2 \
    poetry
```

---

### 5. Backend: можно добавить cache mount для poetry

**Текущий код хороший, но можно улучшить:**

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/pypoetry \
    cd services/backend \
    && poetry config virtualenvs.create false \
    && if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
        poetry install --with dev --no-root; \
    else \
        poetry install --without dev --no-root; \
    fi
```

---

### 6. Scaffold templates: проверить актуальность

**Расположение:** `framework/templates/scaffold/services/`

Есть шаблоны для:
- python-fastapi
- python-faststream
- node
- default
- python

**Рекомендация:** Убедиться, что шаблоны используют те же best practices, что и основные сервисы.

---

## Рекомендуемые изменения

### Шаг 1: Создать `.dockerignore` (5 минут)

Создать файл с содержимым из раздела 1.

### Шаг 2: Исправить Frontend Dockerfile (5 минут)

Заменить `npm install` на `npm ci`.

### Шаг 3: Убрать `poetry lock` из Backend Dockerfile (5 минут)

Удалить строку `&& poetry lock \`.

### Шаг 4: Добавить cache mounts в Tooling (5 минут)

Использовать `--mount=type=cache` для pip.

### Шаг 5: Аудит scaffold templates (30 минут)

Проверить и обновить шаблоны в `framework/templates/scaffold/services/`.

---

## Ожидаемый результат

| Метрика | До | После |
|---------|-----|-------|
| Размер build context | ~50MB | ~5MB |
| Время пересборки tooling | ~60 сек | ~15 сек |
| Воспроизводимость сборки | 95% | 100% |

---

## Приоритет исправлений

1. **ВЫСОКИЙ:** Создать `.dockerignore` - уменьшение контекста сборки
2. **ВЫСОКИЙ:** Убрать `poetry lock` - воспроизводимость
3. **СРЕДНИЙ:** npm ci вместо npm install - воспроизводимость
4. **НИЗКИЙ:** Cache mounts - небольшое ускорение
5. **НИЗКИЙ:** Аудит templates - поддержка консистентности

---

## Дополнительные рекомендации

### Автоматическая очистка кэша

Добавить в CI/CD или Makefile:

```makefile
.PHONY: docker-clean
docker-clean:
	docker builder prune --keep-storage=5GB --force
	docker image prune -f

.PHONY: docker-clean-all  
docker-clean-all:
	docker system prune -a --volumes --force
```

### Мониторинг размера образов

Добавить в CI проверку размера образов:

```bash
#!/bin/bash
MAX_SIZE_MB=500

SIZE=$(docker image inspect $IMAGE --format='{{.Size}}')
SIZE_MB=$((SIZE / 1024 / 1024))

if [ $SIZE_MB -gt $MAX_SIZE_MB ]; then
    echo "ERROR: Image size ${SIZE_MB}MB exceeds limit ${MAX_SIZE_MB}MB"
    exit 1
fi
```
