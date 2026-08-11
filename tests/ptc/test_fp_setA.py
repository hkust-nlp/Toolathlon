# -*- coding: utf-8 -*-
"""Adversarial tests (set A) for _swallowed_error_text in utils/mcp/ptc_wrapper.py.

Servers covered: emails, yahoo-finance, arxiv_local, arxiv-latex, excel.
Every payload below is instantiated from the actual return statements of the
deployed server pins:
  emails       backport/emails_mcp-0.1.12 (tools/*.py)
  yahoo-finance audit_g6/yahoo-finance-mcp @ 469103b (server.py)
  arxiv_local  backport/arxiv-mcp-server @ c29796a (tools/*.py, server.py)
  arxiv-latex  backport/arxiv-latex-mcp @ f8bd3b3 (arxiv-latex-mcp.py)
  excel        backport/excel-mcp-server @ 89ea163 (server.py + impl modules)

expect_swallowed=False  -> _swallowed_error_text must return None  (success stays data)
expect_swallowed=True   -> must return non-None                    (swallowed error caught)
"""

import sys
import json

import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from mcp.types import CallToolResult, TextContent  # noqa: E402
from utils.mcp.ptc_wrapper import _swallowed_error_text  # noqa: E402


CASES = []  # (case_id, server, tool, text, expect_swallowed, note)


def add(server, tool, text, expect_swallowed, note=""):
    CASES.append((len(CASES) + 1, server, tool, text, expect_swallowed, note))


# ===========================================================================
# EMAILS — successes / data (must stay None)
# ===========================================================================

# get_emails listing whose 1st subject is literally an error sentence
add("emails", "get_emails",
    "Folder: INBOX\nPage: 1/1\nTotal emails: 2\n\n"
    "1. ID: 101\n   Subject: Error sending email: SMTP timeout\n"
    "   From: alerts@ci.example.com\n   Date: Tue, 11 Aug 2026 09:12:00 +0000\n\n"
    "2. ID: 102\n   Subject: Re: quarterly report\n"
    "   From: bob@example.com\n   Date: Tue, 11 Aug 2026 10:00:00 +0000\n\n",
    False, "success listing, adversarial subject")

add("emails", "get_emails",
    "Folder 'Archive' is empty or page 3 is out of range",
    False, "empty-folder informational message")

# read_email whose body text begins with an error-looking line
add("emails", "read_email",
    "Email ID: 101\nSubject: Error sending email: SMTP timeout\n"
    "From: alerts@ci.example.com\nTo: me@example.com\n"
    "Date: Tue, 11 Aug 2026 09:12:00 +0000\nMessage-ID: <abc@ci>\n\n"
    "Text Content:\nError sending email: SMTP timeout\n"
    "The nightly job failed to notify the on-call rotation.\n\n",
    False, "success read, body contains error text")

add("emails", "read_email",
    "Email ID: 205\nSubject: 会议纪要（八月）\nFrom: 李雷 <lilei@example.cn>\n"
    "To: me@example.com\nDate: Mon, 10 Aug 2026 15:00:00 +0800\n"
    "Message-ID: <cn1@x>\n\nText Content:\n大家好，附件是本周的会议纪要，请查收。\n\n"
    "Attachments:\n1. 纪要.docx (application/vnd.openxmlformats-officedocument.wordprocessingml.document, 20480 bytes)\n",
    False, "success read, Chinese content")

add("emails", "search_emails",
    "No emails found matching query: Error sending email",
    False, "empty search whose query IS an error string")

add("emails", "search_emails",
    "Search query: Error\nFolder: INBOX\nPage: 1/1\nTotal results: 1\n\n"
    "1. ID: 101\n   Subject: Error sending email: SMTP timeout\n"
    "   From: alerts@ci.example.com\n   Date: Tue, 11 Aug 2026 09:12:00 +0000\n\n",
    False, "search success, adversarial query+subject")

