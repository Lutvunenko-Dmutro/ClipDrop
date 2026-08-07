import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from dotenv import load_dotenv
from core.handlers import router

# Завантажуємо змінні середовища
load_dotenv()

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
#  Конфігурація
# ============================================================
TOKEN        = os.getenv("TOKEN")
WEBHOOK_URL  = os.getenv("WEBHOOK_URL", "").rstrip("/")
WEBHOOK_PATH = "/webhook"
PORT         = int(os.environ.get("PORT", 8080))

# ============================================================
#  Хендлери веб-сервера
# ============================================================
async def health_check(request):
    """Для Render health check та браузерної перевірки."""
    return web.Response(text="✅ ClipDrop Bot is running!")

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
        drop_pending_updates=True   # Ігнорувати старі повідомлення при старті
    )
    logger.info(f"✅ Webhook встановлено: {webhook_full_url}")

async def on_shutdown(bot: Bot):
    logger.info("🔻 Видаляємо webhook...")
    await bot.delete_webhook()

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

    # Реєструємо хуки старту / зупинки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Створюємо aiohttp додаток
    app = web.Application()

    # Маршрут для health check
    app.router.add_get("/", health_check)

    # Aiogram обробляє POST /webhook — всі оновлення від Telegram йдуть сюди
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    logger.info(f"🚀 Запуск ClipDrop Webhook сервера на порту {PORT}...")
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
