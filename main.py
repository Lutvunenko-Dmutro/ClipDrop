import os
import logging
import asyncio
from dotenv import load_dotenv
load_dotenv()

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from core.handlers import router
from core.pexels_client import search_videos, get_best_video_file, get_lowest_video_file

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
#  Конфігурація
# ============================================================
TOKEN          = os.getenv("TOKEN")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL", "").rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
WEBHOOK_PATH   = "/webhook"
PORT           = int(os.environ.get("PORT", 8080))
USE_WEBHOOK    = os.getenv("USE_WEBHOOK", "True").lower() in ("true", "1", "yes")

# ============================================================
#  Хендлери веб-сервера
# ============================================================
async def health_check(request):
    """Для Render health check та браузерної перевірки."""
    return web.Response(text="✅ ClipDrop Bot is running!")

async def web_app_handler(request):
    """Віддає сторінку Web App (index.html)."""
    with open("public/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return web.Response(text=html, content_type="text/html")

async def api_search(request):
    """API для пошуку футажів з Web App."""
    query = request.query.get("q", "")
    if not query:
        return web.json_response({"videos": []})
        
    raw_videos = await search_videos(query, per_page=15)
    videos = []
    for vid in raw_videos:
        hd_url = get_best_video_file(vid)
        sd_url = get_lowest_video_file(vid)
        if hd_url and sd_url:
            videos.append({
                "id": vid.get("id"),
                "sd_url": sd_url,
                "hd_url": hd_url,
                "duration": vid.get("duration", 0),
                "author": vid.get("user", {}).get("name", "Невідомий")
            })
            
    return web.json_response({"videos": videos})

# ============================================================
#  Старт і зупинка
# ============================================================
async def on_startup(bot: Bot):
    if not WEBHOOK_URL:
        logger.error("WEBHOOK_URL не задано! Встановіть змінну оточення.")
        return

    webhook_full_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(
        url=webhook_full_url,
        secret_token=WEBHOOK_SECRET if WEBHOOK_SECRET else None,
        drop_pending_updates=False
    )
    logger.info(f"✅ Webhook встановлено: {webhook_full_url}")

async def on_startup_polling(bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Запущено режим Polling (Локальне тестування)")

async def start_polling_and_web(dp: Dispatcher, bot: Bot, app: web.Application, port: int):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Локальний веб-сервер запущено на http://localhost:{port}")
    await dp.start_polling(bot)

# ============================================================
#  Точка входу
# ============================================================
def main():
    if not TOKEN:
        logger.error("Не задано TOKEN! Перевірте .env файл.")
        return

    bot = Bot(token=TOKEN)
    dp  = Dispatcher()
    dp.include_router(router)
    
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/app", web_app_handler)
    app.router.add_get("/api/search", api_search)
    app.router.add_static("/public", "public")

    if USE_WEBHOOK:
        dp.startup.register(on_startup)
        SimpleRequestHandler(
            dispatcher=dp, 
            bot=bot, 
            secret_token=WEBHOOK_SECRET if WEBHOOK_SECRET else None
        ).register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        logger.info(f"🚀 Запуск ClipDrop Webhook сервера на порту {PORT}...")
        web.run_app(app, host="0.0.0.0", port=PORT)
    else:
        dp.startup.register(on_startup_polling)
        logger.info("🚀 Запуск ClipDrop у режимі Polling...")
        asyncio.run(start_polling_and_web(dp, bot, app, PORT))

if __name__ == "__main__":
    main()
