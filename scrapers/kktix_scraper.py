import asyncio

from curl_cffi import requests as curl_requests

from scrapers.base import BaseScraper


class KKTIXScraper(BaseScraper):

    def __init__(self, url: str):
        super().__init__(url, keyword="")
        self.api_url = self.url.replace("/events/", "/g/events/").replace("/registrations/new", "/register_info")
        self.headers = {
            "Accept": "application/json",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _check_sync(self) -> bool:

        try:
            response = curl_requests.get(
                self.api_url,
                headers=self.headers,
                timeout=10,
                impersonate="chrome"
            )

            if response.status_code != 200:
                print(f"[ERROR] API HTTP {response.status_code}")
                return False

            data = response.json()
            register_status = data.get("register_status", "")

            if register_status in ("IN_STOCK", "NEARLY_SOLD_OUT"):
                return True

            sections = data.get("sections", [])
            for section in sections:
                if section.get("stock_level") in ("IN_STOCK", "NEARLY_SOLD_OUT"):
                    return True

            return False

        except Exception as e:
            print(f"[ERROR] {e}")
            return False

    async def check_status(self) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._check_sync)