add("emails", "send_email",
    "Email sent successfully to bob@example.com with 2 attachments",
    False, "send success")

add("emails", "reply_email", "Reply sent successfully to sender", False)
add("emails", "reply_email", "Reply sent successfully to all recipients", False)
add("emails", "forward_email", "Email forwarded successfully to carol@example.com", False)
add("emails", "delete_email", "Email 42 deleted successfully", False)
add("emails", "move_email", "Email 42 moved to Archive successfully", False)
add("emails", "mark_emails", "Successfully marked 3/3 emails as read", False)

add("emails", "move_emails",
    "Successfully moved 2/3 emails to Archive (1 failed: 17)",
    False, "partial success stays data")

add("emails", "delete_emails",
    "Successfully deleted 0/2 emails (2 failed: 5, 6)",
    False, "all-failed batch still reported via success template - deliberate data")

# check_connection total failure: contains 'Error:' on a later line only
add("emails", "check_connection",
    "Connection Status:\nIMAP: ✗ Failed\nSMTP: ✗ Failed\n\n"
    "Error: Both connections failed - check configuration",
    False, "status report containing an interior 'Error:' line")

add("emails", "get_email_headers",
    "Email Headers for ID: 101\n" + "=" * 50 + "\n"
    "Subject: Error sending email: SMTP timeout\n"
    "From: alerts@ci.example.com\nTo: me@example.com\n",
    False, "headers success, adversarial Subject header")

add("emails", "save_draft", "Draft saved successfully with ID: draft_20260812_093000", False)
add("emails", "get_drafts", "No drafts found", False, "empty drafts informational")

add("emails", "get_drafts",
    "Drafts (Page 1/1):\nTotal drafts: 1\n\n"
    "1. ID: draft_1\n   Subject: Error sending email: please investigate\n"
    "   To: ops@example.com\n   Updated: 2026-08-12T09:30:00\n\n",
    False, "drafts listing, adversarial subject")

add("emails", "update_draft", "Draft draft_1 updated successfully", False)
add("emails", "delete_draft", "Draft draft_1 deleted successfully", False)

add("emails", "export_emails",
    "Successfully exported 150 emails to /workspace/INBOX_export.json",
    False)

add("emails", "export_emails",
    "No emails found to export from INBOX",
    False, "deliberately kept as data (empty result)")

add("emails", "export_emails",
    "Successfully exported 12 emails to /workspace/all_folders_export.json\n"
    "Export breakdown by folder:\n  - INBOX: 10 emails\n  - SENT: 2 emails",
    False, "all-folders export success")

add("emails", "import_emails",
    "Successfully imported 10/10 emails to INBOX",
    False)

add("emails", "import_emails",
    "No emails found in import file /tmp/backup.json",
    False, "deliberately kept as data (empty import)")

add("emails", "import_emails",
    "Successfully imported 8/10 emails\n\n2 emails failed to import:\n"
    "  - Email 3: Cannot access folder 'JUNK': SELECT failed\n"
    "  - Email 4: APPEND to 'INBOX' failed",
    False, "partial import stays data")

add("emails", "download_attachment",
    "Attachment 'report.pdf' saved to: /downloads/report.pdf",
    False, "download success")

# ADVERSARIAL: attachment filename containing \"' not found\" makes the SUCCESS
# message match the greedy regex \AAttachment '.*' not found
add("emails", "download_attachment",
    "Attachment 'report' not found.pdf' saved to: /downloads/report' not found.pdf",
    False, "ADVERSARIAL filename ending in <' not found> - success must stay data")

add("emails", "get_folders",
    "Available folders:\n1. INBOX (52 total, 3 unread)\n2. SENT (10 total, 0 unread)\n"
    "3. Error Reports (4 total, 1 unread)\n4. [Gmail] (cannot select)\n",
    False, "folder list containing a folder literally named 'Error Reports'")

