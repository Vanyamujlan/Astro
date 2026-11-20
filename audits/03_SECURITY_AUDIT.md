# 03. Аудит безопасности (Security Audit)

> **Статус на Этапе 1.2:** Меры защиты секретов, логов, серверного доступа к Firestore и безопасной обработки callback реализованы (`COMPLETED` в коде; `NOT_TESTED` в production Firebase).  
> **Критическое правило:** реальные токены, API-ключи и содержимое Firebase Service Account JSON никогда не сохраняются в репозиторий или аудиты.

---

## 1. Секреты и конфигурация

| Проверка | Реализация и путь к файлу | Статус |
| :--- | :--- | :--- |
| Исключение секретов из Git | `.gitignore` блокирует `.env`, `.env.*`, `serviceAccountKey.json`, `firebase-credentials.json`, `*firebase-adminsdk*.json`, `*.pem`, `*.key`, `*.log`, `.venv/`. | `COMPLETED` |
| Типизированная загрузка и `SecretStr` | `app/config.py` (`Settings.bot_token: SecretStr`) — токен маскируется в `repr()`/`str()`. | `COMPLETED` |
| Ошибка без утечки данных при старте | `app/config.py` и `app/main.py` выводят понятное сообщение об отсутствии переменных без вывода значений. | `COMPLETED` |
| Фильтрация логов | `app/logging_config.py` + `app/utils/sanitizers.py` редактируют токены и `telegram_id`; `diagnose=False` в Loguru скрывает локальные переменные в стектрейсах. | `COMPLETED` |

---

## 2. Безопасность Telegram UI, Callback-роутинга и Firestore

| Мера защиты | Реализация (путь к файлу) | Статус |
| :--- | :--- | :--- |
| Защита от двойных нажатий (Callback Flood) | `app/utils/callbacks.py` (`CallbackGuard`, `run_guarded_callback`) — блокировка одновременного выполнения и кулдаун `0.35s` на повторные клики одной кнопки. | `COMPLETED` |
| Безопасное редактирование сообщений | `app/utils/callbacks.py` (`safe_edit_message`) — перехват `BadRequest("Message is not modified")` без падения обработчика. | `COMPLETED` |
| Обработка неизвестных callback_data | `app/handlers/menu.py` (`unknown_callback_handler`), зарегистрирован последним в `app/bot/setup.py`. | `COMPLETED` |
| HTML-экранирование пользовательских данных | `app/handlers/profile.py` (`format_profile_text`) применяет `html.escape()` для `first_name`, `username` и `plan`. | `COMPLETED` |
| Белый список обновляемых полей Firestore | `app/database/repositories/user_repository.py` (`_UPDATABLE_FIELDS`) запрещает изменение `telegram_id` и `created_at` через `update_user`. | `COMPLETED` |
| Атомарное создание пользователя без перезаписи | `UserRepository.create_user` вызывает `doc_ref.create(payload)` в `asyncio.to_thread`; дубликаты отклоняются через `UserAlreadyExistsError`. | `COMPLETED` |
| Изоляция доступа к БД | Прямые обращения к Firestore отсутствуют в `app/handlers/*`; все запросы идут через `UserService` → `UserRepository`. | `COMPLETED` |
| Правила безопасности Cloud Firestore | Клиентские правила должны оставаться закрытыми (`allow read, write: if false;`), так как весь доступ серверный через Admin SDK. | `PLANNED` (ручная настройка в Firebase Console) |
