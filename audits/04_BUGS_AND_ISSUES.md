# 04. Ошибки, ограничения и технические риски (Bugs & Issues)

---

## 1. Исправленные ошибки (Этап 1.3 и ранее)

| ID | Файл | Описание и причина | Серьёзность | Статус |
| :--- | :--- | :--- | :--- | :--- |
| `BUG-03` | `app/main.py` | Использование `async with application:` вызывало `shutdown()` до `updater.stop()` и `application.stop()` во внешнем `finally:`, провоцируя `RuntimeError: This Application is still running!`. | Critical | `COMPLETED` (исправлено на явный порядок `stop → shutdown`) |
| `BUG-04` | `app/main.py` | `start_polling()` не передавал `error_callback`, из-за чего ошибки опроса Telegram (`Conflict`, `NetworkError`) обходили `global_error_handler`. | High | `COMPLETED` (передаётся `error_callback`) |
| `BUG-05` | `app/database/repositories/user_repository.py` | `DefaultCredentialsError`, `ValidationError`, `TimeoutError` не перехватывались в `UserRepository`, что вызывало необработанное падение `/start` при отсутствии ADC-прав или битом документе. | High | `COMPLETED` |
| `BUG-06` | `app/bot/setup.py` | При ошибке внутри `CallbackQueryHandler` не вызывался `query.answer()`, а неизвестные `/команды` игнорировались без ответа. | Medium | `COMPLETED` |
| `BUG-07` | `app/utils/callbacks.py` | Словарь `CallbackGuard._last_tap` не очищался от старых меток времени при длительной работе. | Low | `COMPLETED` |
| `BUG-01` | `app/utils/sanitizers.py` | Не маскировался токен в URL вида `/bot<id>:<token>`. | High | `COMPLETED` (Этап 1.1) |
| `BUG-02` | `app/database/repositories/user_repository.py` | Передача `telegram_id` в kwargs `update_user` вызывала `TypeError`. | Low | `COMPLETED` (Этап 1.1) |

---

## 2. Оставшиеся ограничения и задачи ручной проверки

| ID | Область | Описание | Серьёзность | Статус |
| :--- | :--- | :--- | :--- | :--- |
| `ISSUE-01` | Облачный Firebase Firestore | Реальные чтение/запись в облаке с настоящим Service Account JSON не проверялись ввиду отсутствия ключей в среде. | High | `NOT_TESTED` |
| `ISSUE-02` | Живой Telegram Bot API | Реальный запуск с настоящим `BOT_TOKEN` и проверка `/start` в клиенте Telegram не выполнялись (логи реального сбоя отсутствуют). | High | `NOT_TESTED` |
| `ISSUE-03` | Языки `en` / `de` | Подготовлены как слоты `enabled=False`; переводы относятся к следующим этапам. | Low | `PLANNED` |
| `ISSUE-04` | Среда контейнера (`.git`) | В текущем контейнере отсутствует `.git`, поэтому SHA коммита и `git diff` недоступны. | Low | Open (ограничение среды) |
