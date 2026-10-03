from fastapi import FastAPI

from app.api.routes import ingestion, predictions, prices, recommendations

app = FastAPI(title="Price Transparency Engine")

app.include_router(predictions.router)
app.include_router(ingestion.router)
app.include_router(prices.router)
app.include_router(recommendations.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}