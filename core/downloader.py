import os
import asyncio
import logging
import yt_dlp
import uuid
import subprocess

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
        'outtmpl': output_path,
        'quiet': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'merge_output_format': 'mp4',
    }
    
    loop = asyncio.get_running_loop()
    
    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
            
    return await loop.run_in_executor(None, _download)

async def download_and_process_youtube_video(url: str) -> tuple[str, bool]:
    """
    Завантажує YouTube відео, і якщо потрібно - стискає.
    Повертає (шлях_до_файлу, чи_було_стиснення).
    """
    logger.info(f"Завантажуємо YouTube: {url}")
    file_id = str(uuid.uuid4())
    original_path_tpl = os.path.join(VIDEOS_DIR, f"{file_id}_orig.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'outtmpl': original_path_tpl,
        'quiet': True,
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': ['android']}}
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
            'ffmpeg', '-i', original_path,
            '-vf', 'scale=-2:720',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '28',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y', resized_path
        ]
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
