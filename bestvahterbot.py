from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import json
import logging
import os
import re
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    # Fallback: простой парсинг .env, если python-dotenv не установлен
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN не найден. Создайте файл .env (см. .env.example) рядом с ботом.")

from bestvahterbot_words import (
    add_forbidden_words,
    get_forbidden_words,
    initialize_word_db,
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vahter")

# --- Учёт чатов, в которых работает бот ---
# Telegram Bot API не даёт списка чатов, поэтому запоминаем чаты,
# из которых видели сообщения. Список хранится в data/chats.json (volume).
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CHATS_FILE = os.path.join(DATA_DIR, "chats.json")


def load_chats():
    try:
        with open(CHATS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_chats():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = CHATS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(known_chats, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CHATS_FILE)
    except Exception as e:
        log.warning("Не удалось сохранить список чатов: %s", e)


known_chats = load_chats()


def remember_chat(message: types.Message):
    chat = message.chat
    known_chats[str(chat.id)] = {
        "type": chat.type,
        "title": chat.title or chat.username or chat.first_name or "",
        "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_chats()


# --- Запрещённые слова хранятся в SQLite в каталоге data/ ---
initialize_word_db()
FORBIDDEN = get_forbidden_words()


@dp.message_handler(commands=["add"])
async def cmd_add(message: types.Message):
    """Добавляет запрещённые слова. Доступно только администратору."""
    remember_chat(message)
    if not message.from_user or message.from_user.id != ADMIN_CHAT_ID:
        await message.reply("⛔ Эта команда доступна только администратору.")
        return
    args = message.get_args()
    if not args or not args.strip():
        await message.reply("Использование: /add слово1, слово2, слово3\n"
                            "Слова разделяйте запятыми или переносами строк.")
        return
    new_words = [w.strip() for w in re.split(r"[,\n;]+", args) if w.strip()]
    added, skipped = add_forbidden_words(new_words)
    if added:
        FORBIDDEN.extend(w.casefold() for w in added)
    parts = []
    if added:
        parts.append("✅ Добавлено слов: {} ({})".format(len(added), ", ".join(added)))
    if skipped:
        parts.append("⏭ Уже были в списке: {} ({})".format(len(skipped), ", ".join(skipped)))
    parts.append("📋 Всего слов в списке: {}".format(len(FORBIDDEN)))
    await message.reply("\n".join(parts))


START_MESSAGE = (
    "👋 Привет! Я бот-вахтёр 🛡\n\n"
    "Что я делаю в чатах:\n"
    "• 🧹 удаляю сообщения с запрещёнными словами ({words_count} слов в списке);\n"
    "• 🈲 удаляю сообщения с китайскими иероглифами;\n"
    "• 🚪 удаляю системные сообщения (вход/выход из группы, закрепление и т.п.);\n"
    "• 📨 уведомляю администратора о каждом удалении.\n\n"
    "👀 Сейчас я слежу за {total} чат(ами): {groups} групп(ы), {privates} личных."
)


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    remember_chat(message)
    groups = sum(1 for c in known_chats.values() if c.get("type") in ("group", "supergroup"))
    privates = len(known_chats) - groups
    await message.reply(
        START_MESSAGE.format(words_count=len(FORBIDDEN), total=len(known_chats),
                             groups=groups, privates=privates)
    )


# Системные (сервисные) сообщения, которые удаляем:
SYSTEM_MESSAGE_TYPES = [
    types.ContentType.NEW_CHAT_MEMBERS,              # вход в группу
    types.ContentType.LEFT_CHAT_MEMBER,              # выход из группы
    types.ContentType.PINNED_MESSAGE,                # закрепление сообщения
    types.ContentType.NEW_CHAT_TITLE,                # смена названия группы
    types.ContentType.NEW_CHAT_PHOTO,                # смена фото группы
    types.ContentType.DELETE_CHAT_PHOTO,             # удаление фото группы
    types.ContentType.GROUP_CHAT_CREATED,            # создана группа
    types.ContentType.MIGRATE_TO_CHAT_ID,            # миграция в супергруппу
    types.ContentType.MIGRATE_FROM_CHAT_ID,          # миграция из группы
    types.ContentType.MESSAGE_AUTO_DELETE_TIMER_CHANGED,  # изменён таймер автоудаления
    types.ContentType.PROXIMITY_ALERT_TRIGGERED,     # предупреждение о близости
    types.ContentType.VIDEO_CHAT_SCHEDULED,          # запланирован видеочат
    types.ContentType.VIDEO_CHAT_STARTED,            # начался видеочат
    types.ContentType.VIDEO_CHAT_ENDED,              # закончился видеочат
    types.ContentType.VIDEO_CHAT_PARTICIPANTS_INVITED,  # приглашение в видеочат
    types.ContentType.VOICE_CHAT_SCHEDULED,          # (старое имя) запланирован войсчат
    types.ContentType.VOICE_CHAT_STARTED,            # (старое имя) начался войсчат
    types.ContentType.VOICE_CHAT_ENDED,              # (старое имя) закончился войсчат
    types.ContentType.VOICE_CHAT_PARTICIPANTS_INVITED,  # (старое имя) приглашение в войсчат
    types.ContentType.FORUM_TOPIC_CREATED,           # создана тема форума
    types.ContentType.FORUM_TOPIC_CLOSED,            # закрыта тема форума
    types.ContentType.FORUM_TOPIC_REOPENED,          # переоткрыта тема форума
    types.ContentType.FORUM_TOPIC_EDITED,            # изменена тема форума
    types.ContentType.GENERAL_FORUM_TOPIC_HIDDEN,    # скрыта General-тема
    types.ContentType.GENERAL_FORUM_TOPIC_UNHIDDEN,  # показана General-тема
    types.ContentType.WRITE_ACCESS_ALLOWED,          # разрешён доступ к веб-приложению
    types.ContentType.USER_SHARED,                   # передан контакт пользователя (кнопкой)
    types.ContentType.CHAT_SHARED,                   # передан чат (кнопкой)
]


@dp.message_handler(content_types=SYSTEM_MESSAGE_TYPES)
async def delete_system_message(message: types.Message):
    # Удаляем системные сообщения: вход/выход из группы, закрепление и т.п.
    remember_chat(message)
    log.info("Удаляю системное сообщение: content_type=%s chat_id=%s",
             message.content_type, message.chat.id)
    try:
        await message.delete()
    except Exception as e:
        log.warning("Не удалось удалить системное сообщение: %s", e)


# --- Детект китайских иероглифов (CJK) ---
# Проверяем кодовые точки: иероглифы и CJK-пунктуация.
# Тайский (U+0E00-0E7F), лаосский (U+0E80-0EFF) и прочие письменности НЕ считаются китайскими.

def is_cjk_char(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x3400 <= cp <= 0x4DBF or      # CJK Extension A
        0x4E00 <= cp <= 0x9FFF or      # CJK Unified Ideographs (основной блок)
        0xF900 <= cp <= 0xFAFF or      # CJK Compatibility Ideographs
        0x2E80 <= cp <= 0x2EFF or      # CJK радикалы
        0x3000 <= cp <= 0x303F or      # CJK пунктуация (。，《》 и т.п.)
        0x31C0 <= cp <= 0x31EF or      # CJK штрихи
        0x20000 <= cp <= 0x3134F       # CJK Extensions B-F
    )


def contains_cjk(text: str) -> bool:
    return any(is_cjk_char(ch) for ch in text)


@dp.message_handler(content_types=types.ContentType.TEXT)
async def echo(message: types.Message):
    # Проверяем все сообщения по списку слов, загруженному из SQLite.
    if not message.text:
        return
    remember_chat(message)
    if contains_cjk(message.text):
        log.info("Удаляю сообщение с китайскими иероглифами: chat_id=%s message_id=%s",
                 message.chat.id, message.message_id)
        try:
            await bot.delete_message(message.chat.id, message.message_id)
            text_preview = message.text[:500] + ("…" if len(message.text) > 500 else "")
            await bot.send_message(ADMIN_CHAT_ID, text="Удалено сообщение с китайскими иероглифами: " + text_preview)
        except Exception as e:
            log.warning("Ошибка при удалении сообщения с иероглифами: %s", e)
        return
    await forbidden_msg(message)

async def forbidden_msg(message: types.Message):
    if not message.text:
        return
    text_lower = message.text.casefold()
    for word in FORBIDDEN:
        if word in text_lower:
            print("Есть такое слово")
            await forward_message_to_admin(message)

async def forward_message_to_admin(message: types.Message):
    # Пересылаем сообщение администратору
    print("пересылаем администратору message.message_id = ", message.message_id)
    # Создаем кнопку "Удалить" для сообщения
    await bot.send_message(ADMIN_CHAT_ID, text="Удалено сообщение: "+ message.text)
   #  await message.delete()  # Удаляем сообщение в чате
    await bot.delete_message(message.chat.id, message.message_id)
    # Отправляем сообщение 
    print("Удалено сообщение:")
    print("message.chat.id =", message.chat.id)
    print("message.message_id = ", message.message_id)
    print("message.text = ", message.text)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
