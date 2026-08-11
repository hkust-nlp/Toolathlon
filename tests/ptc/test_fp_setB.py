"""Adversarial test set B for utils.mcp.ptc_wrapper._swallowed_error_text.

Payloads are constructed to match, byte-for-byte, what the deployed servers
actually emit (templates read from the pinned sources):
  - snowflake:    lockon-n/mcp-snowflake-server @ bca38f3
  - google-cloud: google-cloud-mcp @ 7df9ca2 (src/server.py)
  - wandb:        wandb-mcp-server @ 83f6d7f
  - terminal:     cli-mcp-server @ da1dcb5

Primary goal: false positives (realistic SUCCESS outputs that must stay data).
Secondary: true positives for every error template.
"""

import sys

import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import json

import yaml
from mcp import types

from utils.mcp.ptc_wrapper import _swallowed_error_text


# ---------------------------------------------------------------------------
# Payload builders that mirror the servers' own construction code
# ---------------------------------------------------------------------------

def sf_yaml(data, data_id="d4t4-1d-0001"):
    """snowflake handle_read_query: to_yaml({'type': 'data', ...}).
    serialization.to_yaml == yaml.dump(..., indent=2, sort_keys=False)."""
    return yaml.dump(
        {"type": "data", "data_id": data_id, "data": data},
        indent=2,
        sort_keys=False,
    )


