I'm putting together a reading list on LLM agent benchmarks for a survey, but I only remember the papers vaguely. Please find the following four papers on arXiv:

1. The original WebArena paper: a realistic, self-hostable web environment for building autonomous agents, first posted in July 2023 (not the later VisualWebArena paper).
2. The original SWE-bench paper, whose title asks whether language models can resolve real-world GitHub issues, first posted in October 2023 (not SWE-bench Multimodal or any other SWE-bench spin-off).
3. The GAIA benchmark paper for general AI assistants, first posted in November 2023.
4. The Tool Decathlon paper, which benchmarks language agents on diverse, realistic, and long-horizon task execution, first posted in October 2025.

For each paper, use the current state of arXiv (as of today) and record: `arxiv_id` (without the version suffix), `title` (of the latest version), `first_author`, `num_authors` (of the latest version), `v1_date` (the date the first version was submitted, UTC, YYYY-MM-DD), `latest_version` (an integer, e.g. 3 for v3), `latest_version_date` (UTC, YYYY-MM-DD), and `primary_category` (e.g. cs.CL). Also download the latest-version PDF of each paper into the `papers/` folder of the workspace, named `{arxiv_id}v{latest_version}.pdf`.

Save all of this to `arxiv_audit.json` in the workspace, following the schema in `audit_spec.md` exactly, with the four papers sorted by `v1_date` from earliest to latest. Finally, reply with the four paper titles in that same order, one per line, in plain text without markdown.
