from datetime import date
from typing import Any, Dict, List, Optional

from app.ingestion.base import DataSourceClient


class AgmarknetClient(DataSourceClient):
    """Pulls mandi (market) price data from the Agmarknet/eNAM dataset
    exposed via the data.gov.in resource API."""

    source_name = "agmarknet"

    async def fetch(
        self,
        state: Optional[str] = None,
        commodity: Optional[str] = None,
        arrival_date: Optional[date] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit,
        }
        if state:
            params["filters[state]"] = state
        if commodity:
            params["filters[commodity]"] = commodity
        if arrival_date:
            params["filters[arrival_date]"] = arrival_date.strftime("%d/%m/%Y")

        payload = await self._get(self.base_url, params)
        records = payload.get("records", [])
        return [self._normalize(r) for r in records]

    @staticmethod
    def _normalize(record: Dict[str, Any]) -> Dict[str, Any]:
        def _num(key: str) -> float:
            try:
                return float(record.get(key, 0) or 0)
            except (TypeError, ValueError):
                return 0.0

        return {
            "source": "agmarknet",
            "state": record.get("state"),
            "district": record.get("district"),
            "market": record.get("market"),
            "commodity": record.get("commodity"),
            "variety": record.get("variety"),
            "grade": record.get("grade"),
            "arrival_date": record.get("arrival_date"),
            "min_price": _num("min_price"),
            "max_price": _num("max_price"),
            "modal_price": _num("modal_price"),
        }
