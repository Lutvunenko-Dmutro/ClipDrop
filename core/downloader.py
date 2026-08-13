import os
import asyncio
import logging
import yt_dlp
import uuid
import subprocess
import re
import aiohttp
from aiogram import types

logger = logging.getLogger(__name__)

# Папка для тимчасових відео
VIDEOS_DIR = "videos"
os.makedirs(VIDEOS_DIR, exist_ok=True)


async def download_tiktok_video(url: str) -> str:
    """Завантажує відео з TikTok."""
    logger.info(f"Завантажуємо TikTok: {url}")
    file_id = str(uuid.uuid4())
    output_path = os.path.join(VIDEOS_DIR, f"{file_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": output_path,
        "quiet": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "merge_output_format": "mp4",
    }

    loop = asyncio.get_running_loop()

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    return await loop.run_in_executor(None, _download)


async def download_youtube_rapidapi(
    url: str, message: types.Message
) -> tuple[str, bool]:
    """
    Завантажує YouTube відео через RapidAPI з відображенням прогресу.
    Повертає (шлях_до_файлу, чи_було_стиснення).
    """
    RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
    RAPIDAPI_HOST = "youtube-video-fast-downloader-24-7.p.rapidapi.com"

    if not RAPIDAPI_KEY:
        logger.warning(
            "RAPIDAPI_KEY не знайдено, використовуємо yt-dlp як запасний варіант."
        )
        return await download_and_process_youtube_video(url)

    logger.info(f"RapidAPI: Завантажуємо {url}")

    # Витягуємо ID відео
    match = re.search(r"(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})(?:\?|&|\/|$)", url)
    if not match:
        logger.error("Не вдалося знайти ID відео")
        raise ValueError("Неправильне посилання на YouTube")
    video_id = match.group(1)

    api_url = f"https://{RAPIDAPI_HOST}/download_video/{video_id}"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    try:
        # Даємо API 60 секунд на відповідь, бо воно іноді довго думає
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        ) as session:
            try:
                await message.edit_text("⏳ Зв'язуємось з сервером RapidAPI...")
            except:
                pass

            async with session.get(api_url, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"RapidAPI помилка: {resp.status} - {text}")
                    # Фоллбек на yt-dlp
                    return await download_and_process_youtube_video(url)
                data = await resp.json()

            file_url = data.get("file") or data.get("reserved_file")
            if not file_url:
                logger.error("API не повернуло посилання на файл")
                return await download_and_process_youtube_video(url)

            # Чекаємо поки відео буде готове
            wait_time = 0
            while wait_time < 300:
                async with session.head(
                    file_url,
                    headers={"User-Agent": headers["User-Agent"]},
                    allow_redirects=True,
                ) as head_resp:
                    if head_resp.status == 200:
                        break  # Готово!
                    elif head_resp.status in (404, 403):
                        await asyncio.sleep(5)
                        wait_time += 5
                        if wait_time % 10 == 0:
                            try:
                                await message.edit_text(
                                    f"⏳ Сервер RapidAPI готує відео...\nОчікуємо (минуло {wait_time} сек)"
                                )
                            except Exception:
                                pass  # Ігноруємо помилки, якщо текст не змінився
                    else:
                        logger.warning(
                            f"Неочікувана відповідь при перевірці файлу: {head_resp.status}"
                        )
                        break

            if wait_time >= 300:
                logger.error("Перевищено час очікування готовності відео")
                return await download_and_process_youtube_video(url)

            try:
                await message.edit_text("⏳ Відео готове! Завантажуємо у Telegram...")
            except:
                pass

            file_id_uuid = str(uuid.uuid4())
            output_path = os.path.join(VIDEOS_DIR, f"{file_id_uuid}.mp4")

            async with session.get(
                file_url, headers={"User-Agent": headers["User-Agent"]}
            ) as dl_resp:
                if dl_resp.status == 200:
                    with open(output_path, "wb") as f:
                        while True:
                            chunk = await dl_resp.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                else:
                    logger.error(f"Помилка при завантаженні файлу: {dl_resp.status}")
                    return await download_and_process_youtube_video(url)

            return output_path, False

    except Exception as e:
        logger.error(f"Помилка RapidAPI: {e}")
        # Якщо все падає, фоллбек на старий надійний(або не дуже) yt-dlp
        return await download_and_process_youtube_video(url)


