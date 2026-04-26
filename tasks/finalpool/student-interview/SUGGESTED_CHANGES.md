# Suggested Task Fix Notes

## What We Plan to Change
- Compare calendar event start and end times as actual instants instead of raw strings.

## Why This Change May Be Needed
Google Calendar can represent the same time with different ISO strings or timezone offsets. A raw string comparison may reject an unchanged event.

## Original Logic and Suggested New Logic
- Original: evaluation checked pre-existing calendar events by exact `dateTime` string equality.
- Suggested: evaluation should parse both ISO timestamps and compare the represented time.
- Original: two strings that referred to the same instant could fail if their timezone formatting differed.
- Suggested: a very small tolerance can cover serialization differences without changing scheduling rules.
