"""Adversarial test set C for _swallowed_error_text in utils/mcp/ptc_wrapper.py.

Primary goal: false positives — realistic SUCCESS payloads (taken from the
deployed sources) with adversarial twists must stay data (return None).
Secondary: true positives for every audited error template.

Expectations were double-checked against the deployed sources:
  - 12306-mcp @ 3a2ae5ef (src/index.ts)
  - notion-mcp-server @ 43f11758 (openapi-mcp-server/mcp/proxy.ts)
  - mcp-server-kubernetes @ f6ac1263 (src/tools/kubectl-scale.ts)
  - playwright chunk tarball (lib/tools/snapshotNavigation.js, lib/response.js)
  - modelcontextprotocol/servers 2025.7.1 (src/filesystem/index.ts:
      success segment = f"{path}:\n{content}\n", error = f"{path}: Error - {msg}",
      joined with "\n---\n")
  - pdf-tools-mcp 0.1.4 (pdf_tools_mcp/server.py)
  - office-powerpoint-mcp-server 2.0.6 (tools/*.py, utils/design_utils.py)
  - office-word-mcp-server 1.1.9 (word_document_server/tools/*.py, utils/document_utils.py)
"""

import json
import sys

import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from utils.mcp.ptc_wrapper import _swallowed_error_text  # noqa: E402

try:
    from mcp.types import CallToolResult, TextContent
    HAVE_MCP = True
except Exception:
    HAVE_MCP = False


def mk_obj(text):
    """CallToolResult with a single TextContent block, isError unset."""
    if HAVE_MCP:
        return CallToolResult(content=[TextContent(type="text", text=text)])
    return {"content": [{"type": "text", "text": text}]}


def mk_dict(text):
    """Plain-dict form of the same result."""
    return {"content": [{"type": "text", "text": text}]}


CASES = []  # (case_id, server, tool, result, expect_is_error, note)
_ids = set()


def case(case_id, server, tool, text_or_result, expect_error, note="", form="obj"):
    assert case_id not in _ids, f"duplicate id {case_id}"
    _ids.add(case_id)
    if isinstance(text_or_result, str):
        result = mk_dict(text_or_result) if form == "dict" else mk_obj(text_or_result)
    else:
        result = text_or_result
    CASES.append((case_id, server, tool, result, expect_error, note))


# ===========================================================================
# rail_12306
# ===========================================================================
TICKET_TABLE = (
    "车次 | 出发站 -> 到达站 | 出发时间 -> 到达时间 | 历时\n"
    "G1(实际车次train_no: 24000000G10I) 北京南(telecode: VNP) -> 上海(telecode: SHH) "
    "09:00 -> 13:28 历时：04:28\n"
    "- 商务座: 12张 2318元\n- 一等座: 有票 933元\n- 二等座: 有票 553元\n"
)
case("rail-01", "rail_12306", "get-tickets", TICKET_TABLE, False,
     "Chinese ticket table success")
case("rail-02", "rail_12306", "get-tickets",
     "车次,出发站,到达站,出发时间,到达时间,历时\nG1,北京南,上海,09:00,13:28,04:28",
     False, "CSV variant success", form="dict")
case("rail-03", "rail_12306", "get-tickets", "没有查询到相关车次信息", False,
     "empty-result sentinel is data")
case("rail-04", "rail_12306", "get-stations-code-in-city",
     json.dumps([{"station_code": "VNP", "station_name": "北京南"},
                 {"station_code": "VAP", "station_name": "北京西"}],
                ensure_ascii=False),
     False, "JSON station record list")
case("rail-05", "rail_12306", "get-station-code-of-citys",
     json.dumps({"北京": {"station_code": "BJP", "station_name": "北京"}},
                ensure_ascii=False),
     False, "station-code map, all resolved")
case("rail-06", "rail_12306", "get-station-code-of-citys",
     json.dumps({"北京": {"station_code": "BJP", "station_name": "北京"},
                 "亚特兰蒂斯": {"error": "未检索到城市。"}}, ensure_ascii=False),
     False, "PARTIAL station map: one resolved + one error entry stays data")
