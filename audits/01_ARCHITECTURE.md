# 01. Архитектура и назначение модулей (Architecture)

> **Продукт:** Astralio (`v0.3.0`)  
> **Статус:** `COMPLETED` для стабильной основы Этапов 1.1–1.3; доменные модули Этапа 2+ имеют статус `PLANNED`.

---

## 1. Структура файлов проекта

```text
astralio/
├── .github/
│   └── workflows/
│       └── ci.yml                           # [COMPLETED] CI: Python 3.12, Ruff, pytest (без секретов)
├── app/
│   ├── __init__.py                          # [COMPLETED] Версия 0.3.0
│   ├── main.py                              # [COMPLETED] Исправленный async lifecycle и polling error_callback
│   ├── config.py                            # [COMPLETED] Pydantic Settings + проверка формата BOT_TOKEN
│   ├── logging_config.py                    # [COMPLETED] Loguru + перехват stdlib logging
│   ├── bot/
│   │   ├── __init__.py
│   │   └── setup.py                         # [COMPLETED] Команды, unknown_command, callbacks, global_error_handler
│   ├── database/
│   │   ├── __init__.py
│   │   ├── firebase.py                      # [COMPLETED] FirebaseManager (проверка project_id, close)
│   │   ├── models.py                        # [COMPLETED] UserModel + PLANNED_COLLECTIONS
│   │   └── repositories/
│   │       ├── __init__.py
│   │       └── user_repository.py           # [COMPLETED] Async UserRepository через asyncio.to_thread
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py                         # [COMPLETED] /start + главное меню
│   │   ├── menu.py                          # [COMPLETED] Разделы, nav:main, unknown_callback, unknown_command
│   │   ├── profile.py                       # [COMPLETED] Профиль пользователя из Firestore
│   │   ├── settings.py                      # [COMPLETED] Настройка языка интерфейса
│   │   └── help.py                          # [COMPLETED] Раздел «Помощь» и /help
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── main_menu.py
│   │   └── navigation.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── user_service.py
│   └── utils/
│       ├── __init__.py
│       ├── callbacks.py                     # [COMPLETED] CallbackGuard (с очисткой кэша) и safe_edit_message
│       ├── exceptions.py
│       ├── sanitizers.py
│       └── texts.py
├── tests/
│   ├── test_bot_lifecycle.py                # [COMPLETED] Тесты startup/shutdown, unknown_command, error_handler
│   ├── test_config.py
│   ├── test_navigation_and_profile.py
│   └── test_user_repository.py
├── audits/
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── README.md
└── run.py
```

---

## 2. Порядок жизненного цикла и регистрации обработчиков (`app/main.py`, `app/bot/setup.py`)

1. **Startup:** `load_settings()` → `setup_logging()` → `init_firebase(settings)` → `UserRepository(db_client)` → `UserService` → `create_application()` → `application.initialize()` → `application.start()` → `application.updater.start_polling(..., error_callback=...)`.
2. **Порядок хендлеров в группе `0`:**
   - `CommandHandler("start", start_handler)`
   - `CommandHandler("help", help_command)`
   - `MessageHandler(filters.COMMAND, unknown_command_handler)` (перехватывает неизвестные `/команды`)
   - Специфичные `CallbackQueryHandler` (`nav:main`, `menu:...`, `settings:...`)
   - Fallback `CallbackQueryHandler(unknown_callback_handler)` (строго последним)
3. **Graceful Shutdown (`finally`):** `updater.stop()` → `application.stop()` → `application.shutdown()` → `close_firebase()`.