add("emails", "create_folder", "Folder 'Error Reports' created successfully",
    False, "created a folder named 'Error Reports'")
add("emails", "delete_folder", "Folder 'Old Projects' deleted successfully", False)

add("emails", "get_mailbox_stats",
    "Folder Statistics for 'INBOX':\nTotal messages: 52\nUnread messages: 3\nTotal size: 12.34 MB\n",
    False)
add("emails", "get_unread_count", "Total unread messages: 7", False)

# scoping: per-tool error literals must NOT fire on other tools
add("emails", "get_emails", "Email sending failed",
    False, "send_email-only literal under get_emails")
add("emails", "get_drafts", "Failed to update draft 123",
    False, "update_draft-only literal under get_drafts")
add("emails", "read_email", "No raw message data available for email 12",
    False, "headers/download-only literal under read_email")
add("emails", "get_emails", "Attachment 'x.zip' not found in email 3",
    False, "download_attachment-only regex under get_emails")

# ===========================================================================
# EMAILS — swallowed error templates (must be caught)
# ===========================================================================

add("emails", "get_emails", "Error getting emails: [Errno 111] Connection refused", True)
add("emails", "read_email", "Error reading email: Email 999 not found", True)
add("emails", "search_emails", "Error searching emails: IMAP SEARCH command failed", True)
add("emails", "send_email", "Email sending failed", True)
add("emails", "send_email", "Error sending email: (535, b'5.7.8 Authentication failed')", True)
add("emails", "reply_email", "Reply sending failed", True)
add("emails", "reply_email", "Error replying to email: original email not found", True)
add("emails", "forward_email", "Email forwarding failed", True)
add("emails", "delete_email", "Email deletion failed", True)
add("emails", "move_email", "Email move failed", True)
add("emails", "move_emails", "Error moving emails: connection reset by peer", True)
add("emails", "delete_emails", "Error deleting emails: connection reset by peer", True)
add("emails", "mark_emails",
    "Error: Status must be 'read', 'unread', 'important', or 'not_important'", True)
add("emails", "create_folder", "Failed to create folder 'Projects/2026'", True)
add("emails", "delete_folder", "Failed to delete folder 'Old'", True)
add("emails", "update_draft", "Failed to update draft draft_9", True)
add("emails", "delete_draft", "Failed to delete draft draft_9", True)
add("emails", "get_email_headers", "No raw message data available for email 7", True)
add("emails", "download_attachment", "Attachment 'missing.pdf' not found in email 3", True)
add("emails", "download_attachment", "No raw message data available for email 3", True)
add("emails", "download_attachment", "Could not extract attachment data for 'x.zip'", True)
add("emails", "export_emails",
    "Error: Cannot specify both 'folder' and 'export_all_folders=True'", True)
add("emails", "export_emails", "Error exporting emails: [Errno 13] Permission denied", True)
add("emails", "import_emails", "Error importing emails: Invalid JSON in import file", True)
add("emails", "check_connection", "Error checking connection: timed out", True)

# ===========================================================================
# YAHOO-FINANCE — successes / data (must stay None)
# ===========================================================================

add("yahoo-finance", "get_historical_stock_prices",
    '[{"Date":"2024-01-02T00:00:00.000","Open":187.15,"High":188.44,"Low":183.89,'
    '"Close":185.64,"Volume":82488700,"Dividends":0.0,"Stock Splits":0.0}]',
    False, "history JSON records")

add("yahoo-finance", "get_historical_stock_prices", "[]",
    False, "empty history frame -> empty JSON array")

add("yahoo-finance", "get_stock_price_by_date",
    json.dumps({"ticker": "AAPL", "requested_date": "2024-01-13",
                "actual_date": "2024-01-12", "open": 186.06, "high": 186.74,
                "low": 185.19, "close": 185.92, "volume": 40477800,
                "dividends": 0.0, "stock_splits": 0.0,
                "note": "Requested date 2024-01-13 was not a trading day. Showing nearest trading day."}),
    False, "by-date success JSON with note")

