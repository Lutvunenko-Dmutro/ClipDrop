import os
from aiohttp import web
from core.pexels_client import search_videos, get_best_video_file, get_lowest_video_file

# ============================================================
#  Хендлери веб-сервера
# ============================================================
async def health_check(request):
    """Для Render health check та браузерної перевірки."""
    return web.Response(text="✅ ClipDrop Bot is running!")

async def web_app_handler(request):
    """Віддає сторінку Web App (index.html)."""
    try:
        with open("public/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        return web.Response(text=html, content_type="text/html")
    except FileNotFoundError:
        return web.Response(text="Помилка: Файл index.html не знайдено", status=404)

async def api_search(request):
    """API для пошуку футажів з Web App."""
    query = request.query.get("q", "")
    page = int(request.query.get("page", 1))
    if not query:
        return web.json_response({"videos": []})
        
    raw_videos = await search_videos(query, per_page=15, page=page)
    videos = []
    for vid in raw_videos:
        hd_url = get_best_video_file(vid)
        sd_url = get_lowest_video_file(vid)
        if hd_url and sd_url:
            videos.append({
                "id": vid.get("id"),
                "sd_url": sd_url,
                "hd_url": hd_url,
                "duration": vid.get("duration", 0),
                "author": vid.get("user", {}).get("name", "Невідомий")
            })
            
    return web.json_response({"videos": videos})
