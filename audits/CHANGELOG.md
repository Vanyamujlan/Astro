# История изменений (CHANGELOG)

Все значимые изменения проекта фиксируются в этом файле.  
**Правило:** история предыдущих версий и записей не удаляется и не переписывается задним числом.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

---

## [Unreleased]
### Запланировано (`PLANNED`)
- Этап 1.3+: Ввод и хранение данных рождения (`birth_data`), локальные расчёты (`pyswisseph`), OpenAI-compatible AI-слой (`ai_usage`), Telegram Stars (`payments`), подписки (`subscriptions`), PDF/изображения, реферальная система, админ-панель.

---

## [0.2.0] - 2026-11-20 (Этап 1.2)
### Изменено
- Продукт переименован из `Astro` в **Astralio** во всех пользовательских сообщениях, метаданных (`pyproject.toml`, `README.md`, `app/__init__.py`, `app/main.py`, `run.py`) и базовом исключении `AstralioError`.
- Расширены `UserModel` (`app/database/models.py`), `UserRepository` (`app/database/repositories/user_repository.py`) и `UserService` (`app/services/user_service.py`) полями `interface_language`, `last_activity`, `onboarding_completed`, а также методами `get_user_profile()` и `change_interface_language()`.
- Обновлён `/start` (`app/handlers/start.py`) для отображения минималистичного главного меню **Astralio**.

### Добавлено
- Минималистичные inline-клавиатуры (`app/keyboards/main_menu.py`, `app/keyboards/navigation.py`).
- Обработчики навигации и разделов (`app/handlers/menu.py`, `app/handlers/profile.py`, `app/handlers/settings.py`, `app/handlers/help.py`), включая обработку неизвестных `callback_data`.
- Защита от повторных нажатий (`CallbackGuard`) и безопасное редактирование сообщений (`safe_edit_message`) в `app/utils/callbacks.py`.
- Централизованный словарь текстов и расширяемая языковая архитектура (`ru` активен; `en`, `de` подготовлены) в `app/utils/texts.py`.
- Набор тестов `tests/test_navigation_and_profile.py` (всего 24 passed) и актуализация документации `audits/`.

---

## [0.1.0] - 2026-11-20 (Этап 1.1)
### Удалено
- Удалена вся инфраструктура стартового шаблона React / Vite / TypeScript / Google AI Studio (`package.json`, `bun.lock`, `node_modules/`, `index.html`, `metadata.json`, `tsconfig.json`, `vite.config.ts`, `src/`).

### Добавлено
- Полноценная структура Python 3.12+ проекта (`app/`, `tests/`, `run.py`, `requirements.txt`, `pyproject.toml`, `README.md`).
- Конфигурация `app/config.py` на `pydantic-settings` + обновлённый шаблон `.env.example` и защищённый `.gitignore`.
- Централизованное логирование `app/logging_config.py` на `loguru` с маскированием секретов и `telegram_id` (`app/utils/sanitizers.py`).
- Иерархия доменных исключений (`app/utils/exceptions.py`).
- Централизованное подключение к Firebase Cloud Firestore (Native mode) через Firebase Admin SDK (`app/database/firebase.py`).
- Схема коллекции `users` и чертёж будущих коллекций (`app/database/models.py`).
- Асинхронный `UserRepository` (`app/database/repositories/user_repository.py`) с атомарным созданием и выносом синхронных вызовов Firestore в `asyncio.to_thread`.
- Сервис `UserService` (`app/services/user_service.py`), команда `/start` (`app/handlers/start.py`), сборка и глобальная обработка ошибок (`app/bot/setup.py`, `app/main.py`).
- Комплект unit-тестов (`tests/test_config.py`, `tests/test_user_repository.py`: 14 passed) и настройка `ruff` (0 ошибок).
- Документ `audits/07_LICENSE_AUDIT.md` и актуализация всех отчётов в `audits/`.

### Исправлено
- Исправлено регулярное выражение в `app/utils/sanitizers.py` для маскирования Telegram-токенов внутри URL вида `/bot<id>:<token>`.
- Параметр `telegram_id` в `UserRepository.update_user` сделан positional-only для корректной валидации запрещённых kwargs.

---

## [0.0.0-init] - 2026-11-20 (Этап 0)
### Добавлено
- Спроектирована слоистая модульная архитектура коммерческой астрологической Telegram-платформы.
- Создана папка `audits/` и комплект документов для независимого технического аудита.
