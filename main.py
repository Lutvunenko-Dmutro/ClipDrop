import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
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

# --- ВЕБ-СЕРВЕР ОБМАНКА ДЛЯ RENDER ---
async def handle_health_check(request):
    return web.Response(text="Bot is running! (ClipDrop Health Check OK)")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render передає порт через змінну PORT. Якщо її немає (локально), юзаємо 8080
    port = int(os.environ.get('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Dummy веб-сервер запущено на порту {port}")

# --- ОСНОВНИЙ ЗАПУСК БОТА ---
async def main():
    token = os.getenv("TOKEN")
    if not token:
        logger.error("Не задано токен! Створіть файл .env та додайте TOKEN=ваш_токен")
        return

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)

    # Запускаємо веб-сервер у фоні
    asyncio.create_task(start_web_server())

    logger.info("Запуск Медіа Бота (ClipDrop)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинено.")
