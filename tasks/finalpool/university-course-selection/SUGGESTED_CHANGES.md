# Suggested Task Fix Notes

## What We Plan to Change
- Ignore common teacher titles in the `Instructor` column.
- Ignore trailing week ranges such as `[1-16]` in the `Class Time` column.
- Compare `Course Selection Restrictions` as delimiter- and order-insensitive tokens.
- Compare shared columns in the stable required-column order.

## Why This Change May Be Needed
The source PDF may include titles and week ranges that are not represented in the reference format. Also, the prompt says multiple restrictions may be comma-separated, so order and delimiter should not matter.

## Original Logic and Suggested New Logic
- Original: evaluation compared normalized strings directly.
- Suggested: evaluation should apply small column-specific normalization before comparing.
- Original: restriction text could fail because equivalent restrictions used a different delimiter or order.
- Suggested: restriction comparison should require the same tokens while ignoring delimiter and order.
- Original: shared columns were taken from an unordered `set`, which can make sorting unstable.
- Suggested: rows should be sorted and compared using the reference column order.
