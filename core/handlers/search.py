import logging
import random
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
    InputMediaVideo,
)
from aiogram.exceptions import TelegramBadRequest

from core.pexels_client import search_videos, get_best_video_file, get_lowest_video_file
from core.bulk_downloader import create_bulk_pack
from core.downloader import cleanup_file, download_direct_file
from core.state import get_user_state, update_user_state, add_to_cart, clear_cart

router = Router()
logger = logging.getLogger(__name__)


def get_footage_keyboard(
    page: int, total: int, hd_url: str, in_cart: bool, cart_count: int
) -> InlineKeyboardMarkup:
    """Генерує клавіатуру для пагінації та дій з футажем."""
    buttons = []

    # Пагінація
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{page - 1}"))
    nav_row.append(
        InlineKeyboardButton(text=f"{page + 1} з {total}", callback_data="noop")
    )
    if page < total - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    # Дії з відео — БАГ-ФІКС: якщо hd_url порожній, не додаємо url= кнопку
    cart_text = "🛒 В кошику" if in_cart else "🛒 Додати в кошик"
    action_row = [
        InlineKeyboardButton(text="📥 В Telegram", callback_data="download_single")
    ]
    if hd_url:
        action_row.append(InlineKeyboardButton(text="🌐 Оригінал", url=hd_url))
    buttons.append(action_row)

    buttons.append([InlineKeyboardButton(text=cart_text, callback_data="add_cart")])

    if cart_count > 0:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📦 Завантажити ZIP ({cart_count})",
                    callback_data="download_cart",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_footage_page(user_id: int, message: Message, is_edit: bool = False):
    logger.info(
        f"[send_footage_page] викликано для user_id={user_id}, is_edit={is_edit}"
    )
    state = get_user_state(user_id)
    videos = state.get("videos", [])
    page = state.get("page", 0)
    logger.info(
        f"[send_footage_page] Отримано стан: page={page}, відео знайдено={len(videos)}"
    )
    cart = state.get("cart", [])

    if not videos or page >= len(videos):
        if is_edit:
            await message.edit_text("Не знайдено більше футажів.")
        else:
            await message.answer("Не знайдено більше футажів.")
        return

    video = videos[page]
    hd_url = get_best_video_file(video)
    sd_url = get_lowest_video_file(video)

    # БАГ-ФІКС: якщо hd_url порожній — пропускаємо це відео
    if not hd_url:
        logger.warning(
            f"[send_footage_page] Порожній hd_url на сторінці {page}, пропускаю."
        )
        update_user_state(user_id, "page", page + 1)
        await send_footage_page(user_id, message, is_edit=is_edit)
        return

    in_cart = hd_url in cart
    keyboard = get_footage_keyboard(page, len(videos), hd_url, in_cart, len(cart))

    logger.info(
        f"[send_footage_page] Готую відправку: sd_url={sd_url[:50] if sd_url else 'EMPTY'}, hd_url={hd_url[:50]}"
    )

    text = (
        f"🎬 **{state['query'].capitalize()}**\n"
        f"⏱ Тривалість: {video.get('duration', 0)} сек.\n"
        f"👤 Автор: {video.get('user', {}).get('name', 'Невідомий')}"
    )

    try:
        if is_edit:
            logger.info("[send_footage_page] Спроба edit_media/edit_text")
            if sd_url:
                await message.edit_media(
                    InputMediaVideo(media=sd_url, caption=text, parse_mode="Markdown"),
                    reply_markup=keyboard,
                )
            else:
                await message.edit_text(
                    text, parse_mode="Markdown", reply_markup=keyboard
                )
        else:
            logger.info("[send_footage_page] Спроба answer_video/answer")
            if sd_url:
                await message.answer_video(
                    video=sd_url,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )
            else:
                await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
        logger.info("[send_footage_page] Успішно відправлено.")
    except TelegramBadRequest as e:
        # БАГ-ФІКС: 'message is not modified' — не фатальна помилка, просто ігноруємо
        if "message is not modified" in str(e).lower():
            logger.info(
                "[send_footage_page] Повідомлення не змінилось (той самий URL), ігноруємо."
            )
        else:
            logger.error(f"[send_footage_page] TelegramBadRequest: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"[send_footage_page] ПОМИЛКА ВІДПРАВКИ: {e}", exc_info=True)


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("page_"))
async def page_callback(callback: CallbackQuery):
    logger.info(f"[page_callback] Отримано callback: {callback.data}")
    page = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    update_user_state(user_id, "page", page)
    logger.info(f"[page_callback] Стан оновлено, нова сторінка: {page}")

    await send_footage_page(user_id, callback.message, is_edit=True)
    await callback.answer()
    logger.info("[page_callback] Завершено успішно")


