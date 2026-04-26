# Suggested Task Fix Notes

## What We Plan to Change
- Change the salary rule from `> $3000` to `>= $3000`.

## Why This Change May Be Needed
The evaluator expects companies with exactly `$3000` minimum salary to be included. The original prompt wording excludes that boundary case.

## Original Logic and Suggested New Logic
- Original: the task text said the minimum salary requirement should be greater than `$3000`.
- Suggested: the task text should say the minimum salary requirement is at least `$3000`.
