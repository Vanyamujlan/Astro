# 06. Внешние API и интеграции (API Integrations)

> **Статус документа:** Актуализирован для Этапа 1.3. Новые внешние API не добавлялись.

---

## 1. Подключённые интеграции

### 1.1. Telegram Bot API (`python-telegram-bot==22.8`)
- **Модули:** `app/main.py`, `app/bot/setup.py`, `app/handlers/*`, `app/keyboards/*`.
- **Обработка ошибок:** `InvalidToken`, `Conflict`, `RetryAfter`, `Forbidden`, `TimedOut`, `NetworkError`, `BadRequest("Message is not modified")`, `error_callback` в `start_polling()`.
- **Статус:** Код и mock-тесты завершены (`COMPLETED`), живое подключение к серверам Telegram — `NOT_TESTED`.

### 1.2. Firebase Cloud Firestore (Native mode) (`firebase-admin==6.9.0`)
- **Модули и файлы:** `app/database/firebase.py`, `app/database/models.py`, `app/database/repositories/user_repository.py`, `firebase-blueprint.json`, `firestore.rules`.
- **Подготовленный ресурс AI Studio Firebase:**
  - `projectId`: `gen-lang-client-0054273535` (регион `europe-west2`)
  - `firestoreDatabaseId`: `ai-studio-33d72824-acf4-44fb-aa2f-5775f5c6e33f`
  - Правила безопасности `firestore.rules` развёрнуты (`allow read, write: if false;` для клиентских SDK; доступ только через серверный Admin SDK).
- **Особенности:**
  - Авторизация через `google.oauth2.service_account.Credentials.from_service_account_info` из переменных окружения (`FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_DATABASE_ID`) без JSON-файла.
  - Блокирующие операции вынесены в `asyncio.to_thread(...)`.
  - Проверка совпадения `project_id` и поддержка `FIREBASE_DATABASE_ID`.
  - Перехват `FirebaseError`, `GoogleAPIError`, `GoogleAuthError`, `ValidationError`, `TimeoutError`, `OSError`.
- **Статус:** Подготовка базы и деплой правил завершены (`COMPLETED`), живой запуск Python-бота с реальными `.env`-секретами — `NOT_TESTED`.

---

## 2. Запланированные интеграции (`PLANNED` — Этап 2+)
- `pyswisseph`, `Pillow`, `ReportLab`, OpenAI-compatible LLM API, Telegram Stars (`XTR`).
