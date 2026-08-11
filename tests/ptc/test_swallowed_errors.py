"""Swallowed-error reclassification: every mechanism hits, no false positives."""
import sys
import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from mcp.types import CallToolResult, TextContent
from utils.mcp.ptc_wrapper import _swallowed_error_text

def R(*texts, **extra_flags):
    """CallToolResult with one TextContent per text; extra_flags applies error=True to given indices."""
    blocks = []
    for i, t in enumerate(texts):
        if i in extra_flags.get("error_idx", ()):
            blocks.append(TextContent(type="text", text=t, error=True))
        else:
            blocks.append(TextContent(type="text", text=t))
    return CallToolResult(content=blocks, isError=False)

ERR = object()  # sentinel: expect classified as error
OK = object()   # sentinel: expect kept as data

CASES = [
    # --- prefix rules ---
    ("excel", "create_chart", R("Error: Sheet 'S' not found"), ERR),
    ("excel", "write_data_to_excel", R("Data written to Sheet1 at A1"), OK),
    ("snowflake", "read_query", R("Error: 002003 (42S02): SQL compilation error"), ERR),
    ("snowflake", "write_query", R("Tool write_query is excluded from this data connection"), ERR),
    ("snowflake", "read_query", R("type: data\nrows:\n- a: 1"), OK),
    ("snowflake", "create_schemas", R("Failed to check existing schemas in database 'D': timeout"), ERR),
    # mixed batch stays data (partial success by design)
    ("snowflake", "create_databases",
     R("Warning: Database 'x' already exists\nSuccessfully created database 'y'\nFailed to create database 'z': err"), OK),
    ("google-cloud", "bigquery_run_query", R("Error executing BigQuery query: 403 Access Denied"), ERR),
    ("google-cloud", "bigquery_create_dataset", R("Access denied: Dataset 'd' is not in the allowed list"), ERR),
    ("google-cloud", "bigquery_run_query",
     R("Query executed successfully. 2 rows returned:\nRow 1: {'msg': 'Error: fake'}"), OK),
    ("google-cloud", "compute_wait_for_operation", R("Operation 'op-1' completed successfully"), OK),
    ("google-cloud", "compute_wait_for_operation", R("Operation 'op-1' timed out after 5 minutes"), ERR),
    ("google-cloud", "storage_delete_object", R("Object 'a.txt' not found in bucket 'b'"), ERR),
    ("emails", "read_email", R("Error reading email: boom"), ERR),
    ("emails", "read_email", R("Email ID: 5\nSubject: Error sending email: help me\nBody..."), OK),
    ("emails", "send_email", R("Email sending failed"), ERR),
    ("emails", "send_email", R("Email sent successfully to a@b.c"), OK),
    ("emails", "download_attachment", R("Attachment 'a.pdf' not found in email 3"), ERR),
    ("emails", "download_attachment", R("Attachment 'a.pdf' saved to: /workspace/a.pdf"), OK),
    ("yahoo-finance", "get_stock_info", R("Company ticker XYZQ not found."), ERR),
    ("yahoo-finance", "get_stock_info", R("Error: getting stock information for AAPL: boom"), ERR),
    ("yahoo-finance", "get_stock_price_by_date",
     R("No trading data found for AAPL on 2026-01-01. This might be a weekend or holiday."), OK),
    ("yahoo-finance", "get_historical_stock_prices", R('[{"Date":"2026-01-02","Close":123.4}]'), OK),
    ("arxiv_local", "download_paper", R('{"status": "error", "message": "Paper 9999.9 not found on arXiv"}'), ERR),
    ("arxiv_local", "download_paper", R('{"status": "success", "message": "ok"}'), OK),
    ("arxiv_local", "search_papers", R("Error: Invalid date format - x"), ERR),
    ("arxiv-latex", "get_paper_prompt", R("Error processing paper: 404"), ERR),
    ("arxiv-latex", "get_paper_prompt", R("\\documentclass{article}..."), OK),
    ("rail_12306", "get-tickets", R("Error: get cookie failed. Check your network."), ERR),
    ("rail_12306", "get-tickets", R("车次 | 出发站 -> 到达站 | 出发时间 -> 到达时间"), OK),
    ("rail_12306", "get-interline-tickets", R("很抱歉，未查到相关的列车余票。(undefined)"), OK),  # ambiguous, stays data
    ("k8s", "kubectl_scale", R("Error: MCP error -32603: Failed to scale deployment: exit 1"), ERR),
    ("k8s", "kubectl_scale", R("Scaled deployment nginx to 3 replicas"), OK),
    ("k8s", "kubectl_get", R("Error: something that is not scale"), OK),  # only kubectl_scale audited
    ("playwright_with_chunk", "browser_snapshot_search",
     R("### Result\nError searching: Invalid regular expression: /(/gi: Unterminated group"), ERR),
    ("playwright_with_chunk", "browser_snapshot_search", R("### Result\nNo matches found for pattern: foo"), OK),
    ("pdf-tools", "read_pdf_pages", R("Error: File not found '/x.pdf'"), ERR),
    ("pdf-tools", "read_pdf_pages", R("PDF total pages: 3\n\nError: this is page text"), OK),
    # --- word: prefixes + whole-line regexes + raw-text exemption ---
    ("word", "add_paragraph", R("Failed to add paragraph: boom"), ERR),
    ("word", "add_paragraph", R("Style 'X' not found, paragraph added with default style to f.docx"), OK),
    ("word", "add_heading", R("Document report.docx does not exist"), ERR),
    ("word", "create_document", R("Document report.docx created successfully"), OK),
    ("word", "insert_header_near_text", R("Header 'Intro' (style: Heading 1) inserted after paragraph 3"), OK),
    ("word", "replace_paragraph_block_below_header", R("Header 'Intro' not found in document."), ERR),
    ("word", "get_document_text", R("Failed to plan my day\nis the title of this document"), OK),  # raw text, exempt
    ("word", "get_document_text", R("Document report.docx does not exist"), ERR),  # full-line regex still applies
    ("word", "get_document_text", R("Failed to extract text: broken zip"), ERR),
    ("word", "get_all_comments", R('{\n  "success": false,\n  "error": "Author name cannot be empty"\n}'), ERR),
    # --- structured checks ---
    ("pptx", "add_slide", R('{"error": "Invalid slide index: 9"}'), ERR),
    ("pptx", "add_slide", R('{"message": "Slide added", "slide_index": 1}'), OK),
    ("pptx", "extract_presentation_text",
     R('{"success": true, "slides_text": [{"slide_index": 0, "error": "boom"}]}'), OK),  # partial, by design
    ("notion", "API-post-page", R('{"status":400,"object":"error","code":"validation_error","message":"bad"}'), ERR),
    ("notion", "API-get-self", R('{"status":"error"}'), ERR),
    ("notion", "API-post-page",
     R('{"status":"error","error":"Access denied","message":"You don\'t have permission to access this resource. '
       'Access is restricted to the configured root page and its children.","details":"Page access control violation"}'), ERR),
    ("notion", "API-retrieve-a-page", R('{"object":"page","id":"abc","properties":{"status":{"select":{"name":"error"}}}}'), OK),
    ("wandb", "query_wandb_tool", R('{"errors":[{"message":"Failed to parse initial query: x"}]}'), ERR),
    ("wandb", "query_wandb_tool", R('{"errors":[{"message":"Pagination failed"}],"data":{"runs":[1]}}'), OK),  # partial
    ("wandb", "query_wandb_tool", R('{"data":{"runs":[1,2]}}'), OK),
    ("wandb", "count_weave_traces_tool", R("Error counting traces: boom"), ERR),
    ("wandb", "query_wandb_support_bot", R('{"answer":"Error: Unable to parse response from support bot.","sources":[]}'), OK),  # excluded
    ("rail_12306", "get-station-code-by-names", R('{"火星站":{"error":"未检索到城市。"}}'), ERR),
    ("rail_12306", "get-station-code-of-citys",
     R('{"北京":{"station_code":"BJP","station_name":"北京"},"火星":{"error":"未检索到城市。"}}'), OK),  # partial
    ("filesystem", "read_multiple_files",
     R("a.txt: Error - ENOENT: no such file or directory, open 'a.txt'\n---\nb.txt: Error - Access denied - path outside allowed directories"), ERR),
    ("filesystem", "read_multiple_files",
     R("a.txt:\nhello world\n\n---\nb.txt: Error - ENOENT: no such file or directory"), OK),  # partial
    ("filesystem", "read_text_file", R("Error: this is just file content"), OK),  # not an audited tool
    # --- terminal: error=True flag + trailer semantics ---
    ("terminal", "run_command", R("Security violation: Command 'rm' is not allowed", error_idx=(0,)), ERR),
    ("terminal", "run_command", R("No command provided", error_idx=(0,)), ERR),
    ("terminal", "run_command",
     R("build ok\n", "warning: deprecated flag\n", "\nCommand completed with return code: 0", error_idx=(1,)), OK),
    ("terminal", "run_command",
     R("some stderr\n", "\nCommand completed with return code: 2", error_idx=(0,)), OK),  # ran; rc is data
    ("terminal", "run_command", R("Error: Command execution failed: boom", error_idx=(0,)), ERR),
    # --- unlisted server: never touched ---
    ("canvas", "list_courses", R("Error: whatever"), OK),
    ("github", "get_file_contents", R("Error: in a README"), OK),
]

failures = []
for server, tool, result, expect in CASES:
    got = _swallowed_error_text(server, tool, result)
    is_err = got is not None
    want_err = expect is ERR
    if is_err != want_err:
        failures.append((server, tool, result.content[0].text[:60], "classified" if is_err else "kept", "error" if want_err else "data"))

# dict-shaped results (PTC internal path) work too
d = {"content": [{"type": "text", "text": "Error: Sheet 'S' not found"}], "isError": False}
assert _swallowed_error_text("excel", "create_chart", d) is not None

# pptx returns the inner message, not the JSON envelope
msg = _swallowed_error_text("pptx", "add_slide", R('{"error": "Invalid slide index: 9"}'))
assert msg == "Invalid slide index: 9", msg

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print(f"ALL {len(CASES)} CASES + 2 extra PASSED")
