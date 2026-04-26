# Suggested Task Fix Notes

## What We Plan to Change
- Anchor preprocessing and evaluation to the same task date.
- Save that task date during preprocessing so evaluation can reuse it.
- Generate sample game timestamps that stay inside the task date.

## Why This Change May Be Needed
The task asks for current-day game statistics. If preprocessing uses the machine date while evaluation uses a launch date or a different local day, the data and checks can point at different dates.

## Original Logic and Suggested New Logic
- Original: preprocessing generated rows using `date.today()`.
- Suggested: preprocessing should resolve one authoritative task date from `launch_time` when possible.
- Original: evaluation separately parsed `launch_time` when available, otherwise used the current system date.
- Suggested: preprocessing should persist the task date, and evaluation should reuse that saved date.
- Original: random game timestamps could spill into the next calendar day.
- Suggested: every generated game timestamp should belong to the same task date.
