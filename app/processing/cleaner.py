import pandas as pd


class DataCleaner:
    """The 'clean' half of the Data Processing stage: missing values,
    type coercion, and statistical outlier removal — run before anything
    touches feature engineering or the model."""

    def clean_market_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.dropna(subset=["commodity", "market", "modal_price"]).copy()
        df = df[df["modal_price"] > 0]
        df["arrival_date"] = pd.to_datetime(df["arrival_date"], errors="coerce", dayfirst=True)
        df = df.dropna(subset=["arrival_date"])

        # Remove per-commodity outliers (bad data entry, one-off spikes) via IQR.
        cleaned_parts = []
        for _, group in df.groupby("commodity"):
            q1, q3 = group["modal_price"].quantile([0.25, 0.75])
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            cleaned_parts.append(group[(group["modal_price"] >= lower) & (group["modal_price"] <= upper)])
        return pd.concat(cleaned_parts) if cleaned_parts else df

    def clean_weather(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        for col in ["rainfall_mm", "max_temp_c", "min_temp_c", "humidity_pct"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())
        return df