add("yahoo-finance", "get_stock_price_by_date",
    "No trading data found for AAPL around date 2024-01-01",
    False, "empty result deliberately kept as data")

add("yahoo-finance", "get_stock_price_by_date",
    "No trading data found for AAPL on 2024-01-01. This might be a weekend or holiday. "
    "Use find_nearest=true to get nearest trading day.",
    False, "exact-date empty result stays data")

add("yahoo-finance", "get_stock_info",
    json.dumps({"symbol": "AAPL", "shortName": "Apple Inc.",
                "longBusinessSummary": "Error: this sentence is part of a business "
                "summary quoting an error message, not a tool failure.",
                "currentPrice": 231.5}),
    False, "info JSON embedding 'Error: ' inside a string value")

add("yahoo-finance", "get_yahoo_finance_news",
    "Title: Error: Apple faces new lawsuit over App Store\n"
    "Summary: A headline that literally starts with the word Error.\n"
    "Description: Adversarial title content.\n"
    "URL: https://finance.yahoo.com/news/example.html",
    False, "news whose TITLE starts with 'Error:' - payload still starts 'Title: '")

add("yahoo-finance", "get_yahoo_finance_news",
    "Title: 苹果公司发布新款芯片\nSummary: 新芯片性能大幅提升。\nDescription: 中文新闻摘要。\n"
    "URL: https://finance.yahoo.com/news/cn.html\n\n"
    "Title: Second story\nSummary: s\nDescription: d\nURL: https://x",
    False, "multi-story Chinese news")

add("yahoo-finance", "get_yahoo_finance_news",
    "No news found for company that searched with AAPL ticker.",
    False, "empty news stays data")

add("yahoo-finance", "get_stock_actions",
    '[{"Date":"2024-02-09T00:00:00.000","Dividends":0.24,"Stock Splits":0.0}]',
    False)

add("yahoo-finance", "get_financial_statement",
    json.dumps([{"date": "2024-09-30", "Total Revenue": 391035000000.0,
                 "Net Income": 93736000000.0, "EBITDA": None}]),
    False, "financial statement JSON (with null)")

add("yahoo-finance", "get_holder_info",
    '[{"metric":"insidersPercentHeld","Value":0.02703},'
    '{"metric":"institutionsPercentHeld","Value":0.61897}]',
    False)

add("yahoo-finance", "get_option_expiration_dates",
    '["2026-08-15", "2026-08-22", "2026-09-19"]', False)

add("yahoo-finance", "get_option_chain",
    '[{"contractSymbol":"AAPL260815C00230000","strike":230.0,"lastPrice":5.4,'
    '"inTheMoney":true}]', False)

add("yahoo-finance", "get_recommendations",
    '[{"period":"0m","strongBuy":7,"buy":21,"hold":13,"sell":2,"strongSell":2}]',
    False)

# scoping: 'Company ticker' without the trailing space boundary
add("yahoo-finance", "get_stock_info",
    "Company tickers overview: AAPL, MSFT",
    False, "prefix requires 'Company ticker ' then text; 'tickers' must not match... "
           "actually 'Company tickers overview' DOES start with 'Company ticker '? no: "
           "'Company ticker' + 's' != 'Company ticker' + ' '")

# ===========================================================================
# YAHOO-FINANCE — swallowed error templates (must be caught)
# ===========================================================================

add("yahoo-finance", "get_historical_stock_prices", "Company ticker ZZZFAKE not found.", True)
add("yahoo-finance", "get_historical_stock_prices",
    "Error: getting historical stock prices for AAPL: HTTPSConnectionPool(host='query2.finance.yahoo.com', port=443): Read timed out.",
    True)
