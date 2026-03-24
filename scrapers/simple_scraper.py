import asyncio
from typing import Optional

import aiohttp

from scrapers.base import BaseScraper


class SimpleScraper(BaseScraper):

    def __init__(self, url: str, keyword: str):
        super().__init__(url, keyword)

    async def scrape(self, url: str):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    text = await response.text()
                    return self.keyword in text
        except Exception:
            return False

    async def scrape_multiple(self, urls):
        tasks = [self.scrape(url) for url in urls]
        return await asyncio.gather(*tasks)

    async def check_status(self) -> bool:
        result = await self.scrape(self.url)
        return result
