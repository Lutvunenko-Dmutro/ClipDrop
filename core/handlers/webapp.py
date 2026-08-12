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
                
            if len(urls) == 1:
                status_msg = await message.answer("📥 Завантажую відео...")
                try:
                    import aiohttp
                    import os
                    import uuid
                    from core.downloader import VIDEOS_DIR, cleanup_file
                    
                    url = urls[0]
                    file_id = str(uuid.uuid4())
                    temp_path = os.path.join(VIDEOS_DIR, f"{file_id}.mp4")
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                with open(temp_path, "wb") as f:
                                    # БАГ-ФІКС: потокове читання по чанках (не в RAM)
                                    async for chunk in resp.content.iter_chunked(1024 * 1024):
                                        f.write(chunk)
                                
                                await status_msg.edit_text("✅ Надсилаю відео...")
                                video = FSInputFile(temp_path)
                                await message.answer_video(video)
                                cleanup_file(temp_path)
                            else:
                                await status_msg.edit_text("❌ Помилка завантаження відео з сервера Pexels.")
                except Exception as e:
                    logger.error(f"Error downloading single video: {e}")
                    await status_msg.edit_text("❌ Виникла помилка при завантаженні відео.")
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
