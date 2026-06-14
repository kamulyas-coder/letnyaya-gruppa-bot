"""
Формирование еженедельного дайджеста и инсайтов.
"""

from tracker import get_streak_table, get_weekly_insights
from sheets import get_all_participants


FIRE_EMOJIS = ["🔥", "🔥🔥", "🔥🔥🔥"]
MEDALS = ["🥇", "🥈", "🥉"]


def streak_emoji(streak):
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


def build_weekly_digest():
    """Собирает полный еженедельный дайджест."""
    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📊 *ЕЖЕНЕДЕЛЬНЫЙ ДАЙДЖЕСТ*")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━\n")

    # --- Блок 1: Прогресс по таблице ---
    lines.append("*📋 Прогресс по целям (из таблицы)*\n")
    try:
        participants = get_all_participants()
        if participants:
            for p in participants:
                name = p["name"]
                pct = p["week_pct"]
                done = p["week_completed"]
                total = p["week_total"]

                bar = _progress_bar(pct)
                if total == 0:
                    lines.append(f"• *{name}* — таблица не заполнена")
                else:
                    lines.append(f"• *{name}* {bar} {pct}% ({done}/{total} задач)")
        else:
            lines.append("_Данные из таблицы пока недоступны_")
    except Exception as e:
        lines.append(f"_Не удалось загрузить таблицу: {e}_")

    lines.append("")

    # --- Блок 2: Streak-таблица ---
    lines.append("*🔥 Streak — дни активности подряд*\n")
    streak_table = get_streak_table()
    if streak_table:
        for i, member in enumerate(streak_table[:10]):
            medal = MEDALS[i] if i < 3 else f"{i+1}."
            emoji = streak_emoji(member["streak"])
            streak_days = member["streak"]
            pts = member["points"]
            lines.append(
                f"{medal} *{member['name']}* — {streak_days} дн. {emoji}  ·  {pts} очков"
            )
    else:
        lines.append("_Пока нет данных об активности_")

    lines.append("")

    # --- Блок 3: Инсайты чата ---
    lines.append("*💡 Инсайты недели*\n")
    insights = get_weekly_insights()
    total_msgs = insights["total_messages"]
    active = insights["active_members"]
    top_words = insights["top_words"]

    lines.append(f"💬 Сообщений за неделю: *{total_msgs}*")
    lines.append(f"👥 Активных участников: *{active}*")

    if insights["activity_by_member"]:
        top_member = list(insights["activity_by_member"].items())[0]
        lines.append(f"🏆 Самый активный: *{top_member[0]}* ({top_member[1]} сообщ.)")

    if top_words:
        words_str = ", ".join([f"_{w}_" for w, _ in top_words])
        lines.append(f"🗣 Чаще всего говорили про: {words_str}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("_Следующий дайджест — в воскресенье 🙌_")

    return "\n".join(lines)


def build_streak_only():
    """Только streak-таблица — для команды /streak."""
    lines = []
    lines.append("🔥 *STREAK-ТАБЛИЦА*\n")
    streak_table = get_streak_table()
    if not streak_table:
        return "Пока никто не набрал streak. Пишите в чат каждый день! 💪"

    for i, member in enumerate(streak_table[:10]):
        medal = MEDALS[i] if i < 3 else f"{i+1}."
        emoji = streak_emoji(member["streak"])
        lines.append(
            f"{medal} *{member['name']}* — {member['streak']} дн. {emoji}"
        )

    lines.append("")
    lines.append("_Streak считается по дням активности в чате._")
    lines.append("_Пропустил день — streak сгорает 😬_")
    return "\n".join(lines)


def _progress_bar(pct, length=8):
    filled = round(pct / 100 * length)
    empty = length - filled
    return "▓" * filled + "░" * empty