add("yahoo-finance", "get_historical_stock_prices",
    "Error: Invalid date format. Please use YYYY-MM-DD format, e.g. '2024-01-15'. "
    "Unknown datetime string format, unable to parse: notadate",
    True)
add("yahoo-finance", "get_historical_stock_prices",
    "Error: Invalid period 'weekly'. Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max",
    True)
add("yahoo-finance", "get_stock_price_by_date",
    "Error: Invalid date format '13-2024'. Please use YYYY-MM-DD format, e.g. '2024-01-15'",
    True)
add("yahoo-finance", "get_stock_price_by_date",
    "Error: Cannot get stock price for future date 2030-01-01", True)
add("yahoo-finance", "get_stock_info",
    "Error: getting stock information for AAPL: Expecting value: line 1 column 1 (char 0)", True)
add("yahoo-finance", "get_yahoo_finance_news",
    "Error: getting news for AAPL: Too Many Requests. Rate limited. Try after a while.", True)
add("yahoo-finance", "get_financial_statement",
    "Error: invalid financial type earnings. Please use one of the following: "
    "FinancialType.income_stmt, FinancialType.quarterly_income_stmt, FinancialType.balance_sheet, "
    "FinancialType.quarterly_balance_sheet, FinancialType.cashflow, FinancialType.quarterly_cashflow.",
    True)
add("yahoo-finance", "get_holder_info",
    "Error: invalid holder type owners. Please use one of the following: "
    "HolderType.major_holders, HolderType.institutional_holders, HolderType.mutualfund_holders, "
    "HolderType.insider_transactions, HolderType.insider_purchases, HolderType.insider_roster_holders.",
    True)
add("yahoo-finance", "get_option_chain",
    "Error: No options available for the date 2024-01-01. You can use "
    "`get_option_expiration_dates` to get the available expiration dates.", True)
add("yahoo-finance", "get_option_chain",
    "Error: Invalid option type. Please use 'calls' or 'puts'.", True)
add("yahoo-finance", "get_recommendations",
    "Error: getting recommendations for AAPL: 'NoneType' object has no attribute 'reset_index'",
    True)

# ===========================================================================
# ARXIV_LOCAL — successes / data (must stay None)
# ===========================================================================

add("arxiv_local", "search_papers",
    json.dumps({"total_results": 1, "papers": [{
        "id": "2401.12345v1",
        "title": "Error: A Study of Failure Modes in Large Language Models",
        "authors": ["Ada Lovelace"],
        "abstract": "Error: strings inside abstracts are data. We analyse tool-use "
                    "failures whose messages begin with 'Error: '.",
        "categories": ["cs.CL"],
        "published": "2024-01-20T12:00:00+00:00",
        "url": "http://arxiv.org/pdf/2401.12345v1",
        "resource_uri": "arxiv://2401.12345v1"}]}, indent=2),
    False, "search success, adversarial title/abstract")

add("arxiv_local", "search_papers",
    json.dumps({"total_results": 0, "papers": []}, indent=2),
    False, "empty search result")

add("arxiv_local", "download_paper",
    json.dumps({"status": "success", "message": "Paper already available",
                "resource_uri": "file:///root/.arxiv-mcp-server/papers/2401.12345.md"}),
    False, "already-converted success envelope")

add("arxiv_local", "download_paper",
    json.dumps({"status": "converting", "message": "Paper downloaded, conversion started",
                "started_at": "2026-08-12T10:00:00.000000"}),
    False, "conversion-started envelope")

add("arxiv_local", "download_paper",
    json.dumps({"status": "unknown", "message": "No download or conversion in progress"}),
    False, "check_status unknown envelope")

add("arxiv_local", "read_paper",
    json.dumps({"status": "success", "paper_id": "2401.12345",
                "content": "Error: handling in deep networks\n# Introduction\n"
                           "Papers about errors start with the word Error sometimes."}),
    False, "read success whose markdown content starts with 'Error:'")

