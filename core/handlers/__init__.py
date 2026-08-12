from aiogram import Router

from .commands import router as commands_router
from .search import router as search_router
from .downloader import router as downloader_router
from .webapp import router as webapp_router

router = Router()

# Порядок має значення: специфічні спочатку
router.include_router(commands_router)
router.include_router(webapp_router)
router.include_router(downloader_router)
router.include_router(search_router)
