# Suggested Task Fix Notes

## What We Plan to Change
- Treat `ArXiv`, `Github`, `Wikipedia`, and `StackExchange` as shared datasets that may be listed under either model label.
- Allow GPT-Neo coverage to be satisfied by `The Pile` as an aggregate, or by all required component datasets.
- Check missing dataset names directly instead of relying only on counters.

## Why This Change May Be Needed
The prompt describes some datasets as shared. If evaluation hard-binds a shared dataset to only one model column, a reasonable sheet can be rejected.

## Original Logic and Suggested New Logic
- Original: evaluation counted expected LLaMA and GPT-Neo rows using stricter model labels.
- Suggested: shared datasets should satisfy either LLaMA or GPT-Neo when the row clearly refers to one of those models.
- Original: GPT-Neo handling around `The Pile` and its components was not fully aligned with the prompt.
- Suggested: GPT-Neo should pass if `The Pile` is present, or if all individual GPT-Neo components are present.
- Original: missing data was partly inferred through counters.
- Suggested: evaluation should check which required dataset names are actually missing.
