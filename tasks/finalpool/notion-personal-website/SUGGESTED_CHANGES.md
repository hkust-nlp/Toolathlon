# Suggested Task Fix Notes

## What We Plan to Change
- Add the `Exhibitions` section to the task text.
- Read Notion page blocks with pagination during evaluation.

## Why This Change May Be Needed
The evaluator checks the `Exhibitions` section, but the original prompt did not ask the agent to update it. Also, long Notion pages may return more than one page of blocks.

## Original Logic and Suggested New Logic
- Original: the prompt listed several sections but did not list `Exhibitions`.
- Suggested: the prompt should list every section that evaluation checks.
- Original: evaluation fetched Notion page children once and did not follow `has_more` / `next_cursor`.
- Suggested: evaluation should keep reading block pages until Notion reports no more blocks.
