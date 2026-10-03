# Price Transparency & Predictive Analytics Engine

Standalone microservice matching the **"Price Transparency & Predictive
Analytics Engine (Python, FastAPI, ML)"** box in your architecture diagram.
It ingests from two real, fully public Government of India data sources,
processes the data, predicts prices with ML, and turns that into a fair
price recommendation — served over REST to your Core Backend / Blockchain
layer.

---

## Part 1 — Key design decisions, explained

### 1. `DataSourceClient` is an abstract base class

```
DataSourceClient (ABC)
   ├── fetch(**params) -> List[Dict]      # abstract, every subclass implements this
   └── _get(url, params)                  # shared HTTP helper (httpx)

AgmarknetClient(DataSourceClient)          # mandi prices
IMDWeatherClient(DataSourceClient)         # weather
```

**Why this matters:** `DataIngestionService` never talks to `httpx` or to
Agmarknet/IMD directly — it only ever calls `client.fetch()`. So when you
add the "Other Govt APIs (Soil, Crop, Yield Data)" source from your diagram
later, you write one new class (e.g. `SoilDataClient(DataSourceClient)`),
implement `fetch()`, register it in `DataIngestionService.__init__`, and
nothing else in the codebase changes — not the DB layer, not the API
routes, not the scheduler. This is the Open/Closed Principle applied to
"we will keep adding data sources for the next six months."

It also means you can unit-test `DataIngestionService`'s orchestration
logic (fan-out across states/commodities, error handling) with a fake
client that returns canned data, without ever hitting a real government
server in your test suite.

### 2. One ML model per commodity, not one global model

```
ModelRegistry (in-memory cache)
   ├── "Onion"  -> PricePredictionModel  (trained only on Onion rows)
   ├── "Tomato" -> PricePredictionModel  (trained only on Tomato rows)
   └── "Wheat"  -> PricePredictionModel  (trained only on Wheat rows)
```

**Why:** Onion is perishable, has no MSP, and swings 3x in a week during a
supply shock. Wheat is storable, has a government-set MSP floor, and moves
slowly and seasonally. Forcing one regression model to learn both patterns
at once means it does a mediocre job on both. A separate
`GradientBoostingRegressor` per commodity, each trained only on its own
price history, does much better with the same amount of code — the
commodity is simply which model object you route the request to, decided
in `ModelRegistry.get(commodity)`.

`ModelRegistry` exists so this doesn't cost you a disk read on every
prediction request: it loads each commodity's `.joblib` file once and
keeps it in memory for the life of the process. Call `.refresh(commodity)`
after a retrain to force the next request to reload.

### 3. Fair price recommendation is a separate layer from the ML model

```
predicted_price = PricePredictionModel.predict(features)   # a number, nothing more
   │
   ▼
FairPriceRecommender.recommend(commodity, predicted_price, grade, distance_km)
   ├── apply MSP floor        (farmer is never paid below government MSP)
   ├── apply quality grade    (Grade A sells for more than Grade C)
   ├── add real logistics cost (distance-based)
   └── cap platform margin    (this is the actual anti-intermediary rule)
```

**Why this has to be a separate class, not a smarter model:** the whole
point of your project is *auditability* — a farmer, a judge, or a
regulator needs to be able to point at the recommended price and ask "why
this number?" and get an answer that isn't "the neural network said so."
`FairPriceRecommender` is deterministic, rule-based, and independently
testable: you can assert `recommend("Wheat", 2000)` returns a price ≥ MSP
without ever touching the ML model. It also means you can change the
margin cap from 12% to 8% by changing one constructor argument — no
retraining required. If this logic were baked into the model's loss
function instead, every policy tweak would mean retraining and you'd have
no way to explain a specific number to a farmer.

### 4. Every prediction and recommendation is written to Postgres

