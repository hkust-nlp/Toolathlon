# arxiv_audit.json specification

Write a single JSON object to `arxiv_audit.json` in the workspace root. It must have exactly one top-level key, `papers`, whose value is a list of exactly four objects, one per paper, sorted by `v1_date` from earliest to latest.

Each paper object must contain all of the following keys (extra keys are ignored):

| key | type | meaning |
|---|---|---|
| `arxiv_id` | string | The arXiv identifier without version suffix, e.g. `"2305.10601"` (not `"2305.10601v2"`, not a URL). |
| `title` | string | Title of the latest version, exactly as shown on arXiv. |
| `first_author` | string | Name of the first author as listed on arXiv. |
| `num_authors` | integer | Number of authors of the latest version. |
| `v1_date` | string | Submission date of version 1 in UTC, format `YYYY-MM-DD` (see the "Submission history" of the arXiv abstract page). |
| `latest_version` | integer | The number of the latest version, e.g. `3` when the latest version is v3. |
| `latest_version_date` | string | Submission date of the latest version in UTC, format `YYYY-MM-DD`. |
| `primary_category` | string | The arXiv primary category, e.g. `"cs.CL"` or `"cs.AI"`. |
| `pdf_path` | string | Path of the downloaded PDF relative to the workspace, which must be `papers/{arxiv_id}v{latest_version}.pdf`. |

Rules:

- Use arXiv (arxiv.org) as the only source of truth for every field, and use its current state at the time you work on this task.
- Dates must be the UTC dates shown by arXiv; do not convert to another timezone.
- The PDF must be the actual PDF served by arXiv for the latest version, saved unmodified under `papers/` with the file name `{arxiv_id}v{latest_version}.pdf`.
- Do not wrap the JSON in markdown code fences.

Example with fictional values:

```json
{
  "papers": [
    {
      "arxiv_id": "2301.00001",
      "title": "An Example Benchmark for Agents",
      "first_author": "Jane Doe",
      "num_authors": 5,
      "v1_date": "2023-01-02",
      "latest_version": 2,
      "latest_version_date": "2023-06-15",
      "primary_category": "cs.CL",
      "pdf_path": "papers/2301.00001v2.pdf"
    }
  ]
}
```