add("arxiv_local", "read_paper",
    json.dumps({"status": "success", "paper_id": "2402.00001",
                "content": 'The JSON literal {"status": "error"} appears verbatim '
                           "in this paper about MCP servers."}),
    False, "read success embedding the error-envelope literal inside content")

add("arxiv_local", "list_papers",
    json.dumps({"total_papers": 1, "papers": [{
        "title": "On Errors", "summary": "Error: -prefixed abstract text.",
        "authors": ["B. Fault"], "links": ["http://arxiv.org/abs/2401.12345v1"],
        "pdf_url": "http://arxiv.org/pdf/2401.12345v1"}]}, indent=2),
    False, "list success")

# ===========================================================================
# ARXIV_LOCAL — swallowed error templates (must be caught)
# ===========================================================================

add("arxiv_local", "summarize_paper", "Error: Unknown tool summarize_paper", True,
    "dispatcher unknown-tool guard")
add("arxiv_local", "download_paper", "Error: 'paper_id'", True,
    "KeyError from missing argument via dispatcher catch-all")
add("arxiv_local", "search_papers",
    "Error: Invalid date format - Unknown string format: not-a-date", True)
add("arxiv_local", "search_papers",
    "Error: Page request resulted in HTTP 500", True)
add("arxiv_local", "download_paper",
    json.dumps({"status": "error", "message": "Paper 2401.99999 not found on arXiv"}),
    True, "StopIteration envelope")
add("arxiv_local", "download_paper",
    json.dumps({"status": "error",
                "started_at": "2026-08-12T10:00:00.000000",
                "completed_at": "2026-08-12T10:01:00.000000",
                "error": "cannot open broken document",
                "message": "Paper conversion error"}),
    True, "check_status envelope after failed conversion")
add("arxiv_local", "read_paper",
    json.dumps({"status": "error",
                "message": "Paper 2401.12345 not found in storage. You may need to "
                           "download it first using download_paper."}),
    True)
add("arxiv_local", "read_paper",
    json.dumps({"status": "error",
                "message": "Error reading paper: [Errno 13] Permission denied: "
                           "'/root/.arxiv-mcp-server/papers/2401.12345.md'"}),
    True)

# ===========================================================================
# ARXIV-LATEX — get_paper_prompt
# ===========================================================================

_LATEX_INSTRUCTIONS = (
    "\n        \n        IMPORTANT INSTRUCTIONS FOR RENDERING:\n"
    "        Whenever I ask you a question about this paper, please use dollar sign "
    "notation ($...$) for inline equations and double dollar signs ($$...$$) for "
    "display equations when providing responses that include LaTeX.\n        "
)

add("arxiv-latex", "get_paper_prompt",
    "\\documentclass[11pt]{article}\n\\usepackage{amsmath}\n\\begin{document}\n"
    "\\title{On Robust Tool Use}\n\\maketitle\nBody text.\n\\end{document}"
    + _LATEX_INSTRUCTIONS,
    False, "flattened LaTeX success")

add("arxiv-latex", "get_paper_prompt",
    "% arXiv flattened source\n\\documentclass{article}\n\\begin{document}\nx\n\\end{document}"
    + _LATEX_INSTRUCTIONS,
    False, "LaTeX starting with a % comment")

add("arxiv-latex", "get_paper_prompt",
    "\\documentclass{article}\n\\begin{document}\n"
    "Our harness logs the line:\n\\begin{verbatim}\n"
    "Error processing paper: HTTP Error 404: Not Found\n"
    "\\end{verbatim}\nwhich models must treat as data.\n\\end{document}"
    + _LATEX_INSTRUCTIONS,
    False, "ADVERSARIAL: error template on a LATER line of real LaTeX - stays data")

add("arxiv-latex", "get_paper_prompt",
    "Error: this is the first line of an unusual paper source\n\\documentclass{article}"
    + _LATEX_INSTRUCTIONS,
    False, "'Error: ' head is NOT a registered prefix for this server")

