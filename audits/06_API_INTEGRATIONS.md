# 06. Внешние API и интеграции (API Integrations)

> **Статус документа:** Актуализирован для Этапа 1.1.

---

## 1. Подключённые интеграции (Этап 1.1)

### 1.1. Telegram Bot API
- **Библиотека:** `python-telegram-bot==22.8` (async).
- **Точка настройки:** `app/bot/setup.py`, `app/main.py`, `app/handlers/start.py`.
- **Используемые возможности:**
  - `ApplicationBuilder().token(...)`
  - `CommandHandler("start", start_handler)`
  - `application.updater.start_polling(allowed_updates=Update.ALL_TYPES)`
  - `application.add_error_handler(global_error_handler)`
- **Переменные окружения:** `BOT_TOKEN` (секрет, обязательна).
- **Статус:** Код реализован (`COMPLETED`), живой запуск против серверов Telegram — `NOT_TESTED` (нет токена в окружении).

### 1.2. Firebase Cloud Firestore (Native mode) через Firebase Admin SDK
- **Библиотека:** `firebase-admin==6.9.0` (`google-cloud-firestore==2.34.1`).
- **Точка настройки:** `app/database/firebase.py` (`FirebaseManager`).
- **Используемые возможности:**
  - `firebase_admin.initialize_app(credential=..., options={"projectId": ...})` с проверкой `firebase_admin.get_app()` против дублирования.
  - `firebase_admin.firestore.client(app=app, database_id=...)`.
  - Серверные операции коллекции `users` через `asyncio.to_thread(...)` (`doc_ref.get()`, `doc_ref.create()`, `doc_ref.update()`).
- **Переменные окружения:**
  - `FIREBASE_PROJECT_ID` (обязательна)
  - `FIREBASE_CREDENTIALS_PATH` (опциональна при наличии ADC в облаке; обязательна локально)
  - `FIREBASE_DATABASE_ID` (опциональна; пусто или `(default)` -> база по умолчанию)
- **Статус:** Код и mock-тесты реализованы (`COMPLETED`), живое облачное подключение — `NOT_TESTED`.

---

## 2. Запланированные интеграции (`PLANNED` — НЕ подключены на Этапе 1.1)

- **OpenAI-compatible LLM API** — генерация текстовых интерпретаций (`PLANNED`).
- **Telegram Stars (`XTR`)** — приём платежей и подписок (`PLANNED`).
- **Swiss Ephemeris (`pyswisseph`), `Pillow`, `ReportLab`** — локальные вычисления и генерация отчётов (`PLANNED`).
