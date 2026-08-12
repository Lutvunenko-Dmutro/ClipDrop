<p align="center">
  <img src="assets/avatar.png" width="140" alt="ClipDrop Bot"/>
</p>

<h1 align="center">🎬 ClipDrop Bot</h1>

<p align="center">
  <b>Твій особистий медіа-комбайн у Telegram для відеомейкерів і контент-мейкерів</b>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"/></a>
  <a href="https://docs.aiogram.dev/"><img src="https://img.shields.io/badge/aiogram-3.15-2BA86D?style=for-the-badge&logo=telegram&logoColor=white"/></a>
  <a href="https://github.com/yt-dlp/yt-dlp"><img src="https://img.shields.io/badge/yt--dlp-latest-FF0000?style=for-the-badge&logo=youtube&logoColor=white"/></a>
  <a href="https://www.pexels.com/api/"><img src="https://img.shields.io/badge/Pexels-API-05A081?style=for-the-badge&logo=pexels&logoColor=white"/></a>
  <a href="https://render.com/"><img src="https://img.shields.io/badge/Deploy-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white"/></a>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge"/>
</p>

---

## 🌟 Що це таке?

**ClipDrop** — це не просто бот для завантаження відео. Це **повноцінний інструмент автоматизації** для людей, що займаються відеомонтажем, рілс, кліпами або будь-яким відео-контентом.

Уяви: тобі потрібно 15 якісних безкоштовних футажів з природою для монтажу. Зазвичай це 15 відкритих вкладок, 15 ручних завантажень, хаос у папці «Завантаження». З ClipDrop — ти пишеш одне слово в Telegram, перегортаєш 80 відео одним пальцем, клікаєш «В кошик» на тих, що сподобались, і тиснеш **одну кнопку** — бот сам качає, пакує в ZIP і надсилає тобі готовий архів.

---

## ✨ Можливості

### 📹 Pexels Footage Finder
Пошук і перегляд стокових відео прямо в Telegram-чаті.
- Введи будь-яке слово → отримай до **80 відео** за один запит
- Перегортай відео кнопками ⬅️ ➡️ без жодного очікування
- Результати **перемішуються** при кожному новому пошуку для різноманітності
- Дивись прев'ю відео прямо в чаті, завантажуй HD-оригінал одним тапом

### 🛒 Розумний Кошик + Bulk ZIP
Збирай футажі й завантажуй пачками — як в інтернет-магазині.
- Додавай відео в кошик під час перегляду пошукової видачі
- Кошик **зберігається в базі даних** — не зникає при перезапуску сервера
- Завантаж усі відео одним ZIP-архівом (`📦 Завантажити ZIP (N)`)
- Якщо архів > 45 МБ — бот автоматично завантажує його на **GoFile.io** і надсилає пряме посилання

### 🖼 Web App — Галерея
Вбудований міні-застосунок прямо всередині Telegram.
- Відкривається кнопкою **«🖼 Відкрити Галерею»** без виходу з Telegram
- Зручний grid-інтерфейс для швидкого перегляду великої кількості відео
- Відправляє вибрані відео або ZIP-архів прямо в чат

### 🎵 TikTok Downloader
- Завантаження у найкращій доступній якості, **без водяних знаків**
- Автоматично розпаковує короткі посилання `vm.tiktok.com` та `vt.tiktok.com`
- Детектує фото-пости та повідомляє замість краша

### 📺 YouTube Downloader
- **RapidAPI** — основний режим для обходу блокувань датацентрових IP (Error 429)
- **yt-dlp** — автоматичний fallback з імітацією Android-клієнта
- Прогрес конвертації відображається в реальному часі

### 🗜 Авто-стиснення (FFmpeg)
- Якщо файл > **49.5 МБ** (ліміт Telegram API = 50 МБ) — бот автоматично стискає відео до 720p
- Стиснення відбувається асинхронно, не блокуючи інших користувачів
- Тимчасові файли видаляються одразу після відправки (Zero-Trace)

### 🛡 Безпека та Стабільність
- **SQL Injection Protection** — всі запити до SQLite через параметризовані `?`-запити
- **Webhook Secret Token** — блокує підроблені запити від сторонніх
- **Anti-flood** — захист від спаму запитами
- **Daily Limit** — ліміт завантажень на день, з bypass для `OWNER_ID`
- **`allowed_updates`** явно вказані: `message`, `callback_query`, `web_app_data`

