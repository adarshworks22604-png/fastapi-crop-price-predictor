import pandas as pd


class FeatureEngineer:
    """Turns cleaned price + weather rows into an ML-ready feature matrix:
    calendar features, lag/rolling price features per commodity+market
    series, and merged weather signals."""

    def build_features(self, prices: pd.DataFrame, weather: pd.DataFrame = None) -> pd.DataFrame:
        if prices.empty:
            return prices

        df = prices.sort_values(["commodity", "market", "arrival_date"]).copy()

        df["day_of_week"] = df["arrival_date"].dt.dayofweek
        df["month"] = df["arrival_date"].dt.month
        df["day_of_year"] = df["arrival_date"].dt.dayofyear

        grouped = df.groupby(["commodity", "market"])["modal_price"]
        df["price_lag_1"] = grouped.shift(1)
        df["price_lag_7"] = grouped.shift(7)
        df["rolling_mean_7"] = grouped.transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
        df["rolling_std_7"] = grouped.transform(lambda s: s.shift(1).rolling(7, min_periods=1).std())
        df["price_spread"] = df["max_price"] - df["min_price"]

        for col in ["rainfall_mm", "max_temp_c", "min_temp_c", "humidity_pct"]:
            df[col] = None

        if weather is not None and not weather.empty and "district" in df.columns:
            weather_renamed = weather.rename(columns={"date": "arrival_date"})
            merge_cols = ["district", "arrival_date", "rainfall_mm", "max_temp_c", "min_temp_c", "humidity_pct"]
            df = df.drop(columns=["rainfall_mm", "max_temp_c", "min_temp_c", "humidity_pct"]).merge(
                weather_renamed[merge_cols], on=["district", "arrival_date"], how="left"
            )

        df = df.dropna(subset=["price_lag_1"])
        return df

    @staticmethod
    def feature_columns() -> list:
        return [
            "day_of_week", "month", "day_of_year",
            "price_lag_1", "price_lag_7", "rolling_mean_7", "rolling_std_7",
            "price_spread", "rainfall_mm", "max_temp_c", "min_temp_c", "humidity_pct",
        ]
