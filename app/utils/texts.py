"""Minimalist UI texts and extensible multi-language registry for Astralio."""

from dataclasses import dataclass

DEFAULT_LANGUAGE = "ru"


@dataclass(frozen=True, slots=True)
class LanguageMeta:
    """Metadata for a supported or planned interface language."""

    code: str
    label: str
    enabled: bool


# Russian is active in Stage 1.2; English and German slots are prepared for future stages.
LANGUAGES: dict[str, LanguageMeta] = {
    "ru": LanguageMeta(code="ru", label="Русский", enabled=True),
    "en": LanguageMeta(code="en", label="English", enabled=False),
    "de": LanguageMeta(code="de", label="Deutsch", enabled=False),
}

# Extensible message catalog keyed by language code.
# Future "en" and "de" dictionaries can be added here without changing handlers.
TEXTS: dict[str, dict[str, str]] = {
    "ru": {
        "main_menu": (
            "Astralio\n\n"
            "Астрология. Персональные разборы. Прогнозы.\n\n"
            "Выберите раздел."
        ),
        "btn_natal": "Натальная карта",
        "btn_compatibility": "Совместимость",
        "btn_forecasts": "Прогнозы",
        "btn_profile": "Профиль",
        "btn_premium": "Premium",
        "btn_help": "Помощь",
        "btn_back": "Назад",
        "btn_main_menu": "Главное меню",
        "btn_change_language": "Изменить язык",
        "natal_section": (
            "Натальная карта\n\n"
            "Расчёт положения планет, домов и аспектов по дате, времени и месту рождения.\n\n"
            "Раздел находится в разработке."
        ),
        "compatibility_section": (
            "Совместимость\n\n"
            "Анализ синастрии двух людей: сильные стороны союза и зоны внимания.\n\n"
            "Раздел находится в разработке."
        ),
        "forecasts_section": (
            "Прогнозы\n\n"
            "Ежедневные, недельные и месячные прогнозы на основе текущих транзитов.\n\n"
            "Раздел находится в разработке."
        ),
        "premium_section": (
            "Astralio Premium\n\n"
            "Будущие преимущества подписки:\n"
            "• Расширенные персональные разборы\n"
            "• Полная совместимость без ограничений\n"
            "• Персональные транзиты и PDF-отчёты\n\n"
            "Оплата и подключение тарифа появятся на следующих этапах."
        ),
        "help_section": (
            "Помощь\n\n"
            "Astralio — сервис персональной астрологии и прогнозов.\n\n"
            "Как пользоваться ботом:\n"
            "• Откройте главное меню командой /start или кнопками навигации.\n"
            "• В разделе «Профиль» доступны ваши данные и настройка языка.\n"
            "• Новые астрологические разделы добавляются поэтапно."
        ),
        "profile_title": "Профиль",
        "profile_not_set": "Не указан",
        "profile_plan_free": "Базовый",
        "language_title": (
            "Язык интерфейса\n\n"
            "Выберите язык. Сейчас доступен русский язык, "
            "английский и немецкий будут добавлены позже."
        ),
        "language_updated": "Язык интерфейса: Русский",
        "language_planned": "Этот язык появится в следующих обновлениях.",
        "unknown_callback": "Неизвестная команда меню. Используйте актуальные кнопки.",
        "unknown_command": "Неизвестная команда. Используйте /start для открытия главного меню.",
        "db_error": "Временная ошибка сервиса. Пожалуйста, повторите попытку позже.",
        "service_unavailable": "Сервис временно недоступен. Пожалуйста, повторите попытку позже.",
    },
}


def get_texts(language_code: str | None) -> dict[str, str]:
    """Return UI text catalog for language_code, falling back to Russian."""
    if language_code and language_code in TEXTS:
        return TEXTS[language_code]
    return TEXTS[DEFAULT_LANGUAGE]


def get_language_label(language_code: str | None) -> str:
    """Return human-readable language label or 'Не указан'."""
    if not language_code:
        return TEXTS[DEFAULT_LANGUAGE]["profile_not_set"]
    meta = LANGUAGES.get(language_code)
    if meta is not None:
        return meta.label
    return language_code
