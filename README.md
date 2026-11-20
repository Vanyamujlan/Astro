# Astralio — Коммерческий астрологический Telegram-бот (Этап 1.2)

Минималистичная астрологическая платформа на **Python 3.12+**, `python-telegram-bot` (async) и **Firebase Cloud Firestore** (Native mode через Firebase Admin SDK).

> **Текущий этап:** 1.2 — минималистичное главное меню, inline-навигация, профиль пользователя из Firestore, настройка языка интерфейса и разделы-заглушки («Натальная карта», «Совместимость», «Прогнозы», «Premium», «Помощь»).  
> Астрологические расчёты (`pyswisseph`), ИИ-интерпретации и платежи (Telegram Stars) относятся к следующим этапам.

---

## Структура проекта

```text
astralio/
├── app/
│   ├── main.py                 # Точка сборки и запуска жизненного цикла бота
│   ├── config.py               # Конфигурация через Pydantic Settings (.env)
│   ├── logging_config.py       # Централизованное логирование (Loguru + маскирование секретов)
│   ├── bot/
│   │   └── setup.py            # Создание Telegram Application, роутинг хендлеров и error handler
│   ├── database/
│   │   ├── firebase.py         # Инициализация Firebase Admin SDK и доступ к Firestore
│   │   ├── models.py           # Схемы документов Firestore (users + чертёж будущих коллекций)
│   │   └── repositories/
│   │       └── user_repository.py  # Асинхронный репозиторий пользователей (asyncio.to_thread)
│   ├── handlers/
│   │   ├── start.py            # /start и вывод главного меню
│   │   ├── menu.py             # Навигация по разделам, возврат и неизвестные callback
│   │   ├── profile.py          # Профиль пользователя из Firestore
│   │   ├── settings.py         # Смена языка интерфейса (ru + архитектура под en/de)
│   │   └── help.py             # Раздел «Помощь» и команда /help
│   ├── keyboards/
│   │   ├── main_menu.py        # Главное меню InlineKeyboardMarkup
│   │   └── navigation.py       # Кнопки «Назад», профиля и выбора языка
│   ├── services/
│   │   └── user_service.py     # Регистрация, синхронизация профиля и смена языка
│   └── utils/
│       ├── callbacks.py        # Защита от повторных нажатий и безопасное редактирование сообщений
│       ├── exceptions.py       # Доменные исключения приложения
│       ├── sanitizers.py       # Маскирование токенов и персональных данных в логах
│       └── texts.py            # Минималистичные тексты и словарь локализации
├── tests/
│   ├── test_config.py          # Тесты конфигурации и валидации секретов
│   ├── test_user_repository.py # Тесты UserRepository, UserService и FirebaseManager
│   └── test_navigation_and_profile.py # Тесты /start, меню, навигации, профиля и смены языка
├── audits/                     # Независимая аудиторская документация проекта
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── run.py                      # Скрипт запуска бота
```

---

## Быстрый старт

### 1. Создание виртуального окружения (Python 3.12+)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
```

Заполните `BOT_TOKEN`, `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY` (и при необходимости `FIREBASE_DATABASE_ID`).

### 3. Запуск и проверка

```bash
python run.py
pytest
ruff check .
```
