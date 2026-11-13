"""SQLite-хранилище запрещённых слов с начальной загрузкой старого списка."""

import json
import logging
import os
import sqlite3


log = logging.getLogger("vahter.words")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DATABASE_PATH = os.path.join(DATA_DIR, "forbidden_words.sqlite3")
LEGACY_EXTRA_WORDS_FILE = os.path.join(DATA_DIR, "extra_words.json")

# Исходный набор загружается в БД только один раз при её создании.
BASE_WORDS = (
    "арбитраж криптовалют",
    "с прибылью 5-8%",
    "начальный депозит",
    "заработать от 100 $ usdt в день",
    "беру 20% от вашего ежедневного заработка",
    "не принимаю ваши деньги на свои счета",
    "это не трейдинг и не работа по сигналам",
    "набираю даже людей без опыта",
    "пассивный доход",
    "профит до +60% в месяц",
    "бесплатное обучение",
    "таргетированная реклама",
    "продам баты",
    "криптовалюта",
    "доходность",
    "криптошкола",
    "вебинар по работе с цифровой валютой",
    "airdrop page for proximax",
    "создать кошелек на sirius chain",
    "мероприятие необычного формата",
    "лиды на недвижимость",
    "хакеры",
    "взломы",
    "what''s app",
    "instagram",
    "viber",
    "вконтакте",
    "telegram",
    "mail",
    "такси через приложение tappy rent",
    "онлайн тренер и диетолог",
    "elf bar с доставкой по паттайе",
    "свободны к сдаче",
    "трансфер в аэропорт",
    "аренда авто, байки",
    "страхование здоровья в тае",
    "обмен валюты",
    "поменяю ваши безналичные рубли и usdt на баты",
    "работа в команде в сфере криптовалюты",
    "парень для постоянных съемок",
    "приглашаю съездить в камбоджу за штампом",
    "ремонт компьютеров,ноутбуков, диагностика, чистка",
    "устанавливаю очень удобное приложение для просмотра фильмов",
    "устанавливаю российское телевидение",
    "друзья напоминаю что у нас есть возможность выкупать брони с agoda.com",
    "статика и анимированные стикеры для телеграм",
    "разработка персональных маркетинговых материалов и маркетинг-плана",
    "нейромаркетинг (продвижение вас как эксперта в телеграм)",
    "tochka co., ltd. ищет учителей на 2023-2024 учебный год",
    "без опыта работы",
    "зарплата в таиланде и вьетнаме",
    "помощь в поиске бюджетного жилья",
    "годовой контракт с рабочей визой",
    "срочно продается",
    "кофешоп",
    "авто в аренду",
    "vip проход",
    "студенческая виза",
    "non-o, non-b",
    "рабочая виза",
    "туристическая виза",
    "штамп на 30 дней",
    "юридические услуги",
    "smm продвижение",
    "накрутка",
    "создание сайтов",
    "работа",
    "удаленная",
    "подработка",
    "прибыль",
    "сдам",
    "продам",
    "аренда",
    "апартаменты",
    "квартира",
    "байк",
    "машина",
    "мопед",
    "рубли онлайн",
    "машину",
    "экскурсии",
    "пересдам",
    "smm",
    "штамп",
    "vip",
    "тренера",
    "тренер",
    "репетитор",
    "репетитора",
    "няни",
    "услуга",
    "услуги",
    "няня",
    "такси",
    "разработка",
    "устанавливаю",
    "ремонт",
    "студенческая",
    "за визой",
    "визаран",
    "бордеран",
    "бордер",
    "приглашаю",
    "поменяю",
    "квартиру",
    "арбитраж",
    "крипта",
    "криптовалюты",
    "криптовалюту",
    "crypto",
    "usdt",
    "крипто",
    "трейдинг",
    "трейдер",
    "профит",
    "доход",
    "набираю",
    "обучение",
    "обучаю",
    "rent",
)


def _normalize(word):
    return word.strip().casefold()


def _insert_words(connection, words, source):
    rows = []
    for word in words:
        if not isinstance(word, str):
            continue
        normalized = _normalize(word)
        if normalized:
            rows.append((normalized, word.strip(), source))
    connection.executemany(
        "INSERT OR IGNORE INTO forbidden_words (normalized, word, source) "
        "VALUES (?, ?, ?)",
        rows,
    )


def initialize_word_db():
    """Создаёт SQLite-БД и один раз переносит начальные и JSON-слова."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH, timeout=30) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS forbidden_words ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "normalized TEXT NOT NULL UNIQUE, "
            "word TEXT NOT NULL, "
            "source TEXT NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )

        seeded = connection.execute(
            "SELECT 1 FROM settings WHERE key = 'base_words_seeded'"
        ).fetchone()
        if not seeded:
            _insert_words(connection, BASE_WORDS, "base")
            connection.execute(
                "INSERT INTO settings (key, value) VALUES ('base_words_seeded', '1')"
            )

        migrated = connection.execute(
            "SELECT 1 FROM settings WHERE key = 'legacy_json_migrated'"
        ).fetchone()
        if not migrated:
            try:
                with open(LEGACY_EXTRA_WORDS_FILE, encoding="utf-8") as file:
                    legacy_words = json.load(file)
                if not isinstance(legacy_words, list):
                    legacy_words = []
            except FileNotFoundError:
                legacy_words = []
            except (json.JSONDecodeError, OSError) as error:
                log.warning("Не удалось прочитать старый список слов: %s", error)
                legacy_words = []

            _insert_words(connection, legacy_words, "legacy")
            connection.execute(
                "INSERT INTO settings (key, value) "
                "VALUES ('legacy_json_migrated', '1')"
            )


def get_forbidden_words():
    """Возвращает слова из SQLite в порядке добавления."""
    with sqlite3.connect(DATABASE_PATH, timeout=30) as connection:
        rows = connection.execute(
            "SELECT normalized FROM forbidden_words ORDER BY id"
        ).fetchall()
    return [row[0] for row in rows]


def add_forbidden_words(words):
    """Добавляет слова и возвращает (добавленные, уже существующие)."""
    added, skipped = [], []
    with sqlite3.connect(DATABASE_PATH, timeout=30) as connection:
        for word in words:
            value = word.strip()
            normalized = _normalize(value)
            if not normalized:
                continue
            cursor = connection.execute(
                "INSERT OR IGNORE INTO forbidden_words (normalized, word, source) "
                "VALUES (?, ?, 'command')",
                (normalized, value),
            )
            if cursor.rowcount:
                added.append(value)
            else:
                skipped.append(value)
    return added, skipped
