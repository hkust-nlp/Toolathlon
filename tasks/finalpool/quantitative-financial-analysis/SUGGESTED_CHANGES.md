# Suggested Task Fix Notes

## What We Plan to Change
- Add the missing `2025-07-31` rows for all four tickers to the ground-truth CSV.
- Leave the stock-value fields for `2025-07-31` blank until the authors confirm the exact ground-truth values.
- During evaluation, treat those blank values as fields that still need to be filled in or confirmed, rather than as final numeric ground truth.

## Why This Change May Be Needed
The task asks for June and July 2025 data. The original ground truth ended at `2025-07-30`, so a complete July answer could have a row-count mismatch.

## Original Logic and Suggested New Logic
- Original: ground truth included trading days through `2025-07-30`.
- Suggested: ground truth should include the final trading day of July 2025.
- Original: evaluation compared the agent sheet against that incomplete file.
- Suggested: evaluation should at least check that `2025-07-31` rows exist for the required tickers, and the exact stock values for that date should be completed after author confirmation.
