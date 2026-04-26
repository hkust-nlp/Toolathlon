# Suggested Task Fix Notes

## What We Plan to Change
- Normalize A-share stock codes before comparison.
- Accept bare six-digit codes and equivalent `.SH` / `.SS` / `.SZ` suffixes when the market is consistent.

## Why This Change May Be Needed
The prompt asks for stock codes but does not require Yahoo-style suffixes. A correct A-share code can be written as `600519`, `600519.SH`, or `600519.SS`.

## Original Logic and Suggested New Logic
- Original: evaluation required the exact code string from its internal mapping.
- Suggested: evaluation should compare the numeric code and market.
- Original: equivalent A-share code formats could fail even when they referred to the same stock.
- Suggested: equivalent formats should pass, while the wrong stock or wrong market should still fail.
