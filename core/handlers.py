import logging
import aiohttp
import asyncio
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, InlineQuery, InlineQueryResultVideo, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, URLInputFile, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, Command
import uuid

from core.downloader import download_tiktok_video, download_youtube_rapidapi, cleanup_file
from core.limiter import check_limits, record_request
from core.pexels_client import search_videos, get_best_video_file, get_lowest_video_file
from core.bulk_downloader import create_bulk_pack, download_single_video
from core.state import get_user_state, update_user_state, add_to_cart, clear_cart

router = Router()
logger = logging.getLogger(__name__)

async def resolve_tiktok_redirect(url: str) -> str:
    """Розпаковує коротке TikTok-посилання (vm.tiktok.com) до повного."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=True) as resp:
            return str(resp.url)

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

def get_footage_keyboard(page: int, total: int, hd_url: str, in_cart: bool, cart_count: int) -> InlineKeyboardMarkup:
    """Генерує клавіатуру для пагінації та дій з футажем."""
    buttons = []
    
    # Пагінація
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page+1} з {total}", callback_data="noop"))
    if page < total - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{page+1}"))
    if nav_row:
        buttons.append(nav_row)
        
    # Дії з відео
    cart_text = "🛒 В кошику" if in_cart else "🛒 Додати в кошик"
    buttons.append([
        InlineKeyboardButton(text="📥 В Telegram", callback_data="download_single"),
        InlineKeyboardButton(text="🌐 Оригінал", url=hd_url)
    ])
    
    buttons.append([
        InlineKeyboardButton(text=cart_text, callback_data="add_cart")
    ])
    
    if cart_count > 0:
        buttons.append([
            InlineKeyboardButton(text=f"📦 Завантажити ZIP ({cart_count})", callback_data="download_cart")
        ])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def send_footage_page(user_id: int, message: Message):
    state = get_user_state(user_id)
    videos = state.get("videos", [])
    page = state.get("page", 0)
    cart = state.get("cart", [])
    
    if not videos or page >= len(videos):
        await message.answer("Не знайдено більше футажів.")
        return
        
    video = videos[page]
    hd_url = get_best_video_file(video)
    sd_url = get_lowest_video_file(video)
    
    in_cart = hd_url in cart
    keyboard = get_footage_keyboard(page, len(videos), hd_url, in_cart, len(cart))
    
    text = (
        f"🎬 **{state['query'].capitalize()}**\n"
        f"⏱ Тривалість: {video.get('duration', 0)} сек.\n"
        f"👤 Автор: {video.get('user', {}).get('name', 'Невідомий')}"
    )
    
    # Використовуємо SD відео як прев'ю, якщо воно є, інакше просто текст/картинка
    if sd_url:
        await message.answer_video(video=sd_url, caption=text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@router.callback_query(F.data.startswith("page_"))
async def page_callback(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    update_user_state(user_id, "page", page)
    
    # Видаляємо старе повідомлення і надсилаємо нове, щоб замінити відео
    await callback.message.delete()
    await send_footage_page(user_id, callback.message)
    await callback.answer()

@router.callback_query(F.data == "add_cart")
async def add_cart_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = get_user_state(user_id)
    videos = state.get("videos", [])
    page = state.get("page", 0)
    
    if not videos:
        await callback.answer("Помилка.", show_alert=True)
        return
        
    hd_url = get_best_video_file(videos[page])
    if add_to_cart(user_id, hd_url):
        await callback.answer("✅ Додано в кошик!")
        
        # Оновлюємо клавіатуру
        in_cart = True
        keyboard = get_footage_keyboard(page, len(videos), hd_url, in_cart, len(state["cart"]))
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    else:
        await callback.answer("Вже у кошику!")

@router.callback_query(F.data == "download_single")
async def download_single_callback(callback: CallbackQuery):
    await callback.answer("⏳ Завантажую відео, зачекайте...")
    user_id = callback.from_user.id
    state = get_user_state(user_id)
    videos = state.get("videos", [])
    page = state.get("page", 0)
    
    if not videos:
        return
        
    hd_url = get_best_video_file(videos[page])
    await callback.message.answer_document(URLInputFile(hd_url, filename=f"footage_{user_id}.mp4"), caption="✅ Твій футаж!")

@router.callback_query(F.data == "download_cart")
async def download_cart_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = get_user_state(user_id)
    cart = state.get("cart", [])
    
    if not cart:
        await callback.answer("Кошик порожній!", show_alert=True)
        return
        
    await callback.answer()
    status_msg = await callback.message.answer(f"📦 Пакую {len(cart)} футажів у ZIP-архів...")
    
    path_or_link, is_link = await create_bulk_pack(cart, user_id)
    
    if not path_or_link:
        await status_msg.edit_text("❌ Помилка при створенні архіву.")
        return
        
    if is_link:
        await status_msg.edit_text(f"✅ Архів занадто великий для Telegram.\n📥 [Завантажити з GoFile]({path_or_link})", parse_mode="Markdown")
    else:
        await status_msg.edit_text("✅ Архів готовий! Надсилаю...")
        doc = FSInputFile(path_or_link)
        await callback.message.answer_document(doc)
        cleanup_file(path_or_link)
        
    clear_cart(user_id)

@router.message(F.text)
async def message_handler(message: Message):
    url = message.text.strip()
    user_id = message.from_user.id
    
    # Перевірка на TikTok / YouTube
    is_tiktok = "tiktok.com" in url.lower()
    is_youtube = "youtube.com" in url.lower() or "youtu.be" in url.lower()

    if not is_tiktok and not is_youtube:
        # Відповідаємо тільки в приватних повідомленнях, щоб не спамити в групах
        if message.chat.type == "private" and not message.web_app_data:
            # Якщо це не TikTok і не YouTube, вважаємо це пошуком на Pexels!
            query = url
            status_msg = await message.reply(f"🔍 Шукаю футажі для: **{query}**...", parse_mode="Markdown")
            
            videos = await search_videos(query, per_page=15)
            if not videos:
                await status_msg.edit_text("❌ Нічого не знайдено.")
                return
                
            update_user_state(user_id, "query", query)
            update_user_state(user_id, "videos", videos)
            update_user_state(user_id, "page", 0)
            
            await status_msg.delete()
            await send_footage_page(user_id, message)
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
        
        # Якщо yt-dlp каже, що URL не підтримується
        if "Unsupported URL" in str(e):
            await wait_msg.edit_text("❌ Ти надіслав посилання на головну сторінку або профіль! Будь ласка, відкрий конкретне відео і скопіюй посилання саме на нього.")
        else:
            await wait_msg.edit_text("❌ Не вдалося завантажити відео. Швидше за все, посилання бите, відео видалене, або це приватний акаунт.")

@router.message(F.web_app_data)
async def web_app_data_handler(message: Message):
    """Обробляє дані, надіслані з Web App (JSON з URL)."""
    import json
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
