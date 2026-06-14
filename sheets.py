"""
Модуль для работы с Google Sheets.
Читает данные участников: цели, недельный каскад, прогресс.
"""

import os
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1VR9U6zoDf-xYr27omQ1Ykh8BRiCbECFLchcpA8bqQAA")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Листы участников (всё кроме служебных)
SKIP_SHEETS = {"Инструкция", "Карта ресурсов", "Пример"}


def get_client():
    creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    return gspread.authorize(creds)


def get_participant_sheets():
    """Возвращает список листов участников."""
    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheets = []
    for ws in spreadsheet.worksheets():
        if ws.title not in SKIP_SHEETS:
            sheets.append(ws)
    return sheets


def get_all_values_cached(ws):
    """Получает все значения листа."""
    return ws.get_all_values()


def find_row_by_keyword(rows, keyword):
    """Ищет номер строки (0-based) по ключевому слову."""
    for i, row in enumerate(rows):
        for cell in row:
            if keyword.lower() in str(cell).lower():
                return i
    return -1


def parse_participant_data(ws):
    """
    Парсит данные одного участника.
    Возвращает словарь с целями, прогрессом недели и колесом баланса.
    """
    rows = get_all_values_cached(ws)
    name = ws.title.strip()

    # --- Цели (раздел 4) ---
    goals = []
    goals_row = find_row_by_keyword(rows, "ГЛАВНЫЕ ЦЕЛИ НА ЛЕТО")
    if goals_row >= 0:
        # Заголовок через 1 строку, данные дальше
        for r in rows[goals_row + 2: goals_row + 6]:
            if len(r) >= 3 and r[1].strip() and r[2].strip():
                goals.append({
                    "num": r[1].strip(),
                    "goal": r[2].strip(),
                    "metric": r[3].strip() if len(r) > 3 else "",
                    "deadline": r[4].strip() if len(r) > 4 else "",
                    "priority": r[5].strip() if len(r) > 5 else "",
                })

    # --- Недельный каскад (раздел 6) ---
    weekly_tasks = []
    week_completed = 0
    week_total = 0

    week_row = find_row_by_keyword(rows, "НЕДЕЛЬНЫЙ КАСКАД")
    if week_row >= 0:
        # Ищем первую незаполненную неделю (или текущую)
        current_week_tasks = []
        i = week_row + 2  # пропускаем заголовок
        while i < len(rows) and i < week_row + 60:
            row = rows[i]
            if len(row) >= 2:
                week_label = row[1].strip() if len(row) > 1 else ""
                task = row[2].strip() if len(row) > 2 else ""
                goal_ref = row[3].strip() if len(row) > 3 else ""
                done = row[4].strip() if len(row) > 4 else ""
                pct = row[5].strip() if len(row) > 5 else ""

                # Новая неделя с заголовком "Нед N"
                if week_label.startswith("Нед") and task:
                    current_week_tasks = []
                    weekly_tasks = []  # берём только последнюю заполненную

                if task:
                    item = {
                        "task": task,
                        "goal_ref": goal_ref,
                        "done": done.lower() in ("да", "yes", "✓", "+", "1"),
                        "done_raw": done,
                    }
                    current_week_tasks.append(item)
                    weekly_tasks = current_week_tasks

                    if pct:
                        try:
                            week_completed_pct = int(pct.replace("%", "").strip())
                        except Exception:
                            pass
            i += 1

        # Считаем %
        week_total = len(weekly_tasks)
        week_completed = sum(1 for t in weekly_tasks if t["done"])

    # --- Колесо баланса (раздел 1) ---
    wheel = []
    wheel_row = find_row_by_keyword(rows, "КОЛЕСО ЖИЗН")
    if wheel_row >= 0:
        for r in rows[wheel_row + 2: wheel_row + 12]:
            if len(r) >= 4 and r[1].strip() and r[2].strip():
                try:
                    now_val = float(r[2].replace(",", "."))
                    want_val = float(r[3].replace(",", "."))
                    wheel.append({
                        "sphere": r[1].strip(),
                        "now": now_val,
                        "want": want_val,
                        "gap": round(want_val - now_val, 1),
                    })
                except Exception:
                    pass

    return {
        "name": name,
        "goals": goals,
        "weekly_tasks": weekly_tasks,
        "week_total": week_total,
        "week_completed": week_completed,
        "week_pct": round(week_completed / week_total * 100) if week_total else 0,
        "wheel": wheel,
    }


def get_all_participants():
    """Читает данные всех участников."""
    sheets = get_participant_sheets()
    result = []
    for ws in sheets:
        try:
            data = parse_participant_data(ws)
            result.append(data)
        except Exception as e:
            print(f"Ошибка при чтении листа {ws.title}: {e}")
    return result
