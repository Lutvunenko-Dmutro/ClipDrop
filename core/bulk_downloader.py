import os
import aiohttp
import asyncio
import zipfile
import shutil
import logging
from typing import Tuple, Optional, List
from core.gofile_client import upload_file_to_gofile

logger = logging.getLogger(__name__)

async def download_single_video(session: aiohttp.ClientSession, url: str, filepath: str):
    """Скачує одне відео і зберігає за вказаним шляхом."""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                return True
            return False
    except Exception as e:
        logger.error(f"Помилка завантаження відео {url}: {e}")
        return False

async def create_bulk_pack(video_urls: List[str], user_id: int) -> Tuple[Optional[str], bool]:
    """
    Скачує відео за списком URL, пакує в ZIP.
    Повертає Tuple (path_or_link, is_link).
    is_link = True, якщо файл занадто великий і був завантажений на GoFile.
    """
    if not video_urls:
        return None, False

    # Створюємо тимчасову папку
    pack_dir = f"videos/pack_{user_id}_{len(video_urls)}items"
    os.makedirs(pack_dir, exist_ok=True)

    tasks = []
    async with aiohttp.ClientSession() as session:
        for idx, video_url in enumerate(video_urls):
            filepath = os.path.join(pack_dir, f"footage_{idx+1}.mp4")
            tasks.append(download_single_video(session, video_url, filepath))
        
        if not tasks:
            shutil.rmtree(pack_dir, ignore_errors=True)
            return None, False

        # Чекаємо завершення всіх завантажень
        await asyncio.gather(*tasks)

    # Архівація
    zip_path = f"{pack_dir}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(pack_dir):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)

    # Видаляємо папку після архівації
    shutil.rmtree(pack_dir, ignore_errors=True)

    # Перевіряємо розмір
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    logger.info(f"Створено архів {zip_path}, розмір: {size_mb:.2f} MB")

    if size_mb > 45.0:
        logger.info("Розмір перевищує ліміт Telegram. Завантажуємо на GoFile...")
        link = await upload_file_to_gofile(zip_path)
        os.remove(zip_path)  # видаляємо локальний ZIP після завантаження
        if link:
            return link, True
        return None, False

    # Повертаємо локальний шлях
    return zip_path, False
