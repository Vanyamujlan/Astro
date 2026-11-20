# 07. Аудит лицензий и зависимостей (License Audit)

> **Статус:** `COMPLETED` (актуализирован на Этапе 1.3 — состав runtime и dev зависимостей не менялся).

---

## 1. Зависимости проекта (`requirements.txt`)

| Пакет | Версия в `.venv` | Лицензия | Статус |
| :--- | :--- | :--- | :--- |
| `python-telegram-bot` | `22.8` | `LGPL-3.0-only` | `COMPLETED` (используется как внешняя библиотека без модификации) |
| `firebase-admin` | `6.9.0` | `Apache-2.0` | `COMPLETED` |
| `pydantic` | `2.14.4` | `MIT` | `COMPLETED` |
| `pydantic-settings` | `2.16.3` | `MIT` | `COMPLETED` |
| `python-dotenv` | `1.2.4` | `BSD-3-Clause` | `COMPLETED` |
| `loguru` | `0.8.0` | `MIT` | `COMPLETED` |
| `pytest` (dev/CI) | `8.4.2` | `MIT` | `COMPLETED` |
| `pytest-asyncio` (dev/CI) | `0.26.0` | `Apache-2.0` | `COMPLETED` |
| `ruff` (dev/CI) | `0.17.6` | `MIT` | `COMPLETED` |

---

## 2. Вывод
- Новые зависимости на Этапе 1.3 не добавлялись (`SQLite`, `SQLAlchemy`, `React`, `Vite`, `pyswisseph`, AI SDK отсутствуют).
- Все лицензии совместимы с коммерческой разработкой и распространением Astralio.
