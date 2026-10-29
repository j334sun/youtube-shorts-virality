"""Offline checks; all records are synthetic and no API requests are made."""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from yt_shorts import collection
from yt_shorts.features import prepare_features
from yt_shorts.models import fit_baselines


def row(**changes):
    record = {
        "video_id": "synthetic-video", "channel_id": "synthetic-channel",
        "title": "Synthetic fixture", "published_at": "2025-07-01T12:00:00Z",
        "channel_created_at": "2020-01-01T00:00:00Z", "duration": "PT30S",
        "viewCount": "100", "subscriberCount": "20", "videoCount": "10",
        "collected_at": "2025-08-01T12:00:00Z",
    }
    record.update(changes)
    return record


class FeatureTests(unittest.TestCase):
    def test_duration_boundaries_duplicates_and_future_dates(self):
        raw = pd.DataFrame([
            row(video_id="one-second", duration="PT1S"),
            row(video_id="sixty-seconds", duration="PT1M"),
            row(video_id="sixty-seconds", duration="PT1M"),
            row(video_id="too-long", duration="PT61S"),
            row(video_id="invalid", duration="bad"),
            row(video_id="future", published_at="2026-01-01T00:00:00Z"),
        ])
        result = prepare_features(raw)
        self.assertEqual(result.video_id.tolist(), ["one-second", "sixty-seconds"])
        self.assertEqual(result.published_days.tolist(), [31, 31])
        self.assertEqual(result.day.tolist(), [1, 1])

    def test_legacy_date_is_required(self):
        raw = pd.DataFrame([row()]).drop(columns="collected_at")
        with self.assertRaisesRegex(ValueError, "reference_date"):
            prepare_features(raw)
        self.assertEqual(len(prepare_features(raw, "2025-08-01T12:00:00Z")), 1)

    def test_recorded_date_takes_precedence_over_fallback(self):
        result = prepare_features(pd.DataFrame([row()]), "2026-01-01")
        self.assertEqual(result.published_days.iloc[0], 31)

    def test_zero_age_and_missing_counts_do_not_become_infinity_or_zero(self):
        result = prepare_features(pd.DataFrame([row(
            channel_created_at="2025-08-01T12:00:00Z", subscriberCount=None,
        )]))
        self.assertTrue(pd.isna(result.channel_freq.iloc[0]))
        self.assertTrue(pd.isna(result.subscriberCount.iloc[0]))


class CollectionTests(unittest.TestCase):
    def test_missing_key_never_builds_client(self):
        with patch.dict("os.environ", {}, clear=True), patch.object(collection, "build") as build:
            with self.assertRaisesRegex(RuntimeError, "YOUTUBE_API_KEY"):
                collection.configure_api()
            build.assert_not_called()

    def test_empty_results_keep_join_columns(self):
        fake = MagicMock()
        fake.videos.return_value.list.return_value.execute.return_value = {"items": []}
        fake.channels.return_value.list.return_value.execute.return_value = {"items": []}
        with patch.object(collection, "youtube", fake):
            self.assertIn("channel_id", collection.get_video_stats(["synthetic"]).columns)
            self.assertIn("channel_id", collection.get_channel_stats(["synthetic"]).columns)
        self.assertIn("video_id", collection.extract_ids({}).columns)

    def test_missing_channel_statistics_remain_missing(self):
        fake = MagicMock()
        fake.channels.return_value.list.return_value.execute.return_value = {"items": [{
            "id": "synthetic", "snippet": {"publishedAt": "2020-01-01T00:00:00Z"},
            "statistics": {},
        }]}
        with patch.object(collection, "youtube", fake):
            result = collection.get_channel_stats(["synthetic"])
        self.assertTrue(pd.isna(result.subscriberCount.iloc[0]))


class ModelTests(unittest.TestCase):
    def test_both_pipelines_fit_without_sharing_preprocessors(self):
        records = [row(video_id=f"synthetic-{i}", viewCount=str(i * i + 1),
                       subscriberCount=str(i + 1), duration=f"PT{1 + i % 59}S")
                   for i in range(40)]
        fitted, metrics = fit_baselines(prepare_features(pd.DataFrame(records)))
        self.assertEqual(set(fitted), {"linear_regression", "random_forest"})
        self.assertTrue(np.isfinite(metrics[["r2_log_views", "rmse_log_views"]]).all().all())
        self.assertIsNot(fitted["linear_regression"]["preprocess"],
                         fitted["random_forest"]["preprocess"])


if __name__ == "__main__":
    unittest.main()