def single_text(text):
    """CallToolResult with one plain TextContent block (object form)."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)]
    )


def single_text_dict(text):
    """Same, dict form."""
    return {"content": [{"type": "text", "text": text}]}


def term_result(*blocks):
    """cli-mcp-server response: list of TextContent, error=True on flagged
    blocks (extra field, pydantic extra='allow'). blocks = (text, flagged)."""
    content = []
    for text, flagged in blocks:
        if flagged:
            content.append(types.TextContent(type="text", text=text, error=True))
        else:
            content.append(types.TextContent(type="text", text=text))
    return types.CallToolResult(content=content)


def term_result_dict(*blocks):
    content = []
    for text, flagged in blocks:
        item = {"type": "text", "text": text}
        if flagged:
            item["error"] = True
        content.append(item)
    return {"content": content}


TRAILER0 = "\nCommand completed with return code: 0"


def trailer(rc):
    return "\nCommand completed with return code: %d" % rc


# ---------------------------------------------------------------------------
# Cases: (id, server, tool, result, expect_error: bool, note)
# ---------------------------------------------------------------------------
CASES = []


def case(cid, server, tool, result, expect_error, note):
    CASES.append((cid, server, tool, result, expect_error, note))


# ===========================================================================
# TERMINAL (cli-mcp-server): block order is stdout, stderr(error=True),
# trailer; pre-execution failures are a single error=True block, no trailer.
# ===========================================================================

# --- successes / ran-commands: must stay DATA -------------------------------
case("T01", "terminal", "run_command",
     term_result(("total 12\ndrwxr-xr-x 2 u u 4096 .\n", False), (TRAILER0, False)),
     False, "plain ls output, rc 0")

case("T02", "terminal", "run_command",
     term_result(("Error: connection refused\nError: retry 2 failed\n", False),
                 (TRAILER0, False)),
     False, "stdout that is literally 'Error: ...' lines (cat of a log), rc 0")

case("T03", "terminal", "run_command",
     term_result(("Security violation: user attempted /etc/shadow access\n", False),
                 (TRAILER0, False)),
     False, "stdout containing 'Security violation: ...' (grep of audit log), rc 0")

case("T04", "terminal", "run_command",
     term_result(("No command provided\n", False), (TRAILER0, False)),
     False, "stdout equal to the 'No command provided' sentence, rc 0")

case("T05", "terminal", "run_command",
     term_result(("Command timed out after 30 seconds\n", False), (TRAILER0, False)),
     False, "stdout echoing the timeout template, rc 0")

case("T06", "terminal", "run_command",
     term_result(("build ok\n", False),
                 ("warning: deprecated API used\n", True),
                 (TRAILER0, False)),
     False, "stderr warning flagged error=True but rc 0 with trailer -> shell semantics, data")

case("T07", "terminal", "run_command",
     term_result(("grep: /etc/shadow: Permission denied\n", True), (trailer(2), False)),
     False, "command ran, rc 2, stderr flagged -> data (shell semantics)")

case("T08", "terminal", "run_command",
     term_result(("FAILED tests/test_x.py::test_y - AssertionError\n1 failed\n", False),
                 ("Error: coverage below threshold\n", True),
                 (trailer(1), False)),
     False, "failing test run: stdout + flagged stderr + rc 1 trailer -> data")

case("T09", "terminal", "run_command",
     term_result((trailer(127), False)),
     False, "no output at all, rc 127 (command not found via shell) -> data")

case("T10", "terminal", "run_command",
     term_result((TRAILER0, False)),
     False, "no output, rc 0 -> data")

case("T11", "terminal", "run_command",
     term_result(("AAAA" * 500 + "...[output truncated]", False), (TRAILER0, False)),
     False, "truncated stdout + trailer -> data")

case("T12", "terminal", "run_command",
     term_result(("Error: disk full\nError: disk full\n...[output truncated]", True),
                 (trailer(1), False)),
     False, "truncated flagged stderr full of Error: lines + trailer rc 1 -> data")

case("T13", "terminal", "run_command",
     term_result(("\nCommand completed with return code: 0\n", False),
                 (TRAILER0, False)),
     False, "stdout that byte-identically mimics the trailer (echo trick) + real trailer -> data")

case("T14", "terminal", "run_command",
     term_result(("Command completed with return code: 1\n", False), (TRAILER0, False)),
     False, "stdout mimicking trailer without leading newline + real trailer -> data")

case("T15", "terminal", "run_command",
     term_result(("Security violation: simulated by test suite\n", True),
                 (trailer(3), False)),
     False, "flagged stderr that *starts like* a pre-exec failure, but trailer present -> data")

case("T16", "terminal", "run_command",
     term_result_dict(("grep: no such file\n", True), (trailer(2), False)),
     False, "dict-form ran command, flagged stderr + trailer -> data")

case("T17", "terminal", "run_command",
     term_result(("out line\n", False),
                 ("err line\n", True),
                 ("more stderr context\n", True),
                 (trailer(1), False)),
     False, "multiple flagged blocks but trailer present -> data")

# --- genuine pre-execution failures: single flagged block, NO trailer ------
case("T18", "terminal", "run_command",
     term_result(("Security violation: Command 'rm' is not allowed", True)),
     True, "CommandSecurityError path")

case("T19", "terminal", "run_command",
     term_result(("No command provided", True)),
     True, "missing-argument guard")

case("T20", "terminal", "run_command",
     term_result(("Command timed out after 30 seconds", True)),
     True, "subprocess.TimeoutExpired path")

case("T21", "terminal", "run_command",
     term_result(("Error: [Errno 2] No such file or directory: 'python3.13'", True)),
     True, "generic Exception path")

case("T22", "terminal", "run_command",
     term_result_dict(("Security violation: Path /root is outside allowed directory", True)),
     True, "dict-form pre-exec failure")

case("T23", "terminal", "run_command",
     types.CallToolResult(content=[]),
     False, "empty content list -> data (nothing to reclassify)")

case("T24", "terminal", "show_security_rules",
     term_result(("Security Configuration:\n==================\n"
                  "Working Directory: /workspace\n\nAllowed Commands:\n----------------\n"
                  "ls, cat, grep\n", False)),
     False, "show_security_rules: single unflagged block, no trailer -> data")

# ===========================================================================
# SNOWFLAKE: '*' prefixes ('Error: ', 'Tool '); per-tool 'Failed to check
# existing ...' whole-response aborts. Partial/mixed batches stay DATA.
# ===========================================================================

# --- read_query YAML successes ("type: data\n...") --------------------------
case("S01", "snowflake", "read_query",
     single_text(sf_yaml([{"ID": 1, "STATUS": "Error: timeout contacting shard 3"},
                          {"ID": 2, "STATUS": "OK"}])),
     False, "YAML rows whose cells are 'Error: ...' strings")

case("S02", "snowflake", "read_query",
     single_text(sf_yaml([{"MSG": "Error: 000904 (42000): invalid identifier 'FOO'"}])),
     False, "single row, cell holds a verbatim Snowflake error message")

case("S03", "snowflake", "read_query",
     single_text(sf_yaml([])),
     False, "empty result set (data: [])")

case("S04", "snowflake", "read_query",
     single_text(sf_yaml([{"LOG_LINE": "Tool write_query is excluded from this data connection"}])),
     False, "cell reproducing the tool-excluded sentence, nested in YAML")

case("S05", "snowflake", "read_query",
     {"content": [
         {"type": "text", "text": sf_yaml([{"A": 1}])},
         {"type": "resource",
          "resource": {"uri": "data://rows", "mimeType": "application/json",
                       "text": json.dumps({"type": "data", "data": [{"A": 1}]})}},
     ]},
     False, "two-block success (YAML + EmbeddedResource JSON) -> never inspected")

case("S06", "snowflake", "describe_table",
     single_text(sf_yaml([{"COLUMN_NAME": "ERR_TEXT", "COMMENT": "Error: stores raw errors"}])),
     False, "describe_table YAML with adversarial comment cell")

# --- write_query str(list-of-dict) successes --------------------------------
case("S07", "snowflake", "write_query",
     single_text("[{'number of rows inserted': 3}]"),
     False, "canonical INSERT result repr")

case("S08", "snowflake", "write_query",
     single_text("[{'status': 'Error: constraint SALES_PK violated'}]"),
     False, "repr whose first cell value is 'Error: ...'")

case("S09", "snowflake", "write_query",
     single_text("[]"),
     False, "empty write result repr")

case("S10", "snowflake", "write_query",
     single_text("[{'number of rows updated': 0, 'number of multi-joined rows updated': 0}]"),
     False, "zero-row UPDATE -> still data")

# --- other single-line successes -------------------------------------------
case("S11", "snowflake", "append_insight",
     single_text("Insight added to memo"),
     False, "append_insight success literal")

case("S12", "snowflake", "create_table",
     single_text("Table created successfully. data_id = a1b2c3"),
     False, "create_table success literal")

# --- batch DDL mixed outputs: partial success MUST stay DATA ---------------
case("S13", "snowflake", "create_databases",
     single_text("Successfully created database 'A'\n"
                 "Failed to create database 'B': 003001 (42501): Insufficient privileges"),
     False, "mixed batch, success first")

case("S14", "snowflake", "create_databases",
     single_text("Failed to create database 'B': 003001 (42501): Insufficient privileges\n"
                 "Successfully created database 'C'"),
     False, "mixed batch, per-item failure line FIRST -> still data")

case("S15", "snowflake", "create_databases",
     single_text("Warning: Database 'A' already exists, skipping creation\n"
                 "Successfully created database 'B'"),
     False, "warnings prepended")

case("S16", "snowflake", "create_databases",
     single_text("Warning: Creating database 'X' is not allowed, you can only create databases "
                 "in the following list: ['A', 'B']\n"),
     False, "warnings-only batch response")

case("S17", "snowflake", "create_databases",
     single_text("Failed to create database 'A': net timeout\n"
                 "Failed to create database 'B': net timeout"),
     False, "every item failed - deliberately still data (per-item lines, not whole-response abort)")

case("S18", "snowflake", "create_schemas",
     single_text("Failed to create schema 'STAGING' in database 'ANALYTICS': 003001 (42501): "
                 "Insufficient privileges\n"
                 "Successfully created schema 'RAW' in database 'ANALYTICS'"),
     False, "create_schemas per-item failure first; must NOT match 'Failed to check existing schemas'")

case("S19", "snowflake", "drop_schemas",
     single_text("Failed to drop schema 'OLD' from database 'ANALYTICS': in use\n"
                 "Successfully dropped schema 'TMP' from database 'ANALYTICS'"),
     False, "drop_schemas per-item failure first")

case("S20", "snowflake", "create_tables",
     single_text("Failed to create table 'T1' in ANALYTICS.PUBLIC: syntax error\n"
                 "Successfully created table 'T2' in ANALYTICS.PUBLIC"),
     False, "create_tables per-item failure first")

case("S21", "snowflake", "drop_tables",
     single_text("Failed to drop table 'T1' from ANALYTICS.PUBLIC: does not exist\n"
                 "Successfully dropped table 'T2' from ANALYTICS.PUBLIC"),
     False, "drop_tables per-item failure first")

case("S22", "snowflake", "create_tables",
     single_text("Invalid table definition format: 42\n"
                 "Successfully created table 'T2' in ANALYTICS.PUBLIC"),
     False, "invalid-definition per-item line first")

# --- snowflake true positives ----------------------------------------------
case("S23", "snowflake", "read_query",
     single_text("Error: 002003 (42S02): SQL compilation error:\n"
                 "Object 'ANALYTICS.PUBLIC.NOPE' does not exist or not authorized."),
     True, "handle_tool_errors decorator template")

case("S24", "snowflake", "write_query",
     single_text("Error: Write operations are not allowed for this data connection"),
     True, "guard raise via decorator")

case("S25", "snowflake", "write_query",
     single_text("Tool write_query is excluded from this data connection"),
     True, "pre-dispatch exclusion guard")

case("S26", "snowflake", "create_schemas",
     single_text("Failed to check existing schemas in database 'ANALYTICS': 250001 (08001): "
                 "Failed to connect to DB"),
     True, "create_schemas whole-response abort")

case("S27", "snowflake", "drop_schemas",
     single_text("Failed to check existing schemas in database 'ANALYTICS': timeout"),
     True, "drop_schemas whole-response abort")

case("S28", "snowflake", "create_tables",
     single_text("Failed to check existing tables in ANALYTICS.PUBLIC: 250001: connection lost"),
     True, "create_tables whole-response abort")

case("S29", "snowflake", "drop_tables",
     single_text_dict("Failed to check existing tables in ANALYTICS.PUBLIC: connection lost"),
     True, "drop_tables whole-response abort, dict form")

case("S30", "snowflake", "list_databases",
     single_text_dict("Error: 390114 (08001): Authentication token has expired."),
     True, "dict-form Error: template on a '*' tool")

# ===========================================================================
# GOOGLE-CLOUD: '*' prefixes ('Error ', 'Access denied: '); per-tool literal
# prefixes; regex table for shared-head templates.
# ===========================================================================

# --- successes that embed error-ish text -----------------------------------
case("G01", "google-cloud", "bigquery_run_query",
     single_text("Query executed successfully.\n"
                 "Total rows: 2, Returned: 2\n"
                 "Bytes processed: 10240, Execution time: 187ms\n\n"
                 "Sample results (first 5 rows):\n"
                 "Row 1: {'log_message': 'Error executing BigQuery query: quota exceeded', 'count': 17}\n"
                 "Row 2: {'log_message': 'Error: upstream 502', 'count': 4}\n"),
     False, "query over an error-log table: cells contain 'Error ...' strings")

case("G02", "google-cloud", "bigquery_run_query",
     single_text("Query validation successful.\nEstimated bytes processed: 1048576\n"
                 "Estimated cost: $0.0050 USD"),
     False, "dry-run success")

case("G03", "google-cloud", "bigquery_run_query",
     single_text("Query executed successfully.\n"
                 "Total rows: 0, Returned: 0\n"
                 "Bytes processed: 0, Execution time: 45ms\n\n"
                 "No results returned."),
     False, "empty result set")

case("G04", "google-cloud", "logging_read_logs",
     single_text("Found 3 log entries:\n"
                 "[2026-08-12T02:11:09Z] ERROR: Error: database connection lost\n"
                 "[2026-08-12T02:11:10Z] ERROR: Traceback (most recent call last): ...\n"
                 "[2026-08-12T02:11:11Z] INFO: recovered\n"),
     False, "log lines starting ERROR/Error: inside a success listing")

case("G05", "google-cloud", "logging_read_logs",
     single_text("No log entries found matching the filter criteria"),
     False, "informational empty -> data")

case("G06", "google-cloud", "bigquery_list_jobs",
     single_text("Found 2 BigQuery jobs:\n"
                 "- job_abc123: DONE (QUERY)\n"
                 "  Created: 2026-08-12 01:00:00\n"
                 "  Error: {'reason': 'invalidQuery', 'message': 'Syntax error at [1:8]'}\n"
                 "- job_def456: DONE (LOAD)\n"
                 "  Created: 2026-08-12 01:05:00\n"),
     False, "'  Error: ...' lines for failed jobs inside a success listing")

case("G07", "google-cloud", "bigquery_list_jobs",
     single_text("No BigQuery jobs found"),
     False, "informational empty")

case("G08", "google-cloud", "logging_list_logs",
     single_text("No logs found"),
     False, "informational empty")

case("G09", "google-cloud", "bigquery_list_datasets",
     single_text("No datasets found or no access to allowed datasets"),
     False, "informational empty")

case("G10", "google-cloud", "compute_wait_for_operation",
     single_text("Operation 'operation-1723427000000-61f7b1c2' completed successfully"),
     False, "wait success - same head as the timed-out error, must stay data")

case("G11", "google-cloud", "bigquery_cancel_job",
     single_text("Successfully cancelled BigQuery job 'job_abc123'"),
     False, "cancel success")

case("G12", "google-cloud", "storage_delete_object",
     single_text("Successfully deleted 'reports/2026/08.csv' from bucket 'acme-data'"),
     False, "delete success - regex 'Object ... not found' must not fire")

case("G13", "google-cloud", "storage_list_objects",
     single_text("Found 2 objects in bucket 'acme-data':\n"
                 "- Error: retry.log: 2048 bytes\n"
                 "- ok.txt: 10 bytes"),
     False, "object literally named 'Error: retry.log' listed after the 'Found' header")

case("G14", "google-cloud", "logging_write_log",
     single_text("Successfully wrote log entry to 'app-errors' with severity 'ERROR'"),
     False, "write success mentioning ERROR severity")

case("G15", "google-cloud", "bigquery_run_query",
     single_text_dict("Query executed successfully.\n"
                      "Total rows: 1, Returned: 1\n"
                      "Bytes processed: 512, Execution time: 12ms\n\n"
                      "Sample results (first 5 rows):\n"
                      "Row 1: {'msg': 'Access denied: simulated row'}\n"),
     False, "dict-form success with 'Access denied:' inside a row cell")

case("G28", "google-cloud", "bigquery_get_dataset_info",
     single_text("Dataset Information for 'error_logs':\n"
                 "Full Name: acme-prod:error_logs\nLocation: US\n"
                 "Description: Errors: raw application error dumps\n"),
     False, "dataset-info success for a dataset literally about errors")

# --- google-cloud true positives -------------------------------------------
case("G16", "google-cloud", "bigquery_run_query",
     single_text("Error executing BigQuery query: 400 Syntax error: Unexpected keyword AS at [1:20]"),
     True, "'Error ' template")

case("G17", "google-cloud", "logging_read_logs",
     single_text("Error reading logs: 403 The caller does not have permission"),
     True, "'Error ' template")

case("G18", "google-cloud", "bigquery_list_jobs",
     single_text("Error listing BigQuery jobs: 401 Request had invalid authentication credentials"),
     True, "'Error ' template")

case("G19", "google-cloud", "logging_delete_log",
     single_text("Access denied: Log 'audit' is not in allowed log buckets list"),
     True, "'Access denied: ' template")

case("G20", "google-cloud", "bigquery_cancel_job",
     single_text("Could not cancel BigQuery job 'job_abc123' (may already be completed)"),
     True, "per-tool literal prefix")

case("G21", "google-cloud", "bigquery_export_table",
     single_text("Export format 'JSON' not yet supported. Currently only CSV is supported."),
     True, "per-tool literal prefix")

case("G22", "google-cloud", "compute_restart_instance",
     single_text("Cannot restart instance 'web-1': current status is 'TERMINATED'. "
                 "Instance must be RUNNING or STOPPING to restart."),
     True, "per-tool literal prefix")

case("G23", "google-cloud", "compute_wait_for_operation",
     single_text("Operation 'operation-1723427000000-61f7b1c2' timed out after 5 minutes"),
     True, "regex-table timed-out template")

case("G24", "google-cloud", "storage_delete_object",
     single_text("Object 'missing.csv' not found in bucket 'acme-data'"),
     True, "regex-table not-found template")

case("G25", "google-cloud", "logging_delete_log",
     single_text("Log 'app' not found or could not be deleted"),
     True, "regex-table template")

case("G26", "google-cloud", "logging_delete_log_sink",
     single_text("Log sink 'archive' not found or could not be deleted"),
     True, "regex-table template")

case("G27", "google-cloud", "storage_upload_file",
     single_text_dict("Error uploading file to bucket 'acme-data': [Errno 2] No such file"),
     True, "dict-form 'Error ' template")

# ===========================================================================
# WANDB: prefix rule only for count_weave_traces_tool; structured GraphQL
# check only for query_wandb_tool (errors && !data). Partial results and
# free-form support-bot text stay DATA.
# ===========================================================================

case("W01", "wandb", "query_wandb_tool",
     single_text(json.dumps({"data": {"project": {"name": "nanogpt", "runs": {
         "edges": [{"node": {"displayName": "run-1", "state": "failed",
                             "summaryMetrics": "{\"loss\": NaN}"}}]}}}})),
     False, "success GraphQL dict (failed *runs* are data, not tool errors)")

case("W02", "wandb", "query_wandb_tool",
     single_text(json.dumps({
         "errors": [{"message": "Pagination failed on page 3: timeout"}],
         "data": {"project": {"runs": {"edges": [{"node": {"name": "r1"}}]}}},
     })),
     False, "partial result: errors + non-empty data MUST stay data")

case("W03", "wandb", "query_wandb_tool",
     single_text(json.dumps({"data": {"viewer": None}})),
     False, "data with null field, no errors")

case("W04", "wandb", "query_wandb_tool",
     single_text(json.dumps({"data": {"project": {"errors": [
         {"message": "row-level error stored in user data"}]}}})),
     False, "'errors' key nested inside data, not top-level")

case("W05", "wandb", "query_wandb_tool",
     single_text(json.dumps({"errors": [], "data": {"project": {"id": "p1"}}})),
     False, "empty errors list + data")

case("W06", "wandb", "query_wandb_support_bot",
     single_text(json.dumps({"answer": "Error handling in W&B: wrap wandb.init in try/except...",
                             "sources": ["https://docs.wandb.ai/guides"]})),
     False, "support-bot JSON answer discussing errors")

case("W07", "wandb", "query_wandb_support_bot",
     single_text("Error: to resume a crashed run, pass resume='must' to wandb.init. "
                 "This 'Error:' opening is part of the bot's free-form answer."),
     False, "support-bot free-form text starting with 'Error' - deliberately excluded, data")

case("W08", "wandb", "query_wandb_support_bot",
     single_text(json.dumps({"errors": [{"message": "wandbot upstream 500"}]})),
     False, "even an errors-shaped support-bot payload stays data (check is per-tool)")

case("W09", "wandb", "count_weave_traces_tool",
     single_text(json.dumps({"total_count": 5000, "root_traces_count": 200})),
     False, "count success json.dumps")

case("W10", "wandb", "query_wandb_entity_projects",
     single_text(json.dumps({"errors": [{"message": "x"}]})),
     False, "errors-shaped payload on a non-audited wandb tool stays data")

# --- wandb true positives ---------------------------------------------------
case("W11", "wandb", "query_wandb_tool",
     single_text(json.dumps({"errors": [{"message": "Failed to parse initial query: "
                                                    "Syntax Error: Expected Name, found }"}]})),
     True, "errors, no data key at all")

case("W12", "wandb", "query_wandb_tool",
     single_text(json.dumps({"errors": [{"message": "project not found"}], "data": None})),
     True, "errors with data: null")

case("W13", "wandb", "count_weave_traces_tool",
     single_text("Error counting traces: HTTPError 502 Bad Gateway"),
     True, "count error template")

case("W14", "wandb", "query_wandb_tool",
     single_text_dict(json.dumps({"errors": [{"message": "Unauthorized"}]})),
     True, "dict-form errors-only payload")

# ===========================================================================
# Shape edge cases (any server)
# ===========================================================================

case("X01", "snowflake", "read_query",
     types.CallToolResult(content=[
         types.TextContent(type="text", text="Error: part 1"),
         types.TextContent(type="text", text="Error: part 2"),
     ]),
     False, "two text blocks -> multi-block results are never inspected")

case("X02", "google-cloud", "bigquery_run_query",
     types.CallToolResult(content=[]),
     False, "empty content -> data")

case("X03", "snowflake", "read_query",
     {"content": []},
     False, "dict form, empty content -> data")

case("X04", "wandb", "query_wandb_tool",
     single_text("not json at all"),
     False, "unparseable text on wandb tool -> data")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    n_pass = 0
    fp = 0  # expected data, classifier said error
    fn = 0  # expected error, classifier said data
    for cid, server, tool, result, expect_error, note in CASES:
        got = _swallowed_error_text(server, tool, result)
        got_error = got is not None
        if got_error == expect_error:
            n_pass += 1
            continue
        if got_error and not expect_error:
            fp += 1
            kind = "FALSE POSITIVE"
        else:
            fn += 1
            kind = "FALSE NEGATIVE"
        print("FAIL [%s] %s: %s/%s - %s" % (cid, kind, server, tool, note))
        print("      expected %s, got %r" % (
            "error" if expect_error else "data",
            (got[:120] + "...") if isinstance(got, str) and len(got) > 120 else got,
        ))
    print("SETB: %d/%d passed, %d false positives, %d false negatives"
          % (n_pass, len(CASES), fp, fn))


if __name__ == "__main__":
    main()