case("rail-07", "rail_12306", "get-station-code-by-names",
     json.dumps({"上海虹桥": {"station_code": "AOH", "station_name": "上海虹桥"},
                 "不存在站": {"error": "未检索到城市。"}}, ensure_ascii=False),
     False, "PARTIAL by-names map stays data", form="dict")
case("rail-08", "rail_12306", "get-interline-tickets",
     "很抱歉，未查到相关的列车余票。(2)", False,
     "12306 apology wrapper is a legitimate empty result, deliberately data")
case("rail-09", "rail_12306", "get-interline-tickets",
     "车次 | 出发站 -> 到达站 | 出发时间 -> 到达时间 | 历时\n", False,
     "header-only interline table is data")
# true positives
case("rail-10", "rail_12306", "get-station-code-of-citys",
     "Error: City not found. ", True, "audited template")
case("rail-11", "rail_12306", "get-tickets",
     "Error: get tickets data failed. ", True, "audited template")
case("rail-12", "rail_12306", "get-tickets",
     "Error: The date cannot be earlier than today.", True, "audited template",
     form="dict")
case("rail-13", "rail_12306", "get-tickets",
     "Error: get cookie failed. Check your network.", True, "audited template")
case("rail-14", "rail_12306", "get-tickets",
     "Error: parse tickets info failed. ", True, "audited template")
case("rail-15", "rail_12306", "get-tickets",
     "Error: Station not found. ", True, "audited template")
case("rail-16", "rail_12306", "get-current-date",
     "Error: Failed to get current date.", True, "audited template")
case("rail-17", "rail_12306", "get-station-code-of-citys",
     json.dumps({"亚特兰蒂斯": {"error": "未检索到城市。"},
                 "黄金国": {"error": "未检索到城市。"}}, ensure_ascii=False),
     True, "every entry failed -> lookup failed outright")
case("rail-18", "rail_12306", "get-station-code-by-names",
     json.dumps({"不存在站": {"error": "未检索到城市。"}}, ensure_ascii=False),
     True, "single-entry all-error map", form="dict")
case("rail-19", "rail_12306", "get-tickets",
     json.dumps({"X": {"error": "未检索到城市。"}}, ensure_ascii=False),
     False, "all-error-shaped map on a NON-audited tool name stays data")

# ===========================================================================
# notion
# ===========================================================================
NOTION_PAGE = {
    "object": "page",
    "id": "b55c9c91-384d-452b-81db-d1ef79372b75",
    "created_time": "2026-08-01T12:00:00.000Z",
    "archived": False,
    "properties": {
        "status": {"id": "a%3Bc", "type": "select",
                   "select": {"name": "error", "color": "red"}},
        "error": {"id": "b%3Bd", "type": "rich_text",
                  "rich_text": [{"type": "text",
                                 "text": {"content": "no error here"},
                                 "plain_text": "no error here"}]},
        "Name": {"id": "title", "type": "title",
                 "title": [{"type": "text", "text": {"content": "Task"}}]},
    },
    "url": "https://www.notion.so/Task-b55c9c91384d452b81dbd1ef79372b75",
}
case("notion-01", "notion", "API-retrieve-a-page", json.dumps(NOTION_PAGE), False,
     "page with properties literally named 'status'/'error', select value 'error'")
NOTION_DB = {
    "object": "database",
    "id": "bc1211ca-e3f1-4939-ae34-5260b16f627c",
    "title": [{"type": "text", "text": {"content": "Error log"},
               "plain_text": "Error log"}],
    "properties": {"status": {"id": "x", "type": "status",
                              "status": {"options": [{"name": "error"}]}}},
}
case("notion-02", "notion", "API-retrieve-a-database", json.dumps(NOTION_DB), False,
     "database titled 'Error log' with a status property")
NOTION_QUERY = {
    "object": "list",
    "results": [NOTION_PAGE],
    "next_cursor": None,
    "has_more": False,
    "type": "page_or_database",
    "page_or_database": {},
}
case("notion-03", "notion", "API-post-database-query", json.dumps(NOTION_QUERY),
     False, "database query result list", form="dict")