# Known accepted risk (documented in ptc_wrapper.py): a paper whose source starts
# with the exact template collides. Expected non-None by design.
add("arxiv-latex", "get_paper_prompt",
    "Error processing paper: a hypothetical paper title starting with the template\n"
    "\\documentclass{article}" + _LATEX_INSTRUCTIONS,
    True, "ACCEPTED RISK per rule-table comment - collision is by design")

add("arxiv-latex", "get_paper_prompt",
    "Error processing paper: HTTP Error 404: Not Found", True, "real error template")
add("arxiv-latex", "get_paper_prompt",
    "Error processing paper: 'NoneType' object has no attribute 'group'", True)

# scoping: rule is registered per-tool, no '*' for this server
add("arxiv-latex", "some_other_tool",
    "Error processing paper: HTTP Error 404: Not Found",
    False, "unknown tool on arxiv-latex has no rules")

# ===========================================================================
# EXCEL — successes / data (must stay None)
# ===========================================================================

add("excel", "apply_formula", "Applied formula '=SUM(A1:A10)' to cell B2", False)
add("excel", "validate_formula_syntax", "Formula is valid but doesn't match cell content", False)
add("excel", "validate_formula_syntax", "Formula is valid and matches cell content", False)
add("excel", "validate_formula_syntax", "Formula is valid but cell contains no formula", False)
add("excel", "format_range", "Range formatted successfully", False)

add("excel", "read_data_from_excel",
    json.dumps({"range": "Sheet1!A1:B3", "sheet_name": "Sheet1", "cells": [
        {"address": "A1", "value": "status", "row": 1, "column": 1},
        {"address": "A2", "value": "Error: division by zero", "row": 2, "column": 1},
        {"address": "B2", "value": "Error: file not found", "row": 2, "column": 2},
    ]}, indent=2, default=str),
    False, "read success whose CELL VALUES are error strings")

add("excel", "read_data_from_excel", "No data found in specified range",
    False, "empty range informational")
add("excel", "write_data_to_excel", "Data written to Sheet1", False)
add("excel", "create_workbook", "Created workbook at /workspace/report.xlsx", False)
add("excel", "create_worksheet", "Sheet 数据表 created successfully", False, "Chinese sheet name")
add("excel", "create_chart", "Line chart created successfully", False)
add("excel", "create_pivot_table", "Summary table created successfully", False)
add("excel", "create_table",
    "Successfully created table 'SalesData' in sheet 'Sheet1'.", False)
add("excel", "copy_worksheet", "Sheet 'Sheet1' copied to 'Backup'", False)
add("excel", "delete_worksheet", "Sheet 'Old' deleted", False)
add("excel", "rename_worksheet", "Sheet renamed from 'Error Log' to 'Log'",
    False, "sheet literally named 'Error Log'")
add("excel", "get_workbook_metadata",
    "{'filename': 'report.xlsx', 'sheets': ['Sheet1', 'Errors'], 'size': 12345, "
    "'modified': 1723449600.0}",
    False, "str(dict) metadata with a sheet named 'Errors'")
add("excel", "get_workbook_metadata",
    "{'filename': '错误汇总.xlsx', 'sheets': ['错误列表'], 'size': 9876, "
    "'modified': 1723449600.0, 'used_ranges': {'错误列表': 'A1:D20'}}",
    False, "str(dict) metadata, Chinese filename meaning 'error summary'")
add("excel", "merge_cells", "Range 'A1:B2' merged in sheet 'Sheet1'", False)
add("excel", "unmerge_cells", "Range 'A1:B2' unmerged successfully", False)
add("excel", "copy_range", "Range copied successfully", False)
add("excel", "delete_range", "Range A1:B2 deleted successfully", False)
add("excel", "validate_excel_range",
    "Range 'A1:C10' is valid. Sheet contains data in range 'A1:F25'", False)
