# 01. Архитектура и назначение модулей (Architecture)

> **Продукт:** Astralio (`v0.2.0`)  
> **Статус:** `COMPLETED` для каркаса Этапов 1.1–1.2; доменные расчёты, ИИ и платежи имеют статус `PLANNED`.

---

## 1. Общая структура файлов (Этап 1.2)

```text
astralio/
├── app/
│   ├── __init__.py                          # [COMPLETED] Версия 0.2.0 (Astralio)
│   ├── main.py                              # [COMPLETED] Асинхронный жизненный цикл бота
│   ├── config.py                            # [COMPLETED] Pydantic Settings (.env)
│   ├── logging_config.py                    # [COMPLETED] Loguru + перехват stdlib logging
│   ├── bot/
│   │   ├── __init__.py
│   │   └── setup.py                         # [COMPLETED] Сборка Application, роутинг, error handler
│   ├── database/
│   │   ├── __init__.py
│   │   ├── firebase.py                      # [COMPLETED] Централизованный FirebaseManager
│   │   ├── models.py                        # [COMPLETED] UserModel (+ interface_language, last_activity, onboarding_completed)
│   │   └── repositories/
│   │       ├── __init__.py
│   │       └── user_repository.py           # [COMPLETED] Асинхронный UserRepository
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py                         # [COMPLETED] /start + главное меню
│   │   ├── menu.py                          # [COMPLETED] Разделы, возврат и неизвестные callback
│   │   ├── profile.py                       # [COMPLETED] Профиль пользователя из Firestore
│   │   ├── settings.py                      # [COMPLETED] Настройка языка интерфейса
│   │   └── help.py                          # [COMPLETED] Раздел «Помощь» и /help
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── main_menu.py                     # [COMPLETED] Главное меню InlineKeyboardMarkup
│   │   └── navigation.py                    # [COMPLETED] Кнопка «Назад», профиль, выбор языка
│   ├── services/
│   │   ├── __init__.py
│   │   └── user_service.py                  # [COMPLETED] UserService (регистрация, профиль, смена языка)
│   └── utils/
│       ├── __init__.py
│       ├── callbacks.py                     # [COMPLETED] CallbackGuard (anti-double-tap) и safe_edit_message
│       ├── exceptions.py                    # [COMPLETED] AstralioError и наследники
│       ├── sanitizers.py                    # [COMPLETED] Маскирование секретов и Telegram ID
│       └── texts.py                         # [COMPLETED] Минималистичные тексты и словарь языков (ru + слоты en/de)
├── tests/
│   ├── test_config.py                       # [COMPLETED] Тесты Settings и санитайзеров
│   ├── test_user_repository.py              # [COMPLETED] Тесты Repository, Service, FirebaseManager
│   └── test_navigation_and_profile.py       # [COMPLETED] Тесты меню, навигации, профиля, языка и защиты от повторов
├── audits/                                  # [COMPLETED] Аудиторская документация
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── README.md
└── run.py
```

---

## 2. Архитектура навигации и Callback-роутинга

Все переходы работают через редактирование одного сообщения (`safe_edit_message`) и обязательный `query.answer()`:

- `/start` → регистрирует/синхронизирует пользователя через `UserService`, отправляет главное меню (`Astralio`).
- `menu:natal`, `menu:compatibility`, `menu:forecasts`, `menu:premium` → `section_callback` → информационная страница + кнопка `Назад` (`nav:main`).
- `menu:help` / `/help` → `help_callback` / `help_command` → справка Astralio + кнопка `Назад` (`nav:main`).
- `menu:profile` / `nav:back:profile` → `profile_callback` → чтение `UserModel` из Firestore через `UserService.get_user_profile`, форматирование профиля (`Не указан` при отсутствии данных) + кнопки `Изменить язык` (`settings:language`) и `Назад` (`nav:main`).
- `settings:language` → `language_menu_callback` → выбор языка (`settings:lang:ru`, `settings:lang:en`, `settings:lang:de`) + кнопка `Назад` (`nav:back:profile`).
- Любой неизвестный `callback_data` → `unknown_callback_handler` → краткое уведомление без сбоя.

---

## 3. Схема коллекции `users` в Firestore (обновление Этапа 1.2)

- **Идентификатор документа:** `str(telegram_id)`
- **Поля:** `telegram_id`, `username`, `first_name`, `language_code`, `interface_language` (по умолчанию `"ru"`), `created_at`, `updated_at`, `last_activity`, `onboarding_completed`, `subscription`, `birth_data`.
- Коллекции `payments`, `subscriptions`, `ai_usage` остаются в статусе `PLANNED`.
