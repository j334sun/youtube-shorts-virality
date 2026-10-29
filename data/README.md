# Local data

Data is intentionally excluded from Git. Suggested locations:

```text
data/
  raw/                  # Authorized collection CSVs
  processed/            # features.csv from notebook 02
  resources/words.txt   # Locally supplied word list
```

The collection schema contains `video_id`, `title`, `channel_id`, `channel_title`, `published_at`, `viewCount`, `likeCount`, `commentCount`, `duration`, `categoryId`, `channel_created_at`, `subscriberCount`, and `videoCount`. Query-specific columns are `category_name`, `search_term`, or `random_key`. New batches additionally contain `collected_at` in UTC.

Statistics may arrive as strings and may be unavailable. Preparation converts counts to numeric values, preserves missing values, and parses ISO 8601 durations. The original notebook used one shared date for age calculations; supply a documented reference date for legacy files instead of silently using today.

The current preparation notebook selects random common-word batches matching `yt_rand_scrape_*.csv`. It does not load every CSV in this folder or infer that differently named collections share a sampling design.

Do not commit CSVs, channel/video records, API responses, or generated outputs. Retain the data locally under the access and usage conditions that apply to its source.
