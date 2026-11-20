# 05. Результаты тестирования (Test Results)

> **Правило честности:** зафиксированы исключительно реально выполненные запуски и их фактические результаты.

---

## 1. Сводка последнего запуска (Этап 1.2)

- **Дата запуска:** `2026-11-20`
- **Среда:** `.venv` (`CPython 3.12.16`, `pytest 8.4.2`, `pytest-asyncio 0.26.0`, `ruff 0.17.6`)

| Инструмент | Команда | Фактический результат | Статус |
| :--- | :--- | :--- | :--- |
| `pytest` | `.venv/bin/pytest -v` | **`24 passed in 1.69s`** (0 failed, 0 skipped) | `COMPLETED` |
| `ruff` | `.venv/bin/ruff check .` | **`All checks passed!`** (0 ошибок) | `COMPLETED` |

---

## 2. Покрытые сценарии (`24/24 PASSED`)

### `tests/test_config.py` (6/6)
- Загрузка настроек, нестандартный `FIREBASE_DATABASE_ID`, ошибки при пустых/отсутствующих `BOT_TOKEN` и `FIREBASE_PROJECT_ID`, маскирование секретов и `telegram_id`.

### `tests/test_user_repository.py` (8/8, mock/fake Firestore)
- Создание, чтение, проверка существования, защита от дубликатов/перезаписи, обновление разрешённых полей, обёртка `GoogleAPIError`, синхронизация и гонка в `UserService`, `/start`, `FirebaseManager` (`missing credentials`, duplicate-init guard, `database_id`).

### `tests/test_navigation_and_profile.py` (10/10, mock Telegram updates/callbacks + FakeFirestoreClient)
- `test_start_renders_minimalist_main_menu` — точный текст приветствия Astralio и 6 однорядных inline-кнопок.
- `test_section_navigation_and_back_to_main` (4 параметризованных сценария: `natal`, `compatibility`, `forecasts`, `premium`) — открытие разделов и возврат в главное меню через `nav:main`.
- `test_help_callback_and_command` — раздел «Помощь» через кнопку и `/help`.
- `test_profile_loads_from_firestore_and_handles_missing_fields` — загрузка профиля из Firestore, экранирование HTML, подстановка `Не указан` при отсутствии полей или документа.
- `test_language_settings_and_no_duplicates` — меню языка, честная обработка запланированных `en`/`de`, обновление `ru` без создания дубликатов.
- `test_unknown_callback_and_double_tap_protection` — ответ на неизвестный `callback_data` и подавление быстрого повторного нажатия.
- `test_create_application_registers_all_stage_1_2_handlers` — проверка регистрации всех 9 обработчиков в `Application`.

---

## 3. Непроверенные сценарии (`NOT_TESTED`)

- Реальное взаимодействие с серверами Telegram Bot API (отсутствует `BOT_TOKEN`).
- Реальное чтение/запись документов `users` в облачном Firebase Cloud Firestore (отсутствуют Firebase credentials).
