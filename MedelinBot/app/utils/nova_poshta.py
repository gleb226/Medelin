
import aiohttp
import logging
from app.common.config import NP_API_KEY

logger = logging.getLogger(__name__)

class NovaPoshtaClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.novaposhta.ua/v2.0/json/"
        self._session = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session

    async def call(self, model: str, method: str, params: dict):
        payload = {
            "apiKey": self.api_key,
            "modelName": model,
            "calledMethod": method,
            "methodProperties": params
        }
        session = await self.get_session()
        try:
            async with session.post(self.url, json=payload) as resp:
                data = await resp.json()
                if not data.get('success'):
                    logger.error(f"NP API Error: {data.get('errors')}")
                    return []
                return data.get('data', [])
        except Exception as e:
            logger.error(f"NP API Exception: {e}")
            return []

    async def search_settlements(self, name: str):
        res = await self.call("Address", "searchSettlements", {"CityName": name, "Limit": "20"})
        if isinstance(res, list) and len(res) > 0 and 'Addresses' in res[0]:
            return res[0]['Addresses']
        return []

    async def get_warehouses(self, city_ref: str, search: str = ""):
        params = {"CityRef": city_ref, "Limit": "100"}
        if search:
            params["FindByString"] = search
        res = await self.call("Address", "getWarehouses", params)
        if not res:
            # Try as SettlementRef if CityRef failed or returned nothing
            params = {"SettlementRef": city_ref, "Limit": "100"}
            if search:
                params["FindByString"] = search
            res = await self.call("Address", "getWarehouses", params)
        return res

    async def search_streets(self, city_ref: str, search: str):
        return await self.call("Address", "searchSettlementStreets", {
            "StreetName": search,
            "SettlementRef": city_ref,
            "Limit": "20"
        })

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

np_client = NovaPoshtaClient(NP_API_KEY)
