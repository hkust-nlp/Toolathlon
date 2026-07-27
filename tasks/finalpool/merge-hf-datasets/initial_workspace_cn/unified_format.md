## 统一格式描述

每条数据包含以下字段：
- `conversation_id`: 格式为`{source}_{index}`，source为数据集名称，index为从0开始的在原始数据集中的序号
- `messages`: 消息列表，每条消息包含：
  - `role`: 可选值：`system`/`user`/`assistant`/`tool`
  - `content`: 消息内容
  - `tool_calls`: (仅assistant角色) 工具调用列表，每个包含`id`(格式为`tool_call_{n}`, n从0开始在整段对话内依次递增)、`name`、`arguments`
  - `tool_call_id`: (仅tool角色) 对应的工具调用ID
- `tools`: 工具定义列表

## 工具参数转换规则

- 每个工具的 `parameters` 必须表示为包含 `type`、`properties` 和 `required` 的 JSON Schema 风格对象。
- 当源数据集使用平铺参数映射时（例如 XLAM），将每个源参数放入 `properties`。
- 满足以下任一条件的参数均为可选参数，不得出现在 `required` 中：
  - 源参数包含显式的 `default` 键，包括其值为 `null` 的情况。
  - 参数以逗号分隔的 `type` 标注中包含不区分大小写的 `optional` 标记（例如 `str, optional`）。
- 其余参数都必须按源参数顺序加入 `required`；没有必填参数时使用空列表。
- 必须先判断参数是否可选，再规范化源数据中的类型别名。不要根据参数描述中的自然语言推断参数是否可选。

## 注意事项
- 如果system只包含了工具集与应该怎样使用工具的指导，则该数据集请去除system，只保留从user开始的对话和工具集
- 如果assistant只调用了工具，则其content为null
- 请不要添加原数据中不存在的工具返回结果或assistant回复

## 统一格式JSON样本

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
