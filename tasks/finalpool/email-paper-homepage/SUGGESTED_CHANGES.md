# Suggested Task Fix Notes

## What We Plan to Change
- Derive the expected conference year from the same date rule used by preprocessing.
- Limit `codeurl` checks to papers that are actually in scope for this task.
- Clarify that links should only be added for repositories that are actually released and finished.

## Why This Change May Be Needed
Preprocessing fills the acceptance email year from `today + 30 days`. A hardcoded evaluator year can become stale. Also, checking unrelated papers can fail a correct homepage update.

## Original Logic and Suggested New Logic
- Original: evaluation expected `2025` conference strings.
- Suggested: evaluation should compute the expected year from the task date file.
- Original: evaluation checked some papers outside the current acceptance-email scope.
- Suggested: evaluation should check only the papers whose status is changed by the current emails.
- Original: the task text did not clearly distinguish released repositories from not-yet-released repositories.
- Suggested: a paper should get a `codeurl` only when its repository is available and complete.