NOTION_BLOCKS = {
    "object": "list",
    "results": [{
        "object": "block", "id": "x", "type": "paragraph",
        "paragraph": {"rich_text": [{
            "type": "text",
            "text": {"content": 'the API replied {"status":"error"} yesterday'},
            "plain_text": 'the API replied {"status":"error"} yesterday'}]},
    }],
    "has_more": False,
}
case("notion-04", "notion", "API-get-block-children", json.dumps(NOTION_BLOCKS),
     False, "rich_text content containing '\"status\":\"error\"' stays data")
NOTION_COMMENTS = {
    "object": "list",
    "results": [{"object": "comment", "id": "c1",
                 "rich_text": [{"type": "text",
                                "text": {"content": "status: error on my end"}}]}],
    "has_more": False,
}
case("notion-05", "notion", "API-retrieve-a-comment", json.dumps(NOTION_COMMENTS),
     False, "comments list mentioning 'status: error'")
case("notion-06", "notion", "API-post-search",
     json.dumps([{"object": "page", "id": "p"}]), False,
     "top-level JSON array is not the error envelope")
case("notion-07", "notion", "API-retrieve-a-page",
     json.dumps({"object": "page", "id": "p",
                 "properties": {"status": "error"}}), False,
     "nested status:'error' under properties stays data", form="dict")
case("notion-08", "notion", "API-retrieve-a-page",
     json.dumps({"object": "page", "status": 200, "id": "p"}), False,
     "hypothetical int status < 400 with object page stays data")
# true positives
case("notion-09", "notion", "API-patch-page",
     json.dumps({"status": 400, "object": "error", "code": "validation_error",
                 "message": "body failed validation",
                 "request_id": "r1"}), True,
     "Notion API 400 body (spread overwrote status with number)")
case("notion-10", "notion", "API-retrieve-a-page",
     json.dumps({"status": "error"}), True, "empty-body error envelope")
case("notion-11", "notion", "API-retrieve-a-page",
     json.dumps({"status": "error", "error": "Access denied",
                 "message": "You don't have permission to access this resource. "
                            "Access is restricted to the configured root page and "
                            "its children.",
                 "details": "Page access control violation"}), True,
     "page access-control JSON", form="dict")
case("notion-12", "notion", "API-retrieve-a-page",
     json.dumps({"status": 404, "object": "error", "code": "object_not_found",
                 "message": "Could not find page with ID: x."}), True,
     "404 error object")
case("notion-13", "notion", "API-retrieve-a-page",
     json.dumps({"object": "error", "code": "unauthorized",
                 "message": "API token is invalid."}), True,
     "object=='error' without usable status")

# ===========================================================================
# k8s (only kubectl_scale audited)
# ===========================================================================
case("k8s-01", "k8s", "kubectl_scale",
     "Scaled deployment nginx to 3 replicas", True is False,
     "scale success")
case("k8s-02", "k8s", "kubectl_scale",
     "Scaled statefulset web to 5 replicas", False, "scale success variant",
     form="dict")
case("k8s-03", "k8s", "kubectl_get",
     "Error: no resources found in default namespace", False,
     "unaudited k8s tool: arbitrary Error text stays data")
case("k8s-04", "k8s", "kubectl_logs",
     json.dumps({"logs": {"pod-a": "Error: connection refused",
                          "pod-b": "started ok"}}), False,
     "kubectl_logs JSON with per-pod Error values stays data")
case("k8s-05", "k8s", "kubectl_generic",
     'Error from server (NotFound): deployments.apps "nginx" not found', False,
     "unaudited tool output")
case("k8s-06", "k8s", "kubectl_scale",
     "Error from server (NotFound): something", False,
     "kubectl_scale text outside its two audited templates stays data")
