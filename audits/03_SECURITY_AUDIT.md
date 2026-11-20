# 03. Аудит безопасности (Security Audit)

> **Статус на Этапе 1.3:** Меры защиты секретов, валидации входных данных, Firestore-изоляции и безопасного логирования проверены статически и unit-тестами (`COMPLETED`). Живой аудит правил в Firebase Console не выполнялся (`NOT_TESTED`).

---

## 1. Защита секретов и конфигурации

| Проверка | Реализация и путь к файлу | Статус |
| :--- | :--- | :--- |
| `.gitignore` и отсутствие секретов в репозитории | Исключены `.env`, `.env.*` (кроме `.env.example`), `serviceAccountKey.json`, `firebase-credentials.json`, `*firebase-adminsdk*.json`, `*.pem`, `*.key`, `*.log`, `.venv/`. | `COMPLETED` |
| Валидация `BOT_TOKEN` и `SecretStr` | `app/config.py` проверяет наличие двоеточия `:` и отсутствие пробелов; хранит в `SecretStr`. | `COMPLETED` |
| Маскирование секретов и PII в логах | `app/logging_config.py` (`diagnose=False`) + `app/utils/sanitizers.py` (`sanitize_secrets`, `mask_telegram_id`). | `COMPLETED` |
| CI без секретов | `.github/workflows/ci.yml` запускает Ruff и pytest исключительно с тестовыми mock-объектами. | `COMPLETED` |

---

## 2. Целостность данных, Firebase и обработка callback

| Проверка | Реализация | Статус |
| :--- | :--- | :--- |
| Соответствие `FIREBASE_PROJECT_ID` | `app/database/firebase.py` сверяет `existing_app.project_id` с `settings.firebase_project_id` и запрещает запуск с чужим проектом. | `COMPLETED` |
| Отсутствие доверия к `callback_data` | Все callback-роуты используют строгие regex-паттерны в `app/bot/setup.py`; `settings:lang:<code>` дополнительно проверяется по белому списку `LANGUAGES` (`enabled=True`) в `UserService` и `settings.py`; неизвестные callback перехватываются `unknown_callback_handler`. | `COMPLETED` |
| Защита от повторного создания пользователя | `UserRepository.create_user` использует атомарный `doc_ref.create()`; `UserService` обрабатывает гонку `UserAlreadyExistsError`. | `COMPLETED` |
| Устойчивость к сбоям БД и повреждённым документам | `UserRepository` ловит `FirebaseError`, `GoogleAPIError`, `GoogleAuthError`, `ValidationError`, `TimeoutError`, `OSError`. | `COMPLETED` |
| Очистка памяти от rate-limit кэша | `CallbackGuard` в `app/utils/callbacks.py` очищает устаревшие записи при превышении 1000 ключей. | `COMPLETED` |
| Отсутствие пустых `except`-блоков | Проверено по всему `app/` (единственное допустимое подавление `ValueError` в `firebase.py` — при проверке отсутствующего `default` App и при `delete_app`). | `COMPLETED` |
