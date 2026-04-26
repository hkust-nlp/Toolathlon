# Suggested Task Fix Notes

## What We Plan to Change
- Normalize `tools.parameters` before comparison.
- Treat flat parameter maps and JSON Schema `properties` forms as equivalent when they describe the same parameters.
- Ignore empty `required: null` fields.
- Compare tool-message JSON content by parsed JSON when possible.

## Why This Change May Be Needed
The source datasets can store the same tool schema in slightly different JSON shapes. A strict raw-object comparison can reject a semantically correct conversion.

## Original Logic and Suggested New Logic
- Original: evaluation mostly compared the generated JSONL against ground truth field by field.
- Suggested: evaluation should normalize known equivalent tool schema shapes before deep comparison.
- Original: harmless fields such as `required: null` could cause hard mismatches.
- Suggested: empty fields with no practical meaning should not fail the task.
- Original: tool message content was sensitive to raw JSON string formatting and wrapper shape.
- Suggested: tool message content should be parsed as JSON where possible and compared semantically within a narrow compatibility rule.
