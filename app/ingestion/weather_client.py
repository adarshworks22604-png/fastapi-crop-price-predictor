from typing import Any, Dict, List, Optional

import httpx

from app.ingestion.base import DataSourceClient


class IMDWeatherClient(DataSourceClient):
    """Pulls weather data from IMD's real public GET endpoints
    (mausam.imd.gov.in / city.imd.gov.in). These are NOT registration-based
    — there is no api-key, no signup, no OAuth. They are plain GET calls
    keyed by a numeric station or district id, published in IMD's own API
    doc (mausam.imd.gov.in/Forecast/marquee_data/API_doc.pdf) and free for
    non-commercial use.

    Two real endpoints are wired here:
      - districtwise_rainfall_api.php : returns ALL districts' rainfall in
        one call, no id needed. This is what feeds the price model, since
        MarketPrice rows are keyed by district too.
      - current_wx_api.php?id=<station_id> : current temp/humidity for one
        station (city). Optional enrichment — pass district_station_ids to
        pull a handful of representative cities.
    """

    source_name = "imd_weather"

    RAINFALL_URL = "https://mausam.imd.gov.in/api/districtwise_rainfall_api.php"
    CURRENT_WX_URL = "https://mausam.imd.gov.in/api/current_wx_api.php"

    async def fetch(
        self,
        district: Optional[str] = None,
        station_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        records.extend(await self._fetch_rainfall(district))
        if station_id:
            records.extend(await self._fetch_current_wx(station_id, district))
        return records

    async def _fetch_rainfall(self, district_filter: Optional[str]) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.RAINFALL_URL)
            response.raise_for_status()
            payload = response.json()

        # IMD returns a flat list of district rainfall rows; shape can vary
        # slightly by release, so handle both a bare list and a wrapped dict.
        rows = payload if isinstance(payload, list) else payload.get("data", [])
        results = []
        for row in rows:
            district_name = row.get("District") or row.get("district")
            if district_filter and district_filter.lower() not in str(district_name).lower():
                continue
            results.append(
                {
                    "source": "imd_rainfall",
                    "district": district_name,
                    "date": row.get("Date") or row.get("date"),
                    "rainfall_mm": self._to_float(row.get("Actual") or row.get("actual")),
                    "max_temp_c": None,
                    "min_temp_c": None,
                    "humidity_pct": None,
                }
            )
        return results

    async def _fetch_current_wx(self, station_id: str, district: Optional[str]) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.CURRENT_WX_URL, params={"id": station_id})
            response.raise_for_status()
            payload = response.json()

        row = payload[0] if isinstance(payload, list) and payload else payload
        return [
            {
                "source": "imd_current_wx",
                "district": district,
                "date": row.get("Date") or row.get("date"),
                "rainfall_mm": None,
                "max_temp_c": self._to_float(row.get("Temperature") or row.get("temperature")),
                "min_temp_c": None,
                "humidity_pct": self._to_float(row.get("Humidity") or row.get("humidity")),
            }
        ]

    @staticmethod
    def _to_float(value) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