`PricePrediction` and `FairPriceRecommendation` tables log every call with
a timestamp and model version. This gives you a replayable audit trail —
useful both for a hackathon demo ("here's the price we predicted last
Tuesday, here's what it actually sold for") and for the real-world
motivation of the project (someone needs to be able to check the
platform's math after the fact).

---

## Part 2 — Installation guide (public government APIs only)

This service uses exactly two government data sources, and they work
**completely differently** from each other. Worth knowing that going in.

| Source | Auth model | Setup effort |
|---|---|---|
| Agmarknet/eNAM mandi prices (data.gov.in) | Self-serve API key, issued instantly | ~5 minutes, one-time |
| IMD weather (mausam.imd.gov.in) | **No key at all** — plain public GET requests | None |

### Step 1 — Get your Agmarknet / data.gov.in API key

This is the one government source that actually requires signup:

1. Go to **https://data.gov.in** and click **Register** (top right).
2. Sign up with an email + OTP verification — no organizational approval
   needed, this is instant for individuals/students.
3. Once logged in, go to **My Account → API Keys** and copy your key.
   It looks like a long alphanumeric string.
4. (Optional but recommended) Go to the dataset page directly to confirm
   the resource ID hasn't changed:
   **https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity**
   — the "Data API" link on that page shows the exact
   `api.data.gov.in/resource/<uuid>` URL to hit. The code currently uses
   `9ef84268-d588-465a-a308-a864a43d0070`, which is the commonly-cited ID
   for this dataset, but **verify it against the live page** — data.gov.in
   resource IDs occasionally get re-issued when a dataset is republished.
5. Test it directly in a browser before touching the code:
   ```
   https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=YOUR_KEY&format=json&limit=5
   ```
   You should get back JSON with a `records` array containing `state`,
   `market`, `commodity`, `min_price`, `max_price`, `modal_price`, etc.
   If you get an error instead, the resource ID has likely changed — go
   back to the dataset page and grab the current one.

### Step 2 — IMD weather: nothing to sign up for

Unlike Agmarknet, IMD does **not** issue self-serve developer API keys.
Their real registration-based API platform (`api.imd.gov.in`) requires
contacting a nodal officer and is meant for organizations, not individual
projects — not practical for a hackathon timeline.

What IMD *does* publish, and what this service actually uses, is a set of
plain public GET endpoints with no authentication:

```
https://mausam.imd.gov.in/api/districtwise_rainfall_api.php
https://mausam.imd.gov.in/api/current_wx_api.php?id=<station_id>
```

The first one returns rainfall for every district in India in a single
call — no key, no station id needed — which is what `IMDWeatherClient`
uses by default. The second is optional per-city enrichment; station ids
are IMD/WMO 5-digit codes (e.g. `42182` = Delhi Safdarjung) findable via
IMD's city weather page dropdown or their published station lists.

These are documented in IMD's own API doc
(`mausam.imd.gov.in/Forecast/marquee_data/API_doc.pdf`), which states they
are free for non-commercial use. Sanity-check the rainfall endpoint in a
browser before running the service — if IMD has changed the response
shape since this was written, `IMDWeatherClient._fetch_rainfall` may need
a small field-name tweak (it already tries a couple of common key
spellings defensively).

### Step 3 — Local setup

```bash
git clone <this project, or unzip it>
cd price-transparency-engine

# 1. Postgres — either install locally or run via Docker:
docker run --name price-engine-db -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=price_engine -p 5432:5432 -d postgres:16

# 2. Python deps
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Config
cp .env.example .env
# edit .env: paste your AGMARKNET_API_KEY, adjust DATABASE_URL if not using the Docker default

# 4. Start the API (this also creates the DB tables on first run)
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` — you'll see the Swagger UI with all
four route groups.

### Step 4 — Pull real data and train

```bash
# Trigger ingestion for a few states/commodities (uses your real Agmarknet key)
curl -X POST http://localhost:8000/api/v1/ingestion/trigger \
  -H "Content-Type: application/json" \
  -d '{"states": ["Uttar Pradesh"], "commodities": ["Onion", "Wheat"]}'

# Check it landed in Postgres
curl "http://localhost:8000/api/v1/prices/?commodity=Onion&limit=5"

# Once you have a few days/weeks of data, train the models
python -m app.ml.train
```

`app/ml/train.py` needs at least ~20 clean rows per commodity to fit a
model (see the `ValueError` in `PricePredictionModel.train`), so for a
hackathon demo you'll likely want to trigger ingestion across a wider date
range or several states before your first training run.

### Step 5 — Try a fair price recommendation end to end

```bash
curl -X POST http://localhost:8000/api/v1/recommendations/ \
  -H "Content-Type: application/json" \
  -d '{
        "commodity": "Wheat",
        "market": "Ghaziabad",
        "target_date": "2026-09-10",
        "grade": "FAQ",
        "distance_km": 40
      }'
```

You'll get back `predicted_market_price`, `msp_floor`, `recommended_farmer_price`,
`recommended_consumer_price`, and `margin_band` — the full chain from raw
mandi data to an explainable, auditable number.

### Honest caveats

- The Agmarknet resource ID and IMD rainfall response field names were
  verified against public documentation and cited tutorials as of this
  write-up, but government API schemas do drift over time — the Step 1
  and Step 2 browser sanity-checks above exist specifically so you catch
  a schema change before it silently breaks ingestion.
- IMD's public GET endpoints are meant for non-commercial use; fine for a
  hackathon/academic project, but re-check IMD's terms before any
  commercial deployment.
- `Base.metadata.create_all` (no Alembic migrations) is fine for this
  demo; add real migrations before this touches production data.
