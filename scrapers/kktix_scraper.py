import asyncio

from curl_cffi import requests as curl_requests

from scrapers.base import BaseScraper


class KKTIXScraper(BaseScraper):

    def __init__(self, url: str):
        super().__init__(url, keyword="")
        self.api_url = self.url.replace("/events/", "/g/events/").replace("/registrations/new", "").rstrip("/")
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
            return register_status in ("IN_STOCK", "NEARLY_SOLD_OUT")

        except Exception as e:
            print(f"[ERROR] {e}")
            return False

    def _fetch_data_sync(self) -> dict:
        try:
            response = curl_requests.get(
                self.api_url,
                headers=self.headers,
                timeout=10,
                impersonate="chrome"
            )
            if response.status_code != 200:
                return {}
            return response.json()
        except Exception as e:
            print(f"[ERROR] {e}")
            return {}

    async def fetch_sections(self) -> list[dict]:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, self._fetch_data_sync)
        return data.get("sections", [])

    async def fetch_tickets(self) -> list[dict]:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, self._fetch_data_sync)
        return data.get("tickets", [])

    async def check_specific_tickets(self, ticket_ids: list[int]) -> list[int]:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, self._fetch_data_sync)
        tickets = data.get("tickets", [])
        return [t["id"] for t in tickets if t["id"] in ticket_ids and t.get("in_stock")]

    async def check_status(self) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._check_sync)
