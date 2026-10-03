import pandas as pd
import xgboost as xgb
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from app.db.session import SessionLocal



ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def load_training_data() -> pd.DataFrame:
    """Pull all ingested Agmarknet records from your db."""
    session = SessionLocal()
    try:
        query = """
            SELECT state, commodity, market, arrival_date, modal_price
            FROM market_prices
            WHERE modal_price IS NOT NULL AND arrival_date IS NOT NULL
        """
        df = pd.read_sql(query, session.bind)
    finally:
        session.close()

    # arrival_date is stored as String — parse defensively (Agmarknet often uses DD/MM/YYYY)
    df["arrival_date"] = pd.to_datetime(df["arrival_date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["arrival_date"])
    return df.sort_values("arrival_date")

def build_encoders(df: pd.DataFrame) -> dict:
    encoders = {}
    for col in ["state", "commodity"]:
        unique_vals = sorted(df[col].dropna().unique())
        encoders[col] = {val: i for i, val in enumerate(unique_vals)}
    return encoders


def build_features(df: pd.DataFrame, encoders: dict) -> pd.DataFrame:
    df = df.sort_values(["state", "commodity", "market", "arrival_date"])
    grp = df.groupby(["state", "commodity", "market"])["modal_price"]

    df["lag_1"] = grp.shift(1)
    df["rolling_7_mean"] = grp.transform(lambda s: s.shift(1).rolling(7).mean())
    df["rolling_30_mean"] = grp.transform(lambda s: s.shift(1).rolling(30).mean())
    df["rolling_7_std"] = grp.transform(lambda s: s.shift(1).rolling(7).std())

    df["day_of_week"] = df["arrival_date"].dt.dayofweek
    df["day_of_month"] = df["arrival_date"].dt.day
    df["month"] = df["arrival_date"].dt.month

    df["state_enc"] = df["state"].map(encoders["state"])
    df["commodity_enc"] = df["commodity"].map(encoders["commodity"])

    return df.dropna(subset=["lag_1", "rolling_7_mean", "rolling_30_mean", "rolling_7_std"])


def main():
    print("Loading data...")
    df = load_training_data()
    print(f"Loaded {len(df)} rows")

    encoders = build_encoders(df)
    df = build_features(df, encoders)

    feature_cols = [
        "day_of_week", "day_of_month", "month",
        "state_enc", "commodity_enc",
        "lag_1", "rolling_7_mean", "rolling_30_mean", "rolling_7_std",
    ]
    X = df[feature_cols]
    y = df["modal_price"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False  # time series: don't shuffle
    )

    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    print(f"MAE: {mae:.2f} | R²: {r2:.4f}")

    model.save_model(str(ARTIFACTS_DIR / "price_model.json"))
    with open(ARTIFACTS_DIR / "encoders.json", "w") as f:
        json.dump(encoders, f)

    print(f"Saved model + encoders to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()