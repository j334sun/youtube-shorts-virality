"""Cleaning and feature definitions adapted from the exploratory notebook."""

import numpy as np
import pandas as pd
import isodate
import holidays

REQUIRED = {
    "video_id", "channel_id", "title", "published_at", "channel_created_at",
    "duration", "viewCount", "subscriberCount", "videoCount",
}


def _duration_seconds(value):
    try:
        return isodate.parse_duration(str(value)).total_seconds()
    except (ValueError, TypeError, OverflowError, isodate.ISO8601Error):
        return np.nan


def prepare_features(raw, reference_date=None):
    """Return one row per video in the original 1–60 second study cohort.

    Use each row's collected_at timestamp where available. For legacy rows,
    an explicit documented reference_date is required; never default to now.
    Repeated video IDs keep the first row in input order, matching the notebook.
    """
    missing = REQUIRED - set(raw.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    frame = raw.copy()
    observed = pd.to_datetime(
        frame.get("collected_at", pd.Series(pd.NaT, index=frame.index)),
        utc=True, errors="coerce", format="mixed",
    )
    if reference_date is not None:
        fallback = pd.to_datetime(reference_date, utc=True, errors="raise")
        observed = observed.fillna(fallback)
    if observed.isna().any():
        raise ValueError("Legacy rows need a documented reference_date or collected_at timestamp.")

    frame["observation_date"] = observed
    for column in ["viewCount", "likeCount", "commentCount", "subscriberCount", "videoCount"]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
            frame.loc[frame[column] < 0, column] = np.nan
    frame["published_at"] = pd.to_datetime(frame["published_at"], utc=True, errors="coerce", format="mixed")
    created = pd.to_datetime(frame["channel_created_at"], utc=True, errors="coerce", format="mixed")
    frame["title_length"] = frame["title"].fillna("").astype(str).str.len()
    frame["duration_seconds"] = frame["duration"].map(_duration_seconds)
    frame["channel_age_days"] = (observed - created).dt.days
    denominator = frame["channel_age_days"].where(frame["channel_age_days"] > 0)
    frame["channel_freq"] = frame["videoCount"].div(denominator) * 365
    frame["published_days"] = (observed - frame["published_at"]).dt.days

    keep = (
        frame["duration_seconds"].between(1, 60)
        & frame["published_days"].between(0, 800)
        & frame["video_id"].notna()
        & frame["video_id"].astype(str).str.strip().ne("")
        & frame["channel_id"].notna()
        & frame["channel_id"].astype(str).str.strip().ne("")
    )
    frame = frame.loc[keep].drop_duplicates("video_id", keep="first").copy()
    frame["year"] = frame["published_at"].dt.year
    frame["month"] = frame["published_at"].dt.month
    frame["day"] = frame["published_at"].dt.day
    frame["day_name"] = frame["published_at"].dt.day_name()
    calendar = holidays.US()
    frame["is_holiday"] = frame["published_at"].dt.date.map(lambda date: date in calendar)
    return frame.reset_index(drop=True)
