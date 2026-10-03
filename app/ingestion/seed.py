import asyncio
import logging

from app.db.session import SessionLocal
from app.ingestion.ingestion_service import DataIngestionService

logging.basicConfig(level=logging.INFO)

# Keep this small for the first run — just enough to unblock training.
# Expand once you confirm it works end-to-end.
STATES = ["Uttar Pradesh", "Maharashtra"]
COMMODITIES = ["Potato", "Onion", "Tomato"]


async def main():
    db = SessionLocal()
    service = DataIngestionService()
    try:
        await service.run_full_ingestion(db, commodities=COMMODITIES, states=STATES)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())