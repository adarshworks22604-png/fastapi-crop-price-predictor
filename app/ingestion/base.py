from abc import ABC, abstractmethod
from typing import Any, Dict, List

import httpx


class DataSourceClient(ABC):
    """Every external API integration (Agmarknet, IMD Weather, future
    govt APIs) implements this contract so the ingestion service can
    treat them interchangeably."""

    source_name: str = "base"

    def __init__(self, base_url: str, api_key: str = "", timeout: float = 15.0):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    @abstractmethod
    async def fetch(self, **params) -> List[Dict[str, Any]]:
        """Fetch and normalize raw records from the external API.
        Must always return a list of plain dicts ready for the DB layer."""
        raise NotImplementedError

    async def _get(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