# true positives
case("k8s-07", "k8s", "kubectl_scale",
     "Error: MCP error -32603: Failed to scale deployment: Command failed: "
     'kubectl scale deployment nginx --replicas=3 --namespace=default\n'
     'Error from server (NotFound): deployments.apps "nginx" not found\n', True,
     "outer catch of McpError")
case("k8s-08", "k8s", "kubectl_scale",
     "Failed to scale resource: input.name is required", True,
     "outer generic catch", form="dict")

# ===========================================================================
# playwright_with_chunk (only browser_snapshot_search audited)
# ===========================================================================
case("pw-01", "playwright_with_chunk", "browser_snapshot_search",
     "### Result\nFound 3 matches in 2 spans:\n"
     "- span 12: link \"Error handling guide\"\n"
     "- span 12: text: how to handle Error searching states\n"
     "- span 14: heading \"Errors\"", False,
     "search success whose matches mention errors")
case("pw-02", "playwright_with_chunk", "browser_snapshot_search",
     "### Result\nNo matches found for pattern: x", False,
     "no-matches informational result is data")
case("pw-03", "playwright_with_chunk", "browser_snapshot_search",
     "### Result\nFound 1 matches in 1 spans:\n"
     "text before\nError searching: this is page content", False,
     "'Error searching: ' on a later line must not trip the anchored prefix")
case("pw-04", "playwright_with_chunk", "browser_click",
     "### Result\nError searching: boom", False,
     "rule is scoped to browser_snapshot_search only", form="dict")
case("pw-05", "playwright_with_chunk", "browser_snapshot_search",
     "Error searching: no header", False,
     "payload without the '### Result' head does not match the audited template")
# true positive
case("pw-06", "playwright_with_chunk", "browser_snapshot_search",
     "### Result\nError searching: Invalid regular expression: /[/: "
     "Unterminated character class", True, "invalid-regex catch branch")

# ===========================================================================
# filesystem (only read_multiple_files audited)
# ===========================================================================
case("fs-01", "filesystem", "read_multiple_files",
     "a.txt:\nhello world\n\n---\n"
     "b.txt: Error - ENOENT: no such file or directory, open 'b.txt'", False,
     "partial result (one ok + one failed) stays data")
case("fs-02", "filesystem", "read_multiple_files",
     "a.txt: Error - ENOENT: no such file or directory, open 'a.txt'\n---\n"
     "b.txt: Error - EACCES: permission denied, open 'b.txt'", True,
     "every file failed -> reclassified")
case("fs-03", "filesystem", "read_multiple_files",
     "missing.txt: Error - ENOENT: no such file or directory, open 'missing.txt'",
     True, "single-file all-failed", form="dict")
case("fs-04", "filesystem", "read_multiple_files",
     "notes.txt:\nintro line\n---\nx: Error - y\n", False,
     "success file whose CONTENT contains '\\n---\\nx: Error - y' stays data")
case("fs-05", "filesystem", "read_multiple_files",
     "empty.txt:\n\n", False,
     "empty-file success segment (path:\\n + empty content + \\n)")
case("fs-06", "filesystem", "read_multiple_files",
     "f.txt:\nx: Error - y\n", False,
     "success whose content is exactly one error-shaped line")
case("fs-07", "filesystem", "read_text_file",
     "a.txt: Error - ENOENT: no such file or directory", False,
     "rule scoped to read_multiple_files only", form="dict")
case("fs-08", "filesystem", "read_multiple_files",
     "x: Error - y:\n---\nz: Error - w\n", False,
     "adversarial path containing ': Error - ' + content starting '---\\n': "
     "success trailing newline keeps it data")
case("fs-09", "filesystem", "read_multiple_files", "", False,
     "empty payload stays data")
case("fs-10", "filesystem", "read_multiple_files",
     "a.txt: Error - ENOENT\n---\nb.txt:\ncontents\n\n---\nc.txt: Error - EACCES",
     False, "middle file succeeded -> partial, stays data")

