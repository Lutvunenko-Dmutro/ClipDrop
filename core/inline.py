import re
import asyncio
import aiohttp
import logging
from aiogram import Router, F
from aiogram.types import InlineQuery, InlineQueryResultAudio
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from aiogram.exceptions import TelegramBadRequest
from deep_translator import GoogleTranslator

router = Router()
logger = logging.getLogger(__name__)

MYINSTANTS_BASE_URL = "https://www.myinstants.com"

CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'є': 'ye', 'ж': 'zh', 
    'з': 'z', 'и': 'i', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 
    'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ь': '', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Є': 'Ye', 'Ж': 'Zh',
    'З': 'Z', 'И': 'I', 'І': 'I', 'Ї': 'Yi', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F',
    'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ь': '', 'Ю': 'Yu', 'Я': 'Ya'
}

def normalize_ukrainian(text: str) -> str:
    replacements = {'і': 'и', 'І': 'И', 'ї': 'ий', 'Ї': 'Ий', 'є': 'е', 'Є': 'Е'}
    for ua, ru in replacements.items():
        text = text.replace(ua, ru)
    return text

def transliterate_to_latin(text: str) -> str:
    return "".join(CYRILLIC_TO_LATIN.get(c, c) for c in text)

async def translate_query(query: str, target_lang: str) -> str:
    try:
        def do_translate():
            return GoogleTranslator(source='auto', target=target_lang).translate(query)
        return await asyncio.to_thread(do_translate)
    except Exception as e:
        logger.error(f"Помилка перекладу '{query}' на {target_lang}: {e}")
        return ""

async def fetch_myinstants(session, url: str):
    """Fetches HTML and parses sounds using regex."""
    try:
        async with session.get(url, timeout=5) as response:
            if response.status == 200:
                html = await response.text()
                pattern = r"onclick=\"play\('([^']+)'[^)]*\)\".*?class=\"[^\"]*instant-link[^\"]*\"[^>]*>([^<]+)</a>"
                return re.findall(pattern, html, re.DOTALL)
    except Exception as e:
        logger.error(f"Помилка парсингу {url}: {e}")
    return []

@router.inline_query()
async def search_myinstants(inline_query: InlineQuery):
    query = inline_query.query.strip()
    logger.info(f"ОТРИМАНО ІНЛАЙН ЗАПИТ: '{query}'")
    results = []
    
    try:
        async with aiohttp.ClientSession() as session:
            if not query:
                # Тренди локальні
                matches = await fetch_myinstants(session, f"{MYINSTANTS_BASE_URL}/ru/index/ru/")
                for idx, (audio_path, title) in enumerate(matches[:50]):
                    results.append(
                        InlineQueryResultAudio(
                            id=f"trend_{idx}",
                            audio_url=f"{MYINSTANTS_BASE_URL}{audio_path}",
                            title=f"🔥 {title.strip()}"
                        )
                    )
            else:
                # 1. Базові адаптації
                norm_query = normalize_ukrainian(query)
                trans_query = transliterate_to_latin(query)
                
                # 2. ШІ-переклад (виконується паралельно)
                ru_query, en_query = await asyncio.gather(
                    translate_query(query, 'ru'),
                    translate_query(query, 'en')
                )
                
                # 3. Збираємо всі можливі варіанти пошуку
                search_terms = {query, norm_query, trans_query, ru_query, en_query}
                
                # 4. Fuzzy Fallback: розбиття на окремі слова, якщо фраза довга
                def add_words(text: str):
                    if text and len(text.split()) > 1:
                        for w in text.split():
                            if len(w) > 2: # Ігноруємо короткі прийменники
                                search_terms.add(w)
                
                add_words(query)
                add_words(ru_query)
                add_words(en_query)
                
                # 5. Генеруємо URL для кожного терміну
                urls_to_fetch = set()
                for term in search_terms:
                    if not term:
                        continue
                    # Якщо є кирилиця — шукаємо в локальній базі, інакше в глобальній
                    if re.search(r'[а-яА-ЯёЁїЇіІєЄ]', term):
                        urls_to_fetch.add(f"{MYINSTANTS_BASE_URL}/ru/search/?name={term}")
                    else:
                        urls_to_fetch.add(f"{MYINSTANTS_BASE_URL}/search/?name={term}")
                
                # 6. Робимо всі запити одночасно
                tasks = [fetch_myinstants(session, url) for url in urls_to_fetch]
                responses = await asyncio.gather(*tasks)
                
                # 7. Об'єднання та видалення дублікатів
                seen_urls = set()
                all_matches = []
                for response_matches in responses:
                    for audio_path, title in response_matches:
                        if audio_path not in seen_urls:
                            seen_urls.add(audio_path)
                            all_matches.append((audio_path, title))
                
                if not all_matches:
                    results.append(
                        InlineQueryResultArticle(
                            id="not_found",
                            title=f"❌ За запитом '{query}' нічого не знайдено",
                            description="Я намагався перекласти та шукати окремі слова, але таких звуків немає.",
                            input_message_content=InputTextMessageContent(
                                message_text=f"Я шукав звук '{query}' (і його переклади), але на MyInstants нічого схожого не існує 😢"
                            )
                        )
                    )
                else:
                    for idx, (audio_path, title) in enumerate(all_matches[:50]):
                        results.append(
                            InlineQueryResultAudio(
                                id=f"sound_{idx}",
                                audio_url=f"{MYINSTANTS_BASE_URL}{audio_path}",
                                title=title.strip()
                            )
                        )
    except Exception as e:
        logger.error(f"Помилка обробки інлайн запиту: {e}", exc_info=True)

    try:
        await inline_query.answer(results, cache_time=5)
    except TelegramBadRequest as e:
        logger.error(f"TelegramBadRequest: {e}")
