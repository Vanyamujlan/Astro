# 00. Обзор проекта (Project Overview)

> **Название продукта:** Astralio  
> **Статус этапа 1.3:** `COMPLETED` *(диагностика `/start`, исправление жизненного цикла `run_bot`, усиление обработки ошибок Firebase/Telegram, CI GitHub Actions и 32 unit-теста выполнены; живое подключение к Telegram Bot API и облачному Firebase Firestore остаётся `NOT_TESTED` из-за отсутствия секретов и логов реального запуска в среде).*  
> **Текущая версия:** `0.3.0`  
> **Целевая платформа:** Python 3.12+ (проверено в `.venv` на CPython `3.12.16`)

---

## 1. Описание проекта

**Astralio** — минималистичный коммерческий астрологический Telegram-бот на Python 3.12+ и **Firebase Cloud Firestore (Native mode)**.

На **Этапе 1.3** проведена глубокая диагностика команды `/start` и устойчивости приложения: исправлены ошибки асинхронного жизненного цикла `python-telegram-bot`, перехват ошибок polling (`error_callback`), обработка `DefaultCredentialsError` и повреждённых документов в `UserRepository`, добавлен обработчик неизвестных команд и настроен GitHub Actions CI.

---

## 2. Статус функционала (Реализовано vs Запланировано)

### Реализовано (`COMPLETED`)
- **Этап 1.1:** Python 3.12+ каркас, `pydantic-settings`, `loguru`, централизованный `FirebaseManager` (`firebase-admin`), `UserRepository` (`users`), `UserService`.
- **Этап 1.2:** Переименование в **Astralio**, минималистичное главное меню, inline-навигация, профиль из Firestore (`Не указан` для пустых полей), настройка языка (`ru` активен; `en`/`de` подготовлены), `CallbackGuard`.
- **Этап 1.3 (Stability & Hardening):**
  - Исправлен асинхронный порядок остановки `Application` в `app/main.py` (`updater.stop()` → `app.stop()` → `app.shutdown()` → `close_firebase()`).
  - Подключён `error_callback` для `updater.start_polling()` с передачей ошибок в `global_error_handler` (включая `InvalidToken`, `Conflict`).
  - Расширен перехват исключений в `UserRepository` (`GoogleAuthError` / `DefaultCredentialsError`, `ValidationError`, `TimeoutError`, `OSError`).
  - Проверка совпадения `project_id` в `FirebaseManager` и валидация формата `BOT_TOKEN` в `Settings`.
  - Обработчик неизвестных команд (`unknown_command_handler`), снятие спиннера callback-кнопок при ошибках, ограничение роста кэша `CallbackGuard`.
  - GitHub Actions CI workflow (`.github/workflows/ci.yml`: Python 3.12, `ruff`, `pytest`).
  - Автотесты `pytest` (`32 passed`) и проверка `ruff check .` (0 ошибок).

### Запланировано (`PLANNED` — Этап 2+)
- Ввод и сохранение данных рождения (`birth_data`).
- Астрономические расчёты (`pyswisseph`), графика (`Pillow`), PDF (`ReportLab`).
- OpenAI-compatible AI-слой (`ai_usage`), Telegram Stars (`payments`), подписки (`subscriptions`), рефералы и админ-панель.
