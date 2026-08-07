import logging
import aiohttp
import asyncio
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile

from core.downloader import download_tiktok_video, download_youtube_rapidapi, cleanup_file
from core.limiter import check_limits, record_request

router = Router()
logger = logging.getLogger(__name__)

async def resolve_tiktok_redirect(url: str) -> str:
    """Розпаковує коротке TikTok-посилання (vm.tiktok.com) до повного."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=True) as resp:
            return str(resp.url)

@router.message(CommandStart())
async def start_handler(message: Message):
    text = (
        "Привіт! 👋 Я **ClipDrop** — твій універсальний медіа-бот.\n\n"
        "Надішли мені посилання на відео з **YouTube** або **TikTok**, "
        "і я завантажу його для тебе!"
    )
    await message.reply(text, parse_mode="Markdown")

@router.message(Command("version"))
async def version_handler(message: Message):
    await message.reply("Версія бота: 2.0.0 (ClipDrop)")

@router.message(F.text)
async def message_handler(message: Message):
    url = message.text.strip()
    user_id = message.from_user.id
    
    # Перевірка на TikTok / YouTube
    is_tiktok = "tiktok.com" in url.lower()
    is_youtube = "youtube.com" in url.lower() or "youtu.be" in url.lower()

    if not is_tiktok and not is_youtube:
        # Відповідаємо тільки в приватних повідомленнях, щоб не спамити в групах
        if message.chat.type == "private":
            await message.reply("Будь ласка, надішліть дійсне посилання на YouTube або TikTok.")
        return

    # ── Перевірка лімітів (Anti-flood + Daily limit) ──────────────────
    allowed, reason = check_limits(user_id)
    if not allowed:
        await message.reply(reason, parse_mode="Markdown")
        return
    # ──────────────────────────────────────────────────────────────────

    # Запускаємо обробку у фоновому завданні, щоб миттєво повернути HTTP 200 для Webhook
    asyncio.create_task(process_video_task(message, url, is_tiktok, is_youtube, user_id))

async def process_video_task(message: Message, url: str, is_tiktok: bool, is_youtube: bool, user_id: int):
    wait_msg = await message.reply("⏳ Обробляю посилання, зачекайте...")

    try:
        if is_tiktok:
            if "vm.tiktok.com" in url.lower():
                url = await resolve_tiktok_redirect(url)
                
            if "/photo/" in url.lower() or "aweme_type=150" in url.lower():
                await wait_msg.edit_text("❌ Це фото-пост, а бот підтримує лише відео.")
                return

            video_path = await download_tiktok_video(url)
            video = FSInputFile(video_path)
            await message.reply_video(video)
            cleanup_file(video_path)
            
        elif is_youtube:
            video_path, was_compressed = await download_youtube_rapidapi(url, wait_msg)
            
            if was_compressed:
                await wait_msg.edit_text("⏳ Відео завелике, стискаю його щоб відправити в Telegram (це може зайняти хвилину)...")
                
            # Перевіряємо фінальний розмір
            import os
            final_size = os.path.getsize(video_path) / (1024 * 1024)
            if final_size > 50:
                await wait_msg.edit_text(f"❌ Навіть після стиснення файл занадто великий ({final_size:.2f} МБ). Максимум 50 МБ.")
            else:
                video = FSInputFile(video_path)
                await message.reply_video(video)
                
            cleanup_file(video_path)

        # Фіксуємо успішний запит (лічильник + часова мітка для anti-flood)
        record_request(user_id)

        # Видаляємо повідомлення "Обробляю..."
        await wait_msg.delete()

    except Exception as e:
        logger.error(f"Помилка завантаження {url}: {e}", exc_info=True)
        await wait_msg.edit_text("❌ Виникла помилка при завантаженні відео. Переконайтеся, що посилання правильне і відео доступне.")
