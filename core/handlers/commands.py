import os
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, Command

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message):
    # Беремо URL для Web App (використовуємо WEBHOOK_URL з .env, або placeholder)
    web_app_url = os.getenv("WEBHOOK_URL", "https://your-ngrok-url.app").rstrip("/") + "/app"
    
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🖼 Відкрити Галерею (Web App)", web_app=WebAppInfo(url=web_app_url))]
        ],
        resize_keyboard=True
    )
    
    text = (
        "Привіт! 👋 Я **ClipDrop** — твій універсальний медіа-бот.\n\n"
        "1. Надішли мені посилання на відео з **YouTube** або **TikTok**, і я завантажу його для тебе!\n"
        "2. Просто напиши будь-яке слово (наприклад, `кіберпанк`), щоб **знайти футажі** на Pexels!\n"
        "3. Або натисни кнопку **Відкрити Галерею** знизу, щоб шукати відео в зручному інтерфейсі!"
    )
    await message.reply(text, parse_mode="Markdown", reply_markup=markup)

@router.message(Command("version"))
async def version_handler(message: Message):
    await message.reply("Версія бота: 2.1.0 (ClipDrop + Footage Finder)")
