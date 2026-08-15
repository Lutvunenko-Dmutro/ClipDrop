import asyncio, aiohttp, re

async def test():
    async with aiohttp.ClientSession() as session:
        url = 'https://www.myinstants.com/ru/search/?name=путин'
        async with session.get(url) as r:
            html = await r.text()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            pattern = r"onclick=\"play\('([^']+)'[^)]*\)\".*?class=\"[^\"]*instant-link[^\"]*\"[^>]*>([^<]+)</a>"
            matches = re.findall(pattern, html, re.DOTALL)
            print('Matches found via regex:', len(matches))
            if matches:
                print('First match:', matches[0])

asyncio.run(test())