@router.callback_query(F.data == "add_cart")
async def add_cart_callback(callback: CallbackQuery):
    logger.info(f"[add_cart_callback] Отримано запит від {callback.from_user.id}")
    user_id = callback.from_user.id
    state = get_user_state(user_id)
    videos = state.get("videos", [])
    page = state.get("page", 0)

    if not videos:
        logger.warning(
            f"[add_cart_callback] Відео не знайдено в стані для користувача {user_id}"
        )
        await callback.answer("Помилка.", show_alert=True)
        return

    hd_url = get_best_video_file(videos[page])
    logger.info(f"[add_cart_callback] Спроба додати в кошик URL: {hd_url[:50]}...")
    if add_to_cart(user_id, hd_url):
        logger.info("[add_cart_callback] Успішно додано в кошик")
        await callback.answer("✅ Додано в кошик!")

        # БАГ-ФІКС: читаємо ОНОВЛЕНИЙ стан після запису в БД для правильного підрахунку кошика
        updated_state = get_user_state(user_id)
        in_cart = True
        keyboard = get_footage_keyboard(
            page, len(videos), hd_url, in_cart, len(updated_state["cart"])
        )
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            logger.info(
                f"[add_cart_callback] Клавіатуру оновлено, кошик тепер: {len(updated_state['cart'])} відео"
            )
        except TelegramBadRequest as e:
            logger.warning(
                f"[add_cart_callback] TelegramBadRequest при оновленні клавіатури: {e}"
            )
        except Exception as e:
            logger.error(
                f"[add_cart_callback] ПОМИЛКА оновлення клавіатури: {e}", exc_info=True
            )
    else:
        logger.info("[add_cart_callback] Вже було у кошику")
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
    try:
        status_msg = await callback.message.answer("⏳ Завантажую відео на сервер...")
        local_path = await download_direct_file(hd_url)
        await status_msg.edit_text("✅ Завантажено! Відправляю...")
        await callback.message.answer_document(
            FSInputFile(local_path, filename=f"footage_{user_id}.mp4"),
            caption="✅ Твій футаж!",
        )
        await status_msg.delete()
        cleanup_file(local_path)
    except Exception as e:
        logger.error(f"Помилка завантаження: {e}")
        await callback.message.answer("❌ Не вдалося завантажити відео.")


@router.callback_query(F.data == "download_cart")
async def download_cart_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = get_user_state(user_id)
    cart = state.get("cart", [])

    if not cart:
        await callback.answer("Кошик порожній!", show_alert=True)
        return

    await callback.answer()
    status_msg = await callback.message.answer(
        f"📦 Пакую {len(cart)} футажів у ZIP-архів..."
    )

    path_or_link, is_link = await create_bulk_pack(cart, user_id)

    if not path_or_link:
        await status_msg.edit_text("❌ Помилка при створенні архіву.")
        return

    if is_link:
        await status_msg.edit_text(
            f"✅ Архів занадто великий для Telegram.\n📥 [Завантажити з GoFile]({path_or_link})",
            parse_mode="Markdown",
        )
    else:
        await status_msg.edit_text("✅ Архів готовий! Надсилаю...")
        doc = FSInputFile(path_or_link)
        await callback.message.answer_document(doc)
        cleanup_file(path_or_link)

    clear_cart(user_id)


@router.message(F.text)
async def message_handler_search(message: Message):
    url = message.text.strip()
    user_id = message.from_user.id

    is_tiktok = "tiktok.com" in url.lower()
    is_youtube = "youtube.com" in url.lower() or "youtu.be" in url.lower()

    if not is_tiktok and not is_youtube:
        if message.chat.type == "private" and not message.web_app_data:
            query = url
            status_msg = await message.reply(
                f"🔍 Шукаю футажі для: <b>{query}</b>...", parse_mode="HTML"
            )

            videos = await search_videos(query, per_page=80)
            if not videos:
                await status_msg.edit_text("❌ Нічого не знайдено.")
                return

            random.shuffle(videos)

            update_user_state(user_id, "query", query)
            update_user_state(user_id, "videos", videos)
            update_user_state(user_id, "page", 0)

            await status_msg.delete()
            await send_footage_page(user_id, message)
