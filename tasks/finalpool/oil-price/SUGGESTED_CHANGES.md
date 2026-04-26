# Suggested Task Fix Notes

## What We Plan to Change
- Align the evaluator backtest with `detail.md`.
- Treat the signal month as the entry month.
- Close the position at the next month-end.

## Why This Change May Be Needed
The task instructions describe a signal generated at month-end, an entry at that same month-end, and an exit at the next month-end. If evaluation shifts the entry window, trade rows and metrics can differ from the task definition.

## Original Logic and Suggested New Logic
- Original: the backtest logic opened and closed positions with an extra month-shift risk.
- Suggested: for each non-flat signal month, compute the return from that month-end to the next month-end.
- Original: some comparisons allowed alternate entry-month interpretations.
- Suggested: trade rows and metrics should be checked against the month alignment described in `detail.md`.
