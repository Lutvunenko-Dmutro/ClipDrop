from typing import Dict, Any, List

# Глобальний стан для збереження даних користувачів
# Формат:
# {
#     user_id: {
#         "query": "cars",
#         "videos": [...],
#         "page": 0,
#         "cart": ["url1", "url2"]
#     }
# }
user_states: Dict[int, Dict[str, Any]] = {}

def get_user_state(user_id: int) -> Dict[str, Any]:
    if user_id not in user_states:
        user_states[user_id] = {
            "query": "",
            "videos": [],
            "page": 0,
            "cart": []
        }
    return user_states[user_id]

def update_user_state(user_id: int, key: str, value: Any):
    state = get_user_state(user_id)
    state[key] = value

def add_to_cart(user_id: int, video_url: str) -> bool:
    """Додає відео в кошик, якщо його там ще немає. Повертає True, якщо додано."""
    state = get_user_state(user_id)
    if video_url not in state["cart"]:
        state["cart"].append(video_url)
        return True
    return False

def clear_cart(user_id: int):
    state = get_user_state(user_id)
    state["cart"] = []
