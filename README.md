# YouTube Shorts Virality Analysis

**Status: ongoing exploratory research.** This project studies how video metadata, channel characteristics, and publication timing relate to observed view counts in short-form YouTube content.

The current workflow covers YouTube Data API collection, dataset cleaning, feature engineering, exploratory visualization, and initial linear-regression and random-forest models. The modeling target is `log1p(viewCount)` at the observation date. A validated definition and prediction task for future *virality* remain open research questions.

## Progress

| Area | Current state |
| --- | --- |
| Collection | Implemented category-keyword, random common-word, and chosen-term queries; historical collection batches exist locally. |
| Cleaning | Implemented video-ID deduplication, duration parsing, and the original 1–60 second / up-to-800-day study filters. |
| Features | Implemented title length, channel age, lifetime upload-rate proxy, video age, duration, and calendar features. |
| Exploration | Notebook workflow for view-count distributions and numeric-feature correlations. |
| Modeling | Preliminary linear-regression and random-forest experiments using a random holdout. No validated benchmark is reported. |
| Title analysis | Hashtag counts and sentiment were proposed in the original notes and remain to be implemented. |
| Validation | Channel-grouped and temporal evaluation, prediction-time feature audits, and sampling-bias analysis remain open. |

## Repository

```text
notebooks/
  01_collection.ipynb                # Optional live collection
  02_exploration_and_features.ipynb  # Local data, EDA, and feature export
  03_baseline_models.ipynb           # Exploratory regressions
yt_shorts/
  collection.py                     # API and query-strategy helpers
  features.py                       # Cleaning and feature definitions
  models.py                         # Baseline training and log-scale metrics
data/README.md                      # Local data locations and schema
docs/research-notes.md               # Assumptions, limitations, next steps
tests/test_workflow.py               # Offline checks using synthetic inputs
requirements.txt
```

This code was organized from the working notebook `Data scraping and preping.ipynb`. The original working folder is preserved separately. Collected CSVs, the local word list, credentials, trained models, and notebook outputs are not included in Git.

## Setup

Use Python 3.11 or newer. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
jupyter lab
```

Open the numbered notebooks. Reusable code lives in `yt_shorts/` so feature and model definitions can be maintained separately from exploration.

### Work with existing data

Place authorized collection CSVs under `data/raw/`. The preparation notebook currently selects `yt_rand_scrape_*.csv`, matching the original random common-word analysis cohort. Other search strategies should be compared separately before pooling them.

Legacy batches do not record the exact observation timestamp. Set `LEGACY_REFERENCE_DATE` in notebook 02 to a documented collection reference date before running them. New collection records include `collected_at`. Using the current date for old counts would change age features and the cohort, so it is not the default.

Notebook 02 writes the ignored `data/processed/features.csv`; notebook 03 reads it. Keep plots and model scores local while the evaluation design is still developing.

### Collect new observations

Set `YOUTUBE_API_KEY` in your local environment using your own key. No key is stored in the code, and no `.env` file is automatically loaded. In notebook 01, explicitly enable `RUN_COLLECTION` and run only the strategies you need. Live requests use your API quota; collection is disabled by default.

For random common-word sampling, provide a word list you have permission to use at `data/resources/words.txt`, one word per line. The original `20k.txt` is not redistributed because its provenance was not documented.

## Interpretation

- **The cohort is a duration-based proxy.** The API's `videoDuration="short"` filter means under four minutes; the later 1–60 second filter defines this project's historical study cohort. Neither confirms that a video is a platform-classified Short. [YouTube API reference](https://developers.google.com/youtube/v3/docs/search/list#videoDuration)
- Query results and random date cutoffs are not a random sample of all YouTube videos. Language relevance and region settings also do not establish creator language or location. [Search parameters](https://developers.google.com/youtube/v3/docs/search/list)
- Subscriber counts and upload counts are measured at collection time. They cannot be assumed available before a video's release. The current work models observed associations, not a deployable pre-publication prediction system.
- The original random train/test split can share channels across partitions. Stronger evaluation and a simple reference predictor are needed before drawing performance conclusions.
- US holiday features use UTC publication dates and a study assumption, not verified viewer or creator locations.

See [research notes](docs/research-notes.md) for the next experiments and the changes made during organization.

## Check the workflow

```sh
python -m unittest discover -s tests -v
```

The checks use synthetic records and mocked API responses. They do not contact YouTube or establish research performance. Clear notebook outputs before committing updates.

Maintained by [Jialu Sun](https://github.com/j334sun).
