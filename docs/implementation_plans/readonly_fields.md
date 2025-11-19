# План реализации поддержки `readonly` полей в спецификациях

Этот документ описывает архитектуру и план внедрения поддержки атрибута `readonly` в файлах спецификаций (`shared/spec/*.yaml`) и генераторе кода (`scripts/generate_from_spec.py`).

## 1. Цель

Автоматизировать исключение полей (таких как `id`, `created_at`, `updated_at`) из моделей создания и обновления (Create/Update requests), используя декларативный флаг `readonly: true`, вместо ручного дублирования списков `exclude`.

## 2. Изменения в спецификации (Syntax)

### Добавление флага `readonly`
В `shared/spec/models.yaml` добавляется атрибут `readonly: true` для полей, которые не должны изменяться клиентом.

```yaml
models:
  User:
    fields:
      id:
        type: int
        readonly: true  # <-- Новое поле
      username:
        type: string
      created_at:
        type: datetime
        readonly: true  # <-- Новое поле
```

### Логика наследования и Variants
*   **Create/Update варианты**: Поля с `readonly: true` **автоматически исключаются** из схемы.
*   **Read вариант**: Поля с `readonly: true` **включаются** в схему и помечаются атрибутом `readOnly: true` (для OpenAPI/JSON Schema).
*   **Override (Escape Hatch)**: Если поле помечено как `readonly`, но его необходимо передать (например, при миграции или для админа), его можно вернуть через список `include` в варианте.

```yaml
    variants:
      Create:
        # id и created_at исключатся автоматически
        exclude: [] # Можно очистить
      Update:
        # id и created_at исключатся автоматически
        optional: [username]
      AdminCreate:
        # Принудительное включение readonly поля
        include: [id] 
```

## 3. Изменения в генераторе (`scripts/generate_from_spec.py`)

Необходимо модифицировать функцию `convert_to_json_schema`:

1.  **Считывание флага**: При парсинге полей считывать значение `readonly`.
2.  **JSON Schema Metadata**: Добавлять `readOnly: True` в словарь валидаций поля (для отображения в документации Swagger/OpenAPI для моделей ответов).
3.  **Фильтрация в вариантах**:
    *   При итерации по полям варианта проверять флаг `readonly`.
    *   Если `variant_name` содержит "Create" или "Update" (или является входной моделью):
        *   Если `readonly: true` И поле НЕ в списке `include` -> **Пропустить поле** (continue).
    *   Логика `exclude` остается приоритетной (если поле в `exclude`, оно пропускается всегда).

## 4. План реализации (Iterative)

### Фаза 1: Подготовка теста (Non-breaking)
1.  Создать тестовую спецификацию `shared/spec/test_readonly.yaml` с примером модели, использующей новый флаг.
2.  Создать unit-тест в `tests/tooling/test_generate_from_spec.py`, который будет запускать генерацию для этой спеки и проверять JSON схему на наличие `readOnly` и отсутствие полей в Create/Update.

### Фаза 2: Доработка генератора
1.  Изменить `scripts/generate_from_spec.py`.
2.  Реализовать проброс флага `readOnly` в JSON Schema.
3.  Реализовать логику автоматического исключения для вариантов `Create` и `Update`.
4.  Убедиться, что существующие модели (где `readonly` еще нет) генерируются так же, как раньше.

### Фаза 3: Миграция основной спецификации
1.  В `shared/spec/models.yaml` проставить `readonly: true` для:
    *   `id` (во всех моделях)
    *   `created_at`
    *   `updated_at`
2.  Запустить `make generate-from-spec`.
3.  Проверить `shared/generated/schemas.py` — убедиться, что поля корректно исчезли из Create/Update моделей (или остались, если они еще дублируются в `exclude`).

### Фаза 4: Очистка (Refactoring)
1.  Удалить явные `exclude: [id, created_at, ...]` из вариантов в `shared/spec/models.yaml`.
2.  Перегенерировать код.
3.  Прогнать `make typecheck` и `make tests`, чтобы убедиться, что API контракты не нарушены.

## 5. Критерии приемки
*   [ ] Поля `id`, `created_at` имеют `readonly: true` в `models.yaml`.
*   [ ] Модели `*Create` и `*Update` в `schemas.py` не содержат этих полей.
*   [ ] Модели `*Read` (Response) содержат эти поля.
*   [ ] Отсутствует дублирование в списках `exclude` в yaml файлах.
*   [ ] `make tooling-tests` проходит успешно.

