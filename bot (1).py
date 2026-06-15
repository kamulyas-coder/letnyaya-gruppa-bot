"""
Главный файл бота — Летняя группа целей 2026.

Функции:
- Читает ВСЕ сообщения чата (работает как админ)
- Трекает активность, streak, очки участников
- Еженедельный дайджест каждое воскресенье в 19:00 МСК
- Команды: /start, /digest, /streak, /mystats, /goals
"""

import logging
import os
from datetime import time as dtime

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tracker import record_message, get_member_stats
from digest import build_weekly_digest, build_streak_only
from sheets import get_all_participants

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DIGEST_DAY = int(os.getenv("DIGEST_DAY", "6"))    # 6 = воскресенье
DIGEST_HOUR = int(os.getenv("DIGEST_HOUR", "19"))  # 19:00 МСК = 16:00 UTC
DIGEST_MINUTE = int(os.getenv("DIGEST_MINUTE", "0"))

# UTC = МСК - 3
DIGEST_HOUR_UTC = (DIGEST_HOUR - 3) % 24


# ──────────────────────────────────────────────
# ОБРАБОТЧИКИ КОМАНД
# ──────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и вывод chat_id."""
    chat = update.effective_chat
    msg = (
        f"Привет! Я бот Летней группы целей 2026.\n\n"
        f"Слежу за активностью в чате, считаю streak и каждое воскресенье "
        f"отправляю дайджест с прогрессом группы.\n\n"
        f"Chat ID этой группы: {chat.id}\n"
        f"(сохрани в переменную TELEGRAM_CHAT_ID на Railway)\n\n"
        f"Команды:\n"
        f"/digest - дайджест прямо сейчас\n"
        f"/streak - таблица активности\n"
        f"/mystats - твоя статистика\n"
        f"/goals - цели участников из таблицы"
    )
    await update.message.reply_text(msg)


async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос дайджеста вручную."""
    await update.message.reply_text("Собираю данные...")
    try:
        text = build_weekly_digest()
        await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Ошибка дайджеста: {e}")
        await update.message.reply_text(f"Ошибка: {e}")


async def cmd_streak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Таблица streak'ов."""
    text = build_streak_only()
    await update.message.reply_text(text)


async def cmd_mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика вызвавшего команду."""
    user = update.effective_user
    stats = get_member_stats(user.id)
    if not stats:
        await update.message.reply_text(
            "Ты пока не попал в базу. Напиши что-нибудь в чат!"
        )
        return

    emoji = streak_emoji_plain(stats["streak"])
    text = (
        f"Твоя статистика, {stats['name']}\n\n"
        f"Активных дней: {stats['streak']} {emoji}\n"
        f"Рекорд: {stats['longest_streak']} дн.\n"
        f"Очки: {stats['points']}\n"
        f"Сообщений: {stats['messages_count']}\n\n"
        f"Каждый день в чате — плюс один активный день!"
    )
    await update.message.reply_text(text)


def streak_emoji_plain(streak):
    if streak == 0:
        return "😴"
    elif streak < 3:
        return "✨"
    elif streak < 7:
        return "🔥"
    elif streak < 14:
        return "🔥🔥"
    else:
        return "🔥🔥🔥"


async def cmd_goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Цели всех участников из Google Sheets."""
    await update.message.reply_text("Читаю таблицу...")
    try:
        participants = get_all_participants()
        if not participants:
            await update.message.reply_text("Данные в таблице ещё не заполнены.")
            return

        lines = ["ЦЕЛИ УЧАСТНИКОВ НА ЛЕТО\n"]
        for p in participants:
            if not p["goals"]:
                continue
            lines.append(p["name"])
            for g in p["goals"]:
                priority_icon = "⭐" if g.get("priority", "").lower() == "главная" else "•"
                lines.append(f"  {priority_icon} {g['goal']}")
                if g.get("deadline"):
                    lines.append(f"     дедлайн: {g['deadline']}")
            lines.append("")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logger.error(f"Ошибка /goals: {e}")
        await update.message.reply_text(f"Не удалось загрузить таблицу: {e}")


# ──────────────────────────────────────────────
# ТРЕКИНГ ВСЕХ СООБЩЕНИЙ
# ──────────────────────────────────────────────

async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Вызывается на каждое сообщение в чате.
    Записывает активность пользователя.
    """
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    text = update.message.text or update.message.caption or ""

    # Не трекаем ботов
    if user.is_bot:
        return

    name = user.full_name
    username = user.username or ""

    record_message(
        user_id=user.id,
        name=name,
        username=username,
        text=text,
    )

    # Реакция на milestone'ы (каждые 7 активных дней)
    stats = get_member_stats(user.id)
    if stats:
        streak = stats["streak"]
        if streak in (3, 7, 14, 21, 30, 50, 100):
            congrats = _streak_congrats(name, streak)
            if congrats:
                await update.message.reply_text(congrats)


def _streak_congrats(name, streak):
    messages = {
        3:   f"3 активных дня, {name}! Хорошее начало!",
        7:   f"7 активных дней, {name}! Целая неделя! +5 очков бонусом 🎉",
        14:  f"14 дней в чате, {name}! Это уже привычка! +5 очков 🔥",
        21:  f"21 день, {name}! Говорят, именно столько нужно для привычки 🧠 +5 очков",
        30:  f"30 активных дней, {name}! Месяц в строю! Легенда! +5 очков 🏆",
        50:  f"50 дней, {name}! Полпути к сотне! Невероятно! 🚀",
        100: f"100 активных дней, {name}! Ты абсолютный чемпион группы! 👑",
    }
    return messages.get(streak)


# ──────────────────────────────────────────────
# АВТОМАТИЧЕСКИЙ ДАЙДЖЕСТ (ПЛАНИРОВЩИК)
# ──────────────────────────────────────────────

async def send_scheduled_digest(application):
    """Отправляет дайджест в чат по расписанию."""
    chat_id = os.getenv("TELEGRAM_CHAT_ID", CHAT_ID)
    if not chat_id:
        logger.warning("TELEGRAM_CHAT_ID не задан — дайджест не отправлен")
        return
    try:
        text = build_weekly_digest()
        await application.bot.send_message(
            chat_id=int(chat_id),
            text=text,
        )
        logger.info("Еженедельный дайджест отправлен")
    except Exception as e:
        logger.error(f"Ошибка отправки дайджеста: {e}")


# ──────────────────────────────────────────────
# ЗАПУСК
# ──────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("digest", cmd_digest))
    app.add_handler(CommandHandler("streak", cmd_streak))
    app.add_handler(CommandHandler("mystats", cmd_mystats))
    app.add_handler(CommandHandler("goals", cmd_goals))

    # Трекинг ВСЕХ сообщений (текст + подписи к медиа)
    app.add_handler(
        MessageHandler(filters.TEXT | filters.CAPTION, track_message)
    )

    # Планировщик дайджеста
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        send_scheduled_digest,
        trigger=CronTrigger(
            day_of_week=DIGEST_DAY,
            hour=DIGEST_HOUR_UTC,
            minute=DIGEST_MINUTE,
        ),
        args=[app],
        id="weekly_digest",
        replace_existing=True,
    )
    scheduler.start()

    logger.info(
        f"Бот запущен. Дайджест: day={DIGEST_DAY}, {DIGEST_HOUR}:00 МСК (UTC {DIGEST_HOUR_UTC}:00)"
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
