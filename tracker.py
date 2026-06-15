"""
Трекер активности участников в чате.
Хранит сообщения, streak'и, очки — в памяти + JSON-файл для персистентности.

Streak НЕ сгорает при пропуске дня — он просто замораживается на текущем значении.
Streak растёт только вперёд — каждый новый день активности +1.
"""

import json
import os
from datetime import date, timedelta
from collections import defaultdict

DATA_FILE = "tracker_data.json"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "members": {},       # user_id -> {name, username, streak, last_active, points, messages}
        "messages": [],      # [{date, user_id, name, text}] — последние 500
        "week_messages": [], # сообщения текущей недели для инсайтов
    }


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def get_or_create_member(data, user_id, name, username):
    uid = str(user_id)
    if uid not in data["members"]:
        data["members"][uid] = {
            "name": name,
            "username": username or "",
            "streak": 0,
            "longest_streak": 0,
            "last_active": None,
            "points": 0,
            "messages_count": 0,
            "active_days": [],  # список дат активности
        }
    else:
        # Обновляем имя если изменилось
        data["members"][uid]["name"] = name
        if username:
            data["members"][uid]["username"] = username
    return data["members"][uid]


def record_message(user_id, name, username, text):
    """Записывает факт сообщения, обновляет streak и очки."""
    data = load_data()
    member = get_or_create_member(data, user_id, name, username)

    today = date.today().isoformat()
    member["messages_count"] = member.get("messages_count", 0) + 1

    # Streak: если сегодня ещё не было активности
    active_days = member.get("active_days", [])
    if today not in active_days:
        active_days.append(today)
        # Оставляем только последние 90 дней
        active_days = sorted(active_days)[-90:]
        member["active_days"] = active_days

        # Пересчитываем streak (накопительный, не сгорает)
        streak = _calc_streak_cumulative(active_days)
        member["streak"] = streak
        member["longest_streak"] = max(member.get("longest_streak", 0), streak)
        member["last_active"] = today

        # Очки за активность
        member["points"] = member.get("points", 0) + 1
        if streak % 7 == 0 and streak > 0:
            member["points"] += 5  # бонус за каждые 7 активных дней

    # Сохраняем сообщение в историю (макс 500)
    entry = {
        "date": today,
        "user_id": str(user_id),
        "name": name,
        "text": text[:300],
    }
    data["messages"] = (data["messages"] + [entry])[-500:]

    # Сообщения текущей недели (пн–вс)
    week_start = _current_week_start()
    data["week_messages"] = [
        m for m in data["messages"] if m["date"] >= week_start
    ]

    save_data(data)
    return member


def _current_week_start():
    today = date.today()
    start = today - timedelta(days=today.weekday())
    return start.isoformat()


def _calc_streak_cumulative(active_days_sorted):
    """
    Считает streak как общее количество уникальных дней активности.
    НЕ сгорает при пропуске — просто растёт каждый новый активный день.
    """
    return len(set(active_days_sorted))


def get_streak_table():
    """Возвращает отсортированный список участников по streak."""
    data = load_data()
    table = []
    for uid, m in data["members"].items():
        streak = _calc_streak_cumulative(m.get("active_days", []))
        m["streak"] = streak  # актуализируем
        table.append({
            "name": m["name"],
            "streak": streak,
            "points": m.get("points", 0),
            "messages_count": m.get("messages_count", 0),
        })
    save_data(data)
    return sorted(table, key=lambda x: (-x["streak"], -x["points"]))


def get_weekly_insights():
    """Анализирует сообщения недели: топ-темы, активность."""
    data = load_data()
    week_msgs = data.get("week_messages", [])

    # Активность по участникам
    activity = defaultdict(int)
    for msg in week_msgs:
        activity[msg["name"]] += 1

    # Простой анализ тем — ищем частые слова (исключаем стоп-слова)
    STOP_WORDS = {
        "и", "в", "на", "с", "по", "не", "что", "это", "как", "я", "у",
        "а", "но", "то", "из", "за", "к", "о", "от", "до", "все", "уже",
        "так", "есть", "был", "была", "мне", "мой", "моя", "мои", "ещё",
        "еще", "да", "нет", "для", "или", "когда", "если", "чтобы", "им",
        "он", "она", "они", "его", "её", "их", "вот", "там", "тут", "же",
        "бы", "ну", "вы", "мы", "вас", "нас", "то", "ты", "со", "при",
        "про", "без", "под", "над", "между", "через", "после", "перед",
    }

    word_freq = defaultdict(int)
    for msg in week_msgs:
        words = msg["text"].lower().split()
        for w in words:
            w = w.strip(".,!?:;\"'()—–-")
            if len(w) > 3 and w not in STOP_WORDS:
                word_freq[w] += 1

    top_words = sorted(word_freq.items(), key=lambda x: -x[1])[:5]

    return {
        "total_messages": len(week_msgs),
        "activity_by_member": dict(sorted(activity.items(), key=lambda x: -x[1])),
        "top_words": top_words,
        "active_members": len(activity),
    }


def get_member_stats(user_id):
    """Статистика конкретного участника."""
    data = load_data()
    uid = str(user_id)
    if uid not in data["members"]:
        return None
    m = data["members"][uid]
    streak = _calc_streak_cumulative(m.get("active_days", []))
    return {
        "name": m["name"],
        "streak": streak,
        "longest_streak": m.get("longest_streak", 0),
        "points": m.get("points", 0),
        "messages_count": m.get("messages_count", 0),
    }
