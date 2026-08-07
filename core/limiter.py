import time
import logging
import os
from datetime import date

logger = logging.getLogger(__name__)

# ============================================================
#  Налаштування
# ============================================================
# OWNER_ID береться з змінної оточення (.енв файл або Render Environment)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # 0 = нікому не буде прав власника
DAILY_LIMIT = 5            # Максимум відео на добу для звичайного юзера
FLOOD_COOLDOWN = 30        # Мінімум секунд між запитами (Anti-flood)

# ============================================================
#  Сховище (в пам'яті, скидається при рестарті бота)
# ============================================================
# Структура: { user_id: {"count": int, "reset_date": date, "last_request_ts": float} }
_user_data: dict[int, dict] = {}

def _get_user(user_id: int) -> dict:
    """Повертає дані юзера, скидаючи лічильник якщо настала нова доба."""
    today = date.today()
    if user_id not in _user_data:
        _user_data[user_id] = {"count": 0, "reset_date": today, "last_request_ts": 0.0}
    
    user = _user_data[user_id]
    # Якщо новий день — скидаємо лічильник
    if user["reset_date"] < today:
        user["count"] = 0
        user["reset_date"] = today
    
    return user


def check_limits(user_id: int) -> tuple[bool, str]:
    """
    Перевіряє всі ліміти для юзера.
    
    Повертає (allowed: bool, reason: str).
    Якщо allowed=True — запит дозволений.
    Якщо allowed=False — reason містить текст для відповіді юзеру.
    """
    # Власник бота — завжди пропускаємо
    if user_id == OWNER_ID:
        logger.info(f"Owner request — no limits applied.")
        return True, ""
    
    user = _get_user(user_id)
    now = time.time()
    
    # Перевірка Anti-flood
    elapsed = now - user["last_request_ts"]
    if elapsed < FLOOD_COOLDOWN:
        wait_sec = int(FLOOD_COOLDOWN - elapsed) + 1
        logger.warning(f"User {user_id} flood detected (waited only {elapsed:.1f}s)")
        return False, (
            f"⏱ Не так швидко! Зачекайте ще **{wait_sec} сек.** перед наступним запитом.\n"
            f"_(Захист від спаму)_"
        )
    
    # Перевірка денного ліміту
    if user["count"] >= DAILY_LIMIT:
        logger.warning(f"User {user_id} hit daily limit ({DAILY_LIMIT})")
        return False, (
            f"🚫 Ти вичерпав денний ліміт **{DAILY_LIMIT} відео**.\n"
            f"Ліміт оновиться опівночі. Повертайся завтра! 😊"
        )
    
    return True, ""


def record_request(user_id: int):
    """
    Фіксує успішний запит юзера.
    Викликати ПІСЛЯ того, як запит пройшов всі перевірки.
    """
    if user_id == OWNER_ID:
        return  # Власника не рахуємо
    
    user = _get_user(user_id)
    user["count"] += 1
    user["last_request_ts"] = time.time()
    logger.info(f"User {user_id}: {user['count']}/{DAILY_LIMIT} videos today")
