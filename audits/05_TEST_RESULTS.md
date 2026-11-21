# 05. Результаты тестирования (Test Results)

> **Правило честности:** указаны только реально выполненные запуски тестов в `.venv` и их фактический вывод.

---

## 1. Сводка последнего запуска (`/start` hardening + Firebase `.env` auth + Этап 1.3)

- **Дата запуска:** `2026-11-21`
- **Среда:** `.venv` (`CPython 3.12.16`, `pytest 8.4.2`, `pytest-asyncio 0.26.0`, `ruff 0.17.6`)

| Проверка | Команда | Фактический результат | Статус |
| :--- | :--- | :--- | :--- |
| `pytest` | `pytest -v` | **`37 passed in 1.41s`** (0 failed, 0 skipped) | `COMPLETED` |
| `ruff` | `ruff check .` | **`All checks passed!`** (0 ошибок) | `COMPLETED` |

### Новые проверки `/start` и устойчивости (mock-тесты)
- `test_start_end_to_end_application_dispatch_and_no_duplicates` — прохождение реального `telegram.Update` с `/start` через `create_application()` и `Application.process_update()`, проверка точного текста, `InlineKeyboardMarkup` со всеми 6 кнопками, записи в Firestore и отсутствия дубликатов при повторном `/start`.
- `test_start_handles_firebase_error_gracefully_and_logs_safely` — при `ServiceUnavailable` из Firestore пользователь получает понятное сообщение об ошибке, исключение не пробрасывается, а в лог безопасно пишутся типы ошибки и первопричины.
- `test_start_and_callbacks_handle_missing_user_service_without_key_error` — отсутствие `user_service` в `context.bot_data` не вызывает `KeyError` ни в `/start`, ни в `profile_callback`, ни в `set_language_callback`.
- Обновлён `test_run_bot_startup_and_graceful_shutdown_order` — подтверждён строгий порядок `init_firebase → create_application → app.initialize → app.start → updater.start_polling`.

### Проверки авторизации Firebase через `.env` (mock-тесты)
- Преобразование однострочного `FIREBASE_PRIVATE_KEY` с `\n` и кавычками в стандартный PEM внутри `SecretStr` (`tests/test_config.py`).
- Отклонение отсутствующих `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`, некорректного email, отсутствующих PEM-маркеров и битого base64 без утечки секрета в `ConfigurationError`.
- Маскирование полных и усечённых PEM-ключей в `sanitize_secrets()`.
- Создание `google.oauth2.service_account.Credentials.from_service_account_info` и передача в `firebase_admin.initialize_app` с `FIREBASE_DATABASE_ID` и без него, безопасный перехват невалидного ключа и совместимость с `UserRepository` (`tests/test_user_repository.py`).

---

## 2. Тесты Этапа 1.3

### `tests/test_bot_lifecycle.py` (5/5)
1. `test_run_bot_startup_and_graceful_shutdown_order` — проверка строгого порядка: `app.initialize` → `app.start` → `updater.start_polling(error_callback=...)` → `updater.stop` → `app.stop` → `app.shutdown` → `close_firebase` (имитация проверки `if self.running: raise RuntimeError`).
2. `test_run_bot_invalid_token_cleans_up_resources` — при `InvalidToken` выбрасывается `ConfigurationError`, `close_firebase()` вызывается гарантированно.
3. `test_unknown_command_handler_replies_politely` — ответ на неизвестную команду с подсказкой `/start`.
4. `test_global_error_handler_handles_telegram_db_and_callbacks` — обработка `Conflict`, `NetworkError`, `DatabaseOperationError`, обычных исключений и закрытие спиннера `callback_query.answer()`.
5. `test_create_application_registers_unknown_command_handler` — проверка регистрации всех 10 обработчиков в группе `0`.

### Дополнения в `tests/test_config.py` и `tests/test_user_repository.py` (+3)
6. `test_load_settings_invalid_bot_token_format` — отклонение `BOT_TOKEN` без `:` или с пробелами.
7. `test_firestore_auth_and_corrupted_doc_handling` — обработка `DefaultCredentialsError` и повреждённого документа Firestore (`ValidationError`) через `DatabaseOperationError`.
8. `test_firebase_manager_project_mismatch_and_close` — отклонение чужого `project_id` и проверка `close()`.

*(Все 24 теста из Этапов 1.1–1.2 также перепроверены и пройдены.)*

---

## 3. Непроверенные сценарии (`NOT_TESTED`)

- Реальный long-polling цикл с живым `BOT_TOKEN` в Telegram Bot API.
- Реальные запись/чтение документов в облачном Firebase Cloud Firestore с настоящим Service Account JSON.
- Выполнение GitHub Actions workflow `.github/workflows/ci.yml` на серверах GitHub.