add("excel", "get_data_validation_info",
    json.dumps({"sheet_name": "Sheet1", "validation_rules": [
        {"range": "B2:B10", "validation_type": "list",
         "allowed_values": ["Error: red", "ok"]}]}, indent=2, default=str),
    False, "validation JSON embedding error-looking allowed value")
add("excel", "get_data_validation_info",
    "No data validation rules found in this worksheet", False)

# ===========================================================================
# EXCEL — swallowed error templates (must be caught)
# ===========================================================================

add("excel", "apply_formula", "Error: Sheet 'Data' not found", True)
add("excel", "apply_formula", "Error: Invalid cell reference: 5A", True)
add("excel", "validate_formula_syntax",
    "Error: Invalid formula syntax: Formula must start with '='", True)
add("excel", "apply_formula",
    "Error: Invalid cell range reference in formula: A1:XyZ", True)
add("excel", "get_workbook_metadata", "Error: File not found: /workspace/missing.xlsx", True)
add("excel", "get_data_validation_info", "Error: Sheet 'Résumé' not found", True)
add("excel", "delete_worksheet", "Error: Cannot delete the only sheet in workbook", True)

# ===========================================================================
# Cross-server / shape checks
# ===========================================================================

add("some-other-server", "foo", "Error: boom",
    False, "server without registered rules")


def _result_obj(text):
    return CallToolResult(content=[TextContent(type="text", text=text)])


def _result_dict(text):
    return {"content": [{"type": "text", "text": text}]}


def main():
    n_pass = n_total = fp = fn = 0

    for case_id, server, tool, text, expect, note in CASES:
        n_total += 1
        got_obj = _swallowed_error_text(server, tool, _result_obj(text))
        got_dict = _swallowed_error_text(server, tool, _result_dict(text))

        forms_agree = (got_obj is None) == (got_dict is None)
        ok = forms_agree and ((got_obj is not None) == expect)

        if ok:
            n_pass += 1
        else:
            if not forms_agree:
                print(f"FAIL case {case_id} [{server}/{tool}] FORM MISMATCH "
                      f"obj={got_obj is not None} dict={got_dict is not None} :: {note}")
            got = got_obj if got_obj is not None else got_dict
            if expect and got is None:
                fn += 1
                kind = "FALSE NEGATIVE (error not caught)"
            else:
                fp += 1
                kind = "FALSE POSITIVE (success reclassified as error)"
            print(f"FAIL case {case_id} [{server}/{tool}] {kind}")
            print(f"     note: {note}")
            print(f"     payload: {text[:160]!r}")

    # --- shape checks: rules must only apply to single-text-block results ----
    shape_checks = [
        ("multi-block, both error-shaped", "emails", "get_emails",
         {"content": [{"type": "text", "text": "Error getting emails: x"},
                      {"type": "text", "text": "Error getting emails: y"}]},
         False),
        ("single non-text (image) block", "emails", "get_emails",
         {"content": [{"type": "image", "data": "AAAA", "mimeType": "image/png"}]},
         False),
        ("empty content list", "excel", "apply_formula",
         {"content": []},
         False),
        ("multi-block CallToolResult", "yahoo-finance", "get_stock_info",
         CallToolResult(content=[TextContent(type="text", text="Error: a"),
                                 TextContent(type="text", text="Error: b")]),
         False),
    ]
    for note, server, tool, result, expect in shape_checks:
        n_total += 1
        got = _swallowed_error_text(server, tool, result)
        if (got is not None) == expect:
            n_pass += 1
        else:
            if expect:
                fn += 1
                kind = "FALSE NEGATIVE"
            else:
                fp += 1
                kind = "FALSE POSITIVE"
            print(f"FAIL shape [{server}/{tool}] {kind} :: {note}")

    print(f"SETA: {n_pass}/{n_total} passed, {fp} false positives, {fn} false negatives")


if __name__ == "__main__":
    main()
