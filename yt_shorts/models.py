"""Exploratory models of observed views, not a future-virality benchmark."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

NUMERIC = ["subscriberCount", "videoCount", "title_length", "channel_age_days",
           "channel_freq", "duration_seconds", "published_days", "year", "month", "day"]
CATEGORICAL = ["day_name", "is_holiday"]


def fit_baselines(features, random_state=42):
    """Fit the original two model families on a reproducible random 80/20 split.

    Scores are in log1p(viewCount) units. Channel and time holdouts remain future
    work; same-channel examples can occur in both partitions of this split.
    """
    required = NUMERIC + CATEGORICAL + ["viewCount"]
    frame = features[required].replace([np.inf, -np.inf], np.nan).dropna().copy()
    frame = frame.loc[frame["viewCount"] >= 0]
    if len(frame) < 10:
        raise ValueError("At least 10 complete rows are required for this exploratory split.")
    x = frame[NUMERIC + CATEGORICAL]
    y = np.log1p(frame["viewCount"])
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=random_state,
    )
    fitted, scores = {}, []
    for name, estimator in {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(random_state=0),
    }.items():
        preprocess = ColumnTransformer(
            [("categorical", OneHotEncoder(drop="first", handle_unknown="ignore"), CATEGORICAL)],
            remainder="passthrough",
        )
        pipeline = Pipeline([("preprocess", preprocess), ("regressor", estimator)])
        pipeline.fit(x_train, y_train)
        prediction = pipeline.predict(x_test)
        scores.append({"model": name, "r2_log_views": r2_score(y_test, prediction),
                       "rmse_log_views": np.sqrt(mean_squared_error(y_test, prediction)),
                       "train_rows": len(x_train), "test_rows": len(x_test)})
        fitted[name] = pipeline
    return fitted, pd.DataFrame(scores)
