from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration. Values are overridden via a .env file or
    real environment variables in production/Docker."""

    app_name: str = "Price Transparency & Predictive Analytics Engine"

    database_url: str = "postgresql://postgres:postgres@localhost:5432/price_engine"

    # --- External data sources (see "EXTERNAL DATA SOURCES" box in diagram) ---
    # Agmarknet/eNAM: self-serve key from data.gov.in — see README for signup steps.
    agmarknet_api_key: str = ""
    agmarknet_base_url: str = (
        "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    )
    # IMD Weather: no key needed — these are open GET endpoints. Left here only
    # so IMDWeatherClient's constructor signature matches DataSourceClient's.
    imd_weather_api_key: str = ""
    imd_weather_base_url: str = "https://mausam.imd.gov.in/api"

    msp_data_path: str = "app/data/msp_rates.json"
    model_registry_path: str = "app/ml/artifacts"
    ingestion_interval_minutes: int = 60

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
