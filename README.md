<p align="center">
  <img src="assets/avatar.png" width="150" alt="ClipDrop Bot Avatar"/>
</p>

# 🎬 ClipDrop — Universal Telegram Media Downloader

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![aiogram](https://img.shields.io/badge/aiogram-3.15-2BA86D.svg)
![yt-dlp](https://img.shields.io/badge/yt--dlp-latest-red.svg)

**ClipDrop** — це потужний, швидкий та сучасний Telegram-бот для завантаження медіафайлів з найпопулярніших платформ (**YouTube** та **TikTok**). Бот побудований на асинхронному фреймворку `aiogram 3.x` і використовує комбінацію API та локальних інструментів для обходу блокувань датацентрів.

---

## ✨ Основні можливості

- 🎵 **TikTok:** Миттєве завантаження відео в найкращій якості (автоматично розпаковує короткі посилання `vm.tiktok.com`).
- 📺 **YouTube (RapidAPI):** Використовує стороннє API для швидкого завантаження відео, обходячи блокування IP-адрес від YouTube для хмарних серверів. Бот відображає прогрес конвертації відео в реальному часі.
- 🛡 **YouTube Fallback (yt-dlp):** Якщо ліміт API вичерпано, бот автоматично переключається на локальне завантаження через `yt-dlp` (з імітацією Android-клієнта для обходу помилок 403).
- 🗜 **Авто-стиснення (FFmpeg):** Якщо відео важить понад 50 МБ (ліміт Telegram API), бот автоматично стискає його за допомогою `ffmpeg`, щоб ви все одно отримали свій файл.
- 🧹 **Zero-Trace (Очищення):** Бот автоматично видаляє файли з сервера одразу після відправки в Telegram, не забиваючи дисковий простір сервера.

---

## 🛠 Змінні оточення (.env)

Для роботи бота необхідно створити файл `.env` у корені проєкту:

```env
# Токен вашого Telegram-бота (отримайте у @BotFather)
TOKEN=your_telegram_bot_token

# Ключ від YouTube Video FAST Downloader 24/7 (RapidAPI)
RAPIDAPI_KEY=your_rapidapi_key
```

---

## 🚀 Встановлення та запуск (Локально)

1. **Встановіть залежності системи:**
   Переконайтеся, що у вас встановлено Python 3.10+ та **FFmpeg**. 
   - На Windows: завантажте з офіційного сайту та додайте в PATH.
   - На Linux: `sudo apt install ffmpeg`

2. **Встановіть Python-бібліотеки:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Створіть `.env` файл** (див. розділ вище).

4. **Запустіть бота:**
   ```bash
   python main.py
   ```

---

## 🐳 Встановлення (через Docker)

Це найзручніший спосіб розгортання, оскільки Docker-образ вже містить у собі встановлений `ffmpeg`.

```bash
# 1. Збірка образу
docker build -t clipdrop-bot .

# 2. Запуск контейнера у фоновому режимі (з підключенням .env файлу)
docker run -d --name clipdrop-bot --env-file .env clipdrop-bot
```

---

## ☁️ Деплой на Render (Безкоштовно)

Бот ідеально оптимізований для розгортання на безкоштовному тарифі [Render.com](https://render.com/).

1. Зробіть **Fork** або завантажте цей репозиторій на свій GitHub.
2. Створіть новий **Web Service** на Render.
3. Підключіть свій репозиторій.
4. Вкажіть **Environment**: `Docker` (Render сам прочитає `Dockerfile` і встановить `ffmpeg`).
5. У розділі **Environment Variables** обов'язково додайте `TOKEN` та `RAPIDAPI_KEY`.
6. Натисніть **Deploy**.

> **Примітка:** Оскільки Render використовує датацентрові IP, без використання RapidAPI завантаження з YouTube може блокуватися (HTTP Error 429). Бот обробляє це автоматично завдяки інтеграції RapidAPI.