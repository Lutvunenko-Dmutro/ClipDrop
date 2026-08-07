import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

# Завантажуємо змінні середовища
load_dotenv()

from core.handlers import router

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    token = os.getenv("TOKEN")
    if not token:
        logger.error("Не задано токен! Створіть файл .env та додайте TOKEN=ваш_токен")
        return

    bot = Bot(token=token)
    dp = Dispatcher()

    # Підключаємо наші обробники
    dp.include_router(router)

    logger.info("Запуск Медіа Бота...")
    # Запускаємо поллінг
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинено.")
