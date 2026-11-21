# История изменений (CHANGELOG)

Все значимые изменения проекта фиксируются в этом файле.  
**Правило:** история предыдущих версий и записей не удаляется и не переписывается задним числом.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

---

## [Unreleased]
### Запланировано (`PLANNED`)
- Этап 2+: Ввод и хранение данных рождения (`birth_data`), расчёты (`pyswisseph`), OpenAI-compatible AI-слой (`ai_usage`), Telegram Stars (`payments`), подписки (`subscriptions`), PDF/изображения, рефералы и админ-панель.

---

## [0.3.3] - 2026-11-21 (Провижининг Firebase Firestore и деплой `firestore.rules`)
### Добавлено
- Подключён Firebase/Firestore в проекте `gen-lang-client-0054273535` (регион `europe-west2`, `firestoreDatabaseId`: `ai-studio-33d72824-acf4-44fb-aa2f-5775f5c6e33f`).
- Создан `firebase-blueprint.json` со схемой сущности `User` и коллекции `/users/{telegramId}`.
- Созданы и развёрнуты строгие серверные правила `firestore.rules` (полный запрет клиентского доступа `allow read, write: if false;` для всех документов и `/users/{telegramId}`).

---

## [0.3.2] - 2026-11-21 (Стабилизация `/start` и защита от `KeyError`)
### Исправлено
- В `app/handlers/start.py`, `app/handlers/profile.py` и `app/handlers/settings.py` устранён риск необработанного `KeyError` при отсутствии `user_service` в `context.bot_data` и гарантирован вызов `query.answer()`.
- В `app/handlers/start.py` расширен перехват ошибок Firebase (`DatabaseConnectionError`, `DatabaseOperationError`, `FirebaseError`, `GoogleAPIError`, `GoogleAuthError`) с безопасным логированием типа ошибки и причины (`cause`).
- В `app/handlers/settings.py` исправлен перехват ошибок БД внутри ветки восстановления `UserNotFoundError`.
- В `app/main.py` создание `Application` перенесено в `try ... finally` для гарантированного вызова `close_firebase()`.

### Добавлено
- Текст `service_unavailable` в `app/utils/texts.py`.
- End-to-end mock-тест маршрутизации `/start` через `Application.process_update()`, тесты сбоя Firebase, отсутствия `UserService`, отсутствия дубликатов при повторном `/start` и порядка инициализации Firebase (`37 passed`, `ruff check .` — 0 ошибок).

---

## [0.3.1] - 2026-11-20 (Firebase Admin `.env` Auth)
### Изменено
- Авторизация Firebase Admin SDK в `app/database/firebase.py` переведена на `google.oauth2.service_account.Credentials.from_service_account_info` исключительно через переменные окружения (`FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_DATABASE_ID`), без файла `firebase-credentials.json`.
- В `app/config.py` добавлена нормализация однострочных `\n` и валидация `FIREBASE_CLIENT_EMAIL` и PEM/base64-формата `FIREBASE_PRIVATE_KEY` (`SecretStr`) без утечки секретов.
- Усилено маскирование усечённых PEM-ключей в `app/utils/sanitizers.py`.
- Обновлены `.env.example` (безопасные заглушки), `README.md` и unit-тесты (`34 passed`, `ruff check .` — 0 ошибок).

---

## [0.3.0] - 2026-11-20 (Этап 1.3)
### Исправлено
- Исправлена ошибка жизненного цикла `Application` в `app/main.py` (удалён некорректный `async with application:` вокруг `start()`, внедрён строгий порядок `updater.stop() → stop() → shutdown() → close_firebase()`).
- В `updater.start_polling()` добавлен `error_callback` для передачи ошибок опроса Telegram в `global_error_handler`.
- Расширен перехват исключений в `app/database/repositories/user_repository.py` (`GoogleAuthError` / `DefaultCredentialsError`, `ValidationError`, `TimeoutError`, `OSError`).
- В `global_error_handler` добавлен вызов `callback_query.answer()` при сбоях внутри inline-кнопок и обработка `InvalidToken` / `Conflict`.
- В `CallbackGuard` (`app/utils/callbacks.py`) добавлена очистка устаревших записей.

### Добавлено
- Обработчик неизвестных slash-команд `unknown_command_handler` (`app/handlers/menu.py`, `app/bot/setup.py`).
- Проверка совпадения `project_id` при повторном использовании Firebase App (`app/database/firebase.py`) и валидация формата `BOT_TOKEN` (`app/config.py`).
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) для Python 3.12, Ruff и pytest.
- Тестовый модуль `tests/test_bot_lifecycle.py` и дополнительные тесты конфигурации и ошибок Firestore (всего 32 passed).

---

## [0.2.0] - 2026-11-20 (Этап 1.2)
### Изменено
- Продукт переименован из `Astro` в **Astralio**.
- Расширены `UserModel`, `UserRepository` и `UserService` полями `interface_language`, `last_activity`, `onboarding_completed`.
- Обновлён `/start` для отображения минималистичного главного меню **Astralio**.

### Добавлено
- Минималистичные inline-клавиатуры, навигация, профиль из Firestore, настройки языка, `CallbackGuard`, `tests/test_navigation_and_profile.py` (24 passed).

---

## [0.1.0] - 2026-11-20 (Этап 1.1)
### Удалено
- Удалена вся инфраструктура React / Vite / TypeScript / Google AI Studio.

### Добавлено
- Python 3.12+ структура, `Settings`, `Loguru`, `FirebaseManager`, `UserRepository`, `UserService`, `/start` и базовые тесты (14 passed).

---

## [0.0.0-init] - 2026-11-20 (Этап 0)
### Добавлено
- Спроектирована архитектура и создана система отчётов `audits/`.
