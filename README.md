# 🤖 Летняя группа целей 2026 — Telegram Bot

## Что умеет бот

| Функция | Описание |
|---|---|
| 📋 Читает таблицу | Каждый дайджест бот берёт прогресс из Google Sheets |
| 💬 Трекает чат | Видит все сообщения (работает как админ группы) |
| 🔥 Streak | Считает дни активности подряд, поздравляет на milestone'ах |
| 📊 Дайджест | Каждое воскресенье в 19:00 МСК — полный отчёт |
| 💡 Инсайты | Топ-темы недели, самый активный участник |

## Команды

| Команда | Что делает |
|---|---|
| `/start` | Приветствие + узнать Chat ID |
| `/digest` | Запросить дайджест вручную |
| `/streak` | Таблица streak'ов прямо сейчас |
| `/mystats` | Твоя личная статистика |
| `/goals` | Цели всех участников из таблицы |

---

## Шаг 1 — Настройка Google Sheets API

1. Открой [Google Cloud Console](https://console.cloud.google.com/)
2. Создай новый проект (или выбери существующий)
3. Включи **Google Sheets API** и **Google Drive API**:
   - Меню → *APIs & Services* → *Library* → найди и включи оба
4. Создай Service Account:
   - *APIs & Services* → *Credentials* → *Create Credentials* → *Service Account*
   - Имя: `letnyaya-gruppa-bot`
   - Роль: *Editor*
5. Скачай ключ:
   - Зайди в созданный Service Account → вкладка *Keys* → *Add Key* → *JSON*
   - Сохрани файл как **`service_account.json`** в папку бота
6. Открой доступ к таблице:
   - Скопируй email из `service_account.json` (поле `client_email`)
   - Открой таблицу → *Поделиться* → вставь email → роль *Редактор*

---

## Шаг 2 — Деплой на Railway (бесплатно)

1. Зарегистрируйся на [railway.app](https://railway.app)
2. *New Project* → *Deploy from GitHub repo*
   (или залей папку через *Deploy from local*)
3. В разделе **Variables** добавь:

```
TELEGRAM_BOT_TOKEN=8961294024:AAHjP1BG4vhpV_aGovs3uguBf-7wabqid-4
TELEGRAM_CHAT_ID=  ← заполнишь после шага 3
SPREADSHEET_ID=1VR9U6zoDf-xYr27omQ1Ykh8BRiCbECFLchcpA8bqQAA
```

4. В разделе **Settings** → *Start Command*:
```
pip install -r requirements.txt && python bot.py
```

5. Также загрузи `service_account.json` через Railway Files или добавь его содержимое как переменную `GOOGLE_CREDENTIALS_JSON`

---

## Шаг 3 — Добавить бота в чат

1. Открой группу в Telegram
2. *Участники* → *Добавить участника* → найди `@letnyaya_gruppa_bot`
3. Сделай его **администратором** (чтобы видел все сообщения):
   - *Управление группой* → *Администраторы* → выбери бота
   - Включи: *Чтение сообщений* ✓
4. Напиши в чате `/start`
5. Бот ответит и покажет **Chat ID** — скопируй его в переменную `TELEGRAM_CHAT_ID`

---

## Геймификация — как начисляются очки

| Действие | Очки |
|---|---|
| Написал сообщение в день (первое за день) | +1 |
| Streak 7 дней без пропуска | +5 бонус |
| Streak 14 дней | +5 бонус |
| Streak 21 день | +5 бонус |
| Streak 30 дней | +5 бонус |

### Streak milestone'ы — бот поздравляет публично:
- 🔥 3 дня подряд
- 🔥🔥 7 дней — неделя
- 🔥🔥🔥 14 дней — две недели  
- ⚡ 21 день — привычка сформирована
- 🏆 30 дней — месяц без пропусков

---

## Структура проекта

```
letnyaya_gruppa_bot/
├── bot.py              # Главный файл — запуск, команды, трекинг
├── sheets.py           # Чтение Google Sheets
├── tracker.py          # Трекинг активности, streak, очки
├── digest.py           # Формирование дайджеста и инсайтов
├── tracker_data.json   # Данные (создаётся автоматически)
├── service_account.json # Ключ Google API (добавить самостоятельно)
├── requirements.txt
├── .env.example
└── README.md
```