---

## 🏗 Архітектура проєкту

```
my-telegram-bot/
├── main.py                    # Точка входу: Webhook / Polling режими
├── core/
│   ├── handlers/
│   │   ├── __init__.py        # Реєстрація роутерів (порядок важливий)
│   │   ├── commands.py        # /start, /version
│   │   ├── search.py          # Pexels пошук, пагінація, кошик
│   │   ├── downloader.py      # YouTube + TikTok завантаження
│   │   └── webapp.py          # Обробка даних з Web App
│   ├── db.py                  # SQLite: init, get_state, save_state
│   ├── state.py               # Інтерфейс для роботи зі станом
│   ├── pexels_client.py       # Pexels API клієнт
│   ├── downloader.py          # FFmpeg, yt-dlp, завантаження файлів
│   ├── bulk_downloader.py     # Паралельне завантаження + ZIP
│   ├── gofile_client.py       # Завантаження великих архівів на GoFile.io
│   ├── limiter.py             # Anti-flood + денний ліміт
│   └── web_routes.py          # aiohttp: health check, Web App, API
├── public/
│   ├── index.html             # Web App (Telegram Mini App)
│   ├── css/style.css
│   └── js/app.js
├── Dockerfile                 # Docker з ffmpeg включно
└── requirements.txt
```

---

## 🛠 Налаштування (.env)

Створи файл `.env` у корені проєкту:

```env
# ── Обов'язкові ──────────────────────────────────────────────
TOKEN=1234567890:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PEXELS_API_KEY=your_pexels_api_key

# ── YouTube ───────────────────────────────────────────────────
RAPIDAPI_KEY=your_rapidapi_key

# ── Для Webhook-режиму (потрібен при деплої на Render) ────────
WEBHOOK_URL=https://your-service.onrender.com
WEBHOOK_SECRET=MySuperSecretToken123

# ── Додаткові ─────────────────────────────────────────────────
OWNER_ID=123456789

# Для локального тестування: вимикає Webhook, вмикає Polling
USE_WEBHOOK=False
```

> **Як дізнатись свій `OWNER_ID`?** Напиши [@userinfobot](https://t.me/userinfobot) в Telegram.

---

## 🚀 Запуск локально

**1. Встанови FFmpeg:**

| ОС | Команда |
|----|---------|
| Windows | [Завантаж](https://ffmpeg.org/download.html), додай у `PATH` |
| Ubuntu / Debian | `sudo apt install ffmpeg` |
| macOS | `brew install ffmpeg` |

**2. Встанови Python-бібліотеки:**
```bash
pip install -r requirements.txt
```

**3. Налаштуй `.env`** (обов'язково `USE_WEBHOOK=False` для локалки).

**4. Запусти:**
```bash
python main.py
```

Бот стартує в режимі Polling + підніме веб-сервер на `http://localhost:8080` для Web App.

---

## 🐳 Docker

```bash
# Збірка (ffmpeg вже всередині образу)
docker build -t clipdrop-bot .

# Запуск
docker run -d --name clipdrop-bot --env-file .env clipdrop-bot
```

---

## ☁️ Безкоштовний деплой на Render

**Кроки:**

1. Зроби **Fork** цього репозиторію на свій GitHub
2. Зайди на [render.com](https://render.com) → **New Web Service**
3. Підключи свій репозиторій
4. **Environment** → вибери `Docker`
5. Додай **Environment Variables**:

| Змінна | Значення |
|--------|----------|
| `TOKEN` | Токен бота від @BotFather |
| `PEXELS_API_KEY` | Ключ з [pexels.com/api](https://www.pexels.com/api/) |
| `RAPIDAPI_KEY` | Ключ з RapidAPI |
| `WEBHOOK_URL` | `https://your-app.onrender.com` |
| `WEBHOOK_SECRET` | Будь-який складний пароль |
| `OWNER_ID` | Твій Telegram ID |

6. Натисни **Deploy** — готово!

> **💡 Free Tier:** Сервер «засинає» через 15 хв бездіяльності. Webhook-режим гарантує, що перше повідомлення розбудить сервер (~30 сек), і далі все працює миттєво без втрати жодного оновлення.

---

## 🤝 Contributing

Читай [CONTRIBUTING.md](CONTRIBUTING.md) перед Pull Request.

---

## 📄 Ліцензія

Поширюється під ліцензією [MIT](LICENSE).