# ===========================================================================
# pdf-tools
# ===========================================================================
case("pdf-01", "pdf-tools", "read_pdf_pages",
     "PDF total pages: 10\nExtracted page range: 1-2\n\n"
     "Error: this line is text extracted from the PDF\n"
     "Error reading the manual? See appendix B.", False,
     "extracted text containing Error lines after the header")
case("pdf-02", "pdf-tools", "read_pdf_pages",
     "PDF total pages: 3\nSpecified page range (5-6) has no extractable text "
     "content.", False, "informational empty extraction")
case("pdf-03", "pdf-tools", "search_pdf",
     "Search ID: a1b2c3\nFound 2 matches for pattern: revenue\n"
     "Page 3: ...total revenue grew...\nPage 7: ...revenue decline...", False,
     "search session success", form="dict")
case("pdf-04", "pdf-tools", "merge_pdfs",
     "Successfully merged 3 PDFs into 'out.pdf'\nTotal pages: 42", False,
     "merge success")
case("pdf-05", "pdf-tools", "search_pdf",
     "No matches found for pattern: revenue", False,
     "no-matches is a legitimate answer, deliberately data")
case("pdf-06", "pdf-tools", "extract_pdf_pages",
     "Successfully extracted 2 pages from 'a.pdf' to 'b.pdf'\n"
     "Extracted pages: [1, 2]\nSource PDF total pages: 9", False,
     "extract success")
case("pdf-07", "pdf-tools", "read_pdf_pages",
     "Warning: page 4 had no text layer; results may be incomplete", False,
     "warning head is not an error template")
# true positives
case("pdf-08", "pdf-tools", "read_pdf_pages",
     "Error processing PDF: EOF marker not found", True, "audited template")
case("pdf-09", "pdf-tools", "read_pdf_pages",
     "Error: File not found '/workspace/x.pdf'", True, "audited template",
     form="dict")
case("pdf-10", "pdf-tools", "get_pdf_info",
     "Error reading PDF file: invalid xref table", True, "audited template")
case("pdf-11", "pdf-tools", "read_pdf_pages",
     "Error resolving path: [Errno 13] Permission denied", True,
     "audited template")
case("pdf-12", "pdf-tools", "read_pdf_pages",
     "Error: Path '/etc/passwd' is outside the allowed workspace '/workspace'",
     True, "workspace guard")
case("pdf-13", "pdf-tools", "read_pdf_pages",
     "Error: No permission to read file '/workspace/x.pdf'", True,
     "audited template")

# ===========================================================================
# pptx
# ===========================================================================
case("pptx-01", "pptx", "add_slide",
     json.dumps({"message": "Added slide 1 with layout 1", "slide_index": 1,
                 "layout_name": "Title and Content", "presentation_id": "p1"}),
     False, "success dict")
case("pptx-02", "pptx", "manage_text",
     json.dumps({"message": "Renamed shape to 'error handler box'; text now "
                            "reads 'on error resume next'",
                 "presentation_id": "p1", "slide_index": 0}),
     False, "success whose message VALUE contains 'error' text", form="dict")
PPTX_EXTRACT = {
    "success": True,
    "presentation_id": "p1",
    "total_slides": 2,
    "slides_with_text": 1,
    "slides_text": [
        {"slide_index": 0,
         "text_content": {"all_text_combined": "Q3 results"},
         "has_title": True, "has_tables": False},
        {"slide_index": 1, "error": "Shape extraction failed: no text frame",
         "text_content": None},
    ],
}
case("pptx-03", "pptx", "extract_presentation_text", json.dumps(PPTX_EXTRACT),
     False, "top-level success:true with per-slide error entries nested inside")
case("pptx-04", "pptx", "get_presentation_info",
     json.dumps({"message": "Master 0 information", "master_index": 0,
                 "layouts": ["Title Slide", "Title and Content"]}), False,
     "master info success")
case("pptx-05", "pptx", "add_connector", json.dumps([{"error": "x"}]), False,
     "JSON array is not the error envelope")
case("pptx-06", "pptx", "get_slide_info",
     json.dumps({"result": {"error": "nested does not count"}}), False,
     "nested error key stays data", form="dict")
