# Suggested Task Fix Notes

## What We Plan to Change
- Parse `survey.tex` as a 5-column LaTeX table.
- Compare the required fields: model name, method category, parameter count, FID-50K, Inception Score, and descending FID order.
- Accept harmless header and parameter-unit wording differences already implied by the prompt.

## Why This Change May Be Needed
Two correct LaTeX tables can use different spacing, header wording, or parameter units. A source-level comparison can reject a table that contains the right answer.

## Original Logic and Suggested New Logic
- Original: evaluation normalized whitespace and case, then compared the whole file text against ground truth.
- Suggested: evaluation should parse the table rows and compare the actual values.
- Original: harmless wording differences such as `Model Name` versus `Model`, or `million` versus `M`, could fail.
- Suggested: evaluation should accept these narrow equivalent expressions while still requiring the same rows, values, and order.
