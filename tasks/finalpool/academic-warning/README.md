# Academic Warning Initial Workspace

This folder contains seed assets used by the task and its evaluation:

- latest_quiz_scores.xlsx: latest quiz scores file to be read via the Excel MCP server.
- After preprocess runs, JSON mirrors are written alongside:
  - students.json
  - latest_quiz_scores.json
  - historical_exam_data.json
  - bigquery_data_summary.json (dataset_id=student_scores, tables exam_2501-2507)
- init_bigquery_via_mcp.py: example script that demonstrates initializing the BigQuery dataset via the google-cloud MCP server.

Run preprocess before executing the task:

```bash
uv run -m tasks.weihao.academic_warning.preprocess.main --agent_workspace tasks/weihao/academic_warning/initial_workspace
``` 