case("pptx-07", "pptx", "create_presentation",
     "Presentation created", False, "non-JSON text stays data")
case("pptx-08", "pptx", "add_connector", json.dumps({"error": 5}), False,
     "non-string error value is not the audited envelope (server always "
     "stringifies)")
# true positives: a dozen distinct templates
case("pptx-09", "pptx", "add_connector",
     json.dumps({"error": "Presentation not found"}), True, "template")
case("pptx-10", "pptx", "add_connector",
     json.dumps({"error": "Slide index 5 out of range"}), True, "template")
case("pptx-11", "pptx", "add_connector",
     json.dumps({"error": "Invalid connector type. Use: ['straight', 'elbow', "
                          "'curved']"}), True, "template", form="dict")
case("pptx-12", "pptx", "add_connector",
     json.dumps({"error": "Failed to add connector: division by zero"}), True,
     "template")
case("pptx-13", "pptx", "apply_professional_design",
     json.dumps({"success": False, "error": "name 'PP_ALIGN' is not defined"}),
     True, "design_utils failure envelope")
case("pptx-14", "pptx", "add_slide",
     json.dumps({"error": "Failed to add slide: list index out of range"}), True,
     "template")
case("pptx-15", "pptx", "manage_text",
     json.dumps({"error": "Shape at index 3 is not a text shape"}), True,
     "template", form="dict")
case("pptx-16", "pptx", "open_presentation",
     json.dumps({"error": "Failed to open presentation: Package not found at "
                          "'missing.pptx'"}), True, "template")
case("pptx-17", "pptx", "save_presentation",
     json.dumps({"error": "Failed to save presentation: [Errno 13] Permission "
                          "denied"}), True, "template")
case("pptx-18", "pptx", "add_chart",
     json.dumps({"error": "Invalid chart type: pie3d"}), True, "template")
case("pptx-19", "pptx", "add_image",
     json.dumps({"error": "Image file not found: logo.png"}), True, "template")
case("pptx-20", "pptx", "manage_slide_masters",
     json.dumps({"error": "Master index 9 out of range"}), True, "template",
     form="dict")

# ===========================================================================
# word — the hazardous one
# ===========================================================================
case("word-01", "word", "create_document",
     "Document report.docx created successfully", False, "success")
case("word-02", "word", "insert_header_near_text",
     "Header 'Intro' (style: Heading 1) inserted before the target paragraph.",
     False, "header insert success")
case("word-03", "word", "insert_header_near_text",
     "Header 'Intro' (style: Heading 1) inserted after paragraph (index 4).",
     False, "header insert success variant", form="dict")
case("word-04", "word", "add_paragraph",
     "Style 'Fancy' not found, paragraph added with default style to f.docx",
     False, "style-fallback message is a SUCCESS (paragraph was added)")
case("word-05", "word", "get_document_info",
     json.dumps({"title": "Report", "author": "boq", "word_count": 120,
                 "paragraph_count": 9}, indent=2), False,
     "json.dumps(indent=2) success of get_document_info")
# get_document_text: prefix-exempt raw document text
case("word-06", "word", "get_document_text",
     "Failed to submit homework\nMy dog ate the USB stick.\nSincerely, a student.",
     False, "raw doc text starting with 'Failed to ' (prefix-exempt)")
case("word-07", "word", "get_document_text",
     "Cannot modify document: draft\nThis is the opening line of my novel.",
     False, "raw doc text starting with 'Cannot modify document: '", form="dict")
case("word-08", "word", "get_document_text",
     "Invalid thoughts on Monday\nA poem in three parts.", False,
     "raw doc text starting with 'Invalid '")
case("word-09", "word", "get_document_text",
     "Document report.docx does not exist", True,
     "get_document_text single-line whole-payload error template")
case("word-10", "word", "get_document_text",
     "Document report.docx does not exist\nBut it did once, in a dream.", False,
     "first line coincides with the template but MORE lines follow -> data")
case("word-11", "word", "get_document_text",
     "Document report.docx does not exist\n", False,
     "trailing newline breaks the whole-payload match -> data "
     "(genuine template has no trailing newline)")
