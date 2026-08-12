import logging
import json
from aiogram import Router, F
from aiogram.types import Message, FSInputFile

from core.bulk_downloader import create_bulk_pack
from core.downloader import cleanup_file

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.web_app_data)
async def web_app_data_handler(message: Message):
    """Обробляє дані, надіслані з Web App (JSON з URL)."""
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("action") == "download_zip":
            urls = data.get("urls", [])
            if not urls:
                await message.answer("Ти не вибрав жодного відео.")
                return
                
            status_msg = await message.answer(f"📦 Пакую {len(urls)} футажів з Галереї у ZIP-архів...")
            user_id = message.from_user.id
            path_or_link, is_link = await create_bulk_pack(urls, user_id)
            
            if not path_or_link:
                await status_msg.edit_text("❌ Помилка при створенні архіву.")
                return
                
            if is_link:
                await status_msg.edit_text(f"✅ Архів занадто великий для Telegram.\n📥 [Завантажити з GoFile]({path_or_link})", parse_mode="Markdown")
            else:
                await status_msg.edit_text("✅ Архів готовий! Надсилаю...")
                doc = FSInputFile(path_or_link)
                await message.answer_document(doc)
                cleanup_file(path_or_link)
    except Exception as e:
        logger.error(f"Помилка обробки web_app_data: {e}")
        await message.answer("❌ Виникла помилка при обробці запиту з Галереї.")