async def download_and_process_youtube_video(url: str) -> tuple[str, bool]:
    """
    Завантажує YouTube відео, і якщо потрібно - стискає.
    Повертає (шлях_до_файлу, чи_було_стиснення).
    """
    logger.info(f"Завантажуємо YouTube: {url}")
    file_id = str(uuid.uuid4())
    original_path_tpl = os.path.join(VIDEOS_DIR, f"{file_id}_orig.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "outtmpl": original_path_tpl,
        "quiet": True,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "extractor_args": {"youtube": {"player_client": ["android"]}},
    }

    loop = asyncio.get_running_loop()

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    original_path = await loop.run_in_executor(None, _download)

    # Перевіряємо розмір
    file_size_mb = os.path.getsize(original_path) / (1024 * 1024)
    if file_size_mb <= 49.5:
        # Нормальний розмір, віддаємо як є
        return original_path, False

    logger.info(f"Відео {file_size_mb:.2f}MB, починаємо стиснення через ffmpeg...")
    resized_path = os.path.join(VIDEOS_DIR, f"{file_id}_resized.mp4")

    # Запускаємо ffmpeg для стиснення
    def _compress():
        command = [
            "ffmpeg",
            "-i",
            original_path,
            "-vf",
            "scale=-2:720",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            "-y",
            resized_path,
        ]
        process = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if process.returncode != 0:
            logger.error(f"Помилка ffmpeg: {process.stderr.decode()}")
            raise RuntimeError("Помилка при стисненні відео")
        return resized_path

    compressed_path = await loop.run_in_executor(None, _compress)

    # Видаляємо оригінал, щоб не займав місце
    try:
        os.remove(original_path)
    except Exception as e:
        logger.warning(f"Не вдалося видалити оригінал {original_path}: {e}")

    return compressed_path, True


def cleanup_file(filepath: str):
    """Видаляє тимчасовий файл."""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Файл видалено: {filepath}")
    except Exception as e:
        logger.error(f"Помилка видалення файлу {filepath}: {e}")


async def compress_video(original_path: str, file_id: str) -> str:
    """Стискає відео за допомогою ffmpeg, щоб воно влізло в ліміти Telegram (50 МБ)."""
    resized_path = os.path.join(VIDEOS_DIR, f"{file_id}_resized.mp4")
    loop = asyncio.get_running_loop()

    def _compress():
        command = [
            "ffmpeg",
            "-i",
            original_path,
            "-vf",
            "scale=-2:720",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            "-y",
            resized_path,
        ]
        process = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if process.returncode != 0:
            logger.error(f"Помилка ffmpeg: {process.stderr.decode()}")
            raise RuntimeError("Помилка при стисненні відео")
        return resized_path

    compressed_path = await loop.run_in_executor(None, _compress)
    try:
        os.remove(original_path)
    except Exception as e:
        logger.warning(f"Не вдалося видалити оригінал {original_path}: {e}")

    return compressed_path


async def download_direct_file(url: str, ext: str = "mp4") -> str:
    """Завантажує файл за прямим посиланням і стискає його, якщо він > 49 MB."""
    file_id = str(uuid.uuid4())
    output_path = os.path.join(VIDEOS_DIR, f"{file_id}.{ext}")

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(output_path, "wb") as f:
                    while True:
                        chunk = await resp.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)

                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                if file_size_mb > 49.5:
                    logger.info(
                        f"Файл {file_size_mb:.2f} МБ завеликий, починаю стиснення..."
                    )
                    output_path = await compress_video(output_path, file_id)

                return output_path
            else:
                raise RuntimeError(f"Не вдалося завантажити файл: HTTP {resp.status}")