case("word-12", "word", "get_document_text",
     "Target paragraph not found in the wild\nAn essay about lost text.", False,
     "prefix-exempt tool: 'Target paragraph not found' head stays data")
case("word-13", "word", "get_document_text",
     "Failed to extract text: something\nsecond line of an odd document", False,
     "multi-line breaks the 'Failed to extract text' whole-payload regex")
# regexes apply to every word tool
case("word-14", "word", "add_paragraph",
     "Document notes.docx does not exist", True, "regex on non-exempt tool")
case("word-15", "word", "copy_document",
     "Document Notes.docx not found.", True, "not-found regex")
case("word-16", "word", "insert_header_near_text",
     "Header 'Summary' not found in document.", True, "header regex")
case("word-17", "word", "insert_header_near_text",
     "Header 'Summary' not found in documents everywhere\nsecond line", False,
     "regex requires the exact single-sentence payload", form="dict")
case("word-18", "word", "insert_line_or_paragraph_near_text",
     "Start anchor 'Intro' not found.", True, "start-anchor regex")
case("word-19", "word", "remove_paragraph_block",
     "Start anchor 'Intro' not found after deletion (unexpected).", True,
     "start-anchor regex (prefix form, no \\Z)")
case("word-20", "word", "list_available_documents",
     "Directory /docs does not exist", True, "directory regex")
case("word-21", "word", "list_available_documents",
     "Directory /docs does not exist\nCreating it now.", False,
     "multi-line breaks the directory regex")
case("word-22", "word", "get_document_text",
     "Failed to extract text: file is corrupt", True,
     "whole-payload extract-failure regex applies even to the exempt tool")
# prefix true positives
case("word-23", "word", "create_document",
     "Failed to create document: Permission denied", True, "prefix")
case("word-24", "word", "add_heading",
     "Cannot modify document: document is protected with a password. Consider "
     "creating a copy first or creating a new document.", True, "prefix",
     form="dict")
case("word-25", "word", "add_heading",
     "Invalid heading level: 12. Level must be between 1 and 9.", True, "prefix")
case("word-26", "word", "add_heading",
     "Invalid parameter: level must be an integer between 1 and 9", True,
     "prefix")
case("word-27", "word", "create_custom_style",
     "Cannot create document: path already exists", True, "prefix")
case("word-28", "word", "protect_document",
     "Cannot protect document: protection features unavailable", True, "prefix")
case("word-29", "word", "convert_to_pdf",
     "Cannot create PDF: output path invalid", True, "prefix")
case("word-30", "word", "convert_to_pdf",
     "PDF conversion not supported on this platform. Please install LibreOffice.",
     True, "prefix", form="dict")
case("word-31", "word", "insert_paragraph_near_text",
     "Target paragraph not found. Checked text and style anchors.", True,
     "prefix")
case("word-32", "word", "find_text_in_document",
     "Search text cannot be empty", True, "prefix")
case("word-33", "word", "add_picture",
     "Image file not found: /workspace/logo.png", True, "prefix")
case("word-34", "word", "add_picture",
     "Image file appears to be empty: /workspace/logo.png", True, "prefix")
case("word-35", "word", "add_picture",
     "Error checking image file: [Errno 13] Permission denied", True, "prefix")
case("word-36", "word", "merge_documents",
     "Document processing error: styles.xml missing", True, "prefix",
     form="dict")
case("word-37", "word", "add_paragraph",
     "Failed to add paragraph: unexpected end of data", True, "prefix")
# comment-tools JSON errors (FastMCP serializes dict with indent=2)
case("word-38", "word", "get_all_comments",
     '{\n  "error": "Document report.docx does not exist"\n}', True,
     "comment-tool JSON error, indent=2")
case("word-39", "word", "add_comment",
     '{\n  "success": false,\n  "error": "Paragraph index out of range"\n}',
     True, "comment-tool success:false envelope")
