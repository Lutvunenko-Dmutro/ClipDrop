from typing import Dict, Any
from core.db import init_db, get_state, save_state

# Ініціалізація бази даних при завантаженні модуля
init_db()

def get_user_state(user_id: int) -> Dict[str, Any]:
    return get_state(user_id)

def update_user_state(user_id: int, key: str, value: Any):
    state = get_state(user_id)
    state[key] = value
    save_state(user_id, state)

def add_to_cart(user_id: int, video_url: str) -> bool:
    """Додає відео в кошик, якщо його там ще немає. Повертає True, якщо додано."""
    state = get_state(user_id)
    if video_url not in state["cart"]:
        state["cart"].append(video_url)
        save_state(user_id, state)
        return True
    return False

def clear_cart(user_id: int):
    state = get_state(user_id)
    state["cart"] = []
    save_state(user_id, state)
