# Research notes

## Current question

How do video metadata, channel characteristics, and publication timing relate to the observed distribution of view counts among short-duration YouTube videos?

The current target is a snapshot of views, transformed with `log1p`. Descriptive view-count bins in the exploration notebook are working summaries, not a validated viral/non-viral label. No causal claim or final performance estimate is made.

## Existing work

The source notebook contains category-keyword, random-word, and chosen-term collection strategies; descriptive distributions; a combined random-word cohort; duration and age filtering; duplicate-video removal; metadata-derived features; and linear and random-forest regressions. Its hashtag and title-sentiment section is a planning note, not completed functionality.

## Next experiments

1. Define a measurable outcome and horizon: observed lifetime views, views at a fixed age, growth between snapshots, or a justified threshold.
2. Audit the sampling frame. Record query, query strategy, observation timestamp, pagination choices, and retention rules. Compare search strategies before combining cohorts.
3. Replace the exploratory random split with channel-grouped and temporal holdouts. Preserve an untouched test set and compare a simple reference predictor.
4. Separate features available at prediction time from post-publication measurements. Likes and comments are omitted from the current predictors, but channel size and lifetime upload counts are also observation-time measurements.
5. Add the planned hashtag and sentiment features with documented extraction and failure handling.
6. Examine sensitivity to age filters, duration limits, missing statistics, repeated observations, and influential channels. Consider permutation importance on held-out data.

## Organization and fixes

The working notebook was split into collection, preparation, and modeling entry points. Collection helpers and modeling/feature logic were moved into importable modules. The original project files were left untouched.

The organized copy removes the hardcoded API credential and saved outputs; fixes the unfinished channel-statistics dictionary and stray plotting character; supplies the missing day-of-month feature; handles empty API results; treats unavailable API counts as missing; and calculates RMSE using a compatible metric call. Each model owns its preprocessing pipeline, including handling of categories absent from the training split.

Date-dependent features now require a documented observation date for legacy rows and use `collected_at` for new data. Dividing by a zero-age channel yields a missing upload-rate feature instead of infinity. Future publication dates and missing identifiers are excluded. Repeated IDs retain the first input row, as in the original notebook; a longitudinal design would need a different key and policy.

The numbered notebooks provide a clean workflow rather than a transcript of every exploratory cell. The original comparisons, discarded attempts, and historical outputs remain in the local working notebook. The published code has not been used to claim new results on the collected dataset.
