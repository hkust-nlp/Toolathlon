有次调用gpt5nano的时候出现以下情况。注意这个不是代码错误，而且agent使用非管理员的账号调用了越权的工具，导致以下log。这是mcp-server的问题，我认为也无伤大雅。


>>调用工具 canvas-canvas_get_dashboard
>>调用工具 canvas-canvas_get_upcoming_assignments
[Canvas MCP] Executing tool: canvas_get_dashboard
[Canvas API] GET /users/self/dashboard
[Canvas MCP] Executing tool: canvas_get_upcoming_assignments
[Canvas API] GET /users/self/upcoming_events
[Canvas API] Error response: 404, Content-Type: text/html; charset=utf-8, Data type: string
Error executing tool canvas_get_dashboard: CanvasAPIError: Canvas API Error (404): <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Action Controller: Exception caught</title>
  <style>
    body {
      background-color: #FAFAFA;
      color: #333;
      m...
    at file:///ssddata/xiaochen/.cache/npm/_npx/98d39e1a0eb3664e/node_modules/canvas-mcp-server/build/client.js:89:23
    at process.processTicksAndRejections (node:internal/process/task_queues:105:5)
    at async Axios.request (file:///ssddata/xiaochen/.cache/npm/_npx/98d39e1a0eb3664e/node_modules/axios/lib/core/Axios.js:40:14)
    at async CanvasClient.getDashboard (file:///ssddata/xiaochen/.cache/npm/_npx/98d39e1a0eb3664e/node_modules/canvas-mcp-server/build/client.js:356:26)
    at async file:///ssddata/xiaochen/.cache/npm/_npx/98d39e1a0eb3664e/node_modules/canvas-mcp-server/build/index.js:1190:43 {
  statusCode: 404,
  response: '<!DOCTYPE html>\n' +
    '<html lang="en">\n' +
    '<head>\n' +
    '  <meta charset="utf-8" />\n' +
    '  <title>Action Controller: Exception caught</title>\n' +
    '  <style>\n' +
    '    body {\n' +
    '      background-color: #FAFAFA;\n' +
    '      color: #333;\n' +
    '      margin: 0px;\n' +
    '    }\n' +
    '\n' +
    '    body, p, ol, ul, td {\n' +
    '      font-family: helvetica, verdana, arial, sans-serif;\n' +
    '      font-size:   13px;\n' +
    '      line-height: 18px;\n' +
    '    }\n' +
    '\n' +
    '    pre {\n' +
    '      font-size: 11px;\n' +
    '      white-space: pre-wrap;\n' +
    '    }\n' +
    '\n' +
    '    pre.box {\n' +
    '      border: 1px solid #EEE;\n' +
    '      padding: 10px;\n' +
    '      margin: 0px;\n' +
    '      width: 958px;\n' +
    '    }\n' +
    '\n' +
    '    header {\n' +
    '      color: #F0F0F0;\n' +
    '      background: #C52F24;\n' +