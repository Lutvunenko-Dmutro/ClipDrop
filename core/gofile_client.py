import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def get_best_server() -> Optional[str]:
    """Отримує найкращий сервер GoFile для завантаження."""
    url = "https://api.gofile.io/servers"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "ok":
                        servers = data.get("data", {}).get("servers", [])
                        if servers:
                            # Повертаємо ім'я першого сервера (наприклад, "store1")
                            return servers[0].get("name")
        return None
    except Exception as e:
        logger.error(f"Помилка при отриманні сервера GoFile: {e}")
        return None

async def upload_file_to_gofile(file_path: str) -> Optional[str]:
    """
    Завантажує файл на GoFile і повертає публічне посилання (downloadPage).
    """
    server_name = await get_best_server()
    if not server_name:
        logger.error("Не вдалося знайти сервер GoFile для завантаження.")
        return None

    url = f"https://{server_name}.gofile.io/contents/uploadfile"
    
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=file_path.split("/")[-1])
                
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        json_data = await response.json()
                        if json_data.get("status") == "ok":
                            return json_data.get("data", {}).get("downloadPage")
                        else:
                            logger.error(f"GoFile API Error: {json_data}")
                    else:
                        text = await response.text()
                        logger.error(f"GoFile HTTP Error {response.status}: {text}")
        return None
    except Exception as e:
        logger.error(f"Помилка при завантаженні на GoFile: {e}")
        return None
