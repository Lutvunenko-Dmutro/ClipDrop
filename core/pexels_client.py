import os
import aiohttp
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

async def search_videos(query: str, per_page: int = 10, page: int = 1) -> List[Dict[str, Any]]:
    """
    Шукає відео на Pexels за запитом.
    Повертає список словників з інформацією про відео.
    """
    if not PEXELS_API_KEY:
        logger.error("PEXELS_API_KEY не налаштовано!")
        return []

    url = "https://api.pexels.com/videos/search"
    headers = {
        "Authorization": PEXELS_API_KEY
    }
    params = {
        "query": query,
        "per_page": per_page,
        "page": page
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("videos", [])
                else:
                    text = await response.text()
                    logger.error(f"Pexels API Error {response.status}: {text}")
                    return []
    except Exception as e:
        logger.error(f"Помилка при запиті до Pexels: {e}")
        return []

def get_best_video_file(video: Dict[str, Any]) -> str:
    """
    Вибирає найкращий відеофайл з доступних (найвища якість, зазвичай HD).
    """
    video_files = video.get("video_files", [])
    if not video_files:
        return ""
    
    # Відсортуємо за шириною (width) по спаданню
    sorted_files = sorted(video_files, key=lambda x: x.get("width", 0), reverse=True)
    return sorted_files[0].get("link", "")

def get_lowest_video_file(video: Dict[str, Any]) -> str:
    """
    Вибирає найменший відеофайл з доступних (найнижча якість для прев'ю).
    """
    video_files = video.get("video_files", [])
    if not video_files:
        return ""
    
    # Відсортуємо за шириною (width) по зростанню
    sorted_files = sorted(video_files, key=lambda x: x.get("width", 0))
    return sorted_files[0].get("link", "")
