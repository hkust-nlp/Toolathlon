## Unified Format Description

Each data entry contains the following fields:
- `conversation_id`: Format as `{source}_{index}`, where source is the dataset name and index is the sequential number starting from 0 in the original dataset
- `messages`: List of messages, each message contains:
  - `role`: Possible values: `system`/`user`/`assistant`/`tool`
  - `content`: Message content
  - `tool_calls`: (assistant role only) List of tool calls, each containing `id` (format: `tool_call_{n}`, where n increments sequentially from 0 throughout the entire conversation), `name`, `arguments`
  - `tool_call_id`: (tool role only) Corresponding tool call ID
- `tools`: List of tool definitions

## Important Notes
- If the system message only contains the toolset and instructions on how to use tools, please remove the system message from that dataset and keep only the conversation starting from user and the toolset
- If assistant only made tool calls, its content should be null
- Do not add tool return results or assistant replies that do not exist in the original data

## Unified Format JSON Sample

```json
{
  "conversation_id": "dataset1_0",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "What's the weather in Beijing? Also, what time is it there?"
    },
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "tool_call_0",
          "name": "get_weather",
          "arguments": {"city": "Beijing"}
        },
        {
          "id": "tool_call_1",
          "name": "get_time",
          "arguments": {"timezone": "Asia/Shanghai"}
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "tool_call_0",
      "content": "{\"temperature\": 25, \"condition\": \"sunny\"}"
    },
    {
      "role": "tool",
      "tool_call_id": "tool_call_1",
      "content": "{\"time\": \"14:30\", \"date\": \"2024-03-15\"}"
    },
    {
      "role": "assistant",
      "content": "In Beijing, the weather is sunny with 25°C, and the current time is 14:30 (2:30 PM) on March 15, 2024."
    }
  ],
  "tools": [
    {
      "name": "get_weather",
      "description": "Get weather information",
      "parameters": {
        "type": "object",
        "properties": {
          "city": {"type": "string", "description": "City name"}
        },
        "required": ["city"]
      }
    },
    {
      "name": "get_time",
      "description": "Get current time for a specific timezone",
      "parameters": {
        "type": "object",
        "properties": {
          "timezone": {"type": "string", "description": "Timezone identifier (e.g., 'Asia/Shanghai')"}
        },
        "required": ["timezone"]
      }
    }
  ]
}
```