case("word-40", "word", "get_all_comments",
     '{"error": "compact form"}', False,
     "compact JSON error head is NOT an audited word template (deployed "
     "serializer always uses indent=2) -> per rules stays data")
# more word successes that brush against templates
case("word-41", "word", "copy_document",
     "Document copied to report_v2.docx", False, "copy success")
case("word-42", "word", "get_document_outline",
     json.dumps({"headings": [{"text": "Invalid inputs", "level": 2}]}, indent=2),
     False, "outline JSON whose heading text starts with 'Invalid'")
case("word-43", "word", "get_document_text",
     "Cannot create document: a memoir\nChapter 1\nIt was a dark night.", False,
     "raw doc text starting with 'Cannot create document: '")
case("word-44", "word", "get_document_text",
     "Error checking image file: draft caption ideas\n- one\n- two", False,
     "raw doc text starting with 'Error checking image file: '", form="dict")
case("word-45", "word", "add_paragraph",
     "Paragraph added to report.docx", False, "plain success")

case("word-46", "word", "convert_to_pdf",
     "Document successfully converted to PDF: report.pdf", False,
     "convert success (head 'Document ' shared with error templates)")
case("word-47", "word", "convert_to_pdf",
     "Failed to convert document to PDF: soffice not found\n"
     "Note: docx2pdf requires Microsoft Word to be installed.", True,
     "multi-line 'Failed to ' error still caught by anchored prefix")
case("rail-20", "rail_12306", "get-station-code-of-citys", "{}", False,
     "empty map is not an all-failed map")
case("pptx-21", "pptx", "add_connector", json.dumps({"error": ""}), True,
     "empty str(e) from a bare Exception is still the error envelope "
     "(function returns '' which is non-None)")

# ===========================================================================
# cross-cutting shape / scoping cases
# ===========================================================================
case("shape-01", "word",
     "add_paragraph",
     mk_dict("Failed to add paragraph: boom") if False else
     {"content": [{"type": "text", "text": "Failed to add paragraph: boom"},
                  {"type": "text", "text": "second block"}]},
     False, "two text blocks -> not a single-text-block result, never inspected")
case("shape-02", "rail_12306", "get-tickets",
     {"content": []}, False, "empty content list -> no text block -> data")
case("shape-03", "pdf-tools", "read_pdf_pages",
     {"content": [{"type": "image", "data": "aGk=", "mimeType": "image/png"}]},
     False, "non-text block -> data")
case("shape-04", "notion", "API-retrieve-a-page",
     {"content": [{"type": "text", "text": None}]}, False,
     "non-string text -> data")
case("shape-05", "canvas", "list_courses",
     "Error: something exploded", False,
     "server with no audited rules at all is untouched")
case("shape-06", "word", "get_document_text",
     "", False, "empty raw document text stays data")
if HAVE_MCP:
    case("shape-07", "k8s", "kubectl_scale",
         CallToolResult(content=[
             TextContent(type="text", text="Failed to scale resource: x"),
             TextContent(type="text", text="extra"),
         ]), False, "CallToolResult with two blocks never inspected")


# ===========================================================================
# runner
# ===========================================================================
def main():
    n_pass = 0
    fp = 0  # classifier said error, we expected data
    fn = 0  # classifier said data, we expected error
    for case_id, server, tool, result, expect_error, note in CASES:
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
        text = None
        try:
            content = result.get("content") if isinstance(result, dict) \
                else getattr(result, "content", None)
            if content and len(content) >= 1:
                blk = content[0]
                text = blk.get("text") if isinstance(blk, dict) \
                    else getattr(blk, "text", None)
        except Exception:
            pass
        print(f"FAIL [{case_id}] {kind} server={server!r} tool={tool!r}")
        print(f"     note: {note}")
        print(f"     payload: {text!r}")
        print(f"     expected {'ERROR' if expect_error else 'DATA'}, "
              f"classifier returned {got!r}")
    total = len(CASES)
    print(f"SETC: {n_pass}/{total} passed, {fp} false positives, "
          f"{fn} false negatives")


if __name__ == "__main__":
    main